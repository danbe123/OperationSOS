import os
import re
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
REPO = Path(__file__).resolve().parents[2]


def real_tree_errors(errors) -> list[str]:
    """The validator's errors for the repository tree: the warnings aside."""
    return [e for e in errors if not e.startswith("warning: ")]


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def repo_root() -> Path:
    return REPO


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Settings bound to a throwaway tree. The extended root is NOT created,
    so the default state is 'external drive not connected'."""
    core = tmp_path / "core"
    state = tmp_path / "state"
    for d in (core / "zim", core / "maps", core / "docs", core / "models", state / "config"):
        d.mkdir(parents=True)
    monkeypatch.setenv("SOS_CORE", str(core))
    monkeypatch.setenv("SOS_EXT", str(tmp_path / "extended"))
    monkeypatch.setenv("SOS_STATE", str(state))
    monkeypatch.setenv("SOS_WEB", str(tmp_path / "web"))
    monkeypatch.setenv("SOS_MANIFEST_DIR", str(FIXTURES / "manifest"))
    monkeypatch.setenv("SOS_PLAYBOOKS_DIR", str(FIXTURES / "playbooks"))
    monkeypatch.setenv("SOS_KIWIX_URL", "http://kiwix.test/kiwix")
    monkeypatch.setenv("SOS_DEV", "1")
    from sos.config import get_settings

    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


@pytest.fixture
def app(env):
    from sos.main import create_app

    return create_app(env, background=False)


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app, client=("127.0.0.1", 50000)) as c:
        yield c


@pytest.fixture
def remote_client(app):
    from fastapi.testclient import TestClient

    with TestClient(app, client=("10.42.0.7", 50000)) as c:
        yield c

# --- appended by plan 05 (AI assistant) --------------------------------------
import asyncio
import json
import re

import httpx
import pytest
import respx

from sos.config import get_settings
from sos.db import connect, init_schema


@pytest.fixture
def anyio_backend():
    """Run @pytest.mark.anyio tests on asyncio only (trio is not installed)."""
    return "asyncio"


@pytest.fixture
def ai_settings(tmp_path, monkeypatch):
    state, core = tmp_path / "state", tmp_path / "core"
    (state / "config").mkdir(parents=True)
    (core / "models").mkdir(parents=True)
    for key, value in {
        "SOS_DEV": "1", "SOS_STATE": str(state), "SOS_CORE": str(core), "SOS_EXT": str(tmp_path / "ext"),
        "SOS_WEB": str(tmp_path / "web"), "SOS_KIWIX_URL": "http://kiwix.test/kiwix",
        "SOS_LLAMA_URL": "http://llama.test", "SOS_MODEL": "gemma-4-E2B-it-Q4_K_M.gguf",
    }.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


AI_LIBRARY_ROWS = [
    # id, title, kind, category, dest, as_at, search_weight, suggest, available, resolved_as_at
    ("wikipedia_en_100_mini_2026-01", "Wikipedia (mini)", "zim", "reference", "zim/wikipedia_en_100_mini_2026-01.zim", "2026-01", 1.0, 1, 1, None),
    ("nhs.uk_en_medicines_2025-12", "NHS Medicines A to Z", "zim", "medical", "zim/nhs.uk_en_medicines_2025-12.zim", "2025-12", 1.4, 1, 1, "2025-12-15"),
    ("nhs_uk", "NHS conditions and medicines", "zim", "medical", "zim/nhs_uk.zim", "2026-03", 1.4, 1, 0, None),
    ("nwss", "Nuclear War Survival Skills", "pdf", "survival", "docs/nwss.pdf", "1987", 1.0, 0, 1, None),
    ("ifixit_en_all_2025-12", "iFixit", "zim", "practical", "zim/ifixit_en_all_2025-12.zim", "2025-12", 1.0, 1, 0, None),
]

AI_FTS_ROWS = [
    # title, body, doc_id, kind, category, scenarios, page, url
    ("Heart attack",
     "Call 999 now. Sit the person down with their knees bent and keep them calm and still.\n\n"
     "Give one 300 mg aspirin to chew slowly if they are not allergic and can swallow.\n\n"
     "Be ready to start CPR if they stop breathing normally.",
     "card:heart-attack", "card", "playbooks", "", None, "/medical/card/heart-attack"),
    ("Severe bleeding",
     "Call 999. Press hard on the wound with a clean cloth and do not let go.\n\nIf blood soaks through, add more on top.",
     "card:severe-bleeding", "card", "playbooks", "", None, "/medical/card/severe-bleeding"),
    ("Hypothermia",
     "Move the person somewhere warm and dry. Remove wet clothing and wrap them in blankets.\n\nGive warm sweet drinks if they are awake.",
     "card:hypothermia", "card", "playbooks", "", None, "/medical/card/hypothermia"),
    ("Water disinfection",
     "Boil water at a rolling boil for one minute; at altitude boil for three minutes.\n\n"
     "Thin household bleach (4 to 6 per cent) can be used: two drops per litre of clear water, wait 30 minutes.",
     "page:water-disinfection", "page", "playbooks", "", None, "/p/water-disinfection"),
    ("Water",
     "Find water, make it safe, store it. Adults need at least two litres a day to drink.\n\n"
     "Rainwater from a clean roof is usually safe after boiling.",
     "module:water", "module", "playbooks", "", None, "/m/water"),
    ("Nuclear War Survival Skills p. 12",
     "Fallout shielding: about three feet of packed earth or two feet of concrete reduces gamma radiation "
     "to a small fraction. A trench shelter roofed with doors and covered with earth gives good protection from fallout.",
     "nwss#p12", "doc", "survival", "", 12, "/doc/nwss#page=12"),
]


@pytest.fixture
def ai_db(tmp_path):
    conn = connect(tmp_path / "ai-test.db")
    init_schema(conn)
    conn.executemany(
        "INSERT INTO library_items (id, title, kind, tier, category, scenarios_json, dest, size_bytes, as_at, licence, "
        "priority, reader_home, description, search_weight, suggest, overlay_json, available, local_path, fts, "
        "resolved_name, resolved_size, resolved_as_at) "
        "VALUES (?, ?, ?, 'core', ?, '[]', ?, 0, ?, NULL, 10, NULL, NULL, ?, ?, NULL, ?, NULL, 1, NULL, NULL, ?)",
        AI_LIBRARY_ROWS)
    conn.executemany(
        "INSERT INTO fts_docs (title, body, doc_id, kind, category, scenarios, page, url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        AI_FTS_ROWS)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def mocks():
    """One respx router for both fake servers; unmatched requests raise, unused routes are fine."""
    with respx.mock(assert_all_called=False) as router:
        yield router


@pytest.fixture
def kiwix_mock(mocks):
    """The same router; tests add /kiwix/raw and /kiwix/suggest routes under http://kiwix.test/kiwix."""
    return mocks


