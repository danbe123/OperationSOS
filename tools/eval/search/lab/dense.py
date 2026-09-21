"""Experiment A: dense retrieval only. Reads the vectors embed.py saved, ranks the corpus per query (exact cosine),
writes results/A_dense.json (per model: summary per group, guard, per-query best rank, paired comparison with the
control) and scratch/top_<tag>.json (top-100 rows and scores per query, for the hybrid and rerank steps)."""
import json, sys
import numpy as np
from common import *

corpus = json.loads((SCRATCH / "corpus.json").read_text())
queries = json.loads((SCRATCH / "queries.json").read_text())
CONTROL = "bge-small-en-v1.5"


def top100(tag, dims=None):
    P = np.load(SCRATCH / f"P_{tag}.npy").astype(np.float32)
    Q = np.load(SCRATCH / f"Q_{tag}.npy").astype(np.float32)
    if dims:                       # Matryoshka-style truncation, renormalised
        P, Q = P[:, :dims], Q[:, :dims]
        P /= np.linalg.norm(P, axis=1, keepdims=True); Q /= np.linalg.norm(Q, axis=1, keepdims=True)
    S = Q @ P.T
    idx = np.argsort(-S, axis=1)[:, :100]
    return {q["id"]: [(int(i), float(S[n, i])) for i in idx[n]] for n, q in enumerate(queries)}


def ranks_from(lists):
    return {q["id"]: best_rank([i for i, _ in lists[q["id"]]], set(q["rel"])) for q in queries}


if __name__ == "__main__":
    tags = sys.argv[1:] or sorted(p.stem[2:] for p in SCRATCH.glob("P_*.npy"))
    res = {}
    all_ranks = {}
    for tag in tags:
        lists = top100(tag)
        (SCRATCH / f"top_{tag}.json").write_text(json.dumps(lists))
        r = ranks_from(lists)
        all_ranks[tag] = r
        emb = json.loads((RESULTS / "embed" / f"{tag}.json").read_text())
        res[tag] = {"summary": summarise(queries, r), "guard": guard_top3(queries, r), "ranks": r,
                    "params_M": round(emb["params"] / 1e6, 1), "dims": emb["dims"], "passages_per_s": emb["passages_per_s"]}
    ctl = all_ranks.get(CONTROL)
    if ctl:
        for tag in tags:
            if tag == CONTROL:
                continue
            res[tag]["vs_control"] = {g: {"mrr@10": paired_bootstrap(queries, ctl, all_ranks[tag], m_rr, g),
                                          "hit@5": paired_bootstrap(queries, ctl, all_ranks[tag], lambda r: m_hit(r, 5), g)}
                                      for g in ("paraphrase", "safety", "own-library", "ALL")}
    dump("A_dense.json", res)
    print(f"{'model':38s} {'par h@1':>7} {'h@5':>6} {'mrr':>6} | {'saf h@1':>7} {'h@3':>6} {'mrr':>6} {'guard':>5} | {'own h@5':>7} {'mrr':>6}")
    for tag in sorted(tags, key=lambda t: -res[t]["summary"]["ALL"]["mrr@10"]):
        s = res[tag]["summary"]
        print(f"{tag:38s} {s['paraphrase']['hit@1']:7.3f} {s['paraphrase']['hit@5']:6.3f} {s['paraphrase']['mrr@10']:6.3f} | "
              f"{s['safety']['hit@1']:7.3f} {s['safety']['hit@3']:6.3f} {s['safety']['mrr@10']:6.3f} {res[tag]['guard']['in_top3']:>3}/34 | "
              f"{s['own-library']['hit@5']:7.3f} {s['own-library']['mrr@10']:6.3f}")
