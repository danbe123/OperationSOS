# api/tests/test_ai_router.py
import asyncio
import json
import re

import httpx
import pytest
from fastapi import FastAPI

import sos.ai as ai
import sos.routers.ai as ai_router
from sos.ai import MEDICAL_DISCLAIMER, REFUSAL_TEXT, LlamaClient, Passage, Verbatim
from sos.ai_runtime import AiRuntime
from sos.kiwix import KiwixClient
from sos.routers.ai import router
from sos.routers import require_pin

STOP = {"how", "do", "i", "the", "a", "to", "what", "is", "my", "can", "of", "for", "in", "and", "should", "if", "make"}
WATER = Passage(1, "Water disinfection", "/p/water-disinfection", "playbooks", "Boil water at a rolling boil for one minute.")
BLEACH = Passage(2, "Water", "/m/water", "playbooks", "Two drops of thin bleach per litre, wait 30 minutes.")
CARD = Passage(1, "Heart attack", "/medical/card/heart-attack", "playbooks", "Call 999 now.")
VERBATIM = Verbatim("Heart attack", "/medical/card/heart-attack",
                    ["Call 999 now. Sit the person down.", "Give one 300 mg aspirin to chew."], None)


@pytest.fixture
def runtime(ai_settings, fake_llama):
    rt = AiRuntime(settings=ai_settings, llama=LlamaClient(ai_settings.llama_url))
    rt.state, rt.model = "ready", "gemma-4-E2B-it-Q4_K_M"
    return rt


@pytest.fixture
def app(ai_settings, ai_db, runtime):
    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.state.settings = ai_settings
    app.state.conn = ai_db
    app.state.kiwix = KiwixClient(ai_settings.kiwix_url)
    app.state.ai_runtime = runtime
    app.dependency_overrides[require_pin] = lambda: None
    return app


@pytest.fixture
def client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.fixture
def fakes(monkeypatch):
    """Deterministic tokeniser, retrieval and health router; tests mutate the returned dict."""
    state = {"passages": [WATER, BLEACH], "verbatim": None}
    monkeypatch.setattr(ai, "content_terms",
                        lambda q: [t for t in re.findall(r"[a-z0-9]+", q.lower()) if t not in STOP])

    async def fake_retrieve(tokens, conn, kiwix, settings):
        return list(state["passages"])

    async def fake_verbatim(query, conn, kiwix):
        return state["verbatim"]

    monkeypatch.setattr(ai, "retrieve", fake_retrieve)
    monkeypatch.setattr(ai, "verbatim_block", fake_verbatim)
    monkeypatch.setattr(ai_router, "PING_INTERVAL_S", 0.05)
    return state


async def ask(client, question="how do I make water safe to drink", history=None):
    """POST /api/ai/ask; parse the SSE body into [(event, data)], keeping ': ping' comments as ('ping', None)."""
    events, event = [], None
    async with client.stream("POST", "/api/ai/ask", json={"question": question, "history": history or []}) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        assert r.headers["cache-control"] == "no-cache"
        async for line in r.aiter_lines():
            if line.startswith(": ping"):
                events.append(("ping", None))
            elif line.startswith("event: "):
                event = line[7:]
            elif line.startswith("data: "):
                events.append((event, json.loads(line[6:])))
    return events


def names(events):
    return [e for e, _ in events if e != "ping"]


