# api/tests/test_ai_prompt.py
import httpx
import pytest

from sos.ai import (HISTORY_MAX_MESSAGES, MEDICAL_SYSTEM_LINE, PASSAGE_TOKENS, PROMPT_CAP, QUESTION_TOKENS,
                    SYSTEM_PROMPT, SYSTEM_TOKENS, LlamaClient, LlamaError, Passage, build_messages,
                    format_passages, trim_to_tokens)


def words(n: int, prefix: str = "w") -> str:
    return " ".join(f"{prefix}{i}" for i in range(n))


@pytest.fixture
def llama(fake_llama):
    return LlamaClient("http://llama.test")


# --- LlamaClient -------------------------------------------------------------

@pytest.mark.anyio
async def test_stream_chat_parses_sse_and_sends_the_spec_fields(llama, fake_llama):
    fake_llama.reply = "Hello there [1]."
    parts = [p async for p in llama.stream_chat([{"role": "user", "content": "hi"}])]
    assert "".join(parts) == "Hello there [1]." and len(parts) >= 3
    body = fake_llama.requests[0]
    assert body["stream"] is True and body["cache_prompt"] is True
    assert body["max_tokens"] == 400 and body["temperature"] == 0.2
    # Thinking is disabled server-side by --reasoning off (sos-llama.service), not per-request:
    # chat_template_kwargs/enable_thinking is deprecated in llama.cpp and unreliable on Gemma 4.
    assert "chat_template_kwargs" not in body
    assert body["messages"] == [{"role": "user", "content": "hi"}]


@pytest.mark.anyio
async def test_stream_chat_ignores_null_deltas_comments_and_stops_at_done(mocks):
    mocks.post("http://llama.test/v1/chat/completions").mock(return_value=httpx.Response(200, content=(
        b'data: {"choices":[{"delta":{"role":"assistant","content":null}}]}\n\n'
        b': keep-alive\n\n'
        b'data: {"choices":[{"delta":{"content":"a"}}]}\n\n'
        b'data: {"choices":[{"delta":{}}]}\n\n'
        b'data: [DONE]\n\n'
        b'data: {"choices":[{"delta":{"content":"never"}}]}\n\n')))
    assert [p async for p in LlamaClient("http://llama.test").stream_chat([])] == ["a"]


@pytest.mark.anyio
async def test_stream_chat_raises_llama_error_on_transport_status_or_error_chunk(mocks):
    route = mocks.post("http://llama.test/v1/chat/completions")
    route.mock(side_effect=httpx.ConnectError("down"))
    with pytest.raises(LlamaError, match="unreachable"):
        async for _ in LlamaClient("http://llama.test").stream_chat([]):
            pass
    route.mock(return_value=httpx.Response(503, json={"error": {"message": "Loading model"}}))
    with pytest.raises(LlamaError, match="503"):
        async for _ in LlamaClient("http://llama.test").stream_chat([]):
            pass
    route.mock(return_value=httpx.Response(200, content=b'data: {"error":{"message":"context full"}}\n\n'))
    with pytest.raises(LlamaError, match="context full"):
        async for _ in LlamaClient("http://llama.test").stream_chat([]):
            pass


@pytest.mark.anyio
async def test_tokenize_health_and_model_name(llama, fake_llama):
    assert await llama.tokenize("one two three") == 3
    assert await llama.health() is True
    assert await llama.model_name() == "gemma-4-E2B-it-Q4_K_M"
    fake_llama.healthy = False
    assert await llama.health() is False


@pytest.mark.anyio
async def test_tokenize_and_model_name_fall_back_when_llama_is_down(mocks):
    mocks.post("http://llama.test/tokenize").mock(side_effect=httpx.ConnectError("down"))
    mocks.get("http://llama.test/props").mock(side_effect=httpx.ConnectError("down"))
    client = LlamaClient("http://llama.test")
    assert await client.tokenize("x" * 40) == 10
    assert await client.tokenize("") == 1
    assert await client.model_name() is None


# --- prompt and budget -------------------------------------------------------

