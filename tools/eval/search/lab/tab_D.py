import json,glob
for f in sorted(glob.glob("results/D/embed_*.json")):
    d=json.load(open(f)); t4=d["threads"]["4"]; t1=d["threads"]["1"]
    print(f"{d['name']:38s} gguf {d['gguf_mb']:6.1f}MB  cos p {t4['fidelity']['passage_cos_mean']} q {t4['fidelity']['query_cos_mean']} top10ov {t4['fidelity']['top10_overlap_query_only']}  t4 {t4['query_ms']['median']}ms t1 {t1['query_ms']['median']}ms  rss {t4['rss_mb_final']['VmRSS']}MB (t1 {t1['rss_mb_final']['VmRSS']})")
