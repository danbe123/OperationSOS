"""Diagnostic: does the reranker pipeline score sanely, and what does a reranker put first where it demotes the box's own card?"""
import json, sys, torch, numpy as np
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from common import *
from models import RERANK
from hybrid import systems
name = sys.argv[1]
corpus = json.loads((SCRATCH / "corpus.json").read_text()); queries = json.loads((SCRATCH / "queries.json").read_text())
tok = AutoTokenizer.from_pretrained(RERANK[name]["hf"]); m = AutoModelForSequenceClassification.from_pretrained(RERANK[name]["hf"], dtype=torch.float16).cuda().eval()
def sc(q, docs):
    b = tok([q] * len(docs), docs, truncation="only_second", max_length=512, padding=True, return_tensors="pt").to("cuda")
    with torch.no_grad(): return m(**b).logits[:, 0].float().cpu().numpy()
print("sanity:", sc("what is a panda?", ["The giant panda is a bear species endemic to China.", "Paris is the capital of France."]))
lists = json.loads((SCRATCH / "top_e5-base-v2.json").read_text())
pool = {k: [i for i, _ in v][:30] for k, v in systems(lists)["dense"].items()}
out = []
for q in queries:
    if q["set"] != "safety": continue
    r = best_rank(pool[q["id"]], set(q["rel"]))
    if r is None or r > 3: continue
    s = sc(q["query"], [corpus[i]["text"] for i in pool[q["id"]]])
    order = [pool[q["id"]][j] for j in np.argsort(-s)]
    r2 = best_rank(order, set(q["rel"]))
    if r2 is None or r2 > 3:
        out.append({"id": q["id"], "query": q["query"], "gold_rank_before": r, "gold_rank_after": r2,
                    "ce_top3": [(corpus[i]["kind"], corpus[i]["title"][:60], corpus[i]["url"][:50]) for i in order[:3]],
                    "gold": [(corpus[i]["title"][:50], len(corpus[i]["text"])) for i in list(set(q["rel"]) & set(pool[q["id"]]))[:1]]})
for o in out: print(json.dumps(o))
dump(f"C_diag_{name}.json", out)
