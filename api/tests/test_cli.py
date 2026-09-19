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
    shutil.copy(REPO / "playbooks" / "kits" / "schema.json", root / "kits" / "schema.json")
    monkeypatch.setenv("SOS_PLAYBOOKS_DIR", str(root))
    from sos.config import get_settings

    get_settings.cache_clear()
    return root


def test_validate_playbooks_ok(env, tree, capsys):
    assert cli.main(["validate-playbooks"]) == 0
    assert capsys.readouterr().out.strip().endswith("OK 6 documents")


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
    # --deep reaches the kits as well as the playbooks: the water kit cites this article in a why and
    # again in its sources, and both are fetched.
    water = respx_mock.get("http://kiwix.test/kiwix/raw/wikipedia_en_100_mini_2026-01/content/A/Water").mock(return_value=httpx.Response(200))
    assert cli.main(["validate-playbooks", "--deep"]) == 1
    out = capsys.readouterr().out
    assert "returned non-200" in out and "doc 'sos-test-pdf' file missing" in out
    assert water.called


def test_pin_set_and_reset(env):
    assert cli.main(["pin", "set", "2468"]) == 0
    conn = db.connect(env.db_path)
    assert system.verify_pin(conn, "2468") is True
    assert cli.main(["pin", "set", "12"]) == 1
    assert cli.main(["pin", "reset"]) == 0
    assert system.pin_required(db.connect(env.db_path)) is False


def test_eval_dispatches_to_runner(env, monkeypatch):
    from sos import evalrun
    calls = []
    monkeypatch.setattr(evalrun, "run_from_namespace", lambda args: calls.append(args) or 0)
    assert cli.main(["eval", "--retrieval-only"]) == 0
    assert calls[0].retrieval_only


def _spy_wikipedia_cli(monkeypatch) -> list:
    from sos import embeddings
    calls = []
    monkeypatch.setattr(embeddings, "build_wikipedia_cli",
                        lambda settings, cuda=False, limit=None, workers=1, servers=1, resume=True:
                        calls.append((cuda, limit, workers, servers, resume)) or 0)
    return calls


def test_build_embeddings_wikipedia_dispatches_cuda_limit_workers_and_servers(env, monkeypatch):
    calls = _spy_wikipedia_cli(monkeypatch)
    assert cli.main(["build-embeddings-wikipedia", "--cuda", "--limit", "5", "--workers", "3",
                     "--servers", "2"]) == 0
    assert calls == [(True, 5, 3, 2, True)]


def test_build_embeddings_wikipedia_can_be_told_to_start_the_build_afresh(env, monkeypatch):
    """The build resumes from its checkpoint by default, which is what an interrupted multi-hour run
    wants; --no-resume is how an operator says the work already done is not to be trusted."""
    calls = _spy_wikipedia_cli(monkeypatch)
    assert cli.main(["build-embeddings-wikipedia", "--no-resume"]) == 0
    assert calls[0][4] is False


def test_build_embeddings_wikipedia_defaults_no_cuda_no_limit_and_leaves_cores_for_the_gpu_server(env, monkeypatch):
    """The default worker count leaves four cores to Windows and the embedding server itself, and never
    goes above six however many cores the machine has; one embedding server is the default."""
    import os

    calls = _spy_wikipedia_cli(monkeypatch)
    assert cli.main(["build-embeddings-wikipedia"]) == 0
    assert calls == [(False, None, min(6, max(1, (os.cpu_count() or 2) - 4)), 1, True)]


@pytest.mark.parametrize("command", ["build-embeddings", "build-embeddings-wikipedia"])
@pytest.mark.parametrize("servers", ["0", "-1"])
def test_both_embedding_commands_reject_a_nonpositive_server_count(command, servers):
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args([command, "--servers", servers])
    assert exc.value.code == 2


@pytest.mark.parametrize("cores, expected", [(1, 1), (2, 1), (5, 1), (8, 4), (12, 6), (64, 6)])
def test_default_workers_scales_with_the_machine_but_is_capped(monkeypatch, cores, expected):
    monkeypatch.setattr(cli.os, "cpu_count", lambda: cores)
    assert cli.default_workers() == expected


@pytest.mark.parametrize("workers", ["0", "-1"])
def test_wikipedia_cli_rejects_a_nonpositive_worker_count(workers):
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(["build-embeddings-wikipedia", "--workers", workers])
    assert exc.value.code == 2


def test_build_maps_exits_2_with_micromamba_hint_when_tools_missing(env, capsys, monkeypatch):
    from sos import buildmaps

    monkeypatch.setattr(buildmaps, "check_tools", lambda: ["tippecanoe"])
    assert cli.main(["build-maps", "--fixture"]) == 2
    err = capsys.readouterr().err
    assert "tippecanoe" in err and "micromamba activate sos-maps" in err


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


@pytest.mark.parametrize("limit", ["0", "-1"])
def test_wikipedia_cli_rejects_nonpositive_limit(limit):
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(["build-embeddings-wikipedia", "--limit", limit])
    assert exc.value.code == 2


def test_build_embeddings_selects_only_household(env, monkeypatch):
    from sos import embeddings
    calls = []
    monkeypatch.setattr(embeddings, 'build_cli', lambda settings, **kwargs: calls.append(kwargs) or 0)
    assert cli.main(['build-embeddings', '--cuda', '--collection', 'household']) == 0
    assert calls == [{'cuda': True, 'collection': 'household', 'servers': 1}]
    assert cli.main(['build-embeddings', '--servers', '3']) == 0
    assert calls[1] == {'cuda': False, 'collection': 'all', 'servers': 3}
