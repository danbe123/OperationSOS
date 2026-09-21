"""Materialise the corpus and the queries once (scratch copy for the GPU scripts; only the counts are committed)."""
import json
from collections import Counter
from common import *

conn = connect_ro()
corpus = load_corpus(conn)
urls = [c["url"] for c in corpus]
queries, info = load_queries(conn, urls)
SCRATCH.mkdir(parents=True, exist_ok=True)
(SCRATCH / "corpus.json").write_text(json.dumps(corpus))
(SCRATCH / "queries.json").write_text(json.dumps(queries))
lens = [len(c["text"]) for c in corpus]
kinds = Counter(c["kind"] for c in corpus)
stats = {"passages": len(corpus), "unique_urls": len(set(urls)), "kinds": dict(kinds), "mean_chars": sum(lens) / len(lens),
         "at_cap_2584": sum(1 for l in lens if l >= 2584), "queries": info["total"] | {}, "kept": info["kept"],
         "dropped": {s: len(v) for s, v in info["dropped"].items()}, "dropped_ids": info["dropped"],
         "groups": dict(Counter(f"{q['set']}/{q['group']}" for q in queries)),
         "rel_sizes": {"mean": sum(len(q["rel"]) for q in queries) / len(queries), "max": max(len(q["rel"]) for q in queries)}}
print(json.dumps(stats, indent=1))
dump("corpus_stats.json", stats)
