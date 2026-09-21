"""Embed the subset under every representation with one model (fp16 GPU, plain transformers, the model's documented pooling
and prefixes from lab/models.py, 512-token window) and the gold queries.  Saves scratch books/V_<tag>.npz (fp16 unit vectors)
and results/books/embed_<tag>.json (timings).   usage: books_embed.py <model> [--tag T]   (torch venv)"""
import argparse, json, sys, time
from pathlib import Path
import numpy as np, torch
from transformers import AutoModel, AutoTokenizer
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import SCRATCH, RESULTS, REPO   # noqa: E402
from models import EMBED                    # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reps import rep_texts                  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument("name"); ap.add_argument("--tag", default=""); ap.add_argument("--maxlen", type=int, default=512)
args = ap.parse_args()
cfg = EMBED[args.name]; tag = args.name + args.tag
B = SCRATCH / "books"
sub = json.loads((B / "subset.json").read_text())
cat = json.loads((B / "catalogue.json").read_text())
rows = {g["key"]: g for g in cat["gutenberg"]} | {s["key"]: s for s in cat["survivor"]}
recs = {}
for line in (B / "texts.jsonl").read_text().splitlines():
    r = json.loads(line); recs[r["key"]] = r
sys.path.insert(0, str(REPO / "api"))
from sos.books import SHELF_NAMES  # noqa: E402
keys = sub["keys"]
texts = [rep_texts(rows[k], recs[k], SHELF_NAMES) for k in keys]
queries = []
for name in ("books", "books-extra"):
    for line in (REPO / f"tools/eval/search/{name}.jsonl").read_text().splitlines():
        queries.append(json.loads(line))

dev = "cuda"
tok = AutoTokenizer.from_pretrained(cfg["hf"])
model = AutoModel.from_pretrained(cfg["hf"], torch_dtype=torch.float16, trust_remote_code=False).to(dev).eval()
nparams = sum(p.numel() for p in model.parameters())
budget = 24000 if nparams < 200e6 else 12000


@torch.no_grad()
def encode(strings):
    enc = tok(strings, truncation=True, max_length=args.maxlen, padding=False)["input_ids"]
    order = np.argsort([-len(e) for e in enc], kind="stable")
    out = np.zeros((len(strings), model.config.hidden_size), dtype=np.float16)
    i, ntok = 0, 0
    while i < len(order):
        L = len(enc[order[i]]); n = max(1, min(256, budget // L)); idx = order[i:i + n]
        batch = tok.pad({"input_ids": [enc[j] for j in idx]}, return_tensors="pt").to(dev)
        ntok += int(batch["attention_mask"].sum())
        h = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]).last_hidden_state.float()
        if cfg["pool"] == "cls":
            v = h[:, 0]
        else:
            m = batch["attention_mask"].unsqueeze(-1).float(); v = (h * m).sum(1) / m.sum(1).clamp(min=1)
        v = torch.nn.functional.normalize(v, dim=-1)
        assert torch.isfinite(v).all()
        out[idx] = v.cpu().numpy().astype(np.float16); i += n
    return out, ntok


timings = {}
def run(label, strings):
    torch.cuda.synchronize(); t0 = time.perf_counter()
    v, nt = encode([cfg["pp"] + s for s in strings])
    torch.cuda.synchronize(); dt = time.perf_counter() - t0
    timings[label] = {"texts": len(strings), "tokens": nt, "seconds": round(dt, 2), "texts_per_s": round(len(strings) / dt, 1), "tokens_per_s": round(nt / dt)}
    print(label, timings[label], flush=True)
    return v

encode([cfg["pp"] + s for s in ["warm up " * 100] * 64])
out = {}
for rep in ("a", "b1", "b2", "c0", "c1", "c2"):
    out[rep] = run(rep, [t[rep] for t in texts])
NW = max(len(t["dt"]) for t in texts)
for rep in ("dt", "dp"):
    flat, where = [], []
    for i, t in enumerate(texts):
        for j, w in enumerate(t[rep]):
            flat.append(w); where.append((i, j))
    v = run(rep, flat)
    arr = np.zeros((len(keys), NW, v.shape[1]), dtype=np.float16); cnt = np.zeros(len(keys), dtype=np.int16)
    for (i, j), vec in zip(where, v):
        arr[i, j] = vec; cnt[i] = max(cnt[i], j + 1)
    out[rep] = arr; out["n_" + rep] = cnt
qv, _ = encode([cfg["qp"] + q["query"] for q in queries])
out["Q"] = qv
np.savez(B / f"V_{tag}.npz", **out)
(RESULTS / "books").mkdir(parents=True, exist_ok=True)
(RESULTS / "books" / f"embed_{tag}.json").write_text(json.dumps({"model": args.name, "hf": cfg["hf"], "pool": cfg["pool"], "query_prefix": cfg["qp"],
      "passage_prefix": cfg["pp"], "params": nparams, "books": len(keys), "queries": len(queries), "timings": timings}, indent=1))
print("saved", B / f"V_{tag}.npz")
