import json,glob
for f in sorted(glob.glob("results/D/rerank_*.json")):
    d=json.load(open(f)); print(d["name"], d["gguf_mb"], "MB", {t:(v["rerank30_ms"], v["rss_mb_final"]["VmRSS"]) for t,v in d["threads"].items()}, d["fidelity"])
