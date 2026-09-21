"""Experiment E: what switching models costs to rebuild, from the GPU rates measured in experiment A (torch fp16, this PC's
RTX 4070 SUPER, shared with other agents) and the box's last real builds (read only:
/home/dan/sos-content/embeddings/*.meta.json). Two figures per collection:
  gpu_only_h  -- N passages of the docs corpus's mean length (400 tokens) at the measured tokens/s: the model's own cost;
  wall_h      -- max(gpu_only, the last real build's observed rate for that collection): the bge-small builds were
                 bounded by reading ZIMs / extracting PDFs, not by the GPU, so a model no slower than that rate costs no more wall time.
Also: worst case, every text at the 512-token window. Index sizes are raw fp16 vectors (N x dims x 2 bytes)."""
import json, glob
from common import *

META = {k: json.load(open(f"/home/dan/sos-content/embeddings/{k}.meta.json")) for k in ("docs", "household", "wikipedia")}
COLL = {   # name: (N, observed passages/s of the last real bge-small build or None)
    "docs (this corpus)": (21368, None),
    "household (Gutenberg + Survivor Library books)": (META["household"]["count"], META["household"]["count"] / META["household"]["elapsed_s"]),
    "small-library articles (new, assumed)": (150_000, None),
    "Wikipedia (article leads)": (META["wikipedia"]["count"], META["wikipedia"]["count"] / META["wikipedia"]["elapsed_s"]),
}
MODELS = ["bge-small-en-v1.5", "e5-small-v2", "granite-embedding-small-english-r2", "e5-base-v2", "gte-base", "bge-base-en-v1.5",
          "granite-embedding-english-r2", "bge-large-en-v1.5", "mxbai-embed-large-v1"]
res = {"observed_builds": {k: {"count": v["count"], "elapsed_s": v.get("elapsed_s"), "rate_per_s": round(v["count"] / v["elapsed_s"], 1) if v.get("elapsed_s") else None} for k, v in META.items()},
       "models": {}}
# the wikipedia pipeline rate (ZIM reading) is the best available proxy for an unmeasured ZIM-derived collection
pipe_rate = res["observed_builds"]["wikipedia"]["rate_per_s"]
for m in MODELS:
    e = json.loads((RESULTS / "embed" / f"{m}.json").read_text())
    tps, mean_tok = e["tokens_per_s"], e["mean_tokens"]
    r = {"params_M": round(e["params"] / 1e6, 1), "dims": e["dims"], "gpu_passages_per_s": e["passages_per_s"], "gpu_tokens_per_s": tps, "collections": {}}
    for cname, (n, obs) in COLL.items():
        gpu_h = n * mean_tok / tps / 3600
        worst_h = n * 512 / tps / 3600
        floor = obs or pipe_rate if cname != "docs (this corpus)" else None
        wall_h = max(gpu_h, n / floor / 3600) if floor else gpu_h
        r["collections"][cname] = {"n": n, "gpu_only_h": round(gpu_h, 4), "gpu_worst_case_512tok_h": round(worst_h, 4), "wall_h": round(wall_h, 4),
                                   "index_fp16_gb": round(n * e["dims"] * 2 / 1e9, 3)}
    res["models"][m] = r
dump("E_rebuild.json", res)
print(json.dumps(res["observed_builds"]))
names = list(COLL)
print(f"{'model':36s} {'dims':>4} {'docs/s':>7} " + " ".join(f"{n.split(' ')[0][:10]:>22s}" for n in names))
for m, r in res["models"].items():
    print(f"{m:36s} {r['dims']:4d} {r['gpu_passages_per_s']:7.0f} " + " ".join(
        f"{r['collections'][n]['gpu_only_h']:6.2f}h/{r['collections'][n]['wall_h']:6.2f}h/{r['collections'][n]['index_fp16_gb']:6.2f}GB" for n in names))
