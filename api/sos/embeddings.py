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

import asyncio
import contextvars
import fcntl
import hashlib
import itertools
import json
import logging
import multiprocessing
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
from collections import Counter, deque
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
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


def _vectors_from(payload, expected_count: Optional[int] = None) -> np.ndarray:
    """llama-server answers `/embeddings` with a list of {index, embedding} (or, OpenAI-style, {data: [...]})."""
    rows = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise EmbedError("no embeddings in the reply")
    if expected_count is not None and len(rows) != expected_count:
        raise EmbedError(f"expected {expected_count} embeddings, got {len(rows)}")
    if any(isinstance(row, dict) and "index" in row for row in rows):
        indices = [row.get("index") if isinstance(row, dict) else None for row in rows]
        if any(type(i) is not int for i in indices) or sorted(indices) != list(range(len(rows))):
            raise EmbedError("embedding indices must name each input exactly once")
        rows = sorted(rows, key=lambda row: row["index"])
    out = []
    for row in rows:
        vec = row.get("embedding") if isinstance(row, dict) else row
        if isinstance(vec, list) and vec and isinstance(vec[0], list):
            if len(vec) != 1:
                raise EmbedError("expected one pooled embedding per input")
            vec = vec[0]
        out.append(vec)
    try:
        arr = np.asarray(out, dtype=np.float32)
    except (TypeError, ValueError, OverflowError) as exc:
        raise EmbedError("embedding values must be numeric vectors") from exc
    if arr.ndim != 2 or arr.shape[1] != DIMS:
        raise EmbedError(f"expected {DIMS}-dimensional vectors, got shape {arr.shape}")
    if not np.isfinite(arr).all():
        raise EmbedError("embedding values must be finite")
    # float64 prevents a finite float32 vector overflowing while its norm is calculated.
    norms = np.linalg.norm(arr.astype(np.float64), axis=1, keepdims=True)
    if np.any(norms == 0):
        raise EmbedError("embedding vectors must be nonzero")
    return (arr / norms).astype(np.float32)


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
        try:
            return _vectors_from(r.json(), expected_count=len(texts))
        except ValueError as exc:
            raise EmbedError("embedding server returned invalid JSON") from exc

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
    try:
        return _vectors_from(r.json(), expected_count=len(texts))
    except ValueError as exc:
        raise EmbedError("embedding server returned invalid JSON") from exc


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
    def load(cls, folder: Path, collection: str, model: Optional[str] = None) -> Optional["Index"]:
        directory = _check_collection(Path(folder), collection, ("f16.bin", "ids"))
        if directory is None:
            return None
        meta = _read_meta(Path(folder), collection, directory=directory)
        if _meta_refuses(Path(folder), collection, meta, model):
            return None
        vec_path, key_path = directory / f"{collection}.f16.bin", directory / f"{collection}.ids"
        keys = [line for line in key_path.read_text(encoding="utf-8").split("\n") if line]
        raw = np.fromfile(vec_path, dtype=np.float16)
        if len(keys) == 0 or raw.size != len(keys) * DIMS:
            log.warning("embeddings: %s does not match %s (%d keys, %d values)", vec_path.name, key_path.name, len(keys), raw.size)
            return None
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

    def save(self, folder: Path, collection: str, meta: Optional[dict] = None) -> None:
        """Publish the index, its keys and (when given) the metadata describing them as one generation,
        so no reader can ever pair this index with the meta of the one before it."""
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        hnsw_part = folder / f"{collection}.hnsw.part"
        self._hnsw.save_index(str(hnsw_part))
        ids_part = folder / f"{collection}.ids.part"
        ids_part.write_text("\n".join(self.keys) + "\n", encoding="utf-8")
        parts = [hnsw_part, ids_part]
        if meta is not None:
            meta_part = folder / f"{collection}.meta.json.part"
            meta_part.write_text(json.dumps(meta, indent=1), encoding="utf-8")
            parts.append(meta_part)
        _publish_collection(folder, collection, parts)

    @classmethod
    def load(cls, folder: Path, collection: str, model: Optional[str] = None) -> Optional["ApproxIndex"]:
        import hnswlib
        directory = _check_collection(Path(folder), collection, ("hnsw", "ids"))
        if directory is None:
            return None
        if _meta_refuses(Path(folder), collection, _read_meta(Path(folder), collection, directory=directory), model):
            return None
        hnsw_path, ids_path = directory / f"{collection}.hnsw", directory / f"{collection}.ids"
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
    def load(cls, folder: Path, collection: str = "wikipedia",
             model: Optional[str] = None) -> Optional["WikipediaStore"]:
        """The published store, or None when it is not there, not readable or not this build's shape.

        The key count is worked out cheaply first -- from the meta, or by streaming the key file for
        newlines -- and the vector file's size has to agree with it before the 8.4 million keys are
        materialised at all: a file still being copied grows, its mtime moves on every request, and
        reading the whole key list to find that out again costs about 1.8 s and 700 MB each time."""
        directory = _check_collection(Path(folder), collection, ("f16.bin", "ids"))
        if directory is None:
            return None
        meta = _read_meta(Path(folder), collection, directory=directory)
        if _meta_refuses(Path(folder), collection, meta, model):
            return None
        vec_path, key_path = directory / f"{collection}.f16.bin", directory / f"{collection}.ids"
        expected = _key_count(key_path, meta)
        if expected <= 0 or vec_path.stat().st_size != expected * DIMS * 2:
            return None
        with key_path.open(encoding="utf-8") as ids:
            keys = [line.rstrip("\n") for line in ids if line.rstrip("\n")]
        if len(keys) != expected or vec_path.stat().st_size != len(keys) * DIMS * 2:
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