@pytest.mark.anyio
async def test_ask_streams_retrieving_tokens_and_done_with_citations(client, fakes, fake_llama):
    fake_llama.reply = "Boil it for one minute [1]. Or use bleach [2]. Never drink it raw [5]."
    async with client:
        events = await ask(client)
    seq = names(events)
    assert seq[0] == "retrieving" and seq[-1] == "done"
    assert all(n == "token" for n in seq[1:-1]) and seq.count("token") >= 5
    retrieving = events[0][1]
    assert retrieving["query"] == "water safe drink"
    assert retrieving["passages"][0] == {"n": 1, "title": "Water disinfection", "url": "/p/water-disinfection",
                                         "source": "playbooks", "text": "Boil water at a rolling boil for one minute."}
    assert [p["n"] for p in retrieving["passages"]] == [1, 2]
    done = events[-1][1]
    assert done["answer"] == "Boil it for one minute [1]. Or use bleach [2]. Never drink it raw ."
    assert done["grounded"] is True
    assert done["citations"] == [
        {"n": 1, "title": "Water disinfection", "url": "/p/water-disinfection", "source": "playbooks"},
        {"n": 2, "title": "Water", "url": "/m/water", "source": "playbooks"}]
    streamed = "".join(d["text"] for e, d in events if e == "token")
    assert streamed.strip() == done["answer"]
    body = fake_llama.requests[0]
    assert body["messages"][0]["role"] == "system"
    assert "Question: how do I make water safe to drink" in body["messages"][-1]["content"]
    assert body["max_tokens"] == 400 and body["cache_prompt"] is True and body["temperature"] == 0.2


@pytest.mark.anyio
async def test_ask_emits_verbatim_first_and_appends_the_medical_disclaimer(client, fakes, fake_llama):
    fakes["verbatim"], fakes["passages"] = VERBATIM, [CARD]
    fake_llama.reply = "Call 999 and keep them calm [1]."
    async with client:
        events = await ask(client, "what should I do for a heart attack")
    assert names(events)[:2] == ["verbatim", "retrieving"]
    assert events[0][1] == {"title": "Heart attack", "url": "/medical/card/heart-attack",
                            "paragraphs": ["Call 999 now. Sit the person down.", "Give one 300 mg aspirin to chew."],
                            "as_at": None}
    assert events[-2] == ("token", {"text": "\n\n" + MEDICAL_DISCLAIMER})
    done = events[-1][1]
    assert done["answer"] == "Call 999 and keep them calm [1].\n\n" + MEDICAL_DISCLAIMER
    assert done["grounded"] is True and [c["n"] for c in done["citations"]] == [1]
    messages = fake_llama.requests[0]["messages"]
    assert "Sit the person down" not in json.dumps(messages)          # the verbatim excerpt is UI-only
    assert "The question is medical" in messages[0]["content"]


@pytest.mark.anyio
async def test_ask_refuses_without_calling_the_model_when_nothing_is_retrieved(client, fakes, fake_llama):
    fakes["passages"] = []
    async with client:
        events = await ask(client, "what is the weather forecast for tomorrow")
    assert names(events) == ["retrieving", "done"]
    assert events[0][1]["passages"] == []
    assert events[1][1] == {"answer": REFUSAL_TEXT, "grounded": False, "citations": []}
    assert fake_llama.chat.call_count == 0


@pytest.mark.anyio
async def test_ask_marks_ungrounded_when_no_citation_survives(client, fakes, fake_llama):
    fake_llama.reply = "Boil it [7]."
    async with client:
        events = await ask(client)
    assert events[-1][1] == {"answer": "Boil it .", "grounded": False, "citations": []}


@pytest.mark.anyio
async def test_ask_holds_back_a_citation_split_across_chunks(client, fakes, fake_llama):
    fake_llama.chunks = ["Boil", " it [", "1", "]", " then [", "9", "]", " done"]
    async with client:
        events = await ask(client)
    tokens = [d["text"] for e, d in events if e == "token"]
    assert "".join(tokens) == "Boil it [1] then  done"
    assert all("[9" not in t and t != "[" for t in tokens)          # never a dangling bracket on the wire


@pytest.mark.anyio
async def test_ask_unavailable_when_ai_is_off(client, fakes, runtime, fake_llama):
    runtime.state = "off"
    async with client:
        events = await ask(client)
    assert events == [("error", {"code": "unavailable", "message": "The assistant is off. Turn it on in System."})]
    assert fake_llama.chat.call_count == 0


