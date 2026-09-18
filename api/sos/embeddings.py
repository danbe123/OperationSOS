"""Semantic search over the box's own library (the Gutenberg design, section 8, phase 2; built 2026-09-18).

A keyword index finds "tinned food" only where those words are; a household asks "how long does canned food
keep". The box's own guidance — the guides, the quick cards, the modules, the pages, and every page of its
converted documents, some 21,000 passages in `fts_docs` — is embedded once on the PC (`sos build-embeddings`)
with bge-small-en-v1.5 (384 dimensions, 37 MB at q8_0), served by the same llama-server the assistant uses,
on a second port with `--embedding`. On the box a query is embedded (about 25 ms), a brute-force cosine over
the in-memory matrix picks the nearest passages (about 5 ms for 21,000 x 384 in numpy), and `search.py` fuses
them with the keyword results. If the model, the server or the vector files are absent, all of this is
silently off and search is the keyword search.

bge-small was trained with an instruction on the query side only: every query is prefixed with
`QUERY_PREFIX`; the passages are not. Getting that backwards produces no error, just worse retrieval."""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable, Optional

import httpx
import numpy as np

from sos.config import Settings

log = logging.getLogger(__name__)

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
DIMS = 384
# The PC-only, GPU-accelerated second build (install/build-llama-cuda.sh) for bulk embedding of the
# household book collection and Wikipedia: too large to embed on CPU in any reasonable time. A name
# distinct from the plain `llama-server` already on PATH, so neither shadows the other.
CUDA_LLAMA_SERVER = Path.home() / ".local" / "bin" / "llama-server-cuda"
PASSAGE_CHARS = 2584      # bge-small errors past 510 content tokens on this build (512-token context minus
                          # two special tokens) rather than truncating silently: measured by posting real
                          # prose of increasing length to a live llama-server and watching success flip to a
                          # 500 "too large to process" between 2584 and 2585 characters (see docs/superpowers/
                          # plans/2026-09-18-semantic-search-expansion.md Task 1) -- the real window, not a
                          # token:char estimate. A passage heavy with numbers tokenises much denser (measured
                          # as low as ~700 chars for the same 510-token ceiling on real doc content) and still
                          # relies on embed_batch's reactive shortening below.
SHORTEST_CHARS = 200
BATCH = 32
_TOKENS = re.compile(r"\[\[[^\]]*\]\]|\{\{[^}]*\}\}")   # the template directives the guides carry
_SPACE = re.compile(r"\s+")


class EmbedError(RuntimeError):
    """The embedding server is unreachable, not ready, or answered with something that is not vectors."""


def passage_text(title: str, body: str, url: str = "") -> str:
    """What one passage says to the model: its title, then its words, template tokens gone, cut to the
    window. The section heading the words open with ("What to do", "Key facts") is furniture shared by every
    module and card, and a question that begins "what to do if" must not find it: it goes."""
    from .search import strip_heading
    text = _SPACE.sub(" ", _TOKENS.sub(" ", f"{title or ''}. {strip_heading(body, url)}")).strip()
    return text[:PASSAGE_CHARS]


# A page's "Go deeper" and a card's "Source" are lists of other titles: nothing to mean.
SKIP_SECTIONS = ("go-deeper", "source")


def _vectors_from(payload) -> np.ndarray:
    """llama-server answers `/embeddings` with a list of {index, embedding} (or, OpenAI-style, {data: [...]})."""
    rows = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise EmbedError("no embeddings in the reply")
    out = []
    for row in rows:
        vec = row.get("embedding") if isinstance(row, dict) else row
        if isinstance(vec, list) and vec and isinstance(vec[0], list):
            vec = vec[0]
        out.append(vec)
    arr = np.asarray(out, dtype=np.float32)
    if arr.ndim != 2 or arr.shape[1] != DIMS:
        raise EmbedError(f"expected {DIMS}-dimensional vectors, got shape {arr.shape}")
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


class EmbedClient:
    """Talks to a llama-server started with `--embedding`."""

    def __init__(self, url: str, timeout: float = 30.0):
        self.url = url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def healthy(self, timeout: float = 0.5) -> bool:
        try:
            r = await self._client.get(f"{self.url}/health", timeout=timeout)
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def embed(self, texts: list[str], timeout: Optional[float] = None) -> np.ndarray:
        try:
            r = await self._client.post(f"{self.url}/embeddings", json={"input": texts}, timeout=timeout or self.timeout)
        except httpx.HTTPError as exc:
            raise EmbedError(f"embedding server unreachable: {exc}") from exc
        if r.status_code != 200:
            raise EmbedError(f"embedding server returned {r.status_code}")
        return _vectors_from(r.json())

    async def aclose(self) -> None:
        await self._client.aclose()