# Which directory names are a published generation of one collection. New ones are `<collection>.gen-
# <uuid>`: the dot-prefixed `.<collection>-<uuid>` that earlier builds wrote is invisible to `cp -a
# core/embeddings/* dest/`, to `scp -r dir/*` and to a file manager, all of which then deliver a
# `<collection>.current` symlink pointing at nothing. Both are recognised for ever: the generations
# already on the box load by following that symlink, never by their name.
_GENERATION_ID = re.compile(r"^[0-9a-f]{32}$")


def _generation_dirs(folder: Path, collection: str) -> list[Path]:
    prefixes = (f"{collection}.gen-", f".{collection}-")
    found = []
    try:
        entries = list(folder.iterdir())
    except OSError:
        return found
    for path in entries:
        if path.is_symlink() or not path.is_dir():
            continue
        for prefix in prefixes:
            if path.name.startswith(prefix) and _GENERATION_ID.fullmatch(path.name[len(prefix):]):
                found.append(path)
                break
    return found


def _prune_generations(folder: Path, collection: str, keep: set[Path]) -> None:
    """Drop this collection's generations other than the current one and the one before it -- a retained
    Wikipedia generation is 6.47 GB. A reader still holding a deleted generation's files open is unhurt:
    on Linux the inode outlives the name. Nothing any collection's `*.current` resolves to is touched."""
    try:
        live = {link.resolve() for link in folder.glob("*.current") if link.is_symlink()}
    except (OSError, RuntimeError) as exc:
        # An unresolved live pointer makes it unsafe to decide which directories are unused.
        log.warning("embeddings: skipping generation pruning: cannot resolve current links (%s)", exc)
        return
    for path in _generation_dirs(folder, collection):
        if path.resolve() in keep or path.resolve() in live:
            continue
        try:
            shutil.rmtree(path)
        except OSError as exc:      # a publication that worked must not fail over the tidying up
            log.warning("embeddings: could not remove the old generation %s (%s)", path, exc)


