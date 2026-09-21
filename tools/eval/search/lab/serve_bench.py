"""Experiment D on the CPU llama-server (the same flags as install/systemd/sos-embed.service, ports 8110+):
  fidelity   -- GGUF vectors vs the torch fp16 vectors of experiment A, 200 passages (and every query);
  latency    -- one query at a time, -t 1 and -t 4, median/p95 ms after warm-up;
  memory     -- resident set (VmRSS) and peak (VmHWM) of the server after the workload.
usage: serve_bench.py embed <name> <gguf> <port>      (name is a registry key; the torch vectors must exist)
       serve_bench.py rerank <name> <gguf> <port> <pool spec>"""
import json, os, random, subprocess, sys, time, statistics
import httpx, numpy as np
from common import *
from models import EMBED, RERANK

BIN = "/home/dan/.local/bin/llama-server"
corpus = json.loads((SCRATCH / "corpus.json").read_text())
queries = json.loads((SCRATCH / "queries.json").read_text())


def start(gguf, port, threads, extra):
    cmd = [BIN, "-m", str(gguf), *extra, "-c", "512", "-ub", "512", "-b", "512", "--host", "127.0.0.1", "--port", str(port), "-t", str(threads), "--no-webui"]
    log = open(SCRATCH / f"server_{port}.log", "w")
    t0 = time.perf_counter()
    p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
    for _ in range(600):
        time.sleep(0.25)
        if p.poll() is not None:
            raise RuntimeError(f"server exited: {open(SCRATCH / f'server_{port}.log').read()[-800:]}")
        try:
            if httpx.get(f"http://127.0.0.1:{port}/health", timeout=1).status_code == 200:
                return p, time.perf_counter() - t0
        except httpx.HTTPError:
            pass
    p.terminate(); raise RuntimeError("server did not become healthy")


def stop(p):
    p.terminate()
    try:
        p.wait(15)
    except subprocess.TimeoutExpired:
        p.kill(); p.wait()


def rss(pid):
    out = {}
    for line in open(f"/proc/{pid}/status"):
        if line.startswith(("VmRSS", "VmHWM")):
            k, v = line.split(":"); out[k] = round(int(v.split()[0]) / 1024, 1)
    return out