def embed_sync(url: str, texts: list[str], timeout: float = 120.0) -> np.ndarray:
    """The build's blocking call: one batch of passages to vectors."""
    try:
        r = httpx.post(f"{url.rstrip('/')}/embeddings", json={"input": texts}, timeout=timeout)
    except httpx.HTTPError as exc:
        raise EmbedError(f"embedding server unreachable: {exc}") from exc
    if r.status_code != 200:
        raise EmbedError(f"embedding server returned {r.status_code}")
    return _vectors_from(r.json())


class Index:
    """The passages' vectors in memory, keyed by the `fts_docs` url of each (a url survives a re-index; a
    rowid does not). `search` is a dot product over unit vectors: the cosine, with the query unit too."""

    def __init__(self, vectors: np.ndarray, keys: list[str], meta: Optional[dict] = None):
        self.vectors = vectors.astype(np.float32, copy=False)
        self.keys = keys
        self.meta = meta or {}

    def __len__(self) -> int:
        return len(self.keys)

    @classmethod
    def load(cls, folder: Path, collection: str) -> Optional["Index"]:
        folder = Path(folder)
        vec_path, key_path, meta_path = folder / f"{collection}.f16.bin", folder / f"{collection}.ids", folder / f"{collection}.meta.json"
        if not (vec_path.is_file() and key_path.is_file()):
            return None
        keys = [line for line in key_path.read_text(encoding="utf-8").split("\n") if line]
        raw = np.fromfile(vec_path, dtype=np.float16)
        if len(keys) == 0 or raw.size != len(keys) * DIMS:
            log.warning("embeddings: %s does not match %s (%d keys, %d values)", vec_path.name, key_path.name, len(keys), raw.size)
            return None
        meta = {}
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except ValueError:
                meta = {}
        return cls(raw.reshape(len(keys), DIMS), keys, meta)

    def search(self, query: np.ndarray, k: int = 20) -> list[tuple[str, float]]:
        if len(self.keys) == 0:
            return []
        q = np.asarray(query, dtype=np.float32).reshape(-1)
        scores = self.vectors @ q
        k = max(1, min(k, len(scores)))
        top = np.argpartition(-scores, k - 1)[:k]
        top = top[np.argsort(-scores[top])]
        return [(self.keys[i], float(scores[i])) for i in top]