def _publish_collection(folder: Path, collection: str, parts: list[Path]) -> None:
    """Publish a complete generation with one rename, keeping readers on the old files until then.

    The familiar filenames are relative symlinks for copying and inspection. Loaders resolve the
    generation once so a concurrent publication cannot pair old keys with new vectors. The generation
    before this one remains valid for readers holding a memory map; older ones are pruned.
    """
    # All publishers in this folder share a lock: otherwise a second publication can prune a
    # generation the first has created but has not yet made current. The lock file stays in place.
    with (folder / ".publish.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        _publish_collection_locked(folder, collection, parts)


def _publish_collection_locked(folder: Path, collection: str, parts: list[Path]) -> None:
    current = folder / f"{collection}.current"
    previous = current.resolve() if current.is_symlink() else None
    generation = folder / f"{collection}.gen-{uuid.uuid4().hex}"
    generation.mkdir()
    for part in parts:
        os.replace(part, generation / part.name.removesuffix(".part"))
    next_link = folder / f"{collection}.current.{uuid.uuid4().hex}.part"
    next_link.symlink_to(generation.name, target_is_directory=True)
    os.replace(next_link, current)
    for part in parts:
        name = part.name.removesuffix(".part")
        alias = folder / f"{name}.link.{uuid.uuid4().hex}.part"
        alias.symlink_to(f"{current.name}/{name}")
        os.replace(alias, folder / name)
    _prune_generations(folder, collection, {generation.resolve()} | ({previous} if previous else set()))


# What has already been said about each (folder, collection, topic), so a loader that runs on every
# search says it once when it becomes true rather than once per request.
_collection_states: dict[tuple[str, str, str], str] = {}


def _say_once(folder: Path, collection: str, topic: str, state: str, message: str = "",
              level: int = logging.WARNING) -> None:
    key = (str(folder), collection, topic)
    if _collection_states.get(key) == state:
        return
    was = _collection_states.get(key)
    _collection_states[key] = state
    if message:
        log.log(level, message)
    elif was is not None and was not in ("ok", "absent"):
        log.info("embeddings: the %s collection's %s are in order again", collection, topic)


def _check_collection(folder: Path, collection: str, names: tuple[str, ...]) -> Optional[Path]:
    """Where one collection's published files really are, or None when they cannot all be read.

    A collection that was never built is silence: a box may simply have no embeddings. Files that are
    there but resolve to nothing are a copy that went wrong, and are said out loud once, because what
    follows is a search that has quietly become the keyword search with nothing to show for it."""
    folder = Path(folder)
    directory = _collection_folder(folder, collection)
    if all((directory / f"{collection}.{name}").is_file() for name in names):
        _say_once(folder, collection, "files", "ok")
        return directory
    current = folder / f"{collection}.current"
    if current.is_symlink() and not current.is_dir():
        target = os.readlink(current)
        _say_once(folder, collection, "files", f"dangling:{target}",
                  f"embeddings: {current} points at '{target}', which is not there, so the {collection} "
                  f"collection cannot be read and search is keyword-only. A copy that skips a leading-dot "
                  f"directory (cp -a, scp -r, a file manager) leaves exactly this: copy the generation "
                  f"directory across as well.")
    elif [n for n in names if (folder / f"{collection}.{n}").is_symlink()]:
        _say_once(folder, collection, "files", "unresolved",
                  f"embeddings: {folder} names the {collection} collection's files but they do not resolve "
                  f"to readable files, so search is keyword-only.")
    else:
        _say_once(folder, collection, "files", "absent")
    return None


def _meta_refuses(folder: Path, collection: str, meta: dict, model: Optional[str]) -> bool:
    """Whether a store's own metadata says this build must not read it.

    A `dims` that is not this build's is a store whose rows cannot be reshaped into vectors at all:
    refused. A different model name is not. The Wikipedia store is deliberately built by
    bge-small-en-v1.5-fp16-torch while the box queries with the q8_0 GGUF of the same model (measured:
    mean cosine 0.9998, 98 per cent top-10 overlap), so that is worth one line in the log and nothing
    more. A store with no metadata at all is an older one, and loads."""
    dims = meta.get("dims")
    if isinstance(dims, int) and dims != DIMS:
        _say_once(folder, collection, "meta", f"dims:{dims}",
                  f"embeddings: the {collection} collection holds {dims}-dimensional vectors and this "
                  f"build reads {DIMS}-dimensional ones; refusing to load it")
        return True
    built_by = meta.get("model")
    if model and isinstance(built_by, str) and built_by != model:
        _say_once(folder, collection, "meta", f"model:{built_by}", level=logging.INFO,
                  message=f"embeddings: the {collection} collection was built by {built_by} and this box "
                          f"queries with {model}; loading it anyway")
    else:
        _say_once(folder, collection, "meta", "ok")
    return False


def _key_count(key_path: Path, meta: dict) -> int:
    """How many keys a published key file holds, without building any of them: the meta's own count
    when it has one, otherwise the newlines, streamed."""
    count = meta.get("count")
    if isinstance(count, int) and count >= 0:
        return count
    total = 0
    try:
        with key_path.open("rb") as ids:
            while chunk := ids.read(1 << 20):
                total += chunk.count(b"\n")
    except OSError:
        return 0
    return total


def _read_meta(folder: Path, collection: str, *, directory: Optional[Path] = None) -> dict:
    """One collection's published meta, or {} when there is none to read. Two places are tried: the
    current generation, and the flat name beside it -- a collection published before the meta joined
    the generation has its index in a generation directory and its meta loose in the folder, and that
    older layout is exactly the one whose meta a rebuild most needs to read."""
    folder = Path(folder)
    directory = directory if directory is not None else _collection_folder(folder, collection)
    flat = folder / f"{collection}.meta.json"
    paths = [directory / flat.name]
    # Only a real flat file is legacy metadata. A flat alias follows *.current and may already
    # point to a different generation than the vectors this reader resolved above.
    if directory != folder and not flat.is_symlink():
        paths.append(flat)
    for path in paths:
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(meta, dict):
            return meta
    return {}


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

# What one Gutenberg book says to the model. "legacy" (the default, and what the published index was built with) is the
# catalogue's "<title> by <author>" and the first HOUSEHOLD_TEXT_CHARS of the book, which is often only a contents list.
# "meta-opening" describes the book the way the catalogue does first -- title, author, Library of Congress shelf name and the
# subject headings the book's own page carries -- and then only its first HOUSEHOLD_OPENING_CHARS. Measured on a 14,222-book
# sample of the real library (docs/reviews/2026-09-21-book-representation.md): with bge-small it lifts plot-description
# queries (hit@10 +0.11, MRR@10 +0.07, both intervals clear of zero) and leaves everyday ones where they were; Survivor Library
# books are embedded exactly as before under either style. Opt-in, because it changes every Gutenberg vector: rebuild the
# whole household collection (`sos build-embeddings --collection household --household-text meta-opening`) or not at all.
HOUSEHOLD_TEXT_STYLES = ("legacy", "meta-opening")
HOUSEHOLD_TEXT_STYLE = "legacy"
HOUSEHOLD_OPENING_CHARS = 1000
HOUSEHOLD_SUBJECTS_CHARS = 400
_DC_SUBJECT = re.compile(r'<meta\s+content="([^"]*)"\s+name="dc\.subject"', re.I)
_PAGE_HEAD_BYTES = 60000                  # the dc.* <meta> tags sit in the page head, long before the book's own text

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


def _gutenberg_subjects(html_bytes: bytes) -> list[str]:
    """The subject headings ("Whaling -- Fiction", "Sea stories") Project Gutenberg's own page carries in its head as
    <meta name="dc.subject">, in page order; none when the page has none."""
    import html
    head = html_bytes[:_PAGE_HEAD_BYTES].decode("utf-8", errors="replace")
    return [html.unescape(m).strip() for m in _DC_SUBJECT.findall(head) if m.strip()]


def _gutenberg_heading(title: str, author: str, shelf: str, subjects: list[str], style: str) -> str:
    """What a Gutenberg passage opens with (the build adds ". " and the text). "legacy" is the title and author only;
    "meta-opening" adds the shelf's name and the subject headings, so a book's subject is in its vector even when its
    opening pages are a contents list."""
    head = f"{title} by {author}" if author else title
    if style != "meta-opening":
        return head
    from sos.books import SHELF_NAMES
    parts = [head]
    if SHELF_NAMES.get(shelf or ""):
        parts.append(SHELF_NAMES[shelf])
    if subjects:
        parts.append("Subjects: " + "; ".join(subjects)[:HOUSEHOLD_SUBJECTS_CHARS])
    return ". ".join(parts)


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


_GUTENBERG_BOOKS_SQL = ("SELECT id, title, author, shelf, html_path FROM books WHERE zim=? AND html_path IS NOT NULL "
                        "ORDER BY id")


def _household_entries(reader, zim_id: str, conn=None, style: str = HOUSEHOLD_TEXT_STYLE) -> Iterator[tuple[str, str, str]]:
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
    retained, rather than the entire archive.

    `style` ("legacy" or "meta-opening", see HOUSEHOLD_TEXT_STYLES) only changes Gutenberg."""
    if zim_id == "gutenberg_en_all":
        for row in conn.execute(_GUTENBERG_BOOKS_SQL, (zim_id,)):
            raw = reader.read(row["html_path"])
            if not raw:
                continue
            author = (row["author"] or "").strip()
            text = _gutenberg_text(raw)
            if style == "meta-opening":
                text = text[:HOUSEHOLD_OPENING_CHARS]
            yield (f"{zim_id}:{row['id']}",
                   _gutenberg_heading(row["title"], author, row["shelf"], _gutenberg_subjects(raw) if style == "meta-opening" else [], style),
                   text)
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
                    open_zim=None, out: Callable = print, text_style: str = HOUSEHOLD_TEXT_STYLE) -> dict:
    """Embed one vector per real book across the household collections (Project Gutenberg, Survivor
    Library) and write the "household" ApproxIndex -- a second, parallel build to `build()`'s, because
    none of this text is in `fts_docs`: a Gutenberg book is a row of the `books` table `sos index` fills,
    read from its ZIM at that row's `html_path`, and a Survivor Library book is a PDF entry found in its
    own ZIM by its path (see `_household_entries`). A ZIM the box does not have (not downloaded, or not on
    this machine) is a no-op for that collection, exactly as `index_books` already treats a missing
    Gutenberg ZIM -- the household build carries on with whatever collections it can reach."""
    from sos.books import open_zim as real_open_zim
    if text_style not in HOUSEHOLD_TEXT_STYLES:
        raise ValueError(f"household text style {text_style!r} is not one of {', '.join(HOUSEHOLD_TEXT_STYLES)}")
    open_zim = open_zim or real_open_zim
    keys: list[str] = []
    chunks: list[np.ndarray] = []
    t0 = time.perf_counter()
    total_seen = total_skipped = 0
    by_zim = {zim_id: 0 for zim_id in HOUSEHOLD_ZIMS}
    for zim_id in HOUSEHOLD_ZIMS:
        if zim_id in excluded_zims(settings):
            # never an assert: `python -O` strips those, and this is the only live use of the exclusion list
            raise ValueError(f"{zim_id} is excluded from meaning search")
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
        entries = iter(_household_entries(reader, zim_id, conn, text_style))
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
        by_zim[zim_id] = len(keys) - before
        out(f"household: {zim_id} done, {len(keys) - before} books ({len(keys)} so far)")
    duplicates = [key for key, n in Counter(keys).items() if n > 1]
    if duplicates:
        raise ValueError(f"household: {len(duplicates)} book keys would each hold several vectors in one index "
                         f"(e.g. {', '.join(duplicates[:5])}); search would count those books twice over")
    vectors = np.concatenate(chunks) if chunks else np.zeros((0, DIMS), dtype=np.float32)
    meta = {"model": settings.embed_model, "dims": DIMS, "count": len(keys), "by_zim": by_zim,
            "seen": total_seen, "skipped_no_text": total_skipped, "text_style": text_style,
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    meta["elapsed_s"] = time.perf_counter() - t0
    vanished = _household_zims_that_vanished(settings.embeddings_dir, by_zim)
    if vanished:
        published = _published_household_counts(settings.embeddings_dir)
        gone = ", ".join(f"{zim} ({published[zim]} books published, none this run)" for zim in vanished)
        out(f"household: refusing to publish a smaller index: {gone}. "
            f"That is a box with a drive or a download missing, not a library that shrank, so the published "
            f"index and meta are untouched and search keeps every book it had. If the collection really is "
            f"gone for good, delete the published household.* files in {settings.embeddings_dir} and run this "
            f"build again.")
        return meta
    if keys:
        ApproxIndex.build(vectors, keys).save(settings.embeddings_dir, "household", meta)
    out(f"household: wrote {len(keys)} vectors ({time.perf_counter() - t0:.0f}s, {total_skipped} skipped for no usable text)")
    return meta


def _published_household_counts(folder: Path) -> dict[str, int]:
    """How many books each ZIM has in the household index already published, or {} when there is none."""
    by_zim = _read_meta(folder, "household").get("by_zim")
    if isinstance(by_zim, dict):
        return {zim: n for zim, n in by_zim.items() if isinstance(n, int)}
    # A meta written before by_zim existed. The keys themselves are "<zim id>:<book id>", so the
    # published index still says which collections went into it.
    try:
        ids = (_collection_folder(Path(folder), "household") / "household.ids").read_text(encoding="utf-8")
    except OSError:
        return {}
    return Counter(line.split(":", 1)[0] for line in ids.split("\n") if ":" in line)


def _household_zims_that_vanished(folder: Path, by_zim: dict[str, int]) -> list[str]:
    """The ZIMs this run got nothing from that the published index has books from. Only ZIMs the run
    genuinely tried are considered, so a key shape left by some older build cannot block a rebuild."""
    published = _published_household_counts(folder)
    return [zim for zim, count in by_zim.items() if count == 0 and published.get(zim, 0) > 0]


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
CHUNK_TIMEOUT_S = 30 * 60  # a worker that stops answering must not hang a multi-hour build in silence.
                           # Thirty minutes for one chunk of 32 articles is absurdly generous against the
                           # real ZIM (a chunk is milliseconds), which is the point: only a genuinely
                           # wedged worker reaches it, never a slow disk or a machine under load.
MAX_TASKS_PER_CHILD = 2000  # retire and replace a worker after this many chunks. A full build hands one
                            # worker hundreds of thousands of chunks over many hours, all through libzim's
                            # C++ mmap and the HTML parser; recycling bounds whatever they hold on to.
                            # Needs the spawn start method, which this pool already uses.

_WORKER_READER = None     # one archive handle per worker process, opened by _worker_open below


def _worker_open(zim_path: str) -> None:
    """Pool initialiser: give this worker process its own libzim archive over the ZIM on disk."""
    global _WORKER_READER
    from sos.books import open_zim
    _WORKER_READER = open_zim(Path(zim_path))


def _worker_texts(keys: list[str]) -> list[str]:
    """One chunk of keys to their extracted passages -- exactly what the serial path computes in-process."""
    return [_wikipedia_article_text(_WORKER_READER, key) for key in keys]


def _stop_workers(pool: ProcessPoolExecutor) -> None:
    """Kill a wedged pool's worker processes outright. `shutdown(wait=True)` waits for the very chunk that
    has hung, and `wait=False` leaves the processes running; `_processes` is private, but 3.12 offers no
    public way to do this (3.14 added Executor.kill_workers)."""
    for process in list(getattr(pool, "_processes", {}).values()):
        process.terminate()


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
    preload list to stay correct.) The workers therefore always read the real file at `local_path`
    through sos.books.open_zim, which is why build_wikipedia_rerank refuses an `open_zim` override here."""
    if workers <= 1:
        yield ((start, [_wikipedia_article_text(reader, key) for key in all_keys[start:start + BATCH]])
               for start in starts)
        return
    pool = ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn"),
                               initializer=_worker_open, initargs=(str(zim_path),),
                               max_tasks_per_child=MAX_TASKS_PER_CHILD)

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
                texts = future.result(timeout=CHUNK_TIMEOUT_S)
                # refill before the caller embeds, so extraction of later chunks overlaps this one --
                # inside the try because a pool that broke between this result and the next submit is the
                # same interrupted build, and says so rather than escaping raw.
                fill()
            except TimeoutError as exc:
                _stop_workers(pool)   # the outer shutdown(wait=True) would wait on the wedged chunk itself
                raise RuntimeError(
                    f"wikipedia: an article-extraction worker gave nothing back for row {start} in "
                    f"{CHUNK_TIMEOUT_S / 60:.0f} minutes; the workers have been stopped and the build can "
                    f"be resumed from its last checkpoint") from exc
            except BrokenProcessPool as exc:
                raise RuntimeError(
                    f"wikipedia: an article-extraction worker process died at row {start}; the build has "
                    f"stopped and can be resumed from its last checkpoint") from exc
            except Exception as exc:
                raise RuntimeError(
                    f"wikipedia: an article-extraction worker failed at row {start} ({exc}); the build "
                    f"has stopped and can be resumed from its last checkpoint") from exc
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

    `open_zim` overrides how the PARENT opens the archive, for a test that has a reader of its own; the
    workers always open the real file at `local_path` themselves, so the two sides would be reading
    different archives and every row would silently come back zero. `workers` > 1 therefore refuses it.

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
    if open_zim is not None and workers > 1:
        raise ValueError("an open_zim override reaches the parent only, never the worker processes, which "
                         "always read library_items.local_path: use workers=1 with one")
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


