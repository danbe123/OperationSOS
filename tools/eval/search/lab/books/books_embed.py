"""Embed the subset under every representation with one model (fp16 GPU, plain transformers, the model's documented pooling
and prefixes from lab/models.py, 512-token window) and the gold queries.  Saves scratch books/V_<tag>.npz (fp16 unit vectors)
and results/books/embed_<tag>.json (timings).   usage: books_embed.py <model> [--tag T]   (torch venv)"""
import os, argparse, json, sys, time
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
sub = json.loads((B / f"{os.environ.get('BOOKS_SUBSET', 'subset')}.json").read_text())
cat = json.loads((B / "catalogue.json").read_text())
rows = {g["key"]: g for g in cat["gutenberg"]} | {s["key"]: s for s in cat["survivor"]}
want = set(sub["keys"])
recs = {}
with open(B / "texts.jsonl", encoding="utf-8") as fh:      # streamed: the file is ~270 MB
    for line in fh:
        r = json.loads(line)
        if r["key"] in want:
            recs[r["key"]] = r
rows = {k: rows[k] for k in want}
sys.path.insert(0, str(REPO / "api"))
from sos.books import SHELF_NAMES  # noqa: E402
keys = sub["keys"]
queries = []
for name in ("books", "books-extra"):
    for line in (REPO / f"tools/eval/search/{name}.jsonl").read_text().splitlines():
        queries.append(json.loads(line))
SHARD = 4096                                   # texts tokenised and embedded at a time: bounds RAM (an all-at-once run of 134k windows held ~8 GB)
SHARD_DIR = B / f"shards_{tag}"; SHARD_DIR.mkdir(exist_ok=True)

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


def book_texts(i):
    """all representation texts of one book (built on demand so they are never all held at once)."""
    return rep_texts(rows[keys[i]], recs[keys[i]], SHELF_NAMES)


timings = {}
def run(label, n_items, make):
    """embed n_items strings produced by make(lo, hi) -> list[str], shard by shard, each shard a file (resumable); returns [n_items, D] fp16."""
    parts, ntok_total, secs = [], 0, 0.0
    for lo in range(0, n_items, SHARD):
        f = SHARD_DIR / f"{label}_{lo:07d}.npy"
        meta = SHARD_DIR / f"{label}_{lo:07d}.json"
        if f.exists() and meta.exists():
            parts.append(np.load(f)); m = json.loads(meta.read_text()); ntok_total += m["tokens"]; secs += m["seconds"]; continue
        strings = [cfg["pp"] + x for x in make(lo, min(lo + SHARD, n_items))]
        torch.cuda.synchronize(); t0 = time.perf_counter()
        v, nt = encode(strings)
        torch.cuda.synchronize(); dt = time.perf_counter() - t0
        np.save(f, v); meta.write_text(json.dumps({"tokens": nt, "seconds": dt}))
        parts.append(v); ntok_total += nt; secs += dt
        del strings
    timings[label] = {"texts": n_items, "tokens": ntok_total, "seconds": round(secs, 2), "texts_per_s": round(n_items / max(secs, 1e-9), 1), "tokens_per_s": round(ntok_total / max(secs, 1e-9))}
    print(label, timings[label], flush=True)
    return np.concatenate(parts)


encode([cfg["pp"] + s for s in ["warm up " * 100] * 64])
out = {}
for rep in ("a", "b1", "b2", "c0", "c1", "c2"):
    out[rep] = run(rep, len(keys), lambda lo, hi, rep=rep: [book_texts(i)[rep] for i in range(lo, hi)])
NW = 10
for rep in ("dt", "dp"):
    n_win = np.array([len(book_texts(i)[rep]) for i in range(len(keys))])
    starts = np.concatenate([[0], np.cumsum(n_win)])
    flat_book = np.repeat(np.arange(len(keys)), n_win)
    total = int(starts[-1])

    def make(lo, hi, rep=rep, starts=starts, flat_book=flat_book):
        res, cache = [], {}
        for f in range(lo, hi):
            i = int(flat_book[f]); j = f - int(starts[i])
            if i not in cache:
                cache = {i: book_texts(i)[rep]}
            res.append(cache[i][j])
        return res
    v = run(rep, total, make)
    arr = np.zeros((len(keys), NW, v.shape[1]), dtype=np.float16)
    for i in range(len(keys)):
        arr[i, :n_win[i]] = v[starts[i]:starts[i + 1]]
    out[rep] = arr; out["n_" + rep] = n_win.astype(np.int16)
    del v
qv, _ = encode([cfg["qp"] + q["query"] for q in queries])
out["Q"] = qv
np.savez(B / f"V_{tag}.npz", **out)
(RESULTS / "books").mkdir(parents=True, exist_ok=True)
(RESULTS / "books" / f"embed_{tag}.json").write_text(json.dumps({"model": args.name, "hf": cfg["hf"], "pool": cfg["pool"], "query_prefix": cfg["qp"],
      "passage_prefix": cfg["pp"], "params": nparams, "books": len(keys), "queries": len(queries), "timings": timings}, indent=1))
print("saved", B / f"V_{tag}.npz")
