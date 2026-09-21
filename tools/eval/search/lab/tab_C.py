import json
d = json.load(open("results/C_rerank.json"))
for pool, pv in d["pools"].items():
    b = pv["baseline"]; s = b["summary"]
    print(f"\n## pool {pool}  recall@30 {b['recall@30']}  guard {b['guard']['in_top3']}/34")
    print(f"{'system':34s} {'par h1':>6} {'h5':>5} {'mrr':>5} | {'saf h1':>6} {'h3':>5} {'mrr':>5} {'g':>3} | {'own mrr':>7} | {'all mrr':>7}  better/worse/same  left3")
    print(f"{'(pool as is)':34s} {s['paraphrase']['hit@1']:6.3f} {s['paraphrase']['hit@5']:5.3f} {s['paraphrase']['mrr@10']:5.3f} | {s['safety']['hit@1']:6.3f} {s['safety']['hit@3']:5.3f} {s['safety']['mrr@10']:5.3f} {b['guard']['in_top3']:3d} | {s['own-library']['mrr@10']:7.3f} | {s['ALL']['mrr@10']:7.3f}")
    for n, r in pv["rerankers"].items():
        for var in ("ce", "blend"):
            e = r[var]; s = e["summary"]; c = e["changes"]
            print(f"{n+' '+var:34s} {s['paraphrase']['hit@1']:6.3f} {s['paraphrase']['hit@5']:5.3f} {s['paraphrase']['mrr@10']:5.3f} | {s['safety']['hit@1']:6.3f} {s['safety']['hit@3']:5.3f} {s['safety']['mrr@10']:5.3f} {e['guard']['in_top3']:3d} | {s['own-library']['mrr@10']:7.3f} | {s['ALL']['mrr@10']:7.3f}  {c['better']}/{c['worse']}/{c['same']}  {len(e['safety_left_top3'])}")
