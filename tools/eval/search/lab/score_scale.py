"""Cosine scales differ between models, and search.py's meaning layer is gated by fixed cosine floors calibrated on
bge-small (SEMANTIC_FLOOR 0.60/0.66/0.74, SEMANTIC_CEIL 0.82). How do those gates fall on each model's scores?
Per model: percentiles of the top-1 and top-20 cosine per query, of the cosine of the best relevant passage, and of the
cosine of a random passage; and the share of queries whose top-20 clear the smallest floor (0.60)."""
import json, numpy as np
from common import *
queries = json.loads((SCRATCH / "queries.json").read_text())
out = {}
rng = np.random.default_rng(0)
for tag in ["bge-small-en-v1.5", "e5-base-v2", "e5-small-v2", "gte-base", "granite-embedding-english-r2", "granite-embedding-small-english-r2", "bge-base-en-v1.5"]:
    P = np.load(SCRATCH / f"P_{tag}.npy").astype(np.float32); Q = np.load(SCRATCH / f"Q_{tag}.npy").astype(np.float32)
    S = Q @ P.T
    top = -np.sort(-S, axis=1)[:, :20]
    goldc = np.array([S[n, list(q["rel"])].max() for n, q in enumerate(queries)])
    rnd = S[:, rng.integers(0, S.shape[1], 2000)].ravel()
    pc = lambda a: [round(float(np.percentile(a, p)), 3) for p in (5, 50, 95)]
    out[tag] = {"top1_cos_p5_p50_p95": pc(top[:, 0]), "top20th_cos_p5_p50_p95": pc(top[:, 19]), "best_relevant_cos_p5_p50_p95": pc(goldc),
                "random_passage_cos_p5_p50_p95": pc(rnd), "share_of_top20_at_or_above_0.60": round(float((top >= 0.60).mean()), 3),
                "share_of_top20_at_or_above_0.74": round(float((top >= 0.74).mean()), 3), "share_of_queries_with_no_top20_above_0.60": round(float((top[:, 0] < 0.60).mean()), 3)}
    print(tag, out[tag])
dump("score_scale.json", out)
