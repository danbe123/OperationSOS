# api/tests/test_searchreplay.py
"""Record and replay of the search benchmark on a tiny database: a search recorded against a fake Kiwix and a
fake meaning layer, replayed with neither, ranks every query exactly as it did live."""
import asyncio
import json

import numpy as np
import pytest

from sos import db, search, searcheval as se, searchreplay as sr
from sos.embeddings import EmbeddingWatch
from sos.kiwix import KiwixError, KiwixHit
from sos.searcheval import GoldRow


class FakeKiwix:
    def __init__(self):
        self.calls = 0

    async def search(self, names, pattern, n, timeout):
        self.calls += 1
        if "refused" in pattern:
            raise KiwixError("search: HTTP 400: no", status=400)
        if "slow" in pattern:
            raise asyncio.TimeoutError()
        return [KiwixHit("Water", "A/Water", "<b>water</b> supply", "wikipedia_en_all_maxi"),
                KiwixHit("Fire", "A/Fire", "fire", "wikipedia_en_all_maxi")][:n]


class FakeSemantic:
    generation = 0
    cache_namespace = "fake"

    def __init__(self):
        self._vectors = {}
        self.asked = 0

    def refresh(self):
        pass

    def watch_embedding(self):
        import contextlib
        return contextlib.nullcontext(EmbeddingWatch())

    def _vector(self, q):
        vec = np.full(4, 0.5, dtype=np.float32)
        self._vectors[q.strip()] = (vec, 0.0)

    async def query(self, q, k=20):
        self.asked += 1
        self._vector(q)
        return [("/medical/card/choking#steps", 0.80), ("/p/water#boil", 0.70)][:k]

    async def query_household(self, q, k=20):
        self._vector(q)
        return []

    async def rerank_wikipedia(self, q, keys):
        self._vector(q)
        return {key: 0.5 for key in keys[:1]}


@pytest.fixture
def box(tmp_path, env):
    path = tmp_path / "box.db"
    c = db.connect(path)
    db.init_schema(c)
    c.executemany("INSERT INTO fts_docs(title, body, doc_id, kind, category, url) VALUES (?,?,?,?,?,?)", [
        ("Water", "boil water for one minute", "w", "page", "playbooks", "/p/water#boil"),
        ("Choking", "back blows for a choking adult", "c", "card", "playbooks", "/medical/card/choking#steps")])
    c.execute("INSERT INTO library_items(id,title,kind,tier,category,dest,available,fts,priority) "
              "VALUES ('wikipedia_en_all_maxi','Wikipedia','zim','core','reference','zim/w.zim',1,1,10)")
    db.set_setting(c, "zim_languages", json.dumps({"wikipedia_en_all_maxi": "eng"}))
    c.commit()
    c.close()
    return path


ROWS = [GoldRow("q-water", "boil water", [{"url": "/p/water"}], "demo"),
        GoldRow("q-choke", "someone choking", [{"item": "card:choking"}], "demo"),
        GoldRow("q-refused", "refused things", [{"url": "/p/water"}], "demo"),
        GoldRow("q-slow", "slow water", [{"url": "/p/water"}], "demo")]
EXPECTED = {"q-water": ["/p/water"], "q-choke": ["/medical/card/choking"], "q-refused": ["/p/water"], "q-slow": ["/p/water"]}


def live(box, env, folder):
    """A recorded run of ROWS against the fakes; the result of each query in each mode."""
    recorder = sr.Recorder(folder)
    kiwix = sr.RecordingKiwix(FakeKiwix(), recorder)
    semantic = sr.RecordingSemantic(FakeSemantic(), recorder)
    conn = se.open_readonly(box)

    async def search_fn(query, mode):
        kiwix.query = query
        payload = await search.search(conn, env, kiwix, query, None, 40, use_cache=False,
                                      semantic=semantic if mode == "on" else None)
        recorder.flush(query)
        return payload

    try:
        return asyncio.run(se.run_rows(ROWS, EXPECTED, ["off", "on"], search_fn, pause=0))
    finally:
        conn.close()


def test_a_replay_ranks_every_query_as_the_live_run_did(box, env, tmp_path):
    folder = tmp_path / "rec"
    recorded = live(box, env, folder)
    doc = asyncio.run(se.run_replay(ROWS, ["off", "on"], env, 40, box, tmp_path, folder))
    for mode in ("off", "on"):
        for row in ROWS:
            assert doc["runs"][mode][row.id]["rank"] == recorded[mode][row.id]["rank"], (mode, row.id)
            assert [r["url"] for r in doc["runs"][mode][row.id]["top10"]] == \
                [r["url"] for r in recorded[mode][row.id]["top10"]]
    assert doc["meta"]["replay_misses"] == {"kiwix": 0, "wikipedia": 0, "semantic_depth": 0}
    assert doc["runs"]["on"]["q-choke"]["rank"] == 1            # the meaning layer's card is in the replay too
    assert doc["runs"]["on"]["q-choke"]["semantic_ok"] is True


def test_the_recording_keeps_the_answers_refusals_and_vectors(box, env, tmp_path):
    folder = tmp_path / "rec"
    live(box, env, folder)
    files = {p.name for p in folder.glob("*.json")}
    assert sr.query_key("boil water") + ".json" in files
    kept = json.loads((folder / f"{sr.query_key('boil water')}.json").read_text())
    (request,) = kept["kiwix"].values()
    assert request["hits"][0][:2] == ["Water", "A/Water"]
    assert np.frombuffer(__import__("base64").b64decode(kept["semantic"]["vector"]), dtype=np.float32).shape == (4,)
    assert kept["semantic"]["docs"][0] == ["/medical/card/choking#steps", 0.8]
    (refusal,) = json.loads((folder / f"{sr.query_key('refused things')}.json").read_text())["kiwix"].values()
    assert refusal["error"] == "kiwix" and refusal["status"] == 400
    (slow,) = json.loads((folder / f"{sr.query_key('slow water')}.json").read_text())["kiwix"].values()
    assert slow["error"] == "timeout"


