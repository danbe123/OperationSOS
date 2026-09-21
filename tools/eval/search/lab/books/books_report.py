"""Markdown tables from results/books/eval_<tag>.json (no GPU, no torch).  usage: books_report.py <tag> [--vs <other tag>]
Paired bootstrap intervals over queries (lab/common.paired_bootstrap style, 4,000 resamples).  `*` = interval excludes 0."""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import RESULTS, m_rr, m_hit   # noqa: E402

EVERY = "everyday dev+heldout excl. plots"
SHOW = ["a", "b1", "b2", "c0", "c1", "c2", "dt-k3-max", "dt-k3-mean", "dt-k10-max", "dt-k10-mean", "dt-k10-top2", "dt-k10-pool", "dp-k10-max", "dp-k10-mean", "dp-k10-pool",
        "b2+dt10-max", "b2+dt10-avg(max)", "b2+dt10-pooledvec", "c1+dt10-avg(max)", "c0-gut-only", "pooled-gut-only"]
COLS = ["known", "sl", "extra-dev", "extra-heldout", "dev (tuning pool)"]


def load(tag):
    return json.load(open(RESULTS / "books" / f"eval_{tag}.json"))


def table(res, systems=SHOW, cols=COLS, metrics=("mrr@10", "hit@5", "hit@10")):
    n = res["n_queries"]
    head = "| representation | " + " | ".join(f"{c} (n={n[c]})" for c in cols) + " |"
    out = [head, "|---|" + "--:|" * len(cols)]
    for s in systems:
        out.append(f"| {s} | " + " | ".join("/".join(f"{res['systems'][s][c][m]:.2f}" if m != "mrr@10" else f"{res['systems'][s][c][m]:.3f}" for m in metrics) for c in cols) + " |")
    return "\n".join(out) + "\n\n(each cell: MRR@10 / hit@5 / hit@10)"


def ids_for(res, strata_name, ranks_ref):
    import books_eval as be
    return be.ids_of(strata_name)


def boot(d, n_boot=4000, seed=7):
    d = np.asarray(d, dtype=float)
    rng = np.random.default_rng(seed)
    m = d[rng.integers(0, len(d), size=(n_boot, len(d)))].mean(1)
    return round(float(d.mean()), 3), round(float(np.percentile(m, 2.5)), 3), round(float(np.percentile(m, 97.5)), 3), int((d > 1e-12).sum()), int((d < -1e-12).sum())


def paired_table(resB, sysB, resA, sysA, strata, ids_fn, metric="mrr"):
    rows = []
    for st in strata:
        ids = ids_fn(st)
        ra, rb = resA["systems"][sysA]["ranks"], resB["systems"][sysB]["ranks"]
        f = {"mrr": m_rr, "hit5": lambda r: m_hit(r, 5), "hit10": lambda r: m_hit(r, 10)}[metric]
        d, lo, hi, w, l = boot([f(rb[i]) - f(ra[i]) for i in ids])
        rows.append(f"{d:+.3f} [{lo:+.3f}, {hi:+.3f}]{'*' if lo > 0 or hi < 0 else ' '} ({w}W/{l}L)")
    return rows


if __name__ == "__main__":
    import books_eval as be
    tag = sys.argv[1]
    res = load(tag)
    print(f"### {tag}\n")
    print(table(res))
    print()
    strata = ["known", "sl", "extra-dev", "extra-heldout", EVERY, "dev (tuning pool)"]
    for metric in ("mrr", "hit10"):
        print(f"\nPaired difference vs today's text (a), {metric}:\n")
        print("| representation | " + " | ".join(strata) + " |\n|---|" + "---|" * len(strata))
        for s in SHOW[1:]:
            print(f"| {s} | " + " | ".join(paired_table(res, s, res, "a", strata, be.ids_of, metric)) + " |")
    print("\nnDCG@10 / coverage@10 of the acceptable set:\n")
    print("| representation | " + " | ".join(strata) + " |\n|---|" + "---|" * len(strata))
    for s in SHOW:
        print(f"| {s} | " + " | ".join(f"{res['systems'][s][c]['ndcg@10']:.3f}/{res['systems'][s][c]['cov@10']:.2f}" for c in strata) + " |")
    print("\nScaling (MRR@10 / hit@10 by pool size):\n")
    for size, d in res["scaling"].items():
        print(f"pool {size}: " + "; ".join(f"{n}: known {v['known']['mrr@10']:.3f}/{v['known']['hit@10']:.2f}, everyday {v['everyday']['mrr@10']:.3f}/{v['everyday']['hit@10']:.2f}" for n, v in d.items()))
