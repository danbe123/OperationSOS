"""Experiment B: dense + keyword fusion. For each model: dense only, keyword only (bm25 and prod variants) and
fusions of both, all over top-100 lists. RRF k=60 (no tuning); weighted min-max score fusion at alpha (weight of the
dense side) 0.3/0.5/0.7. Writes results/B_hybrid.json.   usage: hybrid.py <tag> [<tag> ...]"""
import json, sys
from common import *

queries = json.loads((SCRATCH / "queries.json").read_text())
KW = json.loads((SCRATCH / "kw.json").read_text())
RRF_K = 60
ALPHAS = (0.3, 0.5, 0.7)


def rrf(a, b, k=RRF_K):
    s = {}
    for lst in (a, b):
        for rank, (i, _) in enumerate(lst, 1):
            s[i] = s.get(i, 0.0) + 1.0 / (k + rank)
    return sorted(s.items(), key=lambda t: -t[1])


def _norm(lst):
    if not lst:
        return {}
    v = [x for _, x in lst]; lo, hi = min(v), max(v)
    return {i: (x - lo) / (hi - lo) if hi > lo else 1.0 for i, x in lst}


def wsum(dense, kw, alpha):
    d, k = _norm(dense), _norm(kw)
    s = {i: alpha * d.get(i, 0.0) + (1 - alpha) * k.get(i, 0.0) for i in set(d) | set(k)}
    return sorted(s.items(), key=lambda t: -t[1])


def systems(tag_lists):
    """name -> {query id: ranked [(row, score)]} for every system built on one model's dense lists."""
    out = {"dense": tag_lists}
    for kwn in ("bm25", "prod"):
        kw = KW[kwn]
        out[f"kw_{kwn}"] = kw
        out[f"rrf+{kwn}"] = {qid: rrf(tag_lists[qid], kw[qid]) for qid in tag_lists}
        for a in ALPHAS:
            out[f"wsum{a}+{kwn}"] = {qid: wsum(tag_lists[qid], kw[qid], a) for qid in tag_lists}
    return out


if __name__ == "__main__":
    tags = sys.argv[1:]
    res, ranks_all = {}, {}
    for tag in tags:
        lists = json.loads((SCRATCH / f"top_{tag}.json").read_text())
        sysm = systems(lists)
        res[tag] = {}
        for name, lst in sysm.items():
            r = {q["id"]: best_rank([i for i, _ in lst[q["id"]]], set(q["rel"])) for q in queries}
            ranks_all[(tag, name)] = r
            res[tag][name] = {"summary": summarise(queries, r), "guard": guard_top3(queries, r), "ranks": r}
        for name in res[tag]:
            if name != "dense" and not name.startswith("kw_"):
                res[tag][name]["vs_dense"] = {g: {"mrr@10": paired_bootstrap(queries, ranks_all[(tag, "dense")], ranks_all[(tag, name)], m_rr, g),
                                                  "hit@5": paired_bootstrap(queries, ranks_all[(tag, "dense")], ranks_all[(tag, name)], lambda x: m_hit(x, 5), g)}
                                              for g in ("paraphrase", "safety", "ALL")}
    dump("B_hybrid.json", res)
    for tag in tags:
        print("==", tag)
        for name, e in res[tag].items():
            s = e["summary"]
            print(f"  {name:16s} par h@1 {s['paraphrase']['hit@1']:.3f} h@5 {s['paraphrase']['hit@5']:.3f} mrr {s['paraphrase']['mrr@10']:.3f} | "
                  f"saf h@1 {s['safety']['hit@1']:.3f} h@3 {s['safety']['hit@3']:.3f} mrr {s['safety']['mrr@10']:.3f} guard {e['guard']['in_top3']}/34 | ALL mrr {s['ALL']['mrr@10']:.3f}")