def test_a_replay_makes_no_request_and_is_repeatable(box, env, tmp_path):
    folder = tmp_path / "rec"
    live(box, env, folder)
    first = asyncio.run(se.run_replay(ROWS, ["off", "on"], env, 40, box, tmp_path, folder))
    second = asyncio.run(se.run_replay(ROWS, ["off", "on"], env, 40, box, tmp_path, folder))
    for mode in first["runs"]:
        assert {q: r["rank"] for q, r in first["runs"][mode].items()} == {q: r["rank"] for q, r in second["runs"][mode].items()}
    # the refused and slow queries replay as the same partial/complete outcomes they were
    assert first["runs"]["off"]["q-slow"]["partial"] is True and first["runs"]["off"]["q-refused"]["partial"] is False


def test_a_question_the_recording_cannot_answer_is_counted_not_hidden(box, env, tmp_path):
    folder = tmp_path / "rec"
    live(box, env, folder)
    path = folder / f"{sr.query_key('boil water')}.json"
    kept = json.loads(path.read_text())
    kept["kiwix"] = {}
    path.write_text(json.dumps(kept))
    doc = asyncio.run(se.run_replay(ROWS[:1], ["off"], env, 40, box, tmp_path, folder))
    assert doc["meta"]["replay_misses"]["kiwix"] == 1 and doc["runs"]["off"]["q-water"]["partial"] is True


def test_a_query_never_recorded_is_an_error(box, env, tmp_path):
    folder = tmp_path / "rec"
    folder.mkdir()
    with pytest.raises(sr.ReplayError):
        asyncio.run(se.run_replay(ROWS[:1], ["off"], env, 40, box, tmp_path, folder))


def test_a_retried_query_keeps_its_answer_over_a_later_refusal(tmp_path):
    rec = sr.Recorder(tmp_path)
    rec.kiwix("q", ["a"], "p", 8, {"hits": [["T", "P", "S", "a"]]})
    rec.kiwix("q", ["a"], "p", 8, {"error": "timeout"})
    rec.kiwix("q", ["b"], "p", 8, {"error": "timeout"})
    rec.kiwix("q", ["b"], "p", 8, {"hits": []})
    kept = rec.queries[sr.query_key("q")]["kiwix"]
    assert "hits" in kept[sr.request_key(["a"], "p")] and "hits" in kept[sr.request_key(["b"], "p")]


def test_record_and_replay_are_exclusive(tmp_path, capsys, monkeypatch):
    from sos import cli
    monkeypatch.setattr(se, "load_gold", lambda *a, **k: ([GoldRow("a", "a", [{"url": "/x"}], "demo")], []))
    assert cli.main(["eval-search", "--record", str(tmp_path / "a"), "--replay", str(tmp_path / "b")]) == 1
    assert "pick one" in capsys.readouterr().err


# --- recorded depth (task 25): a replay must not silently answer a deeper question than was recorded -----------

def _one_query(tmp_path, semantic):
    folder = tmp_path / "rec"
    folder.mkdir()
    (folder / f"{sr.query_key('gash')}.json").write_text(json.dumps({"format": 1, "query": "gash", "kiwix": {},
                                                                     "semantic": semantic}))
    return sr.Replay(folder)


def test_a_replay_asked_deeper_than_the_recording_counts_a_miss(tmp_path):
    """An old recording kept the nearest 100; search() asks CARD_SEMANTIC_K (500). Slicing the 100 and calling
    it an answer would hide that ranks 101-500 were never seen."""
    replay = _one_query(tmp_path, {"docs": [[f"/p/x#{i}", 0.9 - i / 1000] for i in range(100)]})
    near = asyncio.run(sr.ReplaySemantic(replay).query("gash", 500))
    assert len(near) == 100 and replay.misses["semantic_depth"] == 1


def test_a_replay_within_the_recorded_depth_or_of_an_exhausted_list_is_no_miss(tmp_path):
    replay = _one_query(tmp_path, {"docs": [[f"/p/x#{i}", 0.9] for i in range(100)], "docs_k": 500,
                                   "household": [["gutenberg_en_all:1", 0.7]], "household_k": 500})
    sem = sr.ReplaySemantic(replay)
    assert len(asyncio.run(sem.query("gash", 500))) == 100          # asked 500, the index had only 100
    assert len(asyncio.run(sem.query("gash", 20))) == 20
    assert len(asyncio.run(sem.query_household("gash", 60))) == 1
    assert replay.misses["semantic_depth"] == 0


def test_the_recorder_keeps_the_depth_it_asked_for(tmp_path):
    class Inner:
        _vectors = {}

        async def query(self, q, k=20):
            return [("/p/a", 0.8)] * min(k, 3)

        async def query_household(self, q, k=20):
            return []

    rec = sr.Recorder(tmp_path / "rec")
    sem = sr.RecordingSemantic(Inner(), rec)
    asyncio.run(sem.query("gash", 500))
    asyncio.run(sem.query_household("gash", 60))
    slot = rec.queries[sr.query_key("gash")]["semantic"]
    assert slot["docs_k"] == max(500, sr.RECORD_K) and slot["household_k"] == max(60, sr.RECORD_K)
    assert sr.RECORD_K >= search.CARD_SEMANTIC_K      # a fresh recording answers search()'s deepest question
