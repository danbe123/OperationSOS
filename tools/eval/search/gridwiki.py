#!/usr/bin/env python3
"""Grid over the Wikipedia rerank ramp (floor, ceiling, weight) on top of the lab's T1 configuration, judged on the
TUNE half of the wikipedia set and reported on its CHECK half and on the sets the rerank must not hurt.

    PYTHONPATH=api python tools/eval/search/gridwiki.py --replay DIR [--top 15]
"""
from __future__ import annotations

import argparse
import itertools
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab                                   # noqa: E402

T1 = lab.EXPERIMENTS["T1"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", required=True)
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--jobs", type=int, default=6)
    args = ap.parse_args()
    lab.SETS[:] = ["own-library", "paraphrase", "safety", "wikipedia"]
    exps = {f"ramp f{f} c{c} w{w}": {**T1, "T.wiki": "ramp", "T.wiki_floor": f, "T.wiki_ceil": c, "T.wiki_weight": w,
                                                "T.wiki_skip_medical": True}
            for f, c, w in itertools.product((0.68, 0.72, 0.76), (0.82, 0.86), (0.25, 0.4, 0.6, 0.8)) if c > f}
    jobs = [("keyword", {}, args.replay, "off"), ("T1", T1, args.replay, "on")] + [(n, o, args.replay, "on") for n, o in exps.items()]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lab.run_experiment, jobs))
    tune, check = lab.halves(results[0]["queries"])
    print(f"{'config':<26} | wiki tune h1 h3 mrr | wiki check h1 h3 mrr | own h1 h3 | safety h1 h3 | plain hard | para mrr")
    rows = []
    for r in results:
        t, c, a = lab.summarise(r, tune), lab.summarise(r, check), lab.summarise(r)
        g = lab.safety_guard(r)
        rows.append((t["wikipedia"]["mrr@10"], r["name"], t, c, a, g))
    for _m, name, t, c, a, g in rows[:2] + sorted(rows[2:], key=lambda x: -x[0])[:args.top]:
        w1, w2 = t["wikipedia"], c["wikipedia"]
        print(f"{name:<26} | {w1['hit@1']:.3f} {w1['hit@3']:.3f} {w1['mrr@10']:.3f} | {w2['hit@1']:.3f} {w2['hit@3']:.3f} {w2['mrr@10']:.3f} | "
              f"{a['own-library']['hit@1']:.3f} {a['own-library']['hit@3']:.3f} | {a['safety']['hit@1']:.3f} {a['safety']['hit@3']:.3f} | "
              f"{g['plain_top3']}/17 {g['hard_top3']}/17 | {a['paraphrase']['mrr@10']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
