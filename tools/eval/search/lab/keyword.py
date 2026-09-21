"""The keyword side: FTS5 over the same passages, with the project's query preparation (api/sos/query.py).
Two variants, both kept to 100 rows per query:
  bm25 -- one bm25(fts_docs, 5.0, 1.0) ranking over every corpus passage; expanded AND query, OR fallback when
          fewer than FTS_OR_BELOW rows (what search.py's fts_rows does before its re-sort).
  prod -- search.py's fts_rows as the box runs it: the box's own passages (150 rows) and the converted-document
          pages (30 rows) fetched separately, each re-sorted by the share of the query's ideas the passage and its
          title carry, the two halves merged by 1/(K+rank) with the box's own first on ties.
Output: scratch/kw.json {variant: {query id: [[corpus index, score], ...]}}"""
import json
from common import *
from sos import query as query_mod
from sos.search import term_share, FTS_OR_BELOW, FTS_ROWS_OWN, FTS_ROWS_DOC, K, score

conn = connect_ro()
corpus = json.loads((SCRATCH / "corpus.json").read_text())
queries = json.loads((SCRATCH / "queries.json").read_text())
index_of = {c["url"]: i for i, c in enumerate(corpus)}
SQL = ("SELECT url, title, body, kind, bm25(fts_docs, 5.0, 1.0) AS b FROM fts_docs WHERE fts_docs MATCH ? AND kind {op} 'doc' "
       "ORDER BY bm25(fts_docs, 5.0, 1.0) LIMIT {n}")
SQL_ALL = ("SELECT url, title, body, kind, bm25(fts_docs, 5.0, 1.0) AS b FROM fts_docs WHERE fts_docs MATCH ? AND kind != 'item' "
           "ORDER BY bm25(fts_docs, 5.0, 1.0) LIMIT {n}")


def fetch(sql, terms):
    rows = conn.execute(sql, (query_mod.fts_match_expanded(terms, "and"),)).fetchall()
    if len(terms) >= 2 and len(rows) < FTS_OR_BELOW:
        have = {r["url"] for r in rows}
        extra = [r for r in conn.execute(sql, (query_mod.fts_match_expanded(terms, "or"),)).fetchall() if r["url"] not in have]
        rows = list(rows) + extra
    return rows


out = {"bm25": {}, "prod": {}}
for q in queries:
    terms = query_mod.reduce_query(q["query"]).terms
    if not terms:
        out["bm25"][q["id"]] = out["prod"][q["id"]] = []
        continue
    # bm25 variant: fetch a generous 400 (the skipped go-deeper/source rows drop out below), keep 100
    rows = fetch(SQL_ALL.format(n=400), terms)
    lst = [(index_of[r["url"]], -r["b"]) for r in rows if r["url"] in index_of][:100]
    out["bm25"][q["id"]] = lst
    # prod variant
    merged = []
    for docs in (False, True):
        n = FTS_ROWS_DOC if docs else FTS_ROWS_OWN
        rows = fetch(SQL.format(op="=" if docs else "!=", n=n), terms)
        rows = [r for r in rows if r["url"] in index_of]
        key = {r["url"]: term_share(terms, f"{r['title']} {r['body']}") + term_share(terms, r["title"]) for r in rows}
        rows = sorted(rows, key=lambda r: -key[r["url"]])
        merged += [(score(1.0, rank), 0 if not docs else 1, index_of[r["url"]], key[r["url"]]) for rank, r in enumerate(rows, 1)]
    merged.sort(key=lambda t: (-t[0], t[1]))
    out["prod"][q["id"]] = [(i, s) for _, _, i, s in merged][:100]
(SCRATCH / "kw.json").write_text(json.dumps(out))
for v in out:
    ranks = {q["id"]: best_rank([i for i, _ in out[v][q["id"]]], set(q["rel"])) for q in queries}
    s = summarise(queries, ranks)
    print(v, {g: (s[g]["hit@5"], s[g]["mrr@10"]) for g in ("paraphrase", "safety", "own-library")}, "empty:", sum(1 for q in queries if not out[v][q["id"]]))