class ApproxIndex:
    """One vector per book/article across the household collection (Gutenberg, Survivor Library):
    tens of thousands of vectors, an approximate (not exact) nearest-neighbour search via hnswlib,
    because the collection is expected to keep growing and a brute-force scan is the wrong shape for
    that even though it would still be fast today at this size. cosine similarity, matching Index's
    contract exactly, so search.py's fusion code does not need to know which kind of index it has."""

    def __init__(self, hnsw, keys: list[str]):
        self._hnsw = hnsw
        self.keys = keys

    def __len__(self) -> int:
        return len(self.keys)

    @classmethod
    def build(cls, vectors: np.ndarray, keys: list[str], ef_construction: int = 200, m: int = 16) -> "ApproxIndex":
        import hnswlib
        vectors = np.asarray(vectors, dtype=np.float32)
        hnsw = hnswlib.Index(space="cosine", dim=DIMS)
        hnsw.init_index(max_elements=len(keys), ef_construction=ef_construction, M=m)
        hnsw.add_items(vectors, np.arange(len(keys)))
        hnsw.set_ef(max(50, ef_construction // 2))
        return cls(hnsw, keys)

    def save(self, folder: Path, collection: str) -> None:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        hnsw_part = folder / f"{collection}.hnsw.part"
        self._hnsw.save_index(str(hnsw_part))
        ids_part = folder / f"{collection}.ids.part"
        ids_part.write_text("\n".join(self.keys) + "\n", encoding="utf-8")
        os.replace(hnsw_part, folder / f"{collection}.hnsw")
        os.replace(ids_part, folder / f"{collection}.ids")

    @classmethod
    def load(cls, folder: Path, collection: str) -> Optional["ApproxIndex"]:
        import hnswlib
        folder = Path(folder)
        hnsw_path, ids_path = folder / f"{collection}.hnsw", folder / f"{collection}.ids"
        if not (hnsw_path.is_file() and ids_path.is_file()):
            return None
        keys = [line for line in ids_path.read_text(encoding="utf-8").split("\n") if line]
        hnsw = hnswlib.Index(space="cosine", dim=DIMS)
        hnsw.load_index(str(hnsw_path), max_elements=len(keys))
        hnsw.set_ef(max(50, len(keys) // 2) if len(keys) < 100 else 100)
        return cls(hnsw, keys)

    def search(self, query: np.ndarray, k: int = 20) -> list[tuple[str, float]]:
        if len(self.keys) == 0:
            return []
        k = max(1, min(k, len(self.keys)))
        labels, distances = self._hnsw.knn_query(np.asarray(query, dtype=np.float32).reshape(1, -1), k=k)
        # hnswlib's "cosine" space returns a distance (1 - cosine); this class's contract is a similarity.
        return [(self.keys[i], float(1.0 - d)) for i, d in zip(labels[0], distances[0])]


class WikipediaStore:
    """8,425,865 real Wikipedia article vectors -- the ZIM's own real, non-redirect entries (16,643,476,
    reader.paths()) minus the 8,217,611 of them that are images, thumbnails and SVGs under `_assets_/`,
    never articles. Measured against the real wikipedia_en_all_maxi.zim on disk (Task 8, docs/app-
    completion.md, dated 2026-09-18) -- not this plan's earlier "~7 million" guess, which turned out to
    be roughly 20 per cent low, and close only because a real ~17-18 per cent of these entries are "soft
    redirect" stubs (title said twice in under a hundred characters; the same spot check) that a real
    build leaves as zero vectors rather than embedding for real. A THIRD kind of vector store, unlike
    Index (exact search) and ApproxIndex (approximate search): there is no `.search()` here at all, only
    `vector_for(key)`, because an 8GB Pi running kiwix-serve, the kiosk, sos-api and the chat model
    together cannot afford 6+GB of Wikipedia vectors in RAM, and 8.4 million rows is the wrong shape for
    a nearest-neighbour index anyway when the only real use (Task 9) is reranking hits Wikipedia's own
    keyword search already found -- never finding a row by meaning alone.

    Keys are sorted once at build time so a lookup is a binary search over an in-memory list of strings:
    roughly 8.4 million short strings, each perhaps 90-110 bytes all in (a Wikipedia title, mostly
    20-30 ASCII bytes, plus CPython's own ~50-80 bytes of per-string object overhead) -- on the order of
    750 MB to 900 MB. That figure is an estimate from the real key count, not a measurement: Task 10's
    real acceptance run on an actual 8GB Pi should measure it for real. Real but affordable regardless,
    unlike materialising every vector too; only the one row actually asked for is paged in from disk."""

    def __init__(self, mmap: np.memmap, keys: list[str]):
        self._mmap = mmap
        self.keys = keys  # sorted

    def __len__(self) -> int:
        return len(self.keys)

    @classmethod
    def load(cls, folder: Path, collection: str = "wikipedia") -> Optional["WikipediaStore"]:
        folder = Path(folder)
        vec_path, key_path = folder / f"{collection}.f16.bin", folder / f"{collection}.ids"
        if not (vec_path.is_file() and key_path.is_file()):
            return None
        # A real, if temporary, memory-doubling moment worth flagging for Task 10's Pi measurement: for the
        # instant between these two expressions, both the raw ~200+ MB string and the list split from it
        # are alive at once, before the raw string's last reference (the .split() call itself) is dropped.
        keys = [line for line in key_path.read_text(encoding="utf-8").split("\n") if line]
        if not keys:
            return None
        mmap = np.memmap(vec_path, dtype=np.float16, mode="r", shape=(len(keys), DIMS))
        return cls(mmap, keys)

    def vector_for(self, key: str) -> Optional[np.ndarray]:
        import bisect
        i = bisect.bisect_left(self.keys, key)
        if i == len(self.keys) or self.keys[i] != key:
            return None
        return np.asarray(self._mmap[i], dtype=np.float32)


def _write_meta(folder: Path, collection: str, meta: dict) -> None:
    """One collection's meta.json, staged beside its final name and renamed into place -- the same
    atomic pattern write_index uses for the vectors and keys, shared here so it is written exactly
    once, however the vectors themselves were built (the exact Index or the approximate one)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    part = folder / f"{collection}.meta.json.part"
    part.write_bytes(json.dumps(meta, indent=1).encode("utf-8"))
    os.replace(part, folder / f"{collection}.meta.json")


def write_index(folder: Path, collection: str, vectors: np.ndarray, keys: list[str], meta: dict) -> None:
    """The three files for one named collection, written beside their finals and moved into place
    together, so a build that dies halfway leaves the old index whole."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    parts = []
    for name, data in ((f"{collection}.f16.bin", np.asarray(vectors, dtype=np.float16).tobytes()),
                       (f"{collection}.ids", ("\n".join(keys) + "\n").encode("utf-8"))):
        part = folder / (name + ".part")
        part.write_bytes(data)
        parts.append((part, folder / name))
    for part, final in parts:
        os.replace(part, final)
    _write_meta(folder, collection, meta)


def embed_batch(embed: Callable[[list[str]], np.ndarray], texts: list[str]) -> np.ndarray:
    """A batch of passages to vectors; a batch the server refuses (one passage past its window, which the
    character cut cannot promise against) is embedded one at a time, each shortened until it goes in."""
    try:
        return embed(texts)
    except EmbedError:
        rows = []
        for text in texts:
            cut = text
            while True:
                try:
                    rows.append(embed([cut])[0])
                    break
                except EmbedError:
                    if len(cut) <= SHORTEST_CHARS:
                        raise
                    cut = cut[: max(SHORTEST_CHARS, len(cut) // 2)]
        return np.stack(rows)


def build(conn, settings: Settings, embed: Callable[[list[str]], np.ndarray], out: Callable = print) -> dict:
    """Embed every passage of the box's own library and write the index. `embed` takes a batch of texts."""
    rows = [r for r in conn.execute("SELECT url, title, body FROM fts_docs WHERE kind != 'item' ORDER BY rowid").fetchall()
            if r["url"].split("#", 1)[-1] not in SKIP_SECTIONS]
    keys: list[str] = []
    chunks: list[np.ndarray] = []
    t0 = time.perf_counter()
    for start in range(0, len(rows), BATCH):
        batch = rows[start:start + BATCH]
        texts = [passage_text(r["title"], r["body"], r["url"]) for r in batch]
        chunks.append(embed_batch(embed, texts))
        keys.extend(r["url"] for r in batch)
        done = start + len(batch)
        if done % (BATCH * 25) == 0 or done == len(rows):
            out(f"embedded {done} of {len(rows)} passages ({time.perf_counter() - t0:.0f} s)")
    vectors = np.concatenate(chunks) if chunks else np.zeros((0, DIMS), dtype=np.float32)
    meta = {"model": settings.embed_model, "dims": DIMS, "count": len(keys), "prefix": QUERY_PREFIX,
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    write_index(settings.embeddings_dir, "docs", vectors, keys, meta)
    out(f"wrote {len(keys)} vectors to {settings.embeddings_dir}")
    return meta


# --- the household collection: one vector per book across Gutenberg and Survivor Library --------------------

HOUSEHOLD_ZIMS = ("gutenberg_en_all", "survivorlibrary.com_en_all")
HOUSEHOLD_TEXT_CHARS = PASSAGE_CHARS      # the same real safe window Task 1 measured -- one model, one window

# Gutenberg's real book article (confirmed against the live ZIM, Task 5): `<title slug>.<id>`, no extension --
# the epub (`<slug>.<id>.epub`), the covers (`covers/<id>_cover_image.jpg`/`.webp`) and the odd per-book
# auxiliary file (`30282_glossary.html`) all end in something other than a bare number, so this one pattern
# picks out exactly the real articles without reading the catalogue a second time.
_GUTENBERG_ARTICLE = re.compile(r"^([^/]+)\.(\d+)$")
# Survivor Library is a zimit crawl of the live WordPress site, not a book-scraper ZIM: it has no catalogue
# entry and no per-book HTML article at all. Its ~11,800 real books are plain PDF entries at this one path
# shape (Task 5's real finding); everything else in the crawl (theme assets, blog pages, category pages) is not.
_SURVIVOR_BOOK = re.compile(r"^www\.survivorlibrary\.com/library/(.+)\.pdf$", re.I)


def _gutenberg_text(html_bytes: bytes) -> str:
    from sos.kiwix import extract_text

    return " ".join(extract_text(html_bytes.decode("utf-8", errors="replace")))


def _pdf_text(pdf_bytes: bytes) -> str:
    """A Survivor Library entry's raw PDF bytes to plain text, via the box's own pdftotext wrapper
    (api/sos/reflow.py's run_pdftotext) -- reader.read() hands back bytes, not a file on disk, so they
    are staged to a temporary file first and removed once pdftotext has read it. About a fifth of this
    collection is a pure page-image scan with no text layer at all (Task 5's real finding, confirmed
    with pypdf against 25 sampled entries): that is not an error, just nothing to embed, so a pdftotext
    failure on a corrupt or malformed PDF is swallowed the same way -- both come back as an empty string,
    which build_household's own SHORTEST_CHARS check then skips like any other too-short book."""
    from sos.reflow import run_pdftotext

    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(pdf_bytes)
        tmp.flush()
        try:
            return run_pdftotext(Path(tmp.name))
        except (OSError, subprocess.CalledProcessError) as exc:
            log.warning("household: pdftotext could not read a Survivor Library entry: %s", exc)
            return ""


def _household_entries(reader, zim_id: str) -> list[tuple[str, str, str]]:
    """(key, title, plain text) for every real book this ZIM's reader holds, found by walking its
    entries with `reader.paths()` and matching each collection's own real, confirmed entry-naming
    convention (Task 5's diagnostic) -- there is no catalogue to read for Survivor Library the way
    Gutenberg has `full_by_popularity.js`, so both collections are found the same way, by their paths,
    rather than Gutenberg alone getting a shortcut the other collection cannot have.

    The two collections' entries are different shapes and need different extraction: Gutenberg's article
    is genuine HTML (kiwix.extract_text), Survivor Library's book is a PDF (pdftotext via a temp file).
    Each entry is fully extracted here, not just named, so build_household's own loop only has to cut
    and skip on the length of real text it already has."""
    out: list[tuple[str, str, str]] = []
    for path in reader.paths():
        if zim_id == "gutenberg_en_all":
            m = _GUTENBERG_ARTICLE.match(path)
            if not m:
                continue
            slug, book_id = m.group(1), m.group(2)
            raw = reader.read(path)
            if not raw:
                continue
            out.append((f"{zim_id}:{book_id}", slug, _gutenberg_text(raw)))
        else:
            m = _SURVIVOR_BOOK.match(path)
            if not m:
                continue
            slug = m.group(1)
            raw = reader.read(path)
            if not raw:
                continue
            title = re.sub(r"[-_]+", " ", slug).strip()
            out.append((f"{zim_id}:{slug}", title, _pdf_text(raw)))
    return out


def build_household(conn, settings: Settings, embed: Callable[[list[str]], np.ndarray],
                    open_zim=None, out: Callable = print) -> dict:
    """Embed one vector per real book across the household collections (Project Gutenberg, Survivor
    Library) and write the "household" ApproxIndex -- a second, parallel build to `build()`'s, because
    these collections have no SQL table the way the box's own library has `fts_docs`: they are read
    straight from their ZIMs on disk. A ZIM the box does not have (not downloaded, or simply not on
    this machine) is a no-op for that collection, exactly as `index_books` already treats a missing
    Gutenberg ZIM -- the household build carries on with whatever collections it can reach."""
    from sos.books import open_zim as real_open_zim
    open_zim = open_zim or real_open_zim
    keys: list[str] = []
    chunks: list[np.ndarray] = []
    t0 = time.perf_counter()
    total_seen = total_skipped = 0
    for zim_id in HOUSEHOLD_ZIMS:
        row = conn.execute("SELECT available, local_path FROM library_items WHERE id=?", (zim_id,)).fetchone()
        if row is None or not row["available"] or not row["local_path"]:
            out(f"household: {zim_id} is not on the box; skipped")
            continue
        reader = open_zim(Path(row["local_path"]))
        entries = _household_entries(reader, zim_id)
        before = len(keys)
        for start in range(0, len(entries), BATCH):
            batch = entries[start:start + BATCH]
            texts, batch_keys = [], []
            for key, title, text in batch:
                total_seen += 1
                plain = text[:HOUSEHOLD_TEXT_CHARS]
                if len(plain) < SHORTEST_CHARS:
                    total_skipped += 1
                    continue
                texts.append(f"{title}. {plain}")
                batch_keys.append(key)
            if not texts:
                continue
            chunks.append(embed_batch(embed, texts))
            keys.extend(batch_keys)
        out(f"household: {zim_id} done, {len(keys) - before} books ({len(keys)} so far)")
    vectors = np.concatenate(chunks) if chunks else np.zeros((0, DIMS), dtype=np.float32)
    if keys:
        idx = ApproxIndex.build(vectors, keys)
        idx.save(settings.embeddings_dir, "household")
    meta = {"model": settings.embed_model, "dims": DIMS, "count": len(keys), "seen": total_seen,
            "skipped_no_text": total_skipped, "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    _write_meta(settings.embeddings_dir, "household", meta)
    out(f"household: wrote {len(keys)} vectors ({time.perf_counter() - t0:.0f}s, {total_skipped} skipped for no usable text)")
    return meta


# --- Wikipedia: rerank-only vectors for the box's existing keyword search hits, never a nearest-neighbour
# index of its own (Task 8, semantic-search-expansion plan) -------------------------------------------------

CHECKPOINT_BATCHES = 200  # write a resume checkpoint every this-many batches -- frequent enough that an
                          # interrupted multi-hour build loses minutes, not hours, of already-done work
WIKIPEDIA_ZIM = "wikipedia_en_all_maxi"
# The modern mwoffliner "maxi" ZIM layout (confirmed against the real 2026-02-15 ZIM on disk, Task 8's own
# investigation, docs/app-completion.md) keeps every image, thumbnail and SVG under this one prefix --
# 8,217,611 of the ZIM's 16,643,476 real, non-redirect entries. There is no separate CSS or JS entry at
# all in this ZIM (unlike an old-style zimit crawl): Wikipedia even has real articles literally titled
# ".com" or "Favicon", which a naive filename-extension filter would wrongly throw away.
_WIKIPEDIA_ASSET_PREFIX = "_assets_/"


def _wikipedia_article_keys(reader):
    """Every real Wikipedia article path. reader.paths() (api/sos/books.py) already walks the archive
    skipping structural redirects (Task 6); the one further, cheap, path-only filter this ZIM's real
    layout needs is dropping its image/media entries, all under _WIKIPEDIA_ASSET_PREFIX. Everything left
    is genuine article-shaped content (an article, a list, a portal subpage) -- a real minority of it is
    itself a "soft redirect" stub (a real, non-structural-redirect entry whose body is just its own title
    said twice in under a hundred characters of markup: Task 8's spot check of 40 random real entries
    found 7, all well under SHORTEST_CHARS once extracted, against a smallest genuine article's 244
    characters). build_wikipedia_rerank's own SHORTEST_CHARS check catches those during the real build --
    the same mechanism build_household already relies on for near-empty extracted text -- so this
    function does not try to open every entry and check for a second time here."""
    for path in reader.paths():
        if not path.startswith(_WIKIPEDIA_ASSET_PREFIX):
            yield path


def _wikipedia_article_text(reader, key: str) -> str:
    """One article's title and plain text, cut to the model's real safe window -- the same shape build()
    and build_household() already give their own passages. A key this function cannot read back (should
    not happen for a path reader.paths() itself just yielded) or a "soft redirect" stub comes back short;
    build_wikipedia_rerank's own SHORTEST_CHARS check treats both the same way: skipped, not a crash."""
    from sos.kiwix import extract_text
    title = key.replace("_", " ")
    raw = reader.read(key)
    if not raw:
        return title
    body = " ".join(extract_text(raw.decode("utf-8", errors="replace")))
    return f"{title}. {body}"[:HOUSEHOLD_TEXT_CHARS]


def build_wikipedia_rerank(conn, settings: Settings, embed: Callable[[list[str]], np.ndarray],
                           open_zim=None, out: Callable = print, resume: bool = True,
                           limit: Optional[int] = None) -> dict:
    """One vector per real English Wikipedia article, for rerank-only lookup (WikipediaStore), never for
    nearest-neighbour retrieval (Task 9 does that reranking; this function only builds the store). A
    multi-hour build on the real ZIM (8.4 million real article keys, Task 8's own measurement): resumable,
    a checkpoint file records the sorted key list and how many batches have vectors so far, so a restart
    (`resume=True`, the default) skips straight past whatever this process -- or an earlier, interrupted
    one -- already finished, rather than re-embedding it. `limit`, when given, caps the sorted key list to
    its first N entries: a fast, real, small-scale throughput measurement (`sos build-embeddings-wikipedia
    --limit N`) without doing the full build.

    Wikipedia is never in EXCLUDED_ZIMS (Task 9's own general-purpose exclusion check, not written yet):
    this function is scoped to the one WIKIPEDIA_ZIM id below already, which makes it trivially compliant
    on its own -- but a future editor who adds a second ZIM to this function must add the real
    EXCLUDED_ZIMS check at that point, not assume this single-ZIM guard still covers it."""
    from sos.books import open_zim as real_open_zim
    open_zim = open_zim or real_open_zim
    row = conn.execute("SELECT available, local_path FROM library_items WHERE id=?", (WIKIPEDIA_ZIM,)).fetchone()
    if row is None or not row["available"] or not row["local_path"]:
        out("wikipedia: not on the box; skipped")
        return {"count": 0}
    reader = open_zim(Path(row["local_path"]))
    checkpoint_path = Path(settings.embeddings_dir) / "wikipedia.checkpoint.json"
    part_path = Path(settings.embeddings_dir) / "wikipedia.f16.bin.part"
    part_path.parent.mkdir(parents=True, exist_ok=True)
    all_keys = sorted(_wikipedia_article_keys(reader))  # every real article path, sorted once, up front
    if limit is not None:
        all_keys = all_keys[:limit]
    done = 0
    vectors = np.zeros((len(all_keys), DIMS), dtype=np.float16)
    if resume and checkpoint_path.is_file():
        state = json.loads(checkpoint_path.read_text())
        if state.get("keys") == all_keys:  # the ZIM (and any --limit) has not changed under us mid-build
            done = state["done"]
            if part_path.is_file():
                existing = np.memmap(part_path, dtype=np.float16, mode="r", shape=(len(all_keys), DIMS))
                vectors[:done] = existing[:done]
            out(f"wikipedia: resuming from {done} of {len(all_keys)}")
    t0 = time.perf_counter()
    total_seen = total_skipped = 0
    for start in range(done, len(all_keys), BATCH):
        batch_keys = all_keys[start:start + BATCH]
        texts = [_wikipedia_article_text(reader, k) for k in batch_keys]
        total_seen += len(batch_keys)
        # a soft-redirect stub (or anything else with next to nothing to say) is left as the zero vector
        # vectors' own np.zeros() already gave it -- never embedded, exactly as build_household skips a
        # near-empty book, but the key stays in the store: a real article, findable, just with nothing to
        # rerank by (a harmless, never-boosted 0.0 similarity), rather than vanishing from the key list
        # this build's own resumability depends on staying a fixed, known size.
        keep = [i for i, t in enumerate(texts) if len(t) >= SHORTEST_CHARS]
        total_skipped += len(batch_keys) - len(keep)
        if keep:
            vecs = embed_batch(embed, [texts[i] for i in keep])
            for j, i in enumerate(keep):
                vectors[start + i] = vecs[j].astype(np.float16)
        if (start // BATCH) % CHECKPOINT_BATCHES == 0 or start + BATCH >= len(all_keys):
            vectors.tofile(part_path)
            checkpoint_path.write_text(json.dumps({"keys": all_keys, "done": start + len(batch_keys)}))
            elapsed = time.perf_counter() - t0
            rate = (start + len(batch_keys) - done) / max(elapsed, 0.001)
            remaining_s = (len(all_keys) - start - len(batch_keys)) / max(rate, 0.001)
            out(f"wikipedia: {start + len(batch_keys)} of {len(all_keys)} "
                f"({elapsed:.0f}s elapsed, ~{remaining_s / 3600:.1f}h remaining at this rate)")
    os.replace(part_path, Path(settings.embeddings_dir) / "wikipedia.f16.bin")
    (Path(settings.embeddings_dir) / "wikipedia.ids").write_text("\n".join(all_keys) + "\n")
    checkpoint_path.unlink(missing_ok=True)
    meta = {"model": settings.embed_model, "dims": DIMS, "count": len(all_keys), "seen": total_seen,
            "skipped_no_text": total_skipped, "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (Path(settings.embeddings_dir) / "wikipedia.meta.json").write_text(json.dumps(meta, indent=1))
    out(f"wikipedia: wrote {len(all_keys)} keys ({time.perf_counter() - t0:.0f}s, {total_skipped} left as zero vectors for no usable text)")
    return meta


def build_wikipedia_cli(settings: Settings, out: Callable = print, run: Callable = subprocess.Popen,
                        cuda: bool = False, resume: bool = True, limit: Optional[int] = None) -> int:
    """PC only: start the embedding server if none is up, embed Wikipedia for rerank-only lookup, stop
    what was started -- structurally build_cli's own pattern, kept a separate function (and a separate
    `sos build-embeddings-wikipedia` subcommand, not a flag on `build-embeddings`) because this specific
    build genuinely takes hours against the real ZIM and must never be triggered by a routine
    `sos build-embeddings` run."""
    from sos.db import connect
    if not settings.embed_model_path.is_file():
        out(f"FAIL the embedding model is not at {settings.embed_model_path} (manifest item bge-small-en-v1.5)")
        return 1
    started = None
    try:
        if httpx.get(f"{settings.embed_url}/health", timeout=1.0).status_code != 200:
            raise httpx.HTTPError("not ready")
    except httpx.HTTPError:
        binary = server_command(settings, cuda=True)[0] if cuda else (shutil.which("llama-server") or "/usr/local/bin/llama-server")
        cmd = [binary] + server_command(settings, cuda=cuda)[1:]
        out(f"starting {' '.join(cmd)}")
        started = run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            time.sleep(0.5)
            try:
                if httpx.get(f"{settings.embed_url}/health", timeout=1.0).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
        else:
            out("FAIL the embedding server did not come up")
            if started:
                started.terminate()
            return 1
    conn = connect(settings.db_path)
    try:
        embed_fn = lambda texts: embed_sync(settings.embed_url, texts)  # noqa: E731 -- one call site
        build_wikipedia_rerank(conn, settings, embed_fn, out=out, resume=resume, limit=limit)
    except EmbedError as exc:
        out(f"FAIL {exc}")
        return 1
    finally:
        conn.close()
        if started:
            started.terminate()
    return 0


def server_command(settings: Settings, cuda: bool = False) -> list[str]:
    """The embedding server's command line: the same for `sos build-embeddings` on the PC, the dev stack and
    install/systemd/sos-embed.service on the box. `cuda=True` is the PC-only bulk-build variant (the
    household book collection and Wikipedia): the second, CUDA-built binary from install/build-llama-cuda.sh,
    with every layer offloaded to the GPU. The box's own callers never pass it, so their command line is
    identical to today's."""
    host, port = _host_port(settings.embed_url)
    binary = str(CUDA_LLAMA_SERVER) if cuda else "llama-server"
    cmd = [binary, "-m", str(settings.embed_model_path), "--embedding", "--pooling", "cls", "-c", "512", "-ub", "512",
           "-b", "512", "--host", host, "--port", str(port), "-t", "2", "--no-webui"]
    if cuda:
        cmd += ["-ngl", "99"]
    return cmd


def _host_port(url: str) -> tuple[str, str]:
    rest = url.split("://", 1)[-1].rstrip("/")
    host, _, port = rest.partition(":")
    return host or "127.0.0.1", port or "8091"


def build_cli(settings: Settings, out: Callable = print, run: Callable = subprocess.Popen, cuda: bool = False) -> int:
    """PC only: start the embedding server if none is up, embed the library, stop what was started.
    `cuda=True` (`sos build-embeddings --cuda`) starts the CUDA-built llama-server-cuda instead of the
    plain CPU binary -- for the large bulk builds (household books, Wikipedia) that need GPU offload to be
    tractable."""
    from sos.db import connect
    if not settings.embed_model_path.is_file():
        out(f"FAIL the embedding model is not at {settings.embed_model_path} (manifest item bge-small-en-v1.5)")
        return 1
    started = None
    try:
        if httpx.get(f"{settings.embed_url}/health", timeout=1.0).status_code != 200:
            raise httpx.HTTPError("not ready")
    except httpx.HTTPError:
        binary = server_command(settings, cuda=True)[0] if cuda else (shutil.which("llama-server") or "/usr/local/bin/llama-server")
        cmd = [binary] + server_command(settings, cuda=cuda)[1:]
        out(f"starting {' '.join(cmd)}")
        started = run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            time.sleep(0.5)
            try:
                if httpx.get(f"{settings.embed_url}/health", timeout=1.0).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
        else:
            out("FAIL the embedding server did not come up")
            if started:
                started.terminate()
            return 1
    conn = connect(settings.db_path)
    try:
        embed_fn = lambda texts: embed_sync(settings.embed_url, texts)  # noqa: E731 -- one call site, both collections
        build(conn, settings, embed_fn, out)
        build_household(conn, settings, embed_fn, out=out)
    except EmbedError as exc:
        out(f"FAIL {exc}")
        return 1
    finally:
        conn.close()
        if started:
            started.terminate()
    return 0


class Semantic:
    """What the running API holds: the client for the server and the index, read from disk when first asked
    for and read again when the files change (a `sos build-embeddings` copied on later). `query` answers
    with nothing rather than an error whenever any part is missing or slow."""

    QUERY_TIMEOUT_S = 0.6

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = EmbedClient(settings.embed_url)
        self._index: Optional[Index] = None
        self._stamp: Optional[float] = None
        self._household_index: Optional[ApproxIndex] = None
        self._household_stamp: Optional[float] = None
        self._checked = 0.0
        self._household_checked = 0.0
        self.generation = 0        # goes up each time either index is (re)loaded or found gone: search's cache keys on it

    def index(self) -> Optional[Index]:
        path = Path(self.settings.embeddings_dir) / "docs.f16.bin"
        now = time.monotonic()
        if self._index is not None and now - self._checked < 30:
            return self._index
        self._checked = now
        try:
            stamp = path.stat().st_mtime
        except OSError:
            if self._index is not None:
                self.generation += 1
            self._index, self._stamp = None, None
            return None
        if stamp != self._stamp:
            self._index = Index.load(self.settings.embeddings_dir, "docs")
            self._stamp = stamp
            self.generation += 1
            if self._index is not None:
                log.info("embeddings: %d passages loaded", len(self._index))
        return self._index

    def household_index(self) -> Optional[ApproxIndex]:
        """The household collection's approximate index (Gutenberg and Survivor Library, one vector per
        book), read and refreshed exactly as `index()` does for the box's own passages -- a second,
        parallel cache rather than a variant of the first, because the two collections' files change on
        their own schedules (a fresh `sos build-embeddings` writes both, but only one need be present)."""
        path = Path(self.settings.embeddings_dir) / "household.hnsw"
        now = time.monotonic()
        if self._household_index is not None and now - self._household_checked < 30:
            return self._household_index
        self._household_checked = now
        try:
            stamp = path.stat().st_mtime
        except OSError:
            if self._household_index is not None:
                self.generation += 1
            self._household_index, self._household_stamp = None, None
            return None
        if stamp != self._household_stamp:
            self._household_index = ApproxIndex.load(self.settings.embeddings_dir, "household")
            self._household_stamp = stamp
            self.generation += 1
            if self._household_index is not None:
                log.info("embeddings: %d household books loaded", len(self._household_index))
        return self._household_index

    def available(self) -> bool:
        return self.index() is not None

    async def query(self, q: str, k: int = 20) -> list[tuple[str, float]]:
        """The nearest passages to a query: (url, cosine), best first; empty when semantic search is off."""
        index = self.index()
        if index is None or not q.strip():
            return []
        try:
            vec = await self.client.embed([QUERY_PREFIX + q.strip()], timeout=self.QUERY_TIMEOUT_S)
        except EmbedError:
            return []
        return index.search(vec[0], k)

    async def query_household(self, q: str, k: int = 20) -> list[tuple[str, float]]:
        """The nearest household books to a query: (key, cosine) where key is "<zim id>:<book id>", best
        first; empty when the household collection or the embedding server is off. Identical in shape to
        `query`, against the household index instead of the docs one."""
        index = self.household_index()
        if index is None or not q.strip():
            return []
        try:
            vec = await self.client.embed([QUERY_PREFIX + q.strip()], timeout=self.QUERY_TIMEOUT_S)
        except EmbedError:
            return []
        return index.search(vec[0], k)
