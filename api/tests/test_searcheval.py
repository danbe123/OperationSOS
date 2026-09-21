# api/tests/test_searcheval.py
"""The search benchmark's own tests: metrics on hand-made rankings, gold-file loading and validation on tiny
fixtures, the runner with a fake search, and the comparison. No services, no real data."""
import asyncio
import json
import math
from pathlib import Path

import pytest

from sos import cli, db, searcheval as se
from sos.searcheval import GoldRow


# --- metrics -----------------------------------------------------------------------------------------------------

def test_first_rank_is_one_based_and_takes_the_first_of_several_matches():
    urls = ["/a", "/b#x", "/c", "/b"]
    assert se.first_rank(urls, ["/c"]) == 3
    assert se.first_rank(urls, ["/b"]) == 2            # the fragment of the expected page counts
    assert se.first_rank(urls, ["/c", "/b"]) == 2      # alternatives: whichever comes first
    assert se.first_rank(urls, ["/zzz"]) is None       # absent
    assert se.first_rank([], ["/a"]) is None
    assert se.first_rank(urls, []) is None


def test_first_rank_matches_at_a_boundary_only():
    assert se.first_rank(["/book/gutenberg/27011"], ["/book/gutenberg/2701"]) is None
    assert se.first_rank(["/read/w/Iodine_deficiency"], ["/read/w/Iodine"]) is None
    assert se.first_rank(["/read/w/Iodine/sub"], ["/read/w/Iodine"]) == 1
    assert se.first_rank(["/kiwix/content/z/a%20b.pdf"], ["/kiwix/content/z/a b.pdf"]) == 1   # url-encoding is not a difference


def test_hit_reciprocal_rank_and_ndcg_by_rank():
    assert [se.hit_at(r, 3) for r in (1, 3, 4, None)] == [1.0, 1.0, 0.0, 0.0]
    assert se.reciprocal_rank(1) == 1.0
    assert se.reciprocal_rank(4) == 0.25
    assert se.reciprocal_rank(11) == 0.0               # outside the top ten is a miss
    assert se.reciprocal_rank(None) == 0.0
    assert se.ndcg(1) == 1.0
    assert se.ndcg(3) == pytest.approx(0.5)            # 1 / log2(4)
    assert se.ndcg(10) == pytest.approx(1 / math.log2(11))
    assert se.ndcg(11) == 0.0 and se.ndcg(None) == 0.0


def test_percentile_is_nearest_rank_and_empty_safe():
    values = [float(v) for v in range(1, 21)]           # 1..20
    assert se.percentile(values, 95) == 19.0
    assert se.percentile(values, 50) == 10.0
    assert se.percentile([7.0], 95) == 7.0
    assert se.percentile([], 95) is None
    assert se.percentile([3.0, 1.0, 2.0], 95) == 3.0   # unsorted input


def test_metrics_of_a_hand_made_group():
    recs = [{"rank": 1, "latency_ms": 100}, {"rank": 3, "latency_ms": 200}, {"rank": 7, "latency_ms": 300},
            {"rank": 12, "latency_ms": 400}, {"rank": None, "latency_ms": 1000}]
    m = se.metrics(recs)
    assert m["n"] == 5
    assert (m["hit@1"], m["hit@3"], m["hit@5"], m["hit@10"]) == (0.2, 0.4, 0.4, 0.6)
    assert m["mrr@10"] == pytest.approx((1 + 1 / 3 + 1 / 7) / 5)
    assert m["ndcg@10"] == pytest.approx((1 + 0.5 + 1 / math.log2(8)) / 5)
    assert m["lat_median_ms"] == 300 and m["lat_p95_ms"] == 1000
    assert se.metrics([]) == {"n": 0}


def test_buckets():
    assert [se.bucket(r) for r in (1, 2, 3, 4, 10, 11, None)] == ["top1", "top3", "top3", "top10", "top10", "miss", "miss"]