class FakeLlama:
    """A fake llama-server: /health, /props, /tokenize (one token per whitespace-separated word) and a
    scripted /v1/chat/completions SSE stream. Set .reply (or .chunks), .delay and .healthy before the request."""

    def __init__(self, router):
        self.router = router
        self.reply = "Boil it for one minute [1]."
        self.chunks: list[str] | None = None      # explicit chunking when a test needs it
        self.delay = 0.0                           # seconds between chunks
        self.healthy = True
        self.requests: list[dict] = []
        router.get("http://llama.test/health").mock(side_effect=self._health)
        router.get("http://llama.test/props").mock(
            return_value=httpx.Response(200, json={"model_path": "models/gemma-4-E2B-it-Q4_K_M.gguf"}))
        router.post("http://llama.test/tokenize").mock(side_effect=self._tokenize)
        self.chat = router.post("http://llama.test/v1/chat/completions").mock(side_effect=self._chat)

    def _health(self, request):
        if self.healthy:
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(503, json={"error": {"message": "Loading model"}})

    def _tokenize(self, request):
        text = json.loads(request.content)["content"]
        return httpx.Response(200, json={"tokens": list(range(len(text.split())))})

    def _chat(self, request):
        self.requests.append(json.loads(request.content))
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=self._sse())

    async def _sse(self):
        yield b'data: {"choices":[{"index":0,"delta":{"role":"assistant","content":null}}]}\n\n'
        for piece in (self.chunks if self.chunks is not None else re.findall(r"\S+\s*", self.reply)):
            if self.delay:
                await asyncio.sleep(self.delay)
            yield ("data: " + json.dumps({"choices": [{"index": 0, "delta": {"content": piece}}]}) + "\n\n").encode()
        yield b"data: [DONE]\n\n"


@pytest.fixture
def fake_llama(mocks):
    return FakeLlama(mocks)
