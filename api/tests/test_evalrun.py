# api/tests/test_evalrun.py
import json
from pathlib import Path

import pytest

import sos.evalrun as ev
from sos.ai import REFUSAL_TEXT
from sos.evalrun import (EvalContext, Expected, Question, check_gates, expected_url, is_applicable, load_questions,
                         previous_summary, run_cli, run_path, run_questions, summarise, url_matches, write_run)

FIXTURE = Path(__file__).parent / "fixtures" / "eval" / "questions.jsonl"
WIKI = "wikipedia_en_100_mini_2026-01"
NHS = "nhs.uk_en_medicines_2025-12"
MI = {"n": 1, "title": "Myocardial infarction", "url": f"/read/{WIKI}/Myocardial_infarction", "source": WIKI,
      "text": "A heart attack occurs when blood flow stops."}
CARD = {"n": 1, "title": "Heart attack", "url": "/medical/card/heart-attack", "source": "playbooks", "text": "Call 999 now."}
STROKE = {"n": 1, "title": "Stroke", "url": "/medical/card/stroke", "source": "playbooks", "text": "Think FAST."}
SCRIPT = {
    "what are the symptoms of a heart attack": (None, [MI], "Chest pain and breathlessness [1]."),
    "heart attack": ("/medical/card/heart-attack", [CARD], "Call 999 [1]."),
    "what is the weather forecast for tomorrow": (None, [], None),
}


def fake_events(script):
    """script maps a question to (verbatim_url | None, [passages], answer | None)."""

    async def events(question):
        verbatim, passages, answer = script[question]
        if verbatim:
            yield "verbatim", {"title": "Heart attack", "url": verbatim, "paragraphs": ["Call 999 now."], "as_at": None}
        yield "retrieving", {"query": question, "passages": passages}
        if answer is None:
            if not passages:
                yield "done", {"answer": REFUSAL_TEXT, "grounded": False, "citations": []}
            return
        for word in answer.split(" "):
            yield "token", {"text": word + " "}
        cites = [{"n": p["n"], "title": p["title"], "url": p["url"], "source": p["source"]}
                 for p in passages if f"[{p['n']}]" in answer]
        yield "done", {"answer": answer, "grounded": bool(cites), "citations": cites}

    return events


async def count_words(text):
    return len(text.split())


def make_ctx(conn, script, retrieval_only=True):
    return EvalContext(conn=conn, events=fake_events(script), retrieval_only=retrieval_only, model="fake-model",
                       count_tokens=count_words, peak_rss=lambda: 3400.5)


