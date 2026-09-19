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

import hashlib
import json
import logging
import multiprocessing
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from collections import Counter, deque
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from contextlib import contextmanager
from itertools import islice
from pathlib import Path
from typing import Callable, Iterator, Optional

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


def embed_sync(url: str, texts: list[str], timeout: float = 120.0,
               client: Optional[httpx.Client] = None) -> np.ndarray:
    """The build's blocking call: one batch of passages to vectors."""
    try:
        r = (client.post if client is not None else httpx.post)(
            f"{url.rstrip('/')}/embeddings", json={"input": texts}, timeout=timeout)
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
        folder = _collection_folder(Path(folder), collection)
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
        _publish_collection(folder, collection, [hnsw_part, ids_part])

    @classmethod
    def load(cls, folder: Path, collection: str) -> Optional["ApproxIndex"]:
        import hnswlib
        folder = _collection_folder(Path(folder), collection)
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
        folder = _collection_folder(Path(folder), collection)
        vec_path, key_path = folder / f"{collection}.f16.bin", folder / f"{collection}.ids"
        if not (vec_path.is_file() and key_path.is_file()):
            return None
        with key_path.open(encoding="utf-8") as ids:
            keys = [line.rstrip("\n") for line in ids if line.rstrip("\n")]
        if not keys or vec_path.stat().st_size != len(keys) * DIMS * 2:
            return None
        mmap = np.memmap(vec_path, dtype=np.float16, mode="r", shape=(len(keys), DIMS))
        return cls(mmap, keys)

    def vector_for(self, key: str) -> Optional[np.ndarray]:
        import bisect
        i = bisect.bisect_left(self.keys, key)
        if i == len(self.keys) or self.keys[i] != key:
            return None
        vec = np.asarray(self._mmap[i], dtype=np.float32)
        # A soft-redirect stub (build_wikipedia_rerank's own SHORTEST_CHARS check) was never embedded, so
        # its row is still the build's zero-initialised placeholder, not a real, L2-normalised vector -- a
        # genuine embedding always has at least one nonzero component. Handing that zero row back as-is
        # would let a caller compare it for cosine similarity, where 0.0 is the *midpoint* of a real
        # unit-vector dot product's [-1, 1] range, not its floor -- an artificially middling match for
        # every query, rather than the "no real signal here" that a missing key already gets. Returning
        # None here instead lets a caller treat a stub exactly like an absent key, which is what it is.
        return vec if vec.any() else None


def _collection_folder(folder: Path, collection: str) -> Path:
    current = folder / f"{collection}.current"
    return current.resolve() if current.is_symlink() else folder


