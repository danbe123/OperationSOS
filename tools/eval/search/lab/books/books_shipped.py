"""Calibration against the real thing: the shipped 70,558-book household index (bge-small, today's representation), read-only,
searched with the same gold queries (bge-small query vectors from the lab's own embedding of them, fp16 torch; the index holds q8_0 GGUF
vectors, cosine 0.9998 apart).  Ranks are among ALL books of the real library.  Run with the API venv:
   PYTHONPATH=<worktree>/api books_shipped.py -> results/books/shipped_full_scale.json"""
import json, sys, hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import SCRATCH, RESULTS, REPO, m_rr, m_hit   # noqa: E402
from sos.embeddings import ApproxIndex                    # noqa: E402

B = SCRATCH / "books"
Q = np.load(B / "V_bge-small-en-v1.5.npz")["Q"].astype(np.float32)
idx = ApproxIndex.load(Path("/home/dan/sos-content/embeddings"), "household")
ids = {l.strip() for l in open("/home/dan/sos-content/embeddings/household.ids") if l.strip()}
print("index", len(idx), "books")
idx.hnsw.set_ef(2000) if hasattr(idx, "hnsw") else None
queries = []
for name in ("books", "books-extra"):
    for line in (REPO / f"tools/eval/search/{name}.jsonl").read_text().splitlines():
        queries.append(json.loads(line))
out, ranks = {}, {}
for qi, q in enumerate(queries):
    rel = set()
    for e in q["expected"]:
        key = f"gutenberg_en_all:{e['gutenberg']}" if "gutenberg" in e else f"survivorlibrary.com_en_all:{e['survivor']}"
        if key in ids:
            rel.add(key)
    if not rel:
        continue
    hits = idx.search(Q[qi], k=1000)
    pos = next((r for r, (k, _) in enumerate(hits, 1) if k in rel), None)
    ranks[q["id"]] = {"rank": pos, "n_rel": len(rel), "set": q["set"], "group": q["group"]}


def summ(sel):
    r = [v["rank"] for v in sel]
    f = lambda fn: float(np.mean([fn(x) for x in r]))
    return {"n": len(r), "mrr@10": f(m_rr), "hit@5": f(lambda x: m_hit(x, 5)), "hit@10": f(lambda x: m_hit(x, 10)), "hit@100": f(lambda x: m_hit(x, 100)),
            "median_rank": float(np.median([x if x else 1001 for x in r]))}


books = [v for k, v in ranks.items() if v["set"] == "books"]
extra = [v for k, v in ranks.items() if v["set"] == "books-extra"]
res = {"known (books.jsonl Gutenberg)": summ([v for v in books if v["group"] == "gutenberg"]),
       "sl (books.jsonl Survivor)": summ([v for v in books if v["group"] == "survivor"]),
       "extras (all 58)": summ(extra),
       "extras survivor-only": summ([v for v in extra if v["group"] == "survivor"]),
       "extras gutenberg-only": summ([v for v in extra if v["group"] == "gutenberg"]),
       "extras both": summ([v for v in extra if v["group"] == "both"]),
       "everyday (sl + extras)": summ([v for v in books if v["group"] == "survivor"] + extra), "ranks": ranks}
(RESULTS / "books" / "shipped_full_scale.json").write_text(json.dumps(res))
for k, v in res.items():
    if k != "ranks":
        print(f"{k:34s}", {a: round(b, 3) for a, b in v.items()})
