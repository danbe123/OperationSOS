"""Sanity: does the control's torch-fp16 vector agree with the vector the box actually ships (q8_0 GGUF,
llama-server, /home/dan/sos-content/embeddings/docs.f16.bin, read only)? Also confirms the row order/keys."""
import json, numpy as np
from common import *
corpus = json.loads((SCRATCH / "corpus.json").read_text())
ids = [l for l in open("/home/dan/sos-content/embeddings/docs.ids", encoding="utf-8").read().split("\n") if l]
prod = np.fromfile("/home/dan/sos-content/embeddings/docs.f16.bin", dtype=np.float16).reshape(len(ids), 384).astype(np.float32)
mine = np.load(SCRATCH / "P_bge-small-en-v1.5.npy").astype(np.float32)
same_keys = ids == [c["url"] for c in corpus]
common_ = {u: i for i, u in enumerate(ids)}
sel = [(i, common_[c["url"]]) for i, c in enumerate(corpus) if c["url"] in common_]
a = np.stack([mine[i] for i, _ in sel]); b = np.stack([prod[j] for _, j in sel])
cos = (a * b).sum(1) / np.linalg.norm(a, axis=1) / np.linalg.norm(b, axis=1)
res = {"shipped_index_rows": len(ids), "corpus_rows": len(corpus), "same_keys_same_order": same_keys, "matched": len(sel),
       "cosine_mean": float(cos.mean()), "cosine_min": float(cos.min()), "cosine_p1": float(np.percentile(cos, 1)),
       "below_0.99": int((cos < 0.99).sum())}
print(res); dump("control_vs_shipped_index.json", res)