def _publish_collection(folder: Path, collection: str, parts: list[Path]) -> None:
    """Publish a complete generation with one rename, keeping readers on the old files until then.

    The familiar filenames are relative symlinks for copying and inspection. Loaders resolve the
    generation once so a concurrent publication cannot pair old keys with new vectors. Previous
    generations remain valid for readers holding a memory map; never truncate a published file.
    """
    generation = folder / f".{collection}-{uuid.uuid4().hex}"
    generation.mkdir()
    for part in parts:
        os.replace(part, generation / part.name.removesuffix(".part"))
    current = folder / f"{collection}.current"
    next_link = folder / f"{collection}.current.{uuid.uuid4().hex}.part"
    next_link.symlink_to(generation.name, target_is_directory=True)
    os.replace(next_link, current)
    for part in parts:
        name = part.name.removesuffix(".part")
        alias = folder / f"{name}.link.{uuid.uuid4().hex}.part"
        alias.symlink_to(f"{current.name}/{name}")
        os.replace(alias, folder / name)


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
    """Stage and publish one complete generation of vectors, keys and metadata."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    parts = []
    for name, data in ((f"{collection}.f16.bin", np.asarray(vectors, dtype=np.float16).tobytes()),
                       (f"{collection}.ids", ("\n".join(keys) + "\n").encode("utf-8"))):
        part = folder / (name + ".part")
        part.write_bytes(data)
        parts.append((part, folder / name))
    meta_part = folder / f"{collection}.meta.json.part"
    meta_part.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    _publish_collection(folder, collection, [part for part, _ in parts] + [meta_part])


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

# Cached by str(settings.manifests) rather than @lru_cache on settings itself: this codebase's Settings
# (pydantic_settings.BaseSettings) is not hashable (confirmed: hash(get_settings()) raises TypeError), so
# an lru_cache keyed on the settings object itself is not available here. The manifest directory string is
# the only part of settings this function reads, so keying on it gives the same "compute once per real
# manifest location" behaviour the lru_cache sketch wanted, without needing settings to be hashable.
_excluded_zims_cache: dict[str, frozenset[str]] = {}


def excluded_zims(settings: Settings) -> frozenset[str]:
    """Every ZIM id meaning search must never touch: Wiktionary, the Welsh Wikipedia, and every real
    *.stackexchange.com_en_all id in the manifest, computed rather than hand-listed so this set can never
    silently drift as StackExchange sites are added or removed. Lazy, not a module-level constant: computed
    once per real settings.manifests path and cached, rather than frozen at import time -- a module-level
    constant would have latched onto whatever the very first import's environment happened to produce
    (possibly an empty or wrong manifest directory, since load_manifests() glob()s a directory that may not
    exist yet and silently returns [] rather than raising), and every later caller would keep using that
    frozen, possibly-wrong answer forever. Raises rather than silently under-excluding if the real manifest
    yields zero StackExchange ids, which is far more likely to mean "wrong directory" than "genuinely none
    left"."""
    key = str(settings.manifests)
    cached = _excluded_zims_cache.get(key)
    if cached is not None:
        return cached
    from sos.manifest import load_manifests
    ids = {i.id for i in load_manifests(settings.manifests) if i.id.endswith(".stackexchange.com_en_all")}
    if not ids:
        raise RuntimeError(f"excluded_zims: found zero *.stackexchange.com_en_all ids under {settings.manifests} "
                            f"-- this almost certainly means the manifest directory is wrong, not that every "
                            f"StackExchange site was genuinely removed; refusing to silently under-exclude")
    result = frozenset({"wiktionary_en_all_nopic", "wikipedia_cy_all_maxi"}) | frozenset(ids)
    _excluded_zims_cache[key] = result
    return result


# Survivor Library is a zimit crawl of the live WordPress site, not a book-scraper ZIM: it has no catalogue
# entry and no per-book HTML article at all. Its ~11,800 real books are plain PDF entries at this one path
# shape (Task 5's real finding); everything else in the crawl (theme assets, blog pages, category pages) is not.
_SURVIVOR_BOOK = re.compile(r"^www\.survivorlibrary\.com/library/(.+)\.pdf$", re.I)


def _gutenberg_text(html_bytes: bytes) -> str:
    from sos.kiwix import extract_text

    return " ".join(extract_text(html_bytes.decode("utf-8", errors="replace"), max_chars=HOUSEHOLD_TEXT_CHARS))


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


_GUTENBERG_BOOKS_SQL = ("SELECT id, title, author, html_path FROM books WHERE zim=? AND html_path IS NOT NULL "
                        "ORDER BY id")


