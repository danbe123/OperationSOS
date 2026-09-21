"""Make the box's shipped docs index (read only) available as an evaluation tag: 'shipped-index' = its vectors + the
control's torch query vectors (they agree with the GGUF ones to cos 0.9998). Shows what production's own passage
shortening (llama-server refuses >510 tokens, embed_batch halves the text) costs against a clean 512-token cut."""
import json, numpy as np
from common import *
ids = [l for l in open("/home/dan/sos-content/embeddings/docs.ids", encoding="utf-8").read().split("\n") if l]
P = np.fromfile("/home/dan/sos-content/embeddings/docs.f16.bin", dtype=np.float16).reshape(len(ids), 384)
np.save(SCRATCH / "P_shipped-index.npy", P)
np.save(SCRATCH / "Q_shipped-index.npy", np.load(SCRATCH / "Q_bge-small-en-v1.5.npy"))
e = json.loads((RESULTS / "embed" / "bge-small-en-v1.5.json").read_text()); e["tag"] = "shipped-index"; e["name"] = "shipped-index"
(RESULTS / "embed" / "shipped-index.json").write_text(json.dumps(e, indent=1))
