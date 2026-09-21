"""What kind of passage does each model put first? Share of top-1 / top-10 that are the box's authored kinds
(card, module, page, playbook) and median length of the top-1 text: the gold names authored pages, so a model that
likes short authored passages is favoured by this gold. Writes results/bias.json."""
import json, statistics
from common import *
corpus = json.loads((SCRATCH / "corpus.json").read_text()); queries = json.loads((SCRATCH / "queries.json").read_text())
AUTH = {"card", "module", "page", "playbook"}
out = {}
n_auth = sum(1 for c in corpus if c["kind"] in AUTH)
for tag in ["bge-small-en-v1.5", "e5-base-v2", "gte-base", "granite-embedding-english-r2", "granite-embedding-small-english-r2", "bge-base-en-v1.5", "bge-large-en-v1.5", "mxbai-embed-large-v1", "e5-small-v2"]:
    lists = json.loads((SCRATCH / f"top_{tag}.json").read_text())
    top1 = [lists[q["id"]][0][0] for q in queries]
    top10 = [i for q in queries for i, _ in lists[q["id"]][:10]]
    out[tag] = {"top1_authored_share": round(sum(corpus[i]["kind"] in AUTH for i in top1) / len(top1), 3),
                "top10_authored_share": round(sum(corpus[i]["kind"] in AUTH for i in top10) / len(top10), 3),
                "top1_median_chars": int(statistics.median(len(corpus[i]["text"]) for i in top1))}
anyauth = [any(corpus[i]["kind"] in AUTH for i in q["rel"]) for q in queries]
auth_rel = [len([i for i in q["rel"] if corpus[i]["kind"] in AUTH]) for q in queries]
out["_corpus"] = {"authored_passages": n_auth, "of": len(corpus), "queries_with_an_authored_relevant_passage": round(sum(anyauth) / len(anyauth), 3), "queries_with_only_document_pages_relevant": sum(1 for a in anyauth if not a),
                  "median_authored_relevant_per_query": statistics.median(auth_rel), "authored_median_chars": int(statistics.median(len(c["text"]) for c in corpus if c["kind"] in AUTH)), "doc_median_chars": int(statistics.median(len(c["text"]) for c in corpus if c["kind"] not in AUTH))}
dump("bias.json", out)
for k, v in out.items(): print(k, v)
