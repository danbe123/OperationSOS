# api/sos/searchreplay.py
"""Record and replay for the search benchmark (`sos eval-search --record DIR` / `--replay DIR`).

A live run costs about 35 minutes because every query is a round of Kiwix full-text searches (about 1.3 s) and
an embedding call. Everything `sos.search.search()` takes from those services is small and fixed for a given
query, so a live run can keep it, and a later run can put it back with no service at all: the same `search()`
code runs against the same database and the same recorded answers, deterministically and in a fraction of the
time, so a change to the fusion (weights, floors, rules) is measured against the same evidence.

What is kept, per distinct query text, in `DIR/<sha1 of the query>.json`:

  kiwix     every multi-archive request search() made, keyed by its archives and pattern: the hits (title, path,
            snippet, archive), or the refusal (timeout, HTTP status, network fault) it got
  semantic  the query's embedding, the nearest passages of the box's own library and the household books (the
            top RECORD_K of each, deeper than search() asks for so a lab can ask for more), and the cosine of
            every Wikipedia article the rerank was asked about

What is not kept: the database (fts_docs, the library items; replay opens the same file read-only) and the vector
files. A replay against a rebuilt database or a rebuilt index measures the new data against the old Kiwix answers,
which is fair for the Kiwix side and stale for the meaning side: record again after an index rebuild.
"""
from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional

import httpx
import numpy as np

from sos.kiwix import KiwixError, KiwixHit

RECORD_K = 100          # how deep the nearest-passage lists are kept, past the SEMANTIC_K search() asks for
FORMAT = 1


def query_key(query: str) -> str:
    return hashlib.sha1(query.strip().encode("utf-8")).hexdigest()


def request_key(names: list[str], pattern: str) -> str:
    return json.dumps([list(names), pattern], ensure_ascii=False)


def _encode_vector(vec) -> Optional[str]:
    return None if vec is None else base64.b64encode(np.asarray(vec, dtype=np.float32).tobytes()).decode("ascii")


def _decode_vector(text: Optional[str]) -> Optional[np.ndarray]:
    return None if text is None else np.frombuffer(base64.b64decode(text), dtype=np.float32).copy()


def write_atomic(path: Path, doc: Any) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, path)


# --- recording -----------------------------------------------------------------------------------------------------

