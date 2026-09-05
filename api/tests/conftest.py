import os
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
REPO = Path(__file__).resolve().parents[2]


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
