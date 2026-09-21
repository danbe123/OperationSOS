"""CPU latency of the cheapest sensible reranking: 10 candidates, passage cut to 700 characters (about 256 tokens with the query),
gte-reranker-modernbert-base q8_0 on llama-server --reranking, -t 4 and -t 1. Ports 8150+.  Writes results/D/rerank_cheap_latency.json"""
import json, statistics, sys, time
import httpx
from common import *
from serve_bench import start, stop, rss, pct
G = SCRATCH / "gguf" / "gte-reranker-modernbert-base-q8_0.gguf"
corpus = json.loads((SCRATCH / "corpus.json").read_text()); queries = json.loads((SCRATCH / "queries.json").read_text())
lists = json.loads((SCRATCH / "top_e5-base-v2.json").read_text())
qs = [q for q in queries if q["set"] == "paraphrase"][:10]
out = {"model": "gte-reranker-modernbert-base", "candidates": 10, "chars": 700}
for threads, port in ((4, 8150), (1, 8151)):
    p, load = start(G, port, threads, ["--reranking", "--pooling", "rank"])
    try:
        lat = []
        for n, q in enumerate(qs):
            docs = [corpus[i]["text"][:700] for i, _ in lists[q["id"]][:10]]
            t0 = time.perf_counter()
            r = httpx.post(f"http://127.0.0.1:{port}/v1/rerank", json={"query": q["query"], "documents": docs}, timeout=600); r.raise_for_status()
            if n > 0: lat.append((time.perf_counter() - t0) * 1000)
        out[f"t{threads}"] = {"median_ms": round(statistics.median(lat)), "p95_ms": round(pct(lat, 95)), "n": len(lat), "rss_mb": rss(p.pid)["VmRSS"]}
    finally:
        stop(p)
print(out); dump("D/rerank_cheap_latency.json" if False else "rerank_cheap_latency.json", out)
