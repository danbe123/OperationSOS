#!/usr/bin/env python3
"""A parameter grid over the lab's replay: every combination is one experiment, judged on the TUNE half of
paraphrase and safety (lab.halves) and reported on the CHECK half and on own-library, which tuning never saw.

    PYTHONPATH=api python tools/eval/search/grid.py --replay DIR --grid additive|rrf [--top 12] [--jobs 6]
"""
from __future__ import annotations

import argparse
import itertools
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab                                   # noqa: E402

BASE = {"T.protect": "title", "T.protect_share": 0.66, "T.cards_first": True,
        "T.card_kw": True, "T.card_cos": 0.62, "T.card_scope": "best", "T.card_n": 2}
SETS = ["own-library", "paraphrase", "safety"]


def grid(kind: str):
    if kind == "additive":
        for w, own_f, doc_f, doc_w, own_c in itertools.product((0.35, 0.5, 0.7), (-0.02, 0.0, 0.03), (0.0, 0.03, 0.06),
                                                                (0.5, 1.0), (0.75, 0.82)):
            yield (f"add w{w} of{own_f:+.2f} df{doc_f:+.2f} dw{doc_w} oc{own_c}",
                   {**BASE, "SEMANTIC_WEIGHT": w, "T.class_floor": {"own": own_f, "doc": doc_f},
                    "T.class_weight": {"doc": doc_w}, "T.class_ceil": {"own": own_c}})
    else:
        for w, own_f, doc_f, doc_w in itertools.product((1.5, 2.0, 2.5, 3.0), (-0.02, 0.0, 0.03), (0.0, 0.03, 0.06), (0.5, 0.75, 1.0)):
            yield (f"rrf w{w} of{own_f:+.2f} df{doc_f:+.2f} dw{doc_w}",
                   {**BASE, "T.fusion": "rrf", "T.rrf_weight": w, "T.class_floor": {"own": own_f, "doc": doc_f},
                    "T.class_weight": {"doc": doc_w}})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", required=True)
    ap.add_argument("--grid", choices=("additive", "rrf"), required=True)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--jobs", type=int, default=6)
    args = ap.parse_args()
    lab.SETS[:] = SETS
    experiments = dict(grid(args.grid))
    jobs = [("control", {}, args.replay, "on"), ("BASE", BASE, args.replay, "on")] + \
           [(n, o, args.replay, "on") for n, o in experiments.items()]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lab.run_experiment, jobs))
    tune, check = lab.halves(results[0]["queries"])

    def figures(r):
        out = {}
        for label, subset in (("tune", tune), ("check", check)):
            s = lab.summarise(r, subset)
            out[label] = (s["paraphrase"]["mrr@10"], s["paraphrase"]["hit@3"], s["safety"]["mrr@10"], s["safety"]["hit@3"])
        s = lab.summarise(r)
        out["own"] = (s["own-library"]["hit@1"], s["own-library"]["hit@3"], s["own-library"]["mrr@10"])
        g = lab.safety_guard(r)
        out["plain"], out["hard"] = g["plain_top3"], g["hard_top3"]
        return out

    rows = [(r["name"], figures(r)) for r in results]
    objective = lambda f: f["tune"][0] + f["tune"][2]        # paraphrase MRR + safety MRR, tune half
    head = f"{'config':<44} | tune: para mrr h3, safety mrr h3 | check: same | own h1 h3 mrr | plain hard"
    print(head)
    for name, f in [rows[0], rows[1]] + sorted(rows[2:], key=lambda r: -objective(r[1]))[:args.top]:
        t, c, o = f["tune"], f["check"], f["own"]
        print(f"{name:<44} | {t[0]:.3f} {t[1]:.3f}  {t[2]:.3f} {t[3]:.3f} | {c[0]:.3f} {c[1]:.3f}  {c[2]:.3f} {c[3]:.3f} | "
              f"{o[0]:.3f} {o[1]:.3f} {o[2]:.3f} | {f['plain']}/17 {f['hard']}/17")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