def _interrupt(signum, frame) -> None:
    """What SIGTERM does to a build instead of its default. The default stops the process where it
    stands: the `finally` that stops the embedding server never runs, nor the one that shuts the
    extraction pool down, so every worker process is orphaned for good (measured: three of them, and the
    resource tracker, still alive a minute after the parent was signalled). An interruption is a thing
    these builds already know how to survive, so raise one."""
    raise KeyboardInterrupt("stopped by SIGTERM")


@contextmanager
def _interruptible():
    """Run a build with SIGTERM raising an interruption, and hand the signal back as it was found."""
    previous = signal.signal(signal.SIGTERM, _interrupt)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


def _stopped(exc: KeyboardInterrupt, out: Callable, carry_on: str) -> int:
    """What an interrupted build says and exits with: the shell's own 128 + signal number (130 for
    Ctrl-C, 143 for SIGTERM), and one line about where that leaves things -- not a traceback out of the
    middle of a build that in fact lost nothing."""
    by_sigterm = "SIGTERM" in str(exc)
    out(f"stopped by {'SIGTERM' if by_sigterm else 'Ctrl-C'}: {carry_on}")
    return 143 if by_sigterm else 130


def build_wikipedia_cli(settings: Settings, out: Callable = print, run: Callable = subprocess.Popen,
                        cuda: bool = False, resume: bool = True, limit: Optional[int] = None,
                        workers: int = 1, servers: int = 1) -> int:
    """PC only: start the embedding servers if they are not up, embed Wikipedia for rerank-only lookup,
    stop what was started -- structurally build_cli's own pattern, kept a separate function (and a
    separate `sos build-embeddings-wikipedia` subcommand, not a flag on `build-embeddings`) because this
    specific build genuinely takes hours against the real ZIM and must never be triggered by a routine
    `sos build-embeddings` run."""
    from sos.db import connect
    refusal = _missing_model(settings, servers)
    if refusal:
        out(refusal)
        return 1
    conn = None
    try:
        with _interruptible(), embedding_servers(settings, out=out, run=run, cuda=cuda,
                                                 servers=servers) as embed_fn:
            conn = connect(settings.db_path)
            build_wikipedia_rerank(conn, settings, embed_fn, out=out, resume=resume, limit=limit,
                                   workers=workers)
    except EmbedError as exc:
        out(f"FAIL {exc}")
        return 1
    except KeyboardInterrupt as exc:
        return _stopped(exc, out, "run the same command again to carry on from the last checkpoint "
                                  "(--no-resume to start the build afresh instead)")
    finally:
        if conn is not None:
            conn.close()
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