def _household_entries(reader, zim_id: str, conn=None) -> Iterator[tuple[str, str, str]]:
    """(key, heading, plain text) for every real book this ZIM's reader holds. The heading is what the
    embedded passage opens with: for Gutenberg the catalogue's own title and author, for Survivor Library
    a title read off the filename.

    Gutenberg is driven by the `books` table `sos index` fills from the ZIM's own catalogue, one row per
    book, rather than by a scan for path-shaped articles. A scan for `<slug>.<id>` matches 140,765 entries
    on the real ZIM for 64,153 distinct ids: 60,359 of them are a book's "cover" page (long enough to
    embed and saying nothing about the book), 16,455 ids have a second, differently-named page as well,
    and 3,794 ids are not in the catalogue at all -- so most books were embedded two or three times over
    under one key, which search() then lifted once per copy.

    Survivor Library has no catalogue to read (it is a zimit crawl of a WordPress site, not a
    book-scraper ZIM), so its books are still found by their one real path shape; `seen` keeps its keys
    unique whatever the crawl holds. Extract lazily either way: at most one batch of full texts is
    retained, rather than the entire archive."""
    if zim_id == "gutenberg_en_all":
        for row in conn.execute(_GUTENBERG_BOOKS_SQL, (zim_id,)):
            raw = reader.read(row["html_path"])
            if not raw:
                continue
            author = (row["author"] or "").strip()
            yield (f"{zim_id}:{row['id']}", f"{row['title']} by {author}" if author else row["title"],
                   _gutenberg_text(raw))
        return
    seen: set[str] = set()
    for path in reader.paths():
        m = _SURVIVOR_BOOK.match(path)
        if not m:
            continue
        slug = m.group(1)
        key = f"{zim_id}:{slug}"
        if key in seen:
            continue
        raw = reader.read(path)
        if not raw:
            continue
        seen.add(key)
        yield key, re.sub(r"[-_]+", " ", slug).strip(), _pdf_text(raw)


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
        assert zim_id not in excluded_zims(settings), f"{zim_id} is excluded from meaning search"
        row = conn.execute("SELECT available, local_path FROM library_items WHERE id=?", (zim_id,)).fetchone()
        if row is None or not row["available"] or not row["local_path"]:
            out(f"household: {zim_id} is not on the box; skipped")
            continue
        try:
            reader = open_zim(Path(row["local_path"]))
        except (OSError, RuntimeError, ValueError) as exc:
            out(f"household: {zim_id} unreadable; skipped ({exc})")
            continue
        if zim_id == "gutenberg_en_all" and not conn.execute(
                "SELECT 1 FROM books WHERE zim=? AND html_path IS NOT NULL LIMIT 1", (zim_id,)).fetchone():
            out(f"household: {zim_id} has no catalogue rows; run sos index first; skipped")
            continue
        entries = iter(_household_entries(reader, zim_id, conn))
        before = len(keys)
        while batch := list(islice(entries, BATCH)):
            texts, batch_keys = [], []
            for key, title, text in batch:
                total_seen += 1
                plain = text[:HOUSEHOLD_TEXT_CHARS]
                if len(plain) < SHORTEST_CHARS:
                    total_skipped += 1
                    continue
                texts.append(f"{title}. {plain}"[:HOUSEHOLD_TEXT_CHARS])
                batch_keys.append(key)
            if not texts:
                continue
            chunks.append(embed_batch(embed, texts))
            keys.extend(batch_keys)
            if len(keys) // BATCH % 25 == 0:
                out(f"household: {len(keys)} embedded ({time.perf_counter() - t0:.0f}s)")
        out(f"household: {zim_id} done, {len(keys) - before} books ({len(keys)} so far)")
    duplicates = [key for key, n in Counter(keys).items() if n > 1]
    if duplicates:
        raise ValueError(f"household: {len(duplicates)} book keys would each hold several vectors in one index "
                         f"(e.g. {', '.join(duplicates[:5])}); search would count those books twice over")
    vectors = np.concatenate(chunks) if chunks else np.zeros((0, DIMS), dtype=np.float32)
    if keys:
        idx = ApproxIndex.build(vectors, keys)
        idx.save(settings.embeddings_dir, "household")
    meta = {"model": settings.embed_model, "dims": DIMS, "count": len(keys), "seen": total_seen,
            "skipped_no_text": total_skipped, "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    meta["elapsed_s"] = time.perf_counter() - t0
    if keys:
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
    body = " ".join(extract_text(raw.decode("utf-8", errors="replace"), max_chars=HOUSEHOLD_TEXT_CHARS))
    return f"{title}. {body}"[:HOUSEHOLD_TEXT_CHARS]


WORKER_WINDOW_CHUNKS = 3  # chunks of keys kept submitted per worker: enough that no worker ever waits for
                          # the main process to come back round, small enough that the extracted text held
                          # in flight stays a few thousand passages rather than the whole 8.4-million key
                          # list (which is why this is a hand-rolled window and not Executor.map).

_WORKER_READER = None     # one archive handle per worker process, opened by _worker_open below


def _worker_open(zim_path: str) -> None:
    """Pool initialiser: give this worker process its own libzim archive over the ZIM on disk."""
    global _WORKER_READER
    from sos.books import open_zim
    _WORKER_READER = open_zim(Path(zim_path))


def _worker_texts(keys: list[str]) -> list[str]:
    """One chunk of keys to their extracted passages -- exactly what the serial path computes in-process."""
    return [_wikipedia_article_text(_WORKER_READER, key) for key in keys]


@contextmanager
def _wikipedia_text_chunks(reader, all_keys: list[str], starts, workers: int, zim_path: str):
    """Yield (start, texts) for each BATCH-sized chunk of `starts`, strictly in key order, so the caller's
    loop, its checkpoint cadence and its resume arithmetic are the same whether one process or six did the
    reading. Serial (`workers <= 1`) is today's in-process extraction, unchanged.

    Start method: spawn, deliberately. Forking would hand each child a copy-on-write view of a parent that
    is holding the 8.4-million-string key list (touching those pages to refcount them would quietly
    duplicate gigabytes) and, worse, an already-open libzim Archive -- a C++ object over an mmap with its
    own caches, which is not safe to inherit and use in a child. A spawned worker starts from a clean
    interpreter and opens its own handle from the path; the extra second of interpreter startup is nothing
    against a multi-hour build. (forkserver would also avoid the inherited handle, but spawn needs no
    preload list to stay correct.) The parent's `open_zim` override therefore reaches key enumeration
    only: the workers always read the real file at `local_path` through sos.books.open_zim."""
    if workers <= 1:
        yield ((start, [_wikipedia_article_text(reader, key) for key in all_keys[start:start + BATCH]])
               for start in starts)
        return
    pool = ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn"),
                               initializer=_worker_open, initargs=(str(zim_path),))

    def chunks():
        pending: deque = deque()
        remaining = iter(starts)

        def fill():
            while len(pending) < workers * WORKER_WINDOW_CHUNKS:
                start = next(remaining, None)
                if start is None:
                    return
                pending.append((start, pool.submit(_worker_texts, all_keys[start:start + BATCH])))

        fill()
        while pending:
            start, future = pending.popleft()
            try:
                texts = future.result()
            except BrokenProcessPool as exc:
                raise RuntimeError(
                    f"wikipedia: an article-extraction worker process died at row {start}; the build has "
                    f"stopped and can be resumed from its last checkpoint") from exc
            except Exception as exc:
                raise RuntimeError(
                    f"wikipedia: an article-extraction worker failed at row {start} ({exc}); the build "
                    f"has stopped and can be resumed from its last checkpoint") from exc
            fill()   # refill before the caller embeds, so extraction of later chunks overlaps this one
            yield start, texts

    try:
        yield chunks()
    finally:
        pool.shutdown(wait=True, cancel_futures=True)


