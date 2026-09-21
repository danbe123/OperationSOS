"""Paired comparisons of the headline systems (system B minus system A): mean difference, 95% bootstrap interval
over queries, and win/loss/tie counts, for hit@1, hit@5 and MRR@10, on paraphrase, safety, own-library and ALL.
Reads the ranks stored in A_dense/B_hybrid/C_rerank. Writes results/headline.json."""
import json
from common import *
queries = json.loads((SCRATCH / "queries.json").read_text())
A = json.load(open(RESULTS / "A_dense.json")); B = json.load(open(RESULTS / "B_hybrid.json")); C = json.load(open(RESULTS / "C_rerank.json"))


def ranks(spec):
    kind, *rest = spec.split("|")
    if kind == "dense":
        return A[rest[0]]["ranks"]
    if kind == "hyb":
        return B[rest[0]][rest[1]]["ranks"]
    if kind == "rr":                     # rr|pool|reranker|ce or blend
        return C["pools"][rest[0]]["rerankers"][rest[1]][rest[2]]["ranks"]
    if kind == "pool":
        return C["pools"][rest[0]]["baseline"]["ranks"]
    raise KeyError(spec)


PAIRS = [
    ("dense: e5-base-v2 vs control", "dense|bge-small-en-v1.5", "dense|e5-base-v2"),
    ("dense: gte-base vs control", "dense|bge-small-en-v1.5", "dense|gte-base"),
    ("dense: granite-embedding-english-r2 (149M) vs control", "dense|bge-small-en-v1.5", "dense|granite-embedding-english-r2"),
    ("dense: granite-embedding-small-english-r2 (47M) vs control", "dense|bge-small-en-v1.5", "dense|granite-embedding-small-english-r2"),
    ("dense: e5-small-v2 vs control", "dense|bge-small-en-v1.5", "dense|e5-small-v2"),
    ("dense: bge-base-en-v1.5 vs control", "dense|bge-small-en-v1.5", "dense|bge-base-en-v1.5"),
    ("dense: bge-large-en-v1.5 (upper bound) vs control", "dense|bge-small-en-v1.5", "dense|bge-large-en-v1.5"),
    ("dense: mxbai-embed-large-v1 (upper bound) vs control", "dense|bge-small-en-v1.5", "dense|mxbai-embed-large-v1"),
    ("dense: e5-base-v2 vs gte-base", "dense|gte-base", "dense|e5-base-v2"),
    ("dense: e5-base-v2 vs granite-embedding-english-r2", "dense|granite-embedding-english-r2", "dense|e5-base-v2"),
    ("dense: shipped index (production's shortened passages) vs control clean 512-token cut", "dense|bge-small-en-v1.5", "dense|shipped-index"),
    ("control: RRF+keyword(prod) vs control dense", "dense|bge-small-en-v1.5", "hyb|bge-small-en-v1.5|rrf+prod"),
    ("e5-base-v2: RRF+keyword(prod) vs e5-base-v2 dense", "dense|e5-base-v2", "hyb|e5-base-v2|rrf+prod"),
    ("e5-base-v2: wsum0.7+prod vs e5-base-v2 dense", "dense|e5-base-v2", "hyb|e5-base-v2|wsum0.7+prod"),
    ("hybrid RRF+prod: e5-base-v2 vs control", "hyb|bge-small-en-v1.5|rrf+prod", "hyb|e5-base-v2|rrf+prod"),
    ("hybrid wsum0.7+prod: e5-base-v2 vs control", "hyb|bge-small-en-v1.5|wsum0.7+prod", "hyb|e5-base-v2|wsum0.7+prod"),
    ("e5-base-v2 dense vs control production-shape hybrid (RRF+prod)", "hyb|bge-small-en-v1.5|rrf+prod", "dense|e5-base-v2"),
    ("hybrid RRF+prod: gte-base vs control", "hyb|bge-small-en-v1.5|rrf+prod", "hyb|gte-base|rrf+prod"),
    ("hybrid RRF+prod: granite-embedding-english-r2 vs control", "hyb|bge-small-en-v1.5|rrf+prod", "hyb|granite-embedding-english-r2|rrf+prod"),
    ("hybrid RRF+prod: granite-embedding-small-english-r2 vs control", "hyb|bge-small-en-v1.5|rrf+prod", "hyb|granite-embedding-small-english-r2|rrf+prod"),
]
for pool in C["pools"]:
    for rr in ("gte-reranker-modernbert-base", "bge-reranker-v2-m3", "mxbai-rerank-base-v1", "mxbai-rerank-xsmall-v1"):
        for var in ("ce", "blend"):
            PAIRS.append((f"rerank {var}: {rr} on pool {pool}", f"pool|{pool}", f"rr|{pool}|{rr}|{var}"))
PAIRS.append(("control pool (RRF+prod) + gte-reranker-modernbert blend vs e5-base-v2 dense", "dense|e5-base-v2", "rr|bge-small-en-v1.5:rrf+prod|gte-reranker-modernbert-base|blend"))
PAIRS.append(("e5-base-v2 dense + gte-reranker-modernbert blend vs control production-shape hybrid", "hyb|bge-small-en-v1.5|rrf+prod", "rr|e5-base-v2:dense|gte-reranker-modernbert-base|blend"))

out = []
for label, a, b in PAIRS:
    ra, rb = ranks(a), ranks(b)
    row = {"comparison": label, "a": a, "b": b}
    for g in ("paraphrase", "safety", "own-library", "ALL"):
        row[g] = {"mrr@10": paired_bootstrap(queries, ra, rb, m_rr, g), "hit@1": paired_bootstrap(queries, ra, rb, lambda r: m_hit(r, 1), g),
                  "hit@5": paired_bootstrap(queries, ra, rb, lambda r: m_hit(r, 5), g)}
    out.append(row)
dump("headline.json", out)


def cell(x):
    sig = "*" if (x["ci95"][0] > 0 or x["ci95"][1] < 0) else " "
    return f"{x['diff']:+.3f} [{x['ci95'][0]:+.3f},{x['ci95'][1]:+.3f}]{sig} {x['wins']}/{x['losses']}"


if __name__ == "__main__":
    for r in out:
        print(f"\n{r['comparison']}")
        for g in ("paraphrase", "safety", "ALL"):
            print(f"   {g:11s} mrr {cell(r[g]['mrr@10'])}   hit@1 {cell(r[g]['hit@1'])}   hit@5 {cell(r[g]['hit@5'])}")
