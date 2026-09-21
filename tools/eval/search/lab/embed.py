"""Embed the corpus and the queries with one model (fp16, GPU, plain transformers, no remote code) using the
model's documented pooling and prefixes. Saves unit vectors (fp16 .npy) in the scratch dir, and timing in
results/embed/<name>.json.   usage: embed.py <name> [--maxlen 512]"""
import argparse, json, time
import numpy as np, torch
from transformers import AutoModel, AutoTokenizer
from common import SCRATCH, RESULTS
from models import EMBED

ap = argparse.ArgumentParser()
ap.add_argument("name")
ap.add_argument("--maxlen", type=int, default=512)
ap.add_argument("--tag", default="")
args = ap.parse_args()
cfg = EMBED[args.name]
tag = args.name + args.tag
corpus = json.loads((SCRATCH / "corpus.json").read_text())
queries = json.loads((SCRATCH / "queries.json").read_text())
dev = "cuda"

tok = AutoTokenizer.from_pretrained(cfg["hf"])
model = AutoModel.from_pretrained(cfg["hf"], torch_dtype=torch.float16, trust_remote_code=False).to(dev).eval()
nparams = sum(p.numel() for p in model.parameters())


@torch.no_grad()
def encode(texts, budget_tokens):
    enc = tok(texts, truncation=True, max_length=args.maxlen, padding=False)["input_ids"]
    order = np.argsort([-len(e) for e in enc], kind="stable")
    out = np.zeros((len(texts), model.config.hidden_size), dtype=np.float16)
    i, total_tokens = 0, 0
    while i < len(order):
        L = len(enc[order[i]])
        n = max(1, min(256, budget_tokens // L))
        idx = order[i:i + n]
        batch = tok.pad({"input_ids": [enc[j] for j in idx]}, return_tensors="pt").to(dev)
        total_tokens += int(batch["attention_mask"].sum())
        h = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]).last_hidden_state.float()
        if cfg["pool"] == "cls":
            v = h[:, 0]
        else:
            m = batch["attention_mask"].unsqueeze(-1).float()
            v = (h * m).sum(1) / m.sum(1).clamp(min=1)
        v = torch.nn.functional.normalize(v, dim=-1)
        assert torch.isfinite(v).all(), "non-finite vector"
        out[idx] = v.cpu().numpy().astype(np.float16)
        i += n
    return out, total_tokens


budget = 24000 if nparams < 200e6 else 12000
# warm up (kernel selection, allocator) on a slice, then time the real pass
encode([cfg["pp"] + c["text"] for c in corpus[:256]], budget)
torch.cuda.synchronize(); t0 = time.perf_counter()
P, ptok = encode([cfg["pp"] + c["text"] for c in corpus], budget)
torch.cuda.synchronize(); dt = time.perf_counter() - t0
Q, qtok = encode([cfg["qp"] + q["query"] for q in queries], budget)
np.save(SCRATCH / f"P_{tag}.npy", P)
np.save(SCRATCH / f"Q_{tag}.npy", Q)
rec = {"name": args.name, "tag": tag, "hf": cfg["hf"], "pool": cfg["pool"], "query_prefix": cfg["qp"], "passage_prefix": cfg["pp"],
       "max_len": args.maxlen, "params": nparams, "dims": int(P.shape[1]), "passages": len(corpus), "passage_tokens": ptok,
       "mean_tokens": round(ptok / len(corpus), 1), "embed_seconds": round(dt, 2), "passages_per_s": round(len(corpus) / dt, 1),
       "tokens_per_s": round(ptok / dt), "gpu_peak_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2)}
(RESULTS / "embed").mkdir(parents=True, exist_ok=True)
(RESULTS / "embed" / f"{tag}.json").write_text(json.dumps(rec, indent=1))
print(json.dumps(rec))