class Recorder:
    """The answers each query consumed, kept in memory and written to `folder` as they arrive. Asked again (a
    retried search), a query keeps what was answered, never replacing an answer with a refusal."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.queries: dict[str, dict] = {}

    def _slot(self, query: str) -> dict:
        key = query_key(query)
        if key not in self.queries:
            self.queries[key] = {"format": FORMAT, "query": query.strip(), "kiwix": {}, "semantic": None}
        return self.queries[key]

    def kiwix(self, query: str, names: list[str], pattern: str, n: int, answer: dict) -> None:
        slot = self._slot(query)["kiwix"]
        key = request_key(names, pattern)
        if "hits" in answer or key not in slot or "hits" not in slot[key]:
            slot[key] = {**answer, "n": n}

    def semantic(self, query: str, **parts: Any) -> None:
        slot = self._slot(query)
        merged = dict(slot.get("semantic") or {})
        for name, value in parts.items():
            if isinstance(value, dict):
                merged[name] = {**merged.get(name, {}), **value}
            elif value is not None:
                merged[name] = value
        slot["semantic"] = merged

    def flush(self, query: str) -> None:
        write_atomic(self.folder / f"{query_key(query)}.json", self._slot(query))

    def write_meta(self, meta: dict) -> None:
        write_atomic(self.folder / "meta.json", {"format": FORMAT, **meta})


class RecordingKiwix:
    """Passes every search to the real client and notes what came back, hits or refusal alike."""

    def __init__(self, inner, recorder: Recorder):
        self.inner, self.recorder = inner, recorder
        self.query = ""          # the query being searched: set by the harness before each search

    async def search(self, books: list[str], q: str, n: int = 8, timeout: float = 2.0):
        try:
            hits = await self.inner.search(books, q, n, timeout)
        except asyncio.TimeoutError:
            self.recorder.kiwix(self.query, books, q, n, {"error": "timeout"})
            raise
        except KiwixError as exc:
            self.recorder.kiwix(self.query, books, q, n, {"error": "kiwix", "status": exc.status, "message": str(exc)})
            raise
        except (httpx.HTTPError, OSError) as exc:
            self.recorder.kiwix(self.query, books, q, n, {"error": "network", "message": f"{type(exc).__name__}: {exc}"})
            raise
        self.recorder.kiwix(self.query, books, q, n, {"hits": [[h.title, h.path, h.snippet, h.book] for h in hits]})
        return hits

    def __getattr__(self, name):
        return getattr(self.inner, name)


class RecordingSemantic:
    """Passes every call to the real `Semantic` and notes the answers. The nearest lists are asked for
    RECORD_K deep and cut to what search() asked for, so the record can serve a deeper question later."""

    def __init__(self, inner, recorder: Recorder):
        self.inner, self.recorder = inner, recorder

    def _note_vector(self, q: str) -> None:
        remembered = self.inner._vectors.get(q.strip())
        self.recorder.semantic(q, vector=_encode_vector(remembered[0]) if remembered is not None and remembered[0] is not None else None)

    async def query(self, q: str, k: int = 20):
        near = await self.inner.query(q, max(k, RECORD_K))
        self._note_vector(q)
        self.recorder.semantic(q, docs=[[u, c] for u, c in near])
        return near[:k]

    async def query_household(self, q: str, k: int = 20):
        near = await self.inner.query_household(q, max(k, RECORD_K))
        self._note_vector(q)
        self.recorder.semantic(q, household=[[u, c] for u, c in near])
        return near[:k]

    async def rerank_wikipedia(self, q: str, keys: list[str]) -> dict[str, float]:
        cosines = await self.inner.rerank_wikipedia(q, keys)
        self._note_vector(q)
        self.recorder.semantic(q, wiki={key: cosines.get(key) for key in keys})   # None: asked, no vector
        return cosines

    def __getattr__(self, name):
        return getattr(self.inner, name)


# --- replaying -----------------------------------------------------------------------------------------------------

class ReplayError(RuntimeError):
    """A replay asked for something the recording does not hold (a query never recorded)."""


class Replay:
    """A recording folder, read query by query on demand, and a count of every question it could not answer."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.meta: dict = {}
        with contextlib.suppress(OSError, ValueError):
            self.meta = json.loads((self.folder / "meta.json").read_text(encoding="utf-8"))
        self._cache: dict[str, dict] = {}
        self.misses: dict[str, int] = {"kiwix": 0, "wikipedia": 0}

    def get(self, query: str) -> dict:
        key = query_key(query)
        if key not in self._cache:
            try:
                self._cache[key] = json.loads((self.folder / f"{key}.json").read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ReplayError(f"no recording of the query {query!r} in {self.folder}") from exc
        return self._cache[key]

    def has(self, query: str) -> bool:
        return (self.folder / f"{query_key(query)}.json").exists()


class ReplayKiwix:
    """Answers `search()` from the recording of the query set by the harness (`.query`)."""

    def __init__(self, replay: Replay):
        self.replay = replay
        self.query = ""

    async def search(self, books: list[str], q: str, n: int = 8, timeout: float = 2.0):
        recorded = self.replay.get(self.query)["kiwix"].get(request_key(books, q))
        if recorded is None:
            self.replay.misses["kiwix"] += 1
            raise KiwixError(f"replay: no recorded answer for {books} / {q!r}")
        error = recorded.get("error")
        if error == "timeout":
            raise asyncio.TimeoutError()
        if error == "kiwix":
            raise KiwixError(recorded.get("message", ""), status=recorded.get("status"))
        if error:
            raise httpx.ConnectError(recorded.get("message", "recorded network fault"))
        return [KiwixHit(title=t, path=p, snippet=s, book=b) for t, p, s, b in recorded["hits"][:n]]

    async def aclose(self) -> None:
        return None


class ReplaySemantic:
    """The `Semantic` search() sees, answering from the recording. Used for the meaning-on mode only: a
    keyword-only replay passes None, as a live run does."""

    generation = 0
    cache_namespace = "replay"

    def __init__(self, replay: Replay):
        self.replay = replay
        self._vectors: dict[str, tuple[Optional[np.ndarray], float]] = {}

    def refresh(self) -> None:
        return None

    @contextlib.contextmanager
    def watch_embedding(self):
        from sos.embeddings import EmbeddingWatch
        yield EmbeddingWatch()

    def _semantic(self, q: str) -> dict:
        return self.replay.get(q).get("semantic") or {}

    def vector(self, q: str) -> Optional[np.ndarray]:
        return _decode_vector(self._semantic(q).get("vector"))

    def _remember(self, q: str) -> None:
        self._vectors[q.strip()] = (self.vector(q), 0.0)

    async def query(self, q: str, k: int = 20):
        self._remember(q)
        return [(u, float(c)) for u, c in self._semantic(q).get("docs", [])][:k]

    async def query_household(self, q: str, k: int = 20):
        self._remember(q)
        return [(u, float(c)) for u, c in self._semantic(q).get("household", [])][:k]

    async def rerank_wikipedia(self, q: str, keys: list[str]) -> dict[str, float]:
        self._remember(q)
        recorded = self._semantic(q).get("wiki", {})
        self.replay.misses["wikipedia"] += sum(1 for key in keys if key not in recorded)
        return {key: float(recorded[key]) for key in keys if recorded.get(key) is not None}
