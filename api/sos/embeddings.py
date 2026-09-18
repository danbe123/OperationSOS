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
import time
from pathlib import Path
from typing import Callable, Optional

import httpx
import numpy as np

from sos.config import Settings

log = logging.getLogger(__name__)

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
DIMS = 384
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
VECTORS = "docs.f16.bin"
KEYS = "docs.ids"
META = "docs.meta.json"
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
    def load(cls, folder: Path) -> Optional["Index"]:
        folder = Path(folder)
        vec_path, key_path, meta_path = folder / VECTORS, folder / KEYS, folder / META
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


def write_index(folder: Path, vectors: np.ndarray, keys: list[str], meta: dict) -> None:
    """The three files, written beside their finals and moved into place together, so a build that dies
    halfway leaves the old index whole."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    parts = []
    for name, data in ((VECTORS, np.asarray(vectors, dtype=np.float16).tobytes()), (KEYS, ("\n".join(keys) + "\n").encode("utf-8")),
                       (META, json.dumps(meta, indent=1).encode("utf-8"))):
        part = folder / (name + ".part")
        part.write_bytes(data)
        parts.append((part, folder / name))
    for part, final in parts:
        os.replace(part, final)


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
    write_index(settings.embeddings_dir, vectors, keys, meta)
    out(f"wrote {len(keys)} vectors to {settings.embeddings_dir}")
    return meta


def server_command(settings: Settings) -> list[str]:
    """The embedding server's command line: the same for `sos build-embeddings` on the PC, the dev stack and
    install/systemd/sos-embed.service on the box."""
    host, port = _host_port(settings.embed_url)
    return ["llama-server", "-m", str(settings.embed_model_path), "--embedding", "--pooling", "cls", "-c", "512", "-ub", "512",
            "-b", "512", "--host", host, "--port", str(port), "-t", "2", "--no-webui"]


def _host_port(url: str) -> tuple[str, str]:
    rest = url.split("://", 1)[-1].rstrip("/")
    host, _, port = rest.partition(":")
    return host or "127.0.0.1", port or "8091"


def build_cli(settings: Settings, out: Callable = print, run: Callable = subprocess.Popen) -> int:
    """PC only: start the embedding server if none is up, embed the library, stop what was started."""
    from sos.db import connect
    if not settings.embed_model_path.is_file():
        out(f"FAIL the embedding model is not at {settings.embed_model_path} (manifest item bge-small-en-v1.5)")
        return 1
    started = None
    try:
        if httpx.get(f"{settings.embed_url}/health", timeout=1.0).status_code != 200:
            raise httpx.HTTPError("not ready")
    except httpx.HTTPError:
        binary = shutil.which("llama-server") or "/usr/local/bin/llama-server"
        cmd = [binary] + server_command(settings)[1:]
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
        build(conn, settings, lambda texts: embed_sync(settings.embed_url, texts), out)
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
        self._checked = 0.0
        self.generation = 0        # goes up each time the index is (re)loaded or found gone: search's cache keys on it

    def index(self) -> Optional[Index]:
        path = Path(self.settings.embeddings_dir) / VECTORS
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
            self._index = Index.load(self.settings.embeddings_dir)
            self._stamp = stamp
            self.generation += 1
            if self._index is not None:
                log.info("embeddings: %d passages loaded", len(self._index))
        return self._index

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
