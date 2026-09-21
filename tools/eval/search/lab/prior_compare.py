"""Paired comparison of the models AFTER the same authored-passage bonus (1 sd of each model's own cosine), against
the control with the same bonus. Writes results/prior_compare.json."""
import json
from common import *
queries = json.loads((SCRATCH / "queries.json").read_text())
P = json.load(open(RESULTS / "prior.json"))
out = []
for tag in ("e5-base-v2", "gte-base", "granite-embedding-english-r2"):
    a, b = P["bge-small-en-v1.5"]["1.0"]["ranks"], P[tag]["1.0"]["ranks"]
    row = {"comparison": f"{tag} vs bge-small, both with a 1-sd authored bonus"}
    for g in ("paraphrase", "safety", "own-library", "ALL"):
        row[g] = {"mrr@10": paired_bootstrap(queries, a, b, m_rr, g), "hit@1": paired_bootstrap(queries, a, b, lambda r: m_hit(r, 1), g), "hit@5": paired_bootstrap(queries, a, b, lambda r: m_hit(r, 5), g)}
    out.append(row)
    for g in ("paraphrase", "safety", "ALL"):
        x = row[g]["mrr@10"]; print(tag, g, x["diff"], x["ci95"], f"{x['wins']}W/{x['losses']}L")
dump("prior_compare.json", out)