def embed(port, texts):
    r = httpx.post(f"http://127.0.0.1:{port}/embeddings", json={"input": texts}, timeout=300)
    r.raise_for_status()
    rows = r.json(); rows = rows.get("data") if isinstance(rows, dict) else rows
    rows = sorted(rows, key=lambda x: x["index"])
    v = np.asarray([x["embedding"][0] if isinstance(x["embedding"][0], list) else x["embedding"] for x in rows], dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def pct(v, p):
    v = sorted(v); return v[min(len(v) - 1, int(round(p / 100 * (len(v) - 1))))]


def bench_embed(name, gguf, port):
    cfg = EMBED[name]
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(cfg["hf"])
    P = np.load(SCRATCH / f"P_{name}.npy").astype(np.float32)
    Q = np.load(SCRATCH / f"Q_{name}.npy").astype(np.float32)
    rng = random.Random(1)
    lens = [len(x) for x in tok([cfg["pp"] + c["text"] for c in corpus], truncation=False)["input_ids"]]
    fits = [i for i, l in enumerate(lens) if l <= 480]
    pick = rng.sample(fits, 200)
    pooling = ["--pooling", cfg["pool"]]
    res = {"name": name, "gguf": os.path.basename(str(gguf)), "gguf_mb": round(os.path.getsize(gguf) / 1e6, 1), "threads": {}}
    for threads in (4, 1):
        p, load_s = start(gguf, port, threads, ["--embedding", *pooling])
        try:
            r = {"load_s": round(load_s, 2)}
            qtexts = [cfg["qp"] + q["query"] for q in queries]
            for t in qtexts[:5]:
                embed(port, [t])
            lat = []
            for t in qtexts[:60]:
                t0 = time.perf_counter(); embed(port, [t]); lat.append((time.perf_counter() - t0) * 1000)
            r["query_ms"] = {"median": round(statistics.median(lat), 1), "p95": round(pct(lat, 95), 1), "mean": round(statistics.mean(lat), 1), "n": len(lat)}
            r["mean_query_tokens"] = round(float(np.mean([len(x) for x in tok(qtexts[:60])["input_ids"]])), 1)
            if threads == 4:
                vq = embed(port, qtexts)
                cq = (vq * Q).sum(1)
                vp = np.concatenate([embed(port, [cfg["pp"] + corpus[i]["text"] for i in pick[j:j + 8]]) for j in range(0, 200, 8)])
                cp = (vp * P[pick]).sum(1)
                r["fidelity"] = {"passages_n": 200, "passage_cos_mean": round(float(cp.mean()), 5), "passage_cos_min": round(float(cp.min()), 5),
                                 "queries_n": len(qtexts), "query_cos_mean": round(float(cq.mean()), 5), "query_cos_min": round(float(cq.min()), 5)}
                # top-10 agreement on the real task: rank the whole corpus with GGUF query vectors vs torch query vectors (torch passages)
                s_t = Q @ P.T; s_g = vq @ P.T
                a = np.argsort(-s_t, axis=1)[:, :10]; b = np.argsort(-s_g, axis=1)[:, :10]
                r["fidelity"]["top10_overlap_query_only"] = round(float(np.mean([len(set(x) & set(y)) / 10 for x, y in zip(a, b)])), 4)
                r["rss_mb_after_workload"] = rss(p.pid)
                # a 512-token-length passage: the worst-case latency and memory of a build-time batch is irrelevant on the Pi; the query path is what matters
            r["rss_mb_final"] = rss(p.pid)
            res["threads"][str(threads)] = r
        finally:
            stop(p)
    return res


def bench_rerank(name, gguf, port, spec):
    cfg = RERANK[name]
    tag, sysname = spec.split(":", 1)
    from hybrid import systems
    lists = json.loads((SCRATCH / f"top_{tag}.json").read_text())
    pool = {qid: [i for i, _ in l][:30] for qid, l in systems(lists)[sysname].items()}
    qs = [q for q in queries if q["set"] == "paraphrase"][:12]
    res = {"name": name, "gguf": os.path.basename(str(gguf)), "gguf_mb": round(os.path.getsize(gguf) / 1e6, 1), "threads": {}}
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(cfg["hf"])
    for threads in (4, 1):
        p, load_s = start(gguf, port, threads, ["--reranking", "--pooling", "rank"])
        try:
            r = {"load_s": round(load_s, 2)}
            lat, agree, corr, nfail = [], [], [], 0
            for n, q in enumerate(qs):
                docs = [corpus[i]["text"][:1200] for i in pool[q["id"]]]      # capped: a pair must fit the 512-token window
                t0 = time.perf_counter()
                rr = httpx.post(f"http://127.0.0.1:{port}/v1/rerank", json={"query": q["query"], "documents": docs}, timeout=600)
                dt = (time.perf_counter() - t0) * 1000
                if rr.status_code != 200:
                    nfail += 1; continue
                if n > 0 or threads == 1:
                    lat.append(dt)
                sc = np.zeros(len(docs))
                for x in rr.json()["results"]:
                    sc[x["index"]] = x["relevance_score"]
                r.setdefault("_scores", []).append((q["id"], sc.tolist(), docs))
                if threads == 4 and n >= 8 and False:
                    pass
            r["rerank30_ms"] = {"median": round(statistics.median(lat), 1), "p95": round(pct(lat, 95), 1), "n": len(lat), "failed_requests": nfail}
            r["rss_mb_final"] = rss(p.pid)
            res["threads"][str(threads)] = r
        finally:
            stop(p)
    # fidelity: the torch fp16 logits of the same (capped) pairs
    m = AutoModelForSequenceClassification.from_pretrained(cfg["hf"], dtype=torch.float32).eval()
    cors, top1 = [], []
    for qid, sc, docs in res["threads"]["4"].pop("_scores"):
        qt = next(q["query"] for q in queries if q["id"] == qid)
        b = tok([qt] * len(docs), docs, truncation="only_second", max_length=512, padding=True, return_tensors="pt")
        with torch.no_grad():
            lg = m(**b).logits[:, 0].numpy()
        cors.append(float(np.corrcoef(lg, sc)[0, 1])); top1.append(int(np.argmax(lg) == np.argmax(sc)))
    res["threads"]["1"].pop("_scores", None)
    res["fidelity"] = {"queries": len(cors), "pearson_mean": round(float(np.mean(cors)), 5), "pearson_min": round(float(np.min(cors)), 5),
                       "top1_agree": f"{sum(top1)}/{len(top1)}"}
    return res


if __name__ == "__main__":
    kind, name, gguf, port = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
    out = bench_embed(name, gguf, port) if kind == "embed" else bench_rerank(name, gguf, port, sys.argv[5])
    (RESULTS / "D").mkdir(exist_ok=True)
    (RESULTS / "D" / f"{kind}_{name}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
