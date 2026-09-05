import os
from pathlib import Path

from sos.config import Settings


def test_defaults_when_no_env(monkeypatch):
    for key in list(os.environ):
        if key.startswith("SOS_"):
            monkeypatch.delenv(key)
    s = Settings()
    assert s.core == Path("/srv/sos/core")
    assert s.ext == Path("/srv/sos/extended")
    assert s.state == Path("/srv/sos/state")
    assert s.web == Path("/srv/sos/web")
    assert s.manifests == Path("/srv/sos/state/manifest")
    assert s.playbooks == Path("/srv/sos/state/playbooks")
    assert s.kiwix_url == "http://127.0.0.1:8090/kiwix"
    assert s.llama_url == "http://127.0.0.1:8081"
    assert s.model == "gemma-4-E2B-it-Q4_K_M.gguf"
    assert s.dev is False
    assert s.port == 8000
    assert s.db_path == Path("/srv/sos/state/sos.db")
    assert s.library_xml == Path("/srv/sos/state/library.xml")
    assert s.config_dir == Path("/srv/sos/state/config")


def test_env_overrides(env, fixtures_dir):
    assert env.dev is True
    assert env.core.name == "core"
    assert env.manifests == fixtures_dir / "manifest"
    assert env.playbooks == fixtures_dir / "playbooks"
    assert env.tier_root("core") == env.core
    assert env.tier_root("extended") == env.ext


def test_version():
    import sos

    assert sos.__version__ == "0.1.0"
