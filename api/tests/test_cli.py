import shutil
from pathlib import Path

import httpx
import pytest
import respx

from sos import cli, db, system

FX = Path(__file__).parent / "fixtures"
REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def tree(tmp_path, monkeypatch):
    root = tmp_path / "playbooks"
    shutil.copytree(FX / "playbooks", root)
    shutil.copy(REPO / "playbooks" / "schema.json", root / "schema.json")
    monkeypatch.setenv("SOS_PLAYBOOKS_DIR", str(root))
    from sos.config import get_settings

    get_settings.cache_clear()
    return root


def test_validate_playbooks_ok(env, tree, capsys):
    assert cli.main(["validate-playbooks"]) == 0
    assert capsys.readouterr().out.strip().endswith("OK 4 documents")


def test_validate_playbooks_reports_errors(env, tree, capsys):
    path = tree / "scenarios" / "grid-collapse.md"
    path.write_text(path.read_text(encoding="utf-8").replace("overlays: [health, water]", "overlays: [dragons]"), encoding="utf-8")
    assert cli.main(["validate-playbooks"]) == 1
    out = capsys.readouterr().out
    assert "overlay 'dragons'" in out and "FAILED 1 error" in out


def test_validate_playbooks_all_scenarios_flag(env, tree, capsys):
    assert cli.main(["validate-playbooks", "--all-scenarios"]) == 1
    assert "scenarios/nuclear-war.md: missing" in capsys.readouterr().out


@respx.mock
def test_validate_playbooks_deep(respx_mock, env, tree, capsys):
    respx_mock.get("http://kiwix.test/kiwix/raw/wikipedia_en_100_mini_2026-01/content/Precipitation").mock(return_value=httpx.Response(404))
    assert cli.main(["validate-playbooks", "--deep"]) == 1
    out = capsys.readouterr().out
    assert "returned non-200" in out and "doc 'sos-test-pdf' file missing" in out


def test_pin_set_and_reset(env):
    assert cli.main(["pin", "set", "2468"]) == 0
    conn = db.connect(env.db_path)
    assert system.verify_pin(conn, "2468") is True
    assert cli.main(["pin", "set", "12"]) == 1
    assert cli.main(["pin", "reset"]) == 0
    assert system.pin_required(db.connect(env.db_path)) is False


def test_stubs_exit_2(env, capsys):
    assert cli.main(["build-maps", "--fixture"]) == 2
    assert "plan 04" in capsys.readouterr().err
    assert cli.main(["eval", "--retrieval-only"]) == 2
    assert "plan 05" in capsys.readouterr().err


@respx.mock
def test_status_prints_fields(respx_mock, env, capsys):
    respx_mock.get("http://127.0.0.1:8000/api/status").mock(return_value=httpx.Response(200, json={"version": "0.1.0", "dev": True, "mem": {"total_mb": 1}}))
    assert cli.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "version: 0.1.0" in out and "mem: {" in out
    respx_mock.get("http://127.0.0.1:8000/api/status").mock(side_effect=httpx.ConnectError("down"))
    assert cli.main(["status"]) == 1


def test_sync_dry_run_on_fixture_manifest(env, capsys):
    assert cli.main(["sync", "--tier", "core", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "GET  wikipedia_en_100_mini_2026-01: https://download.kiwix.org/zim/wikipedia/wikipedia_en_100_mini_2026-01.zim" in out
    assert "BUILD sos-test-noindex: run `sos zimwriterfs`" in out


@respx.mock
def test_storage_event_add_and_remove(respx_mock, env, capsys):
    route = respx_mock.post("http://127.0.0.1:8000/api/system/rescan").mock(return_value=httpx.Response(200, json={"items": 13, "available": 2}))
    assert cli.main(["storage-event", "add"]) == 0
    assert route.call_count == 1
    assert cli.main(["storage-event", "remove"]) == 0
    assert route.call_count == 2 and env.library_xml.exists()
    respx_mock.post("http://127.0.0.1:8000/api/system/rescan").mock(side_effect=httpx.ConnectError("down"))
    assert cli.main(["storage-event", "add"]) == 1
    assert cli.main(["storage-event", "remove"]) == 0


def test_index_command(env, capsys):
    assert cli.main(["index"]) == 0
    out = capsys.readouterr().out
    assert "rescan:" in out and "content rows" in out
    conn = db.connect(env.db_path)
    assert conn.execute("SELECT count(*) FROM fts_docs").fetchone()[0] > 0