def _server_urls(settings: Settings, servers: int) -> list[str]:
    """`servers` consecutive ports from the one settings.embed_url names, same scheme and host."""
    scheme = settings.embed_url.partition("://")[0] or "http"
    host, port = _host_port(settings.embed_url)
    return [f"{scheme}://{host}:{int(port) + i}" for i in range(servers)]


def _server_healthy(url: str) -> bool:
    try:
        return httpx.get(f"{url}/health", timeout=1.0).status_code == 200
    except httpx.HTTPError:
        return False


def _missing_model(settings: Settings, servers: int) -> Optional[str]:
    """The refusal build_cli and build_wikipedia_cli share, or None to carry on. The model file is what a
    server is *started* from, so it is only required when one has to be started: a port already answering
    /health has always been used as it is (embedding_servers), and that server need not be llama-server
    over settings.embed_model at all -- tools/embed_server_torch.py serves the same model in fp16 from
    Hugging Face with no GGUF on disk anywhere. Insisting on the file first made such a server unusable."""
    if settings.embed_model_path.is_file():
        return None
    if all(_server_healthy(url) for url in _server_urls(settings, servers)):
        return None
    return f"FAIL the embedding model is not at {settings.embed_model_path} (manifest item bge-small-en-v1.5)"


def _even_slices(count: int, parts: int) -> Iterator[tuple[int, int]]:
    """`count` items in `parts` contiguous, as-equal-as-possible pieces, in order."""
    size, extra = divmod(count, parts)
    start = 0
    for i in range(parts):
        end = start + size + (1 if i < extra else 0)
        yield start, end
        start = end


