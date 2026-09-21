"""Experiment C: cross-encoder reranking of the top 30 of a hybrid. fp16, GPU, plain transformers (no remote code).
usage: rerank.py <pool> [<pool> ...] [--models a,b,c]     pool = <embed tag>:<system name>, e.g. bge-small-en-v1.5:rrf+prod
Writes results/C_rerank.json: per pool, per reranker: metrics of (a) the pure cross-encoder order of the 30 and
(b) an RRF blend of the cross-encoder order with the hybrid order; recall@30 of the pool; how many queries got better /
worse / the same (best rank of the answer, absent = worst); every safety row that left the top 3."""
import argparse, json, time
import numpy as np, torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from common import *
from models import RERANK
from hybrid import systems, rrf

ap = argparse.ArgumentParser()
ap.add_argument("pools", nargs="+")
ap.add_argument("--models", default=",".join(RERANK))
ap.add_argument("--depth", type=int, default=30)
ap.add_argument("--maxlen", type=int, default=512)
ap.add_argument("--out", default="C_rerank.json")
args = ap.parse_args()
corpus = json.loads((SCRATCH / "corpus.json").read_text())
queries = json.loads((SCRATCH / "queries.json").read_text())
qtext = {q["id"]: q["query"] for q in queries}
rel = {q["id"]: set(q["rel"]) for q in queries}

pools = {}
for spec in args.pools:
    tag, name = spec.split(":", 1)
    lists = json.loads((SCRATCH / f"top_{tag}.json").read_text())
    pools[spec] = {qid: [i for i, _ in lst][:args.depth] for qid, lst in systems(lists)[name].items()}


@torch.no_grad()
def score_pairs(tok, model, pairs, budget=16000):
    enc = tok([p[0] for p in pairs], [p[1] for p in pairs], truncation="only_second", max_length=args.maxlen, padding=False)["input_ids"]
    order = np.argsort([-len(e) for e in enc], kind="stable")
    out = np.zeros(len(pairs), dtype=np.float32)
    i = 0
    while i < len(order):
        L = len(enc[order[i]]); n = max(1, min(128, budget // L))
        idx = order[i:i + n]
        b = tok.pad({"input_ids": [enc[j] for j in idx]}, return_tensors="pt").to("cuda")
        logits = model(**b).logits.float()
        out[idx] = (logits[:, 0] if logits.shape[-1] == 1 else logits[:, -1]).cpu().numpy()
        i += n
    return out


def change_stats(before, after):
    inf = 10**6
    b = lambda r: inf if r is None else r
    better = sum(1 for q in queries if b(after[q["id"]]) < b(before[q["id"]]))
    worse = sum(1 for q in queries if b(after[q["id"]]) > b(before[q["id"]]))
    return {"better": better, "worse": worse, "same": len(queries) - better - worse}


res = {"depth": args.depth, "pools": {}}
for spec, pool in pools.items():
    base = {q["id"]: best_rank(pool[q["id"]], rel[q["id"]]) for q in queries}
    res["pools"][spec] = {"baseline": {"summary": summarise(queries, base), "guard": guard_top3(queries, base), "ranks": base,
                                       "recall@%d" % args.depth: round(sum(1 for q in queries if base[q["id"]] is not None) / len(queries), 4)},
                          "rerankers": {}}
for name in args.models.split(","):
    cfg = RERANK[name]
    tok = AutoTokenizer.from_pretrained(cfg["hf"])
    model = AutoModelForSequenceClassification.from_pretrained(cfg["hf"], dtype=torch.float16, trust_remote_code=False).to("cuda").eval()
    nparams = sum(p.numel() for p in model.parameters())
    for spec, pool in pools.items():
        pairs, owner = [], []
        for q in queries:
            for i in pool[q["id"]]:
                pairs.append((qtext[q["id"]], corpus[i]["text"])); owner.append((q["id"], i))
        torch.cuda.synchronize(); t0 = time.perf_counter()
        sc = score_pairs(tok, model, pairs)
        torch.cuda.synchronize(); dt = time.perf_counter() - t0
        assert np.isfinite(sc).all()
        per = {}
        for (qid, i), s in zip(owner, sc):
            per.setdefault(qid, []).append((i, float(s)))
        pure = {qid: sorted(v, key=lambda t: -t[1]) for qid, v in per.items()}
        blend = {qid: rrf([(i, 0) for i in pool[qid]], [(i, 0) for i, _ in pure[qid]]) for qid in per}
        base = res["pools"][spec]["baseline"]["ranks"]
        entry = {"params_M": round(nparams / 1e6, 1), "gpu_pairs_per_s": round(len(pairs) / dt, 1)}
        for var, lists in (("ce", pure), ("blend", blend)):
            r = {q["id"]: best_rank([i for i, _ in lists[q["id"]]], rel[q["id"]]) for q in queries}
            left = [q["id"] for q in queries if q["set"] == "safety" and base[q["id"]] is not None and base[q["id"]] <= 3
                    and not (r[q["id"]] is not None and r[q["id"]] <= 3)]
            entered = [q["id"] for q in queries if q["set"] == "safety" and (base[q["id"]] is None or base[q["id"]] > 3)
                       and r[q["id"]] is not None and r[q["id"]] <= 3]
            entry[var] = {"summary": summarise(queries, r), "guard": guard_top3(queries, r), "ranks": r, "changes": change_stats(base, r),
                          "safety_left_top3": left, "safety_entered_top3": entered,
                          "vs_baseline": {g: {"mrr@10": paired_bootstrap(queries, base, r, m_rr, g),
                                              "hit@1": paired_bootstrap(queries, base, r, lambda x: m_hit(x, 1), g)} for g in ("paraphrase", "safety", "ALL")}}
            res["pools"][spec]["rerankers"].setdefault(name, entry)
        s = entry["ce"]["summary"]
        print(f"{spec:36s} {name:30s} par h@1 {s['paraphrase']['hit@1']:.3f} h@5 {s['paraphrase']['hit@5']:.3f} mrr {s['paraphrase']['mrr@10']:.3f} | "
              f"saf h@1 {s['safety']['hit@1']:.3f} h@3 {s['safety']['hit@3']:.3f} | worse {entry['ce']['changes']['worse']} better {entry['ce']['changes']['better']} "
              f"left3 {len(entry['ce']['safety_left_top3'])} | blend mrr {entry['blend']['summary']['paraphrase']['mrr@10']:.3f} {dt:.1f}s", flush=True)
    del model; torch.cuda.empty_cache()
    dump(args.out, res)