def build_wikipedia_rerank(conn, settings: Settings, embed: Callable[[list[str]], np.ndarray],
                           open_zim=None, out: Callable = print, resume: bool = True,
                           limit: Optional[int] = None, workers: int = 1) -> dict:
    """One vector per real English Wikipedia article, for rerank-only lookup (WikipediaStore), never for
    nearest-neighbour retrieval (Task 9 does that reranking; this function only builds the store). A
    multi-hour build on the real ZIM (8.4 million real article keys): resumable, with a memory-mapped
    staging file and an atomic checkpoint identifying its source, key digest and completed rows. A restart
    (`resume=True`, the default) skips straight past whatever this process -- or an earlier, interrupted
    one -- already finished, rather than re-embedding it. `limit`, when given, caps the sorted key list to
    its first N entries: a fast, real, small-scale throughput measurement (`sos build-embeddings-wikipedia
    --limit N`) without doing the full build.

    `workers` > 1 moves the article reading and HTML-to-text extraction into that many worker processes,
    which run ahead of the embedding the main process is doing -- the serial loop leaves eleven of twelve
    cores idle while the GPU works and the GPU idle while one core parses. The batches are still consumed
    strictly in key order, so the store, the counts and the checkpoint are exactly what `workers=1`
    produces; `workers` is a scheduling choice and deliberately not part of the checkpoint identity, so a
    build started on one worker resumes on six and the other way about.

    Wikipedia is not excluded from meaning-based reranking:
    this function is scoped to the one WIKIPEDIA_ZIM id below already, which makes it trivially compliant
    on its own -- but a future editor who adds a second ZIM to this function must add the real
    excluded_zims check at that point, not assume this single-ZIM guard still covers it."""
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")
    if workers < 1:
        raise ValueError("workers must be positive")
    from sos.books import open_zim as real_open_zim
    open_zim = open_zim or real_open_zim
    row = conn.execute("SELECT available, local_path FROM library_items WHERE id=?", (WIKIPEDIA_ZIM,)).fetchone()
    if row is None or not row["available"] or not row["local_path"]:
        out("wikipedia: not on the box; skipped")
        return {"count": 0}
    try:
        reader = open_zim(Path(row["local_path"]))
    except (OSError, RuntimeError, ValueError) as exc:
        out(f"wikipedia: unreadable; skipped ({exc})")
        return {"count": 0}
    folder = Path(settings.embeddings_dir)
    # A measurement must never replace the live store or a full build's checkpoint.
    if limit is not None:
        folder = folder / "wikipedia-sample"
    folder.mkdir(parents=True, exist_ok=True)
    checkpoint_path = folder / "wikipedia.checkpoint.json"
    part_path = folder / "wikipedia.f16.bin.part"
    out("wikipedia: enumerating article keys")
    all_keys = sorted(_wikipedia_article_keys(reader))
    if limit is not None:
        all_keys = all_keys[:limit]
    if not all_keys:
        out("wikipedia: no articles; skipped")
        return {"count": 0}
    # Checkpoint identity covers the source revision, model and ordered row mapping.
    digest = hashlib.sha256()
    for key in all_keys:
        digest.update((key + "\n").encode("utf-8"))
    try:
        stat = Path(row["local_path"]).stat()
        source = [str(row["local_path"]), stat.st_size, stat.st_mtime_ns]
    except OSError:  # fixture readers do not need an actual ZIM on disk
        source = [str(row["local_path"])]
    identity = {"keys_sha256": digest.hexdigest(), "source": source,
                "model": settings.embed_model, "passage_chars": HOUSEHOLD_TEXT_CHARS,
                "count": len(all_keys), "dims": DIMS}
    done = total_skipped = 0
    size = len(all_keys) * DIMS * np.dtype(np.float16).itemsize
    if resume and checkpoint_path.is_file() and part_path.is_file():
        try:
            state = json.loads(checkpoint_path.read_text())
            if (state.get("identity") == identity and part_path.stat().st_size == size
                    and 0 <= state["done"] <= len(all_keys)):
                done = state["done"]
                total_skipped = state["skipped_no_text"]
        except (OSError, ValueError, KeyError, TypeError):
            pass  # an incomplete checkpoint restarts safely
    vectors = np.memmap(part_path, dtype=np.float16, mode="r+" if done else "w+",
                        shape=(len(all_keys), DIMS))
    if done:
        out(f"wikipedia: resuming from {done} of {len(all_keys)}")
    t0 = time.perf_counter()
    total_seen = done
    with _wikipedia_text_chunks(reader, all_keys, range(done, len(all_keys), BATCH), workers,
                                row["local_path"]) as text_chunks:
        for start, texts in text_chunks:
            batch_keys = all_keys[start:start + BATCH]
            vectors[start:start + len(batch_keys)] = 0
            total_seen += len(batch_keys)
            # a soft-redirect stub (or anything else with next to nothing to say) is left as the zero
            # vector vectors' own np.zeros() already gave it -- never embedded, exactly as build_household
            # skips a near-empty book, but the key stays in the store: a real article, findable, just with
            # nothing to rerank by (a harmless, never-boosted 0.0 similarity), rather than vanishing from
            # the key list this build's own resumability depends on staying a fixed, known size.
            keep = [i for i, t in enumerate(texts) if len(t) >= SHORTEST_CHARS]
            total_skipped += len(batch_keys) - len(keep)
            if keep:
                vecs = embed_batch(embed, [texts[i] for i in keep])
                for j, i in enumerate(keep):
                    vectors[start + i] = vecs[j].astype(np.float16)
            if (start // BATCH) % CHECKPOINT_BATCHES == 0 or start + BATCH >= len(all_keys):
                vectors.flush()
                checkpoint_part = checkpoint_path.with_suffix(".json.part")
                checkpoint_part.write_text(json.dumps({"identity": identity, "done": start + len(batch_keys),
                                                       "skipped_no_text": total_skipped}))
                os.replace(checkpoint_part, checkpoint_path)
                elapsed = time.perf_counter() - t0
                rate = (start + len(batch_keys) - done) / max(elapsed, 0.001)
                remaining_s = (len(all_keys) - start - len(batch_keys)) / max(rate, 0.001)
                out(f"wikipedia: {start + len(batch_keys)} of {len(all_keys)} "
                    f"({elapsed:.0f}s elapsed, ~{remaining_s / 3600:.1f}h remaining at this rate)")
    vectors.flush()
    del vectors
    ids_part = folder / "wikipedia.ids.part"
    with ids_part.open("w", encoding="utf-8") as ids:
        for key in all_keys:
            ids.write(key + "\n")

    meta = {"model": settings.embed_model, "dims": DIMS, "count": len(all_keys), "seen": total_seen,
            "skipped_no_text": total_skipped, "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    meta["elapsed_s"] = time.perf_counter() - t0
    meta["processed_this_run"] = len(all_keys) - done
    meta_part = folder / "wikipedia.meta.json.part"
    meta_part.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    _publish_collection(folder, "wikipedia", [part_path, ids_part, meta_part])
    checkpoint_path.unlink(missing_ok=True)
    out(f"wikipedia: wrote {len(all_keys)} keys ({time.perf_counter() - t0:.0f}s, {total_skipped} left as zero vectors for no usable text)")
    return meta


def build_wikipedia_cli(settings: Settings, out: Callable = print, run: Callable = subprocess.Popen,
                        cuda: bool = False, resume: bool = True, limit: Optional[int] = None,
                        workers: int = 1) -> int:
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
    client = httpx.Client()
    try:
        embed_fn = lambda texts: embed_sync(settings.embed_url, texts, client=client)  # noqa: E731 -- one call site
        build_wikipedia_rerank(conn, settings, embed_fn, out=out, resume=resume, limit=limit, workers=workers)
    except EmbedError as exc:
        out(f"FAIL {exc}")
        return 1
    finally:
        client.close()
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


def build_cli(settings: Settings, out: Callable = print, run: Callable = subprocess.Popen, cuda: bool = False,
              collection: str = "all") -> int:
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
    client = httpx.Client()
    try:
        embed_fn = lambda texts: embed_sync(settings.embed_url, texts, client=client)  # noqa: E731 -- one call site, both collections
        if collection in ("all", "docs"):
            build(conn, settings, embed_fn, out)
        if collection in ("all", "household"):
            build_household(conn, settings, embed_fn, out=out)
    except EmbedError as exc:
        out(f"FAIL {exc}")
        return 1
    finally:
        client.close()
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
        self._wikipedia_store: Optional[WikipediaStore] = None
        self._wikipedia_stamp: Optional[float] = None
        self._checked = 0.0
        self._household_checked = 0.0
        self._wikipedia_checked = 0.0   # its own throttle clock -- Task 7's own fix round established that
        # sharing one shared timer between two collections starves whichever one's stat() check runs second
        # (see test_household_index_has_its_own_throttle_clock_not_shared_with_the_docs_index); a third
        # collection must not repeat that mistake by sharing _checked or _household_checked either.
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

    def wikipedia_store(self) -> Optional["WikipediaStore"]:
        """The Wikipedia rerank-only store (Task 8), read and refreshed exactly as `index()` and
        `household_index()` do for their own collections -- a third, parallel cache with its own stamp and
        its own throttle clock (`_wikipedia_checked`), never sharing `_checked` or `_household_checked`
        (see the note on `_wikipedia_checked` in `__init__`)."""
        path = Path(self.settings.embeddings_dir) / "wikipedia.f16.bin"
        now = time.monotonic()
        if self._wikipedia_store is not None and now - self._wikipedia_checked < 30:
            return self._wikipedia_store
        self._wikipedia_checked = now
        try:
            stamp = path.stat().st_mtime
        except OSError:
            if self._wikipedia_store is not None:
                self.generation += 1
            self._wikipedia_store, self._wikipedia_stamp = None, None
            return None
        if stamp != self._wikipedia_stamp:
            self._wikipedia_store = WikipediaStore.load(self.settings.embeddings_dir)
            self._wikipedia_stamp = stamp
            self.generation += 1
            if self._wikipedia_store is not None:
                log.info("embeddings: %d wikipedia rerank vectors loaded", len(self._wikipedia_store))
        return self._wikipedia_store

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

    async def rerank_wikipedia(self, q: str, keys: list[str]) -> dict[str, float]:
        """Cosine similarity for a handful of already-known Wikipedia article keys against one query
        embedding -- never a nearest-neighbour search, just a few real dot products against the store's own
        rows, so search.py needs no numpy import and no direct coupling to this module's internals. Keys
        with no vector in the store (an absent key, or a soft-redirect stub WikipediaStore.vector_for
        already turns into None) are simply left out of the result rather than scored as zero."""
        store = self.wikipedia_store()
        if store is None or not q.strip():
            return {}
        try:
            qvec = (await self.client.embed([QUERY_PREFIX + q.strip()], timeout=self.QUERY_TIMEOUT_S))[0]
        except EmbedError:
            return {}
        out: dict[str, float] = {}
        for key in keys:
            vec = store.vector_for(key)
            if vec is not None:
                out[key] = float(np.dot(qvec, vec) / (np.linalg.norm(qvec) * np.linalg.norm(vec) + 1e-9))
        return out