def _embed_across(urls: list[str], client: httpx.Client, pool, texts: list[str],
                  first: int = 0) -> np.ndarray:
    """One batch across several servers at once, back together in the order it was given in. Every slice
    is waited for even after one has failed, so no request outlives the client it was made with; the
    first EmbedError is then raised exactly as a single server's would be, which is what embed_batch's
    shorten-and-retry recovery reads.

    `first` says which server takes the first slice, and the caller moves it on each call: a batch the
    server refused is re-sent one passage at a time, and every one of those is slice 0, so one server
    would otherwise do all the shortening and retrying while the others idled."""
    parts = [texts[start:end] for start, end in _even_slices(len(texts), len(urls))]
    futures = [pool.submit(embed_sync, urls[(i + first) % len(urls)], part, client=client)
               for i, part in enumerate(parts) if part]
    rows, failure = [], None
    for future in futures:
        try:
            rows.append(future.result())
        except EmbedError as exc:
            failure = failure or exc
    if failure is not None:
        raise failure
    return np.concatenate(rows) if rows else np.zeros((0, DIMS), dtype=np.float32)


@contextmanager
def embedding_servers(settings: Settings, out: Callable = print, run: Callable = subprocess.Popen,
                      cuda: bool = False, servers: int = 1):
    """Run `servers` embedding servers side by side and yield the `embed` callable the builds use; stop
    whatever was started here, on every way out.

    One llama-server answers a batch on a single thread -- the HTTP, the JSON, tokenising 32 passages of
    2,500 characters, serialising 32x384 floats back -- and that thread, not the GPU, is what a bulk build
    waits on: measured on the real Wikipedia build, the card drew 28-45 W of its 220 W while the server's
    main thread sat at about 70 per cent of one core (bigger -c/-ub/-b were worth about a tenth). So N
    servers on consecutive ports from settings.embed_url each take a contiguous slice of every batch, sent
    at the same time from a small thread pool (httpx gives the GIL up while it waits on the socket).

    A port that already answers /health is used as it is and never started a second time, exactly as the
    single-server build has always done. `servers=1` takes neither the slicing nor the threads."""
    if servers < 1:
        raise ValueError("servers must be positive")
    urls = _server_urls(settings, servers)
    started: list = []
    client = httpx.Client()
    pool = ThreadPoolExecutor(max_workers=servers, thread_name_prefix="embed") if servers > 1 else None
    try:
        for url in urls:
            if _server_healthy(url):
                continue
            binary = server_command(settings, cuda=True)[0] if cuda else (shutil.which("llama-server") or "/usr/local/bin/llama-server")
            cmd = [binary] + server_command(settings, cuda=cuda)[1:]
            cmd[cmd.index("--port") + 1] = _host_port(url)[1]
            out(f"starting {' '.join(cmd)}")
            started.append(run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        for url in urls:
            for _ in range(60):
                if _server_healthy(url):
                    break
                time.sleep(0.5)
            else:
                raise EmbedError(f"the embedding server on {url} did not come up")
        if pool is None:
            yield lambda texts: embed_sync(urls[0], texts, client=client)
        else:
            turn = itertools.count()
            yield lambda texts: _embed_across(urls, client, pool, texts, next(turn))
    finally:
        if pool is not None:
            pool.shutdown(wait=True)
        client.close()
        for process in started:
            process.terminate()


def build_cli(settings: Settings, out: Callable = print, run: Callable = subprocess.Popen, cuda: bool = False,
              collection: str = "all", servers: int = 1, household_text: str = HOUSEHOLD_TEXT_STYLE) -> int:
    """PC only: start the embedding servers if they are not up, embed the library, stop what was started.
    `cuda=True` (`sos build-embeddings --cuda`) starts the CUDA-built llama-server-cuda instead of the
    plain CPU binary -- for the large bulk builds (household books, Wikipedia) that need GPU offload to be
    tractable."""
    from sos.db import connect
    refusal = _missing_model(settings, servers)
    if refusal:
        out(refusal)
        return 1
    conn = None
    try:
        with _interruptible(), embedding_servers(settings, out=out, run=run, cuda=cuda,
                                                 servers=servers) as embed_fn:
            conn = connect(settings.db_path)
            if collection in ("all", "docs"):
                build(conn, settings, embed_fn, out)
            if collection in ("all", "household"):
                build_household(conn, settings, embed_fn, out=out, text_style=household_text)
    except EmbedError as exc:
        out(f"FAIL {exc}")
        return 1
    except KeyboardInterrupt as exc:
        return _stopped(exc, out, "nothing was published, and whatever the box already had is untouched; "
                                  "this build has no checkpoint, so run the same command again to redo it")
    finally:
        if conn is not None:
            conn.close()
    return 0


class EmbeddingWatch:
    """What one search learned about its own query vector: `failed` is set when the search needed the vector
    and the server gave none. A search that never needed one (no index built, no Wikipedia hit to rerank)
    leaves it False, and its answer is as good as it will ever be."""

    __slots__ = ("failed",)

    def __init__(self) -> None:
        self.failed = False


_watch: contextvars.ContextVar[Optional[EmbeddingWatch]] = contextvars.ContextVar("sos_embedding_watch", default=None)


class _Cached:
    """One collection's loaded store, the mtime it was loaded from, and when it was last looked for."""

    __slots__ = ("store", "stamp", "checked")

    def __init__(self):
        self.store = None
        self.stamp: Optional[tuple] = None
        self.checked = float("-inf")


class Semantic:
    """What the running API holds: the client for the server and the index, read from disk when first asked
    for and read again when the files change (a `sos build-embeddings` copied on later). `query` answers
    with nothing rather than an error whenever any part is missing or slow."""

    QUERY_TIMEOUT_S = 0.6
    THROTTLE_S = 30
    QUERY_TTL_S = 30          # long enough for one search's three collections and a page of typing-ahead
    FAILED_QUERY_TTL_S = 3    # and short enough that a server coming back is waited for, not cached out
    QUERY_MEMO = 8

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = EmbedClient(settings.embed_url)
        self._vectors: dict[str, tuple[Optional[np.ndarray], float]] = {}   # the last few queries embedded
        self._embedding: dict[str, "asyncio.Task"] = {}                     # and the ones in flight now
        # One cache per collection, each with its own throttle clock -- Task 7's own fix round established
        # that sharing one timer between two collections starves whichever one's stat() check runs second
        # (see test_household_index_has_its_own_throttle_clock_not_shared_with_the_docs_index).
        self._docs = _Cached()
        self._household = _Cached()
        self._wikipedia = _Cached()
        self.generation = 0        # goes up whenever a collection's loaded state changes: search's cache keys on it
        self.cache_namespace = uuid.uuid4().hex  # persistent result caches cannot outlive this reader's state

    def _cached(self, state: "_Cached", collection: str, names: tuple[str, ...], load: Callable,
                loaded_message: str):
        """One collection's store, refreshed from disk at most once every THROTTLE_S.

        The throttle holds whether or not a store is loaded. A file still being copied grows, so its
        mtime moves on every request: without the throttle on this side too, every search re-read the
        whole key list -- 8.4 million of them for Wikipedia, about 1.8 s and 700 MB -- and bumped
        `generation`, which throws search's own results cache away. `generation` goes up only when the
        answer a search would get really changes: nothing to something, something to something else, or
        something to nothing. A load that fails is not a change."""
        now = time.monotonic()
        if now - state.checked < self.THROTTLE_S:
            return state.store
        state.checked = now
        folder = Path(self.settings.embeddings_dir)
        try:
            directory = _collection_folder(folder, collection)
            files = [directory / f"{collection}.{name}" for name in names]
            meta_path = directory / f"{collection}.meta.json"
            if not meta_path.exists() and not (folder / meta_path.name).is_symlink():
                meta_path = folder / meta_path.name
            stats = [p.stat() for p in files]
            meta_stat = meta_path.stat() if meta_path.exists() else None
            stamp = (str(directory), *((s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns) for s in stats),
                     None if meta_stat is None else (meta_stat.st_ino, meta_stat.st_size,
                                                    meta_stat.st_mtime_ns, meta_stat.st_ctime_ns))
        except (OSError, RuntimeError):
            try:
                _check_collection(folder, collection, names)
            except (OSError, RuntimeError) as exc:
                _say_once(folder, collection, "files", "unresolvable",
                          f"embeddings: cannot resolve {collection} files; using keyword search ({exc})")
            stamp = None
        if stamp is None:
            state.stamp = None
            if state.store is not None:
                state.store = None
                self.generation += 1
            return None
        if stamp == state.stamp and state.store is not None:
            return state.store
        state.stamp = stamp
        try:
            store = load()
        except (OSError, ValueError, RuntimeError) as exc:
            log.warning("embeddings: cannot load %s; using keyword search (%s)", collection, exc)
            store = None
        if store is None and state.store is None:
            return None
        state.store = store
        self.generation += 1
        if store is not None:
            log.info(loaded_message, len(store))
        return store

    def index(self) -> Optional[Index]:
        return self._cached(self._docs, "docs", ("f16.bin", "ids"),
                            lambda: Index.load(self.settings.embeddings_dir, "docs",
                                               model=self.settings.embed_model),
                            "embeddings: %d passages loaded")

    def household_index(self) -> Optional[ApproxIndex]:
        """The household collection's approximate index (Gutenberg and Survivor Library, one vector per
        book), read and refreshed exactly as `index()` does for the box's own passages -- a second,
        parallel cache rather than a variant of the first, because the two collections' files change on
        their own schedules (a fresh `sos build-embeddings` writes both, but only one need be present)."""
        return self._cached(self._household, "household", ("hnsw", "ids"),
                            lambda: ApproxIndex.load(self.settings.embeddings_dir, "household",
                                                     model=self.settings.embed_model),
                            "embeddings: %d household books loaded")

    def wikipedia_store(self) -> Optional["WikipediaStore"]:
        """The Wikipedia rerank-only store (Task 8), read and refreshed exactly as `index()` and
        `household_index()` do for their own collections -- a third, parallel cache."""
        return self._cached(self._wikipedia, "wikipedia", ("f16.bin", "ids"),
                            lambda: WikipediaStore.load(self.settings.embeddings_dir,
                                                        model=self.settings.embed_model),
                            "embeddings: %d wikipedia rerank vectors loaded")

    def available(self) -> bool:
        return self.index() is not None

    def refresh(self) -> None:
        """Check generations before a result-cache hit can bypass the query methods entirely."""
        self.index()
        self.household_index()
        self.wikipedia_store()

    @contextmanager
    def watch_embedding(self) -> Iterator[EmbeddingWatch]:
        """Everything awaited inside the block, by the task that entered it, reports its query-vector
        failures to the yielded watch: one search's own outcome, not a memo other searches share, so a
        temporary embedding failure is never kept as a persistent keyword-only result and nothing else
        is kept out of the cache."""
        watch = EmbeddingWatch()
        token = _watch.set(watch)
        try:
            yield watch
        finally:
            _watch.reset(token)

    async def _query_vector(self, q: str) -> Optional[np.ndarray]:
        vector = await self._obtain_vector(q)
        if vector is None and q.strip():
            watch = _watch.get()
            if watch is not None:
                watch.failed = True
        return vector

    async def _obtain_vector(self, q: str) -> Optional[np.ndarray]:
        """The query's embedding, asked of the server once however many collections want it.

        One search asks all three: the docs passages, the household books and the Wikipedia rerank.
        Embedding the same words three times over cost up to three 0.6 s timeouts on a loaded box, and
        three times the work on the Pi, whose sos-embed.service is one thread inside MemoryMax=600M. A
        failure is remembered too, briefly, so a server that is down or wedged costs one timeout a
        search rather than three. None means "no vector to be had": every caller answers with nothing,
        exactly as it did when it caught EmbedError itself."""
        text = q.strip()
        if not text:
            return None
        now = time.monotonic()
        remembered = self._vectors.get(text)
        if remembered is not None:
            vector, at = remembered
            if now - at < (self.QUERY_TTL_S if vector is not None else self.FAILED_QUERY_TTL_S):
                return vector
        waiting = self._embedding.get(text)
        if waiting is None:
            waiting = asyncio.create_task(self._embed_query(text))
            self._embedding[text] = waiting
        # The request that started the embedding is just another waiter. A disconnected phone must
        # not cancel work another phone is using; the HTTP client's timeout still bounds that work.
        return await asyncio.shield(waiting)

    async def _embed_query(self, text: str) -> Optional[np.ndarray]:
        vector = None
        try:
            try:
                vector = (await self.client.embed([QUERY_PREFIX + text], timeout=self.QUERY_TIMEOUT_S))[0]
            except EmbedError:
                vector = None
            self._vectors[text] = (vector, time.monotonic())
            while len(self._vectors) > self.QUERY_MEMO:
                self._vectors.pop(next(iter(self._vectors)))
        finally:
            self._embedding.pop(text, None)
        return vector

    async def query(self, q: str, k: int = 20) -> list[tuple[str, float]]:
        """The nearest passages to a query: (url, cosine), best first; empty when semantic search is off."""
        index = self.index()
        if index is None or not q.strip():
            return []
        vec = await self._query_vector(q)
        return index.search(vec, k) if vec is not None else []

    async def query_household(self, q: str, k: int = 20) -> list[tuple[str, float]]:
        """The nearest household books to a query: (key, cosine) where key is "<zim id>:<book id>", best
        first; empty when the household collection or the embedding server is off. Identical in shape to
        `query`, against the household index instead of the docs one."""
        index = self.household_index()
        if index is None or not q.strip():
            return []
        vec = await self._query_vector(q)
        return index.search(vec, k) if vec is not None else []

    async def rerank_wikipedia(self, q: str, keys: list[str]) -> dict[str, float]:
        """Cosine similarity for a handful of already-known Wikipedia article keys against one query
        embedding -- never a nearest-neighbour search, just a few real dot products against the store's own
        rows, so search.py needs no numpy import and no direct coupling to this module's internals. Keys
        with no vector in the store (an absent key, or a soft-redirect stub WikipediaStore.vector_for
        already turns into None) are simply left out of the result rather than scored as zero."""
        store = self.wikipedia_store()
        if store is None or not q.strip():
            return {}
        qvec = await self._query_vector(q)
        if qvec is None:
            return {}
        out: dict[str, float] = {}
        for key in keys:
            vec = store.vector_for(key)
            if vec is not None:
                out[key] = float(np.dot(qvec, vec) / (np.linalg.norm(qvec) * np.linalg.norm(vec) + 1e-9))
        return out