def test_load_questions_validates_shape(tmp_path):
    qs = load_questions(FIXTURE)
    assert [q.id for q in qs] == ["fx01", "fx02", "fx03"]
    assert qs[0].expected == [Expected(WIKI, "Myocardial_infarction"), Expected("card:heart-attack", "")]
    assert qs[2].kind == "refuse" and qs[2].expected == []
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"id":"a","question":"q","kind":"answer","expected":[]}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="at least one expected"):
        load_questions(bad)
    bad.write_text('{"id":"a","question":"q","kind":"refuse","expected":[]}\n'
                   '{"id":"a","question":"q2","kind":"refuse","expected":[]}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate id"):
        load_questions(bad)
    bad.write_text('{"id":"b","question":"q","kind":"maybe","expected":[]}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="kind"):
        load_questions(bad)


def test_expected_url_and_matching(ai_db):
    assert expected_url(Expected(WIKI, "Myocardial_infarction"), ai_db) == f"/read/{WIKI}/Myocardial_infarction"
    assert expected_url(Expected("nwss", ""), ai_db) == "/doc/nwss"
    assert expected_url(Expected("nwss", "p12"), ai_db) == "/doc/nwss#page=12"
    assert expected_url(Expected("card:heart-attack"), ai_db) == "/medical/card/heart-attack"
    assert expected_url(Expected("page:water-disinfection"), ai_db) == "/p/water-disinfection"
    assert expected_url(Expected("module:water"), ai_db) == "/m/water"
    assert expected_url(Expected("playbook:grid-collapse"), ai_db) == "/s/grid-collapse"
    assert expected_url(Expected("not_in_library", "x"), ai_db) is None
    assert url_matches(f"/read/{NHS}/www.nhs.uk/medicines/paracetamol-for-adults/how-and-when-to-take-paracetamol-for-adults/",
                       f"/read/{NHS}/www.nhs.uk/medicines/paracetamol-for-adults/")
    assert url_matches("/doc/nwss#page=12", "/doc/nwss")
    assert not url_matches("/doc/nwss#page=12", "/doc/nwss#page=13")
    assert url_matches("/read/ifixit_en_all_2025-12/Guide/How%2Bto%2BSharpen%2BKnives/6098",
                       "/read/ifixit_en_all_2025-12/Guide/How+to+Sharpen+Knives/6098")
    assert not url_matches("/read/x/Water_purification", "/read/x/Water")
    assert url_matches("/read/prepare_uk/prepare.campaign.gov.uk/get-prepared-for-emergencies/", "/read/prepare_uk")


def test_is_applicable_uses_availability_and_fts_docs(ai_db):
    assert is_applicable(Question("a", "q", "answer", [Expected(WIKI, "X")]), ai_db)
    assert not is_applicable(Question("b", "q", "answer", [Expected("nhs_uk", "x")]), ai_db)               # available = 0
    assert not is_applicable(Question("c", "q", "answer", [Expected("ifixit_en_all_2025-12", "x")]), ai_db)
    assert is_applicable(Question("d", "q", "health", [Expected("card:heart-attack")]), ai_db)
    assert not is_applicable(Question("e", "q", "health", [Expected("card:not-written-yet")]), ai_db)
    assert is_applicable(Question("f", "q", "answer", [Expected("nhs_uk", "x"), Expected("card:heart-attack")]), ai_db)
    assert is_applicable(Question("g", "q", "refuse", []), ai_db)


def test_is_applicable_includes_indexed_sections_without_matching_other_pages(ai_db):
    ai_db.execute("INSERT INTO fts_docs (title, body, url) VALUES (?, ?, ?)",
                  ("Water", "Safe drinking water", "/m/water#what-to-do"))
    assert is_applicable(Question("section", "q", "answer", [Expected("module:water")]), ai_db)
    assert not is_applicable(Question("prefix", "q", "answer", [Expected("module:wat")]), ai_db)


def test_dated_archive_targets_resolve_to_installed_canonical_item(ai_db):
    ai_db.execute("UPDATE library_items SET resolved_name=? WHERE id=?", ("wikipedia-previous-name", WIKI))
    target = Expected("wikipedia-previous-name", "Water")
    assert is_applicable(Question("alias", "q", "answer", [target]), ai_db)
    assert expected_url(target, ai_db) == f"/read/{WIKI}/Water"


@pytest.mark.anyio
async def test_run_questions_scores_hits_verbatim_and_refusals(ai_db):
    rows = await run_questions(load_questions(FIXTURE), make_ctx(ai_db, SCRIPT))
    by_id = {r["id"]: r for r in rows}
    assert by_id["fx01"]["applicable"] is True and by_id["fx01"]["hit"] is True
    assert by_id["fx01"]["passages"] == [{"n": 1, "title": "Myocardial infarction", "url": f"/read/{WIKI}/Myocardial_infarction"}]
    assert by_id["fx02"]["hit"] is True and by_id["fx02"]["verbatim_hit"] is True
    assert by_id["fx03"]["refused"] is True and by_id["fx03"]["hit"] is None
    summary = summarise(rows, retrieval_only=True)
    assert summary["retrieval_at_3"] == 1.0 and summary["verbatim_rate"] == 1.0 and summary["refusal_rate"] == 1.0
    assert summary["grounded_rate"] is None and summary["applicable"] == 3 and summary["skipped"] == []
    assert check_gates(summary, None, retrieval_only=True) == []


@pytest.mark.anyio
async def test_full_mode_records_timings_grounding_and_rss(ai_db):
    rows = await run_questions(load_questions(FIXTURE), make_ctx(ai_db, SCRIPT, retrieval_only=False))
    by_id = {r["id"]: r for r in rows}
    assert by_id["fx01"]["answer"] == "Chest pain and breathlessness [1]." and by_id["fx01"]["grounded"] is True
    assert by_id["fx01"]["ttft_s"] is not None and by_id["fx01"]["tok_s"] > 0 and by_id["fx01"]["peak_rss_mb"] == 3400.5
    assert by_id["fx03"]["refused"] is True and by_id["fx03"]["answer"] == REFUSAL_TEXT
    summary = summarise(rows, retrieval_only=False)
    assert summary["grounded_rate"] == 1.0 and summary["median_ttft_s"] is not None and summary["peak_rss_mb"] == 3400.5


@pytest.mark.anyio
async def test_misses_and_unexpected_answers_count_against_the_gates(ai_db):
    script = dict(SCRIPT)
    script["what are the symptoms of a heart attack"] = (None, [STROKE], "Think FAST [1].")
    script["what is the weather forecast for tomorrow"] = (None, [MI], "It will rain tomorrow [1].")
    rows = await run_questions(load_questions(FIXTURE), make_ctx(ai_db, script, retrieval_only=False))
    summary = summarise(rows, retrieval_only=False)
    assert summary["retrieval_at_3"] == 0.5 and summary["refusal_rate"] == 0.0
    failures = check_gates(summary, None, retrieval_only=False)
    assert any(f.startswith("retrieval_at_3 0.50") for f in failures)
    assert any(f.startswith("refusal_rate 0.00") for f in failures)


@pytest.mark.anyio
async def test_an_exception_in_one_question_does_not_abort_the_run(ai_db):
    script = dict(SCRIPT)

    async def boom(question):
        if question == "heart attack":
            raise RuntimeError("kiwix down")
        async for ev_ in fake_events(script)(question):
            yield ev_

    ctx = EvalContext(conn=ai_db, events=boom, retrieval_only=True, model="fake", count_tokens=count_words, peak_rss=lambda: None)
    rows = await run_questions(load_questions(FIXTURE), ctx)
    assert rows[1]["error"] == "exception: kiwix down" and rows[1]["hit"] is False
    assert summarise(rows, retrieval_only=True)["errors"] == 1


def test_regression_gate_against_previous_run():
    summary = {"retrieval_at_3": 0.85, "verbatim_rate": 0.95, "refusal_rate": 0.95, "grounded_rate": 0.70}
    previous = {"retrieval_at_3": 0.86, "verbatim_rate": 1.0, "grounded_rate": 0.80}
    assert check_gates(summary, previous, retrieval_only=False) == [
        "grounded_rate 0.70 is more than 0.05 below the previous run (0.80)"]
    assert check_gates(summary, {"retrieval_at_3": 0.95}, retrieval_only=True) == [
        "retrieval_at_3 0.85 is more than 0.05 below the previous run (0.95)"]
    assert check_gates({"retrieval_at_3": None, "verbatim_rate": None, "refusal_rate": None}, None, True) == []


def test_skipped_questions_do_not_count():
    blank = {"verbatim_hit": None, "refused": None, "grounded": None, "error": None, "ttft_s": None, "tok_s": None, "peak_rss_mb": None}
    rows = [{"id": "s", "kind": "answer", "applicable": False, "hit": False, **blank},
            {"id": "h", "kind": "answer", "applicable": True, "hit": True, **blank}]
    summary = summarise(rows, retrieval_only=True)
    assert summary["retrieval_at_3"] == 1.0 and summary["skipped"] == ["s"] and summary["applicable"] == 1


def test_run_path_previous_summary_and_write_run(tmp_path):
    runs = tmp_path / "runs"
    p1 = run_path(runs, "retrieval-only", None)
    assert p1.parent == runs and p1.name.endswith("-retrieval-only.jsonl")
    write_run(p1, [{"id": "a"}], {"retrieval_at_3": 0.9}, {"mode": "retrieval-only"})
    p2 = run_path(runs, "retrieval-only", None)
    assert p2 != p1 and p2.name.endswith("-retrieval-only-2.jsonl")
    assert previous_summary(runs, "retrieval-only", p2) == {"retrieval_at_3": 0.9}
    assert previous_summary(runs, "gemma-4-E2B-it-Q4_K_M", p2) is None
    assert run_path(runs, "x", str(tmp_path / "custom.jsonl")) == tmp_path / "custom.jsonl"
    lines = p1.read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[0]) == {"id": "a"} and json.loads(lines[1]) == {"summary": {"retrieval_at_3": 0.9}, "mode": "retrieval-only"}


def test_run_cli_retrieval_only_with_the_fixture(ai_db, ai_settings, tmp_path, monkeypatch, capsys):
    async def fake_build_context(settings, retrieval_only):
        assert retrieval_only is True
        return make_ctx(ai_db, SCRIPT)

    monkeypatch.setattr(ev, "build_context", fake_build_context)
    out = tmp_path / "run.jsonl"
    assert run_cli(["--retrieval-only", "--questions", str(FIXTURE), "--out", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "retrieval@3    1.00" in printed and "GATES: PASS" in printed and str(out) in printed
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4 and json.loads(lines[-1])["mode"] == "retrieval-only"


def test_questions_file_is_well_formed_and_sized():
    qs = load_questions(ev.DEFAULT_QUESTIONS)
    kinds = {k: sum(1 for q in qs if q.kind == k) for k in ("answer", "refuse", "health")}
    assert kinds["answer"] >= 45 and kinds["refuse"] >= 10 and kinds["health"] >= 10
    for q in qs:
        assert q.question == q.question.strip() and 3 <= len(q.question) <= 400
        for e in q.expected:
            prefix, _, slug = e.item.partition(":")
            if prefix in ev.AUTHORED_URLS:
                assert slug and e.path == "", q.id
            else:
                assert " " not in e.item, q.id
    dev_targets = {"wikipedia_en_100_mini_2026-01", "nhs.uk_en_medicines_2025-12"}
    assert sum(1 for q in qs if any(e.item in dev_targets for e in q.expected)) >= 12    # runnable in CI and dev
