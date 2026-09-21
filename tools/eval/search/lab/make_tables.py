"""Print the report's markdown tables from results/*.json (nothing is computed here that is not in the JSON)."""
import json, os
R = "results/"
J = lambda n: json.load(open(R + n))
A, B, C, E, H = J("A_dense.json"), J("B_hybrid.json"), J("C_rerank.json"), J("E_rebuild.json"), J("headline.json")
BIAS = J("bias.json")
f3 = lambda x: f"{x:.3f}"

def dense_table():
    order = ["bge-small-en-v1.5", "shipped-index", "bge-small-en-v1.5@256", "e5-small-v2", "all-MiniLM-L12-v2", "all-MiniLM-L12-v2@128", "gte-small", "arctic-embed-s",
             "multi-qa-MiniLM-L6-cos-v1", "mxbai-embed-xsmall-v1", "granite-embedding-small-english-r2",
             "e5-base-v2", "gte-base", "bge-base-en-v1.5", "arctic-embed-m", "arctic-embed-m-v1.5", "all-mpnet-base-v2", "granite-embedding-english-r2",
             "bge-large-en-v1.5", "mxbai-embed-large-v1"]
    print("| model | params | dims | par h@1 | par h@5 | par MRR | safety h@1 | safety h@3 | safety MRR | guard (card in top 3) | own h@5 | own MRR | ALL MRR | GPU docs/s |")
    print("|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
    for t in order:
        r = A[t]; s = r["summary"]
        print(f"| {t} | {r['params_M']:.0f}M | {r['dims']} | {f3(s['paraphrase']['hit@1'])} | {f3(s['paraphrase']['hit@5'])} | {f3(s['paraphrase']['mrr@10'])} | "
              f"{f3(s['safety']['hit@1'])} | {f3(s['safety']['hit@3'])} | {f3(s['safety']['mrr@10'])} | {r['guard']['in_top3']}/34 | {f3(s['own-library']['hit@5'])} | {f3(s['own-library']['mrr@10'])} | {f3(s['ALL']['mrr@10'])} | {r['passages_per_s']:.0f} |")

def hybrid_table():
    tags = ["bge-small-en-v1.5", "e5-base-v2", "gte-base", "granite-embedding-english-r2", "granite-embedding-small-english-r2", "bge-base-en-v1.5", "e5-small-v2"]
    names = ["dense", "kw_bm25", "kw_prod", "rrf+bm25", "rrf+prod", "wsum0.5+bm25", "wsum0.7+bm25", "wsum0.5+prod", "wsum0.7+prod"]
    print("| dense model | system | par h@1 | par h@5 | par MRR | safety h@1 | safety h@3 | safety MRR | guard | own MRR | ALL MRR |")
    print("|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
    for t in tags:
        for n in names:
            if n.startswith("kw_") and t != tags[0]:
                continue
            e = B[t][n]; s = e["summary"]
            lab = t if n == "dense" else ("(all)" if n.startswith("kw_") else "")
            if n.startswith("kw_"): lab = "(keyword only, same for all)"
            print(f"| {lab} | {n} | {f3(s['paraphrase']['hit@1'])} | {f3(s['paraphrase']['hit@5'])} | {f3(s['paraphrase']['mrr@10'])} | {f3(s['safety']['hit@1'])} | {f3(s['safety']['hit@3'])} | {f3(s['safety']['mrr@10'])} | {e['guard']['in_top3']}/34 | {f3(s['own-library']['mrr@10'])} | {f3(s['ALL']['mrr@10'])} |")

def rerank_table(pool, fname="C_rerank.json"):
    pv = J(fname)["pools"][pool]; b = pv["baseline"]; s = b["summary"]
    print(f"Pool `{pool}` ({next(k for k in b if k.startswith('recall'))} {b[next(k for k in b if k.startswith('recall'))]:.3f})\n")
    print("| system | par h@1 | par MRR | safety h@1 | safety h@3 | guard | ALL MRR | queries better / worse / same | safety rows leaving top 3 |")
    print("|---|--:|--:|--:|--:|--:|--:|--:|--|")
    print(f"| pool as is | {f3(s['paraphrase']['hit@1'])} | {f3(s['paraphrase']['mrr@10'])} | {f3(s['safety']['hit@1'])} | {f3(s['safety']['hit@3'])} | {b['guard']['in_top3']}/34 | {f3(s['ALL']['mrr@10'])} | | |")
    for n, r in pv["rerankers"].items():
        for var, lab in (("ce", "cross-encoder order"), ("blend", "RRF(cross-encoder, pool)")):
            e = r[var]; s = e["summary"]; c = e["changes"]
            left = ", ".join(x.replace("safety-", "") for x in e["safety_left_top3"]) or "none"
            print(f"| {n} ({r['params_M']:.0f}M), {lab} | {f3(s['paraphrase']['hit@1'])} | {f3(s['paraphrase']['mrr@10'])} | {f3(s['safety']['hit@1'])} | {f3(s['safety']['hit@3'])} | {e['guard']['in_top3']}/34 | {f3(s['ALL']['mrr@10'])} | {c['better']} / {c['worse']} / {c['same']} | {left} |")

def cell(x):
    sig = "*" if (x["ci95"][0] > 0 or x["ci95"][1] < 0) else ""
    return f"{x['diff']:+.3f} [{x['ci95'][0]:+.3f}, {x['ci95'][1]:+.3f}]{sig} ({x['wins']}W/{x['losses']}L)"

def headline_table(rows):
    print("| comparison (B minus A) | paraphrase MRR | safety MRR | ALL MRR | paraphrase hit@1 | safety hit@1 |")
    print("|---|--|--|--|--|--|")
    for r in H:
        if r["comparison"] in rows:
            print(f"| {r['comparison']} | {cell(r['paraphrase']['mrr@10'])} | {cell(r['safety']['mrr@10'])} | {cell(r['ALL']['mrr@10'])} | {cell(r['paraphrase']['hit@1'])} | {cell(r['safety']['hit@1'])} |")

def rebuild_table():
    C_ = list(next(iter(E["models"].values()))["collections"])
    print("| model | dims | docs (21k) | household (70.6k) | small library (150k) | Wikipedia (8.43M) | Wikipedia index fp16 |")
    print("|---|--:|--:|--:|--:|--:|--:|")
    for m, r in E["models"].items():
        c = r["collections"]
        fmt = lambda n: (f"{c[n]['gpu_only_h']*60:.1f} min" if c[n]["gpu_only_h"] < 1 else f"{c[n]['gpu_only_h']:.1f} h") + " GPU / " + (f"{c[n]['wall_h']*60:.0f} min" if c[n]["wall_h"] < 1 else f"{c[n]['wall_h']:.1f} h") + " wall"
        print(f"| {m} | {r['dims']} | {c[C_[0]]['gpu_only_h']*3600:.0f} s | {fmt(C_[1])} | {fmt(C_[2])} | {fmt(C_[3])} | {c[C_[3]]['index_fp16_gb']:.1f} GB |")


def pi_table():
    ctl = json.load(open(R + "D/embed_bge-small-en-v1.5.json"))
    c4, c1 = ctl["threads"]["4"]["query_ms"]["median"], ctl["threads"]["1"]["query_ms"]["median"]
    order = ["bge-small-en-v1.5", "e5-small-v2", "granite-embedding-small-english-r2", "e5-base-v2", "gte-base", "bge-base-en-v1.5", "granite-embedding-english-r2"]
    print("| model | q8_0 GGUF | RSS -t4 (MB) | fidelity: passage cos / query cos (n=200 / 172) | query ms -t4 (PC) | query ms -t1 (PC) | x control (-t4 / -t1) | Pi 5 estimate -t1 (3-4x PC) | ALL MRR (dense) | paraphrase MRR | safety MRR |")
    print("|---|--:|--:|--|--:|--:|--:|--:|--:|--:|--:|")
    for m in order:
        d = json.load(open(R + f"D/embed_{m}.json")); t4, t1 = d["threads"]["4"], d["threads"]["1"]
        s = A[m]["summary"]
        lo, hi = t1["query_ms"]["median"] * 3, t1["query_ms"]["median"] * 4
        print(f"| {m} | {d['gguf_mb']:.0f} MB | {t4['rss_mb_final']['VmRSS']:.0f} | {t4['fidelity']['passage_cos_mean']:.5f} / {t4['fidelity']['query_cos_mean']:.5f} | {t4['query_ms']['median']:.1f} | {t1['query_ms']['median']:.1f} | "
              f"{t4['query_ms']['median']/c4:.2f} / {t1['query_ms']['median']/c1:.2f} | {lo:.0f}-{hi:.0f} ms | {f3(s['ALL']['mrr@10'])} | {f3(s['paraphrase']['mrr@10'])} | {f3(s['safety']['mrr@10'])} |")

def rerank_pi_table():
    print("| reranker | q8_0 GGUF | llama.cpp | fidelity vs torch fp32 (Pearson of scores / top-1 agreement) | 30 pairs -t4 (median) | 30 pairs -t1 (median) | RSS (MB) |")
    print("|---|--:|--|--|--:|--:|--:|")
    for m in ("ms-marco-MiniLM-L-6-v2", "gte-reranker-modernbert-base", "bge-reranker-base", "bge-reranker-v2-m3"):
        p = R + f"D/rerank_{m}.json"
        if not os.path.exists(p):
            continue
        d = json.load(open(p)); f = d["fidelity"]
        print(f"| {m} | {d['gguf_mb']:.0f} MB | serves | {f['pearson_mean']:.4f} (min {f['pearson_min']:.4f}) / {f['top1_agree']} (n={f['queries']}) | {d['threads']['4']['rerank30_ms']['median']/1000:.1f} s | {d['threads']['1']['rerank30_ms']['median']/1000:.1f} s | {d['threads']['4']['rss_mb_final']['VmRSS']:.0f} |")


if __name__ == "__main__":
    import sys
    fn, args = sys.argv[1], sys.argv[2:]
    if fn == "headline_table":
        headline_table(set(args))
    else:
        globals()[fn](*args)