def test_summary_groups_by_set_group_and_overall():
    queries = {"a": {"set": "books", "group": "gutenberg"}, "b": {"set": "books", "group": "survivor"}, "c": {"set": "safety", "group": ""}}
    records = {"a": {"rank": 1, "latency_ms": 1}, "b": {"rank": None, "latency_ms": 2}, "c": {"rank": 2, "latency_ms": 3}}
    s = se.summarise_records(queries, records)
    assert list(s) == ["books", "books/gutenberg", "books/survivor", "safety", "ALL"]
    assert s["books"]["n"] == 2 and s["books"]["hit@1"] == 0.5
    assert s["books/survivor"]["hit@10"] == 0.0
    assert s["ALL"]["n"] == 3


def test_rescued_and_regressed_are_about_the_top_ten_only():
    queries = {q: {"set": "s", "query": q} for q in "abcde"}
    off = {"a": {"rank": None}, "b": {"rank": 4}, "c": {"rank": 2}, "d": {"rank": 12}, "e": {"rank": 1}}
    on = {"a": {"rank": 5}, "b": {"rank": None}, "c": {"rank": 1}, "d": {"rank": 20}, "e": {"rank": 1}}
    out = se.rescued_and_regressed(queries, off, on)
    assert [r["id"] for r in out["rescued"]] == ["a"]
    assert [r["id"] for r in out["regressed"]] == ["b"]       # c only moved up, d stayed out, e stayed put


# --- gold files ----------------------------------------------------------------------------------------------------