@pytest.mark.anyio
async def test_second_question_while_busy_gets_busy_error_at_once(client, fakes, fake_llama, runtime):
    fake_llama.delay = 0.05
    async with client:
        first = asyncio.create_task(ask(client))
        await asyncio.sleep(0.1)
        assert runtime.snapshot()["state"] == "busy"
        second = await ask(client, "another question")
        events = await first
    assert second[0][0] == "error" and second[0][1]["code"] == "busy"
    assert 10 <= second[0][1]["retry_after"] <= 120 and "message" in second[0][1]
    assert names(events)[-1] == "done"
    assert runtime.snapshot()["state"] == "ready" and not runtime.lock.locked()


@pytest.mark.anyio
async def test_ping_comments_are_sent_while_waiting(client, fakes, fake_llama):
    fake_llama.delay = 0.12
    async with client:
        events = await ask(client)
    assert ("ping", None) in events and names(events)[-1] == "done"


@pytest.mark.anyio
async def test_timeout_emits_error_and_releases_the_lock(client, fakes, fake_llama, runtime, monkeypatch):
    monkeypatch.setattr(ai_router, "TOTAL_TIMEOUT_S", 0.2)
    fake_llama.delay = 0.5
    async with client:
        events = await ask(client)
    assert names(events)[0] == "retrieving" and events[-1][0] == "error"
    assert events[-1][1]["code"] == "timeout" and "done" not in names(events)
    assert not runtime.lock.locked() and runtime.snapshot()["state"] == "ready"


@pytest.mark.anyio
async def test_llama_failure_mid_stream_is_reported_as_unavailable(client, fakes, fake_llama):
    fake_llama.chat.mock(side_effect=httpx.ConnectError("connection refused"))
    async with client:
        events = await ask(client)
    assert names(events) == ["retrieving", "error"]
    assert events[-1][1]["code"] == "unavailable" and "unreachable" in events[-1][1]["message"]


@pytest.mark.anyio
async def test_unexpected_exception_is_an_internal_error(client, fakes, monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(ai, "build_messages", boom)
    async with client:
        events = await ask(client)
    assert events[-1] == ("error", {"code": "internal", "message": "The assistant hit an internal error."})


@pytest.mark.anyio
async def test_question_validation_is_422(client, fakes):
    async with client:
        assert (await client.post("/api/ai/ask", json={"question": "x" * 401, "history": []})).status_code == 422
        assert (await client.post("/api/ai/ask", json={"question": "", "history": []})).status_code == 422
        assert (await client.post("/api/ai/ask", json={"question": "ok", "history": [{"role": "tool", "content": "x"}]})).status_code == 422
        assert (await client.post("/api/ai/ask", json={"question": "x" * 400})).status_code == 200


@pytest.mark.anyio
async def test_history_is_passed_to_the_prompt_in_order(client, fakes, fake_llama):
    history = [{"role": "user", "content": "earlier question"}, {"role": "assistant", "content": "earlier answer [1]."}]
    async with client:
        await ask(client, history=history)
    assert fake_llama.requests[0]["messages"][1:3] == history


@pytest.mark.anyio
async def test_status_enable_and_disable_endpoints(client, runtime, fake_llama, monkeypatch):
    import sos.ai_runtime as rt_mod

    async def noop(rt):
        pass

    monkeypatch.setattr(rt_mod, "_start_process", noop)
    monkeypatch.setattr(rt_mod, "_stop_process", noop)
    monkeypatch.setattr(rt_mod, "HEALTH_POLL_S", 0.01)
    runtime.state, runtime.model = "off", None
    async with client:
        assert (await client.get("/api/ai/status")).json() == {"state": "off", "model": None, "message": None}
        r = await client.post("/api/ai/enable")
        assert r.status_code == 200 and r.json() == {"state": "starting"}
        await runtime.starter
        assert (await client.get("/api/ai/status")).json() == {"state": "ready", "model": "gemma-4-E2B-it-Q4_K_M", "message": None}
        assert (await client.post("/api/ai/disable")).json() == {"state": "off"}
        assert (await client.get("/api/ai/status")).json()["state"] == "off"


def test_enable_and_disable_are_pin_gated():
    gated = {r.path for r in router.routes if any(d.call is require_pin for d in r.dependant.dependencies)}
    assert gated == {"/ai/enable", "/ai/disable"}
