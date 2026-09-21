"""Shared pieces of the model bake-off: the corpus (exactly what `sos build-embeddings` embeds for the box's
own library), the gold queries that can be answered from it, and the metrics. Read-only on the dev database."""
from __future__ import annotations

import json
import math
import os
import sqlite3
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent
REPO = LAB.parents[3]
sys.path.insert(0, str(REPO / "api"))

DB_PATH = "/home/dan/OperationSOS/.dev/state/sos.db"
SCRATCH = Path(os.environ.get("LAB_SCRATCH", "/tmp/claude-1000/-home-dan/c0534df7-5406-4037-af74-30748090450c/scratchpad/lab"))
RESULTS = LAB / "results"
SETS = ("own-library", "paraphrase", "safety")
TOP = 10


def connect_ro() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_corpus(conn=None) -> list[dict]:
    """Rows in `sos build-embeddings` order, with the text the box embeds for each (passage_text)."""
    from sos.embeddings import SKIP_SECTIONS, passage_text
    conn = conn or connect_ro()
    rows = [r for r in conn.execute("SELECT url, title, body, kind FROM fts_docs WHERE kind != 'item' ORDER BY rowid").fetchall()
            if r["url"].split("#", 1)[-1] not in SKIP_SECTIONS]
    return [{"url": r["url"], "title": r["title"], "kind": r["kind"], "text": passage_text(r["title"], r["body"], r["url"])}
            for r in rows]


def load_queries(conn, corpus_urls) -> tuple[list[dict], dict]:
    """The gold rows of own-library, paraphrase and safety whose answer is resident in the corpus. Each returned
    query carries `rel`: the set of corpus row indexes that count as relevant (any alternative)."""
    from sos import searcheval
    from sos.evalrun import url_matches
    rows, problems = searcheval.load_gold(searcheval.DEFAULT_GOLD_DIR, list(SETS))
    assert not problems, problems
    kept, dropped = [], {s: [] for s in SETS}
    total = {s: 0 for s in SETS}
    for row in rows:
        total[row.set] += 1
        exp_urls = []
        for entry in row.expected:
            exp_urls += searcheval.resolve_urls(entry, conn)
        rel = [i for i, u in enumerate(corpus_urls) if any(url_matches(u, e) for e in exp_urls)]
        if not rel:
            dropped[row.set].append(row.id)
            continue
        kept.append({"id": row.id, "set": row.set, "group": row.group, "tags": list(row.tags), "query": row.query,
                     "expected": exp_urls, "rel": rel})
    info = {"total": total, "kept": {s: sum(1 for q in kept if q["set"] == s) for s in SETS}, "dropped": dropped}
    return kept, info


def best_rank(order, rel: set, depth: int | None = None) -> int | None:
    """1-based rank of the first relevant passage in `order` (a sequence of corpus row indexes)."""
    for pos, idx in enumerate(order, 1):
        if depth is not None and pos > depth:
            return None
        if idx in rel:
            return pos
    return None


def m_hit(rank, k):
    return 1.0 if rank is not None and rank <= k else 0.0


def m_rr(rank):
    return 1.0 / rank if rank is not None and rank <= TOP else 0.0


def m_ndcg(rank):
    return 1.0 / math.log2(rank + 1) if rank is not None and rank <= TOP else 0.0


def groups_of(q: dict) -> list[str]:
    names = [q["set"], "ALL"]
    if q["group"]:
        names.append(f"{q['set']}/{q['group']}")
    return names


def summarise(queries: list[dict], ranks: dict[str, int | None]) -> dict:
    """{group: {n, hit@1/3/5/10, mrr@10, ndcg@10}} for one system's ranks (id -> best rank or None)."""
    buckets: dict[str, list] = {}
    for q in queries:
        for g in groups_of(q):
            buckets.setdefault(g, []).append(ranks[q["id"]])
    out = {}
    for g, rs in buckets.items():
        n = len(rs)
        out[g] = {"n": n, **{f"hit@{k}": round(sum(m_hit(r, k) for r in rs) / n, 4) for k in (1, 3, 5, 10)},
                  "mrr@10": round(sum(m_rr(r) for r in rs) / n, 4), "ndcg@10": round(sum(m_ndcg(r) for r in rs) / n, 4)}
    return out


def guard_top3(queries, ranks) -> dict:
    """The safety guard: rows whose card must be in the top 3."""
    miss = [q["id"] for q in queries if q["set"] == "safety" and not (ranks[q["id"]] is not None and ranks[q["id"]] <= 3)]
    return {"in_top3": sum(1 for q in queries if q["set"] == "safety") - len(miss), "of": sum(1 for q in queries if q["set"] == "safety"),
            "missing": miss}


def paired_bootstrap(queries, ranks_a, ranks_b, metric, group: str, n_boot: int = 4000, seed: int = 7) -> dict:
    """Paired comparison of system B minus system A on `metric` (a function of a rank) over the queries of `group`:
    mean difference, a 95% bootstrap interval, and the win/loss/tie counts of B against A."""
    import numpy as np
    ids = [q["id"] for q in queries if group in groups_of(q)]
    d = np.array([metric(ranks_b[i]) - metric(ranks_a[i]) for i in ids], dtype=float)
    rng = np.random.default_rng(seed)
    means = d[rng.integers(0, len(d), size=(n_boot, len(d)))].mean(axis=1) if len(d) else np.zeros(1)
    return {"n": len(ids), "diff": round(float(d.mean()), 4) if len(d) else 0.0,
            "ci95": [round(float(np.percentile(means, 2.5)), 4), round(float(np.percentile(means, 97.5)), 4)],
            "wins": int((d > 1e-12).sum()), "losses": int((d < -1e-12).sum()), "ties": int((abs(d) <= 1e-12).sum())}


def dump(name: str, obj) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    p = RESULTS / name
    p.write_text(json.dumps(obj, indent=1, sort_keys=False), encoding="utf-8")
    return p