def write(path, *rows):
    path.write_text("\n".join(r if isinstance(r, str) else json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def row(rid, query="a query", set_="demo", expected=None, **extra):
    return {"id": rid, "query": query, "set": set_, "expected": expected if expected is not None else [{"url": "/p/water"}],
            "notes": "", **extra}


def test_a_good_gold_file_loads(tmp_path):
    write(tmp_path / "demo.jsonl", row("d1", group="g", tags=["guard"]), "", row("d2", expected=[{"item": "module:water"}, {"gutenberg": 5}]))
    rows, problems = se.load_gold_file(tmp_path / "demo.jsonl")
    assert problems == []
    assert [r.id for r in rows] == ["d1", "d2"]
    assert rows[0].group == "g" and rows[0].tags == ["guard"] and rows[0].source == "demo.jsonl:1"


def test_gold_shape_problems_are_all_reported(tmp_path):
    write(tmp_path / "demo.jsonl",
          "{not json",
          row("d1"),
          row("d1", query="again"),                                   # duplicate id
          {"id": "d3", "query": "no set", "expected": [{"url": "/x"}]},
          row("d4", set_="other"),                                     # set differs from the file name
          row("d5", expected=[]),
          row("d6", expected=[{"url": "/x", "gutenberg": 1}]),         # two keys
          row("d7", expected=[{"nonsense": 1}]),
          row("d8", query="  "),
          "[1, 2]")
    rows, problems = se.load_gold_file(tmp_path / "demo.jsonl")
    text = "\n".join(problems)
    for needle in ("not valid JSON", "duplicate id 'd1'", "missing set", "set is 'other'", "expected must be a non-empty list",
                   "exactly one of", "query must be a non-empty string", "must be a JSON object"):
        assert needle in text, needle
    assert [r.id for r in rows] == ["d1", "d4"]     # d4's set is wrong but its shape is otherwise loadable


def test_duplicate_ids_across_files_and_unknown_set_names(tmp_path):
    write(tmp_path / "one.jsonl", row("x1", set_="one"))
    write(tmp_path / "two.jsonl", row("x1", set_="two"), row("x2", set_="two"))
    rows, problems = se.load_gold(tmp_path)
    assert [r.id for r in rows] == ["x1", "x2"]
    assert any("duplicate id 'x1'" in p and "one.jsonl:1" in p for p in problems)
    rows, problems = se.load_gold(tmp_path, ["two", "nope"])
    assert [r.id for r in rows] == ["x1", "x2"] and any("no gold set named 'nope'" in p for p in problems)


# --- validating against data ---------------------------------------------------------------------------------------

class FakeZims:
    def __init__(self, entries):
        self.entries = entries

    def check(self, zim, path):
        return None if (zim, path) in self.entries else f"{zim} has no entry {path!r}"


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "t.db")
    db.init_schema(c)
    c.execute("INSERT INTO fts_docs(title, body, doc_id, kind, category, url) VALUES ('Water','x','w','page','survival','/p/water#boil')")
    c.execute("INSERT INTO fts_docs(title, body, doc_id, kind, category, url) VALUES ('Choking','x','c','card','medical','/medical/card/choking#steps')")
    c.execute("INSERT INTO fts_docs(title, body, doc_id, kind, category, url) VALUES ('Manual','x','m','doc','manual','/doc/manual#page=4')")
    c.execute("INSERT INTO books(zim, id, title, author) VALUES ('gutenberg_en_all', 2701, 'Moby Dick; Or, The Whale', 'Melville, Herman')")
    c.execute("INSERT INTO library_items(id, kind, available, local_path) VALUES ('wikipedia_en_all_maxi','zim',1,'/nowhere.zim')")
    c.commit()
    yield c
    c.close()


def problems_for(conn, tmp_path, *rows, zims=None):
    write(tmp_path / "demo.jsonl", *rows)
    _rows, problems = se.validate_gold(tmp_path, conn, zims or FakeZims({("wikipedia_en_all_maxi", "Iodine"),
                                                                       ("survivorlibrary.com_en_all", "www.survivorlibrary.com/library/bees_1900.pdf")}))
    return problems


def test_validation_passes_real_pages(conn, tmp_path):
    good = [row("d1", expected=[{"url": "/p/water"}]), row("d2", "q2", expected=[{"item": "card:choking"}]),
            row("d3", "q3", expected=[{"url": "/doc/manual#page=4"}]), row("d4", "q4", expected=[{"gutenberg": 2701, "title": "Moby Dick; Or, The Whale"}]),
            row("d5", "q5", expected=[{"url": "/read/wikipedia_en_all_maxi/Iodine"}]), row("d6", "q6", expected=[{"survivor": "bees_1900"}]),
            row("d7", "q7", expected=[{"item": "wikipedia_en_all_maxi", "path": "Iodine"}])]
    assert problems_for(conn, tmp_path, *good) == []


def test_validation_names_every_missing_page(conn, tmp_path):
    bad = [row("d1", expected=[{"url": "/p/nothing"}]), row("d2", "q2", expected=[{"item": "module:nothing"}]),
           row("d3", "q3", expected=[{"gutenberg": 99}]), row("d4", "q4", expected=[{"gutenberg": 2701, "title": "Moby"}]),
           row("d5", "q5", expected=[{"url": "/read/wikipedia_en_all_maxi/Nope"}]), row("d6", "q6", expected=[{"survivor": "nope"}]),
           row("d7", "q7", expected=[{"item": "not_a_zim", "path": "x"}]), row("d8", "q8", expected=[{"url": "/weird/route"}]),
           row("d9", "q9", expected=[{"url": "/doc/absent#page=1"}])]
    text = "\n".join(problems_for(conn, tmp_path, *bad))
    for needle in ("d1: no authored page at /p/nothing", "d2: no authored page", "d3: Gutenberg id 99", "d4: Gutenberg 2701 is titled",
                   "d5: wikipedia_en_all_maxi has no entry 'Nope'", "d6: survivorlibrary.com_en_all has no entry", "d7: 'not_a_zim' is not a known item",
                   "d8: cannot check", "d9: no converted document"):
        assert needle in text, needle


FIXTURE_ZIM = Path(__file__).parent / "fixtures" / "library" / "wikipedia_en_100_mini_2026-01.zim"


def test_zim_checker_finds_articles_and_names_redirects_and_unsearched_zims(conn):
    conn.execute("UPDATE library_items SET local_path=?, fts=1 WHERE id='wikipedia_en_all_maxi'", (str(FIXTURE_ZIM),))
    conn.execute("INSERT INTO library_items(id, kind, available, local_path, fts) VALUES ('unindexed','zim',1,?,0)", (str(FIXTURE_ZIM),))
    zims = se.ZimChecker(conn)
    assert zims.check("wikipedia_en_all_maxi", "Virus") is None
    assert zims.check("wikipedia_en_all_maxi", "") is None                        # the ZIM as a whole
    assert "no entry 'Nope'" in zims.check("wikipedia_en_all_maxi", "Nope")
    assert "redirect to 'Elvis_Presley'" in zims.check("wikipedia_en_all_maxi", "(Keep_Your)_Hands_Off_(Of_It)")
    assert "no full-text index" in zims.check("unindexed", "Virus")
    assert "not an available ZIM" in zims.check("missing", "Virus")
    docs = se.DocUrls(conn)
    assert se.check_expected({"url": "/read/wikipedia_en_all_maxi/Virus"}, conn, docs, zims) is None
    assert se.check_expected({"url": "/read/wikipedia_en_all_maxi"}, conn, docs, zims) is None   # a bare ZIM expectation
    assert se.check_expected({"item": "wikipedia_en_all_maxi", "path": "Nope"}, conn, docs, zims)


def test_validation_flags_a_repeated_query_within_a_set(conn, tmp_path):
    text = "\n".join(problems_for(conn, tmp_path, row("d1", "Same  Query"), row("d2", "same query")))
    assert "d2: same query as d1" in text


def test_cli_validate_exits_non_zero_on_problems(conn, tmp_path, capsys):
    write(tmp_path / "demo.jsonl", row("d1", expected=[{"url": "/p/nothing"}]))
    conn.commit()
    code = se.cmd_validate(tmp_path, tmp_path / "t.db", None)
    out = capsys.readouterr().out
    assert code == 1 and "no authored page" in out and "1 problem" in out
    write(tmp_path / "demo.jsonl", row("d1"))
    assert se.cmd_validate(tmp_path, tmp_path / "t.db", None) == 0


def test_open_readonly_cannot_write(conn, tmp_path):
    conn.commit()
    ro = se.open_readonly(tmp_path / "t.db")
    assert ro.execute("SELECT count(*) FROM books").fetchone()[0] == 1
    with pytest.raises(Exception):
        ro.execute("INSERT INTO settings(key, value) VALUES ('a','b')")
    ro.close()


def test_resolve_expected_forms(conn):
    assert se.resolve_expected({"url": "/x"}, conn) == "/x"
    assert se.resolve_expected({"gutenberg": 5}, conn) == "/book/gutenberg/5"
    assert se.resolve_expected({"survivor": "bees_1900"}, conn) == "/kiwix/content/survivorlibrary.com_en_all/www.survivorlibrary.com/library/bees_1900.pdf"
    assert se.resolve_expected({"item": "module:water"}, conn) == "/m/water"
    assert se.resolve_expected({"item": "wikipedia_en_all_maxi", "path": "Iodine"}, conn) == "/read/wikipedia_en_all_maxi/Iodine"
    assert se.resolve_expected({"item": "unknown"}, conn) is None
    assert se.resolve_urls({"survivor": "bees_1900"}, conn) == [
        "/kiwix/content/survivorlibrary.com_en_all/www.survivorlibrary.com/library/bees_1900.pdf",
        "/read/survivorlibrary.com_en_all/www.survivorlibrary.com/library/bees_1900.pdf"]
    assert se.resolve_urls({"gutenberg": 5}, conn) == ["/book/gutenberg/5"] and se.resolve_urls({"item": "unknown"}, conn) == []


# --- the runner ----------------------------------------------------------------------------------------------------

def make_rows():
    return [GoldRow("q1", "water", [{"url": "/p/water"}], "demo"), GoldRow("q2", "choke", [{"url": "/medical/card/choking"}], "demo", group="g"),
            GoldRow("q3", "moby", [{"gutenberg": 2701}], "books")]


EXPECTED = {"q1": ["/p/water"], "q2": ["/medical/card/choking"], "q3": ["/book/gutenberg/2701"]}


def result(url, title="t", source="s", via=None):
    r = {"title": title, "url": url, "source": source}
    if via:
        r["via"] = via
    return r


def fake_search(calls, script):
    async def search_fn(query, mode):
        calls.append((query, mode))
        return script[(query, mode)]
    return search_fn


SCRIPT = {
    ("water", "off"): {"results": [result("/x"), result("/p/water#boil")]},
    ("water", "on"): {"results": [result("/p/water#boil")]},
    ("choke", "off"): {"results": [result("/y")]},
    ("choke", "on"): {"results": [result("/y"), result("/medical/card/choking#steps", via="meaning")]},
    ("moby", "off"): {"results": [result("/book/gutenberg/2701")]},
    ("moby", "on"): {"results": [result("/z"), result("/book/gutenberg/2701")]},
}


def test_runner_scores_both_modes_and_alternates_their_order():
    calls: list = []
    ticks = iter(x * 0.01 for x in range(1000))
    runs = asyncio.run(se.run_rows(make_rows(), EXPECTED, ["off", "on"], fake_search(calls, SCRIPT), clock=lambda: next(ticks), pause=0))
    assert runs["off"]["q1"]["rank"] == 2 and runs["on"]["q1"]["rank"] == 1
    assert runs["off"]["q2"]["rank"] is None and runs["on"]["q2"]["rank"] == 2
    assert runs["off"]["q3"]["rank"] == 1 and runs["on"]["q3"]["rank"] == 2
    assert calls == [("water", "off"), ("water", "on"), ("choke", "on"), ("choke", "off"), ("moby", "off"), ("moby", "on")]
    rec = runs["on"]["q2"]
    assert rec["latency_ms"] == pytest.approx(10.0) and rec["retries"] == 0 and rec["partial"] is False
    assert rec["top10"][1] == {"title": "t", "url": "/medical/card/choking#steps", "source": "s", "via": "meaning"}
    assert rec["top10"][0]["via"] == ""


def test_runner_records_only_the_top_ten_but_ranks_past_it():
    urls = [result(f"/r{i}") for i in range(30)] + [result("/p/water")]
    rec = asyncio.run(se.run_one(make_rows()[0], ["/p/water"], "off", fake_search([], {("water", "off"): {"results": urls}}), pause=0))
    assert rec["rank"] == 31 and len(rec["top10"]) == 10 and rec["n_results"] == 31
    assert se.hit_at(rec["rank"], 10) == 0.0


def test_a_partial_or_meaningless_search_is_asked_again():
    answers = iter([{"results": [], "partial": True}, {"results": [result("/p/water")], "semantic_ok": False},
                    {"results": [result("/p/water")], "semantic_ok": True}])
    calls = []

    async def search_fn(query, mode):
        calls.append(query)
        return next(answers)

    rec = asyncio.run(se.run_one(make_rows()[0], ["/p/water"], "on", search_fn, pause=0))
    assert len(calls) == 3 and rec["retries"] == 2 and rec["rank"] == 1 and rec["partial"] is False and rec["semantic_ok"] is True


def test_a_search_that_never_comes_back_clean_is_recorded_as_such():
    async def search_fn(query, mode):
        return {"results": [], "partial": True}

    rec = asyncio.run(se.run_one(make_rows()[0], ["/p/water"], "off", search_fn, pause=0))
    assert rec["retries"] == se.MAX_ATTEMPTS - 1 and rec["partial"] is True and rec["rank"] is None


def test_permanently_partial_searches_stop_being_retried():
    calls = []

    async def search_fn(query, mode):
        calls.append(query)
        return {"results": [], "partial": True}

    rows = [GoldRow(f"q{i}", f"q{i}", [{"url": "/x"}], "demo") for i in range(6)]
    runs = asyncio.run(se.run_rows(rows, {r.id: ["/x"] for r in rows}, ["off"], search_fn, pause=0))
    # STUCK_AFTER queries at MAX_ATTEMPTS each, then one attempt per query
    assert len(calls) == se.STUCK_AFTER * se.MAX_ATTEMPTS + (6 - se.STUCK_AFTER)
    assert runs["off"]["q5"]["retries"] == 0 and runs["off"]["q5"]["partial"] is True
    assert runs["off"]["q0"]["retries"] == se.MAX_ATTEMPTS - 1


def test_keyword_only_runs_ignore_the_semantic_flag():
    async def search_fn(query, mode):
        return {"results": [result("/p/water")], "semantic_ok": False}

    rec = asyncio.run(se.run_one(make_rows()[0], ["/p/water"], "off", search_fn, pause=0))
    assert rec["retries"] == 0 and rec["semantic_ok"] is None


def run_document(modes=("off", "on")):
    rows = make_rows()
    runs = asyncio.run(se.run_rows(rows, EXPECTED, list(modes), fake_search([], SCRIPT), pause=0))
    return se.build_document(rows, EXPECTED, runs, {"date": "2026-09-20"})


def test_document_has_summary_changes_and_a_readable_report():
    doc = run_document()
    assert doc["summary"]["off"]["demo"]["hit@1"] == 0.0 and doc["summary"]["on"]["demo"]["hit@1"] == 0.5
    assert doc["summary"]["on"]["books"]["mrr@10"] == 0.5
    assert [c["id"] for c in doc["changes"]["rescued"]] == ["q2"] and doc["changes"]["regressed"] == []
    text = se.format_report(doc)
    assert "keyword only" in text and "meaning layer on" in text and "rescued 1" in text and "choke" in text
    assert "demo/g" in text and "ALL" in text
    assert "changes" not in run_document(["off"])


def test_json_round_trip_is_atomic_and_compact_keeps_misses(tmp_path):
    doc = se.compact(run_document(), keep_hit=1, keep=1)
    assert len(doc["runs"]["off"]["q3"]["top10"]) == 1            # found at rank 1: cut
    assert [r["url"] for r in doc["runs"]["on"]["q3"]["top10"]] == ["/z", "/book/gutenberg/2701"]   # rank 2: the answer stays
    assert doc["meta"]["compact"] == {"keep_hit": 1, "keep": 1}
    path = tmp_path / "out" / "run.json"
    se.write_json(path, doc)
    assert json.loads(path.read_text()) == doc
    assert not list(path.parent.glob("*.tmp"))


def test_compact_keeps_the_answer_when_it_is_deep_in_the_ranking():
    rec = {"rank": 8, "top10": [{"url": f"/r{i}"} for i in range(1, 11)]}
    doc = se.compact({"runs": {"on": {"q": rec}}}, keep_hit=3, keep=5)
    assert [r["url"] for r in doc["runs"]["on"]["q"]["top10"]] == ["/r1", "/r2", "/r3", "/r4", "/r5", "/r8"]
    miss = {"rank": None, "top10": [{"url": "/a"}] * 10}
    assert len(se.compact({"runs": {"on": {"q": miss}}})["runs"]["on"]["q"]["top10"]) == 5


def test_compare_shows_deltas_and_the_queries_that_moved(tmp_path, capsys):
    a, b = run_document(), run_document()
    b["runs"]["on"]["q1"]["rank"] = 5            # got worse: top1 -> top10
    b["runs"]["on"]["q2"]["rank"] = 1            # got better: top3 -> top1
    b["runs"]["off"]["q3"]["rank"] = None        # a miss now
    for name, doc in (("a.json", a), ("b.json", b)):
        se.write_json(tmp_path / name, doc)
    assert cli.main(["eval-compare", str(tmp_path / "a.json"), str(tmp_path / "b.json")]) == 0
    out = capsys.readouterr().out
    assert "mode on: a -> b" in out and "mode off: a -> b" in out
    assert "worse  q1" in out and "better q2" in out and "1 better, 1 worse" in out
    assert "worse  q3" in out
    assert "(+" in out and "(-" in out


def test_compare_rejects_files_that_are_not_runs(tmp_path, capsys):
    (tmp_path / "x.json").write_text("{}")
    (tmp_path / "y.json").write_text("nope")
    assert cli.main(["eval-compare", str(tmp_path / "x.json"), str(tmp_path / "x.json")]) == 1
    assert cli.main(["eval-compare", str(tmp_path / "y.json"), str(tmp_path / "x.json")]) == 1
    assert "not an eval-search run file" in capsys.readouterr().err


def test_cli_dispatches_eval_search(monkeypatch):
    calls = []
    monkeypatch.setattr(se, "run_from_namespace", lambda args: calls.append(args) or 0)
    assert cli.main(["eval-search", "safety", "--semantic", "off", "--limit", "20", "--json", "x.json"]) == 0
    a = calls[0]
    assert a.sets == ["safety"] and a.semantic == "off" and a.limit == 20 and a.json == "x.json" and not a.validate
    assert cli.main(["eval-search", "--validate"]) == 0 and calls[1].validate and calls[1].semantic == "both"


def test_the_committed_gold_files_are_well_formed():
    """Shape only (the real-data check is `sos eval-search --validate`, which needs the box's database)."""
    rows, problems = se.load_gold(se.DEFAULT_GOLD_DIR)
    assert problems == []
    assert len({r.id for r in rows}) == len(rows)