def test_system_prompt_fits_the_budget_under_both_counters_and_uses_uk_terms():
    text = SYSTEM_PROMPT + MEDICAL_SYSTEM_LINE
    assert len(text.split()) <= SYSTEM_TOKENS and len(text) // 4 <= SYSTEM_TOKENS
    for term in ("999", "111", "105", "paracetamol", "British English", "The library doesn't cover this", "[1]"):
        assert term in SYSTEM_PROMPT, term
    assert "acetaminophen" in SYSTEM_PROMPT        # named only as the term to avoid


@pytest.mark.anyio
async def test_trim_to_tokens_cuts_words_until_it_fits(llama):
    text, n = await trim_to_tokens(words(500), 400, llama.tokenize)
    assert n <= 400 and len(text.split()) == n
    assert await trim_to_tokens("short", 400, llama.tokenize) == ("short", 1)


def test_format_passages_numbers_titles_and_sources():
    out = format_passages([Passage(1, "Water", "/m/water", "playbooks", "Boil it."),
                           Passage(2, "Paracetamol", "/read/nhs/p", "nhs_medicines", "Two tablets.")])
    assert out == "Passages from the library:\n\n[1] Water (playbooks)\nBoil it.\n\n[2] Paracetamol (nhs_medicines)\nTwo tablets."


@pytest.mark.anyio
async def test_build_messages_applies_every_budget_line(llama):
    passages = [Passage(n=i + 1, title=f"T{i}", url=f"/m/t{i}", source="playbooks", text=words(500, f"p{i}_"))
                for i in range(3)]
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": words(300, f"h{i}_")} for i in range(10)]
    question = words(200, "q")
    messages, budget = await build_messages(question, passages, history, llama)
    assert messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert messages[-1]["role"] == "user"
    assert len(budget.passages) == 3 and all(n <= PASSAGE_TOKENS for n in budget.passages)
    assert budget.system <= SYSTEM_TOKENS and budget.question <= QUESTION_TOKENS
    assert budget.total <= PROMPT_CAP
    kept = messages[1:-1]
    assert kept and all(m["content"].startswith(("h8_", "h9_")) for m in kept)               # newest survive
    assert [m["content"][:2] for m in kept] == sorted(m["content"][:2] for m in kept)          # chronological
    assert budget.dropped_history == 10 - len(kept)
    user = messages[-1]["content"]
    assert user.startswith("Passages from the library:\n\n[1] T0 (playbooks)\np0_0 ")
    assert "\n\n[3] T2 (playbooks)\n" in user and "\n\nQuestion: q0 q1 " in user
    assert len(user.split("Question: ", 1)[1].split()) == budget.question


@pytest.mark.anyio
async def test_build_messages_medical_flag_history_filter_and_cap(llama):
    passages = [Passage(1, "T", "/m/t", "playbooks", "Boil water.")]
    history = [{"role": "system", "content": "ignored"}, {"role": "user", "content": "   "}]
    history += [{"role": "user", "content": f"turn {i}"} for i in range(12)]
    messages, budget = await build_messages("q", passages, history, llama, medical=True)
    assert messages[0]["content"] == SYSTEM_PROMPT + MEDICAL_SYSTEM_LINE
    kept = [m["content"] for m in messages[1:-1]]
    assert kept == [f"turn {i}" for i in range(12 - HISTORY_MAX_MESSAGES, 12)]
    assert budget.dropped_history == len(history) - HISTORY_MAX_MESSAGES


@pytest.mark.anyio
async def test_build_messages_uses_the_character_fallback_when_tokenize_is_down(mocks):
    mocks.post("http://llama.test/tokenize").mock(side_effect=httpx.ConnectError("down"))
    llama = LlamaClient("http://llama.test")
    passages = [Passage(n=i + 1, title=f"T{i}", url=f"/m/t{i}", source="playbooks", text="word " * 3000) for i in range(3)]
    messages, budget = await build_messages("how", passages, [], llama)
    assert budget.total <= PROMPT_CAP and all(n <= PASSAGE_TOKENS for n in budget.passages)
    assert len(messages) == 2
