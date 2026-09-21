"""Fairness check on the gold: every relevant passage in these gold sets is one of the box's 634 authored passages
(cards, modules, pages, playbooks; 3% of the corpus), and e5-base-v2 puts those first far more often than bge-small
(bias.json). The box's search already boosts authored kinds (PLAYBOOK_WEIGHT, MEDICAL_BOOST, ...). So: how much of
the model gap does a flat additive bonus for authored passages on the cosine buy the control (and the others)?
The bonus is a diagnostic, not a recommendation: delta is swept, never tuned per model. Writes results/prior.json."""
import json, numpy as np
from common import *
corpus = json.loads((SCRATCH / "corpus.json").read_text()); queries = json.loads((SCRATCH / "queries.json").read_text())
auth = np.array([c["kind"] in {"card", "module", "page", "playbook"} for c in corpus], dtype=np.float32)
out = {}
for tag in ["bge-small-en-v1.5", "e5-base-v2", "gte-base", "granite-embedding-english-r2"]:
    P = np.load(SCRATCH / f"P_{tag}.npy").astype(np.float32); Q = np.load(SCRATCH / f"Q_{tag}.npy").astype(np.float32)
    S = Q @ P.T
    sd = float(np.std(S))
    out[tag] = {}
    for mult in (0, 0.5, 1.0, 1.5, 2.0):          # bonus in units of the model's own cosine std, so scales are comparable
        d = mult * sd
        T = S + d * auth
        order = np.argsort(-T, axis=1)[:, :10]
        ranks = {q["id"]: best_rank(order[n].tolist(), set(q["rel"])) for n, q in enumerate(queries)}
        s = summarise(queries, ranks)
        out[tag][str(mult)] = {"bonus": round(d, 4), "par": s["paraphrase"], "safety": s["safety"], "own": s["own-library"], "guard": guard_top3(queries, ranks)["in_top3"], "ALL_mrr": s["ALL"]["mrr@10"],
                               "ranks": ranks}
        print(f"{tag:30s} bonus {mult:>3}sd ({d:.3f}) par h1 {s['paraphrase']['hit@1']:.3f} h5 {s['paraphrase']['hit@5']:.3f} mrr {s['paraphrase']['mrr@10']:.3f} | saf h1 {s['safety']['hit@1']:.3f} h3 {s['safety']['hit@3']:.3f} guard {out[tag][str(mult)]['guard']}/34 | own mrr {s['own-library']['mrr@10']:.3f} | ALL {s['ALL']['mrr@10']:.3f}")
dump("prior.json", out)
