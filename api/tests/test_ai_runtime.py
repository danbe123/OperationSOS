# api/tests/test_ai_runtime.py
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

import sos.ai_runtime as rt_mod
from sos.ai import LlamaClient
from sos.ai_runtime import (SETTING_ENABLED, SETTING_MODEL, UNIT, AiRuntime, disable_ai, enable_ai, get_setting,
                            llama_argv, model_stem, restore_on_startup, set_setting, shutdown, write_ai_env)


@pytest.fixture
def fast(monkeypatch):
    monkeypatch.setattr(rt_mod, "HEALTH_POLL_S", 0.01)
    monkeypatch.setattr(rt_mod, "READY_TIMEOUT_S", 0.2)
    monkeypatch.setattr(rt_mod, "STOP_GRACE_S", 0.2)


@pytest.fixture
def no_process(monkeypatch):
    calls = []

    async def start(rt):
        calls.append("start")

    async def stop(rt):
        calls.append("stop")

    monkeypatch.setattr(rt_mod, "_start_process", start)
    monkeypatch.setattr(rt_mod, "_stop_process", stop)
    return calls


@pytest.fixture
def runtime(ai_settings, fake_llama):
    return AiRuntime(settings=ai_settings, llama=LlamaClient(ai_settings.llama_url))


@pytest.fixture
def prod_settings(ai_settings, monkeypatch):
    from sos.config import get_settings
    monkeypatch.delenv("SOS_DEV")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


def test_llama_argv_matches_the_unit_flags(ai_settings):
    argv = llama_argv(ai_settings)
    assert argv[:3] == ["llama-server", "-m", str(Path(ai_settings.core) / "models" / "gemma-4-E2B-it-Q4_K_M.gguf")]
    assert argv[3:] == ["--host", "127.0.0.1", "--port", "8081", "-c", "4096", "-t", "4", "-ngl", "0", "-fa", "on",
                        "-np", "1", "--no-webui", "--reasoning", "off"]
    assert model_stem(ai_settings) == "gemma-4-E2B-it-Q4_K_M"


def test_setting_helpers_and_ai_env(ai_db, ai_settings):
    assert get_setting(ai_db, SETTING_ENABLED) is None
    set_setting(ai_db, SETTING_ENABLED, "1")
    set_setting(ai_db, SETTING_ENABLED, "0")
    assert get_setting(ai_db, SETTING_ENABLED) == "0"
    path = write_ai_env(ai_settings)
    assert path == Path(ai_settings.state) / "config" / "ai.env"
    assert path.read_text(encoding="utf-8") == "SOS_MODEL=gemma-4-E2B-it-Q4_K_M.gguf\n"


@pytest.mark.anyio
async def test_snapshot_reports_busy_only_while_ready_and_locked(runtime):
    assert runtime.snapshot() == {"state": "off", "model": None, "message": None}
    runtime.state, runtime.model = "ready", "m"
    async with runtime.lock:
        assert runtime.snapshot() == {"state": "busy", "model": "m", "message": None}
    assert runtime.snapshot()["state"] == "ready"
    runtime.state = "starting"
    async with runtime.lock:
        assert runtime.snapshot()["state"] == "starting"


def test_retry_after_is_clamped_between_10_and_120(runtime):
    assert runtime.retry_after() == 120
    runtime.busy_since = time.monotonic() - 100
    assert 15 <= runtime.retry_after() <= 20
    runtime.busy_since = time.monotonic() - 115
    assert runtime.retry_after() == 10


@pytest.mark.anyio
async def test_enable_returns_starting_then_becomes_ready(runtime, ai_db, fast, no_process):
    snap = await enable_ai(runtime, ai_db)
    assert snap == {"state": "starting", "model": "gemma-4-E2B-it-Q4_K_M", "message": None}
    await runtime.starter
    assert runtime.snapshot() == {"state": "ready", "model": "gemma-4-E2B-it-Q4_K_M", "message": None}
    assert get_setting(ai_db, SETTING_ENABLED) == "1"
    assert get_setting(ai_db, SETTING_MODEL) == "gemma-4-E2B-it-Q4_K_M.gguf"
    assert (await enable_ai(runtime, ai_db, wait=True))["state"] == "ready"      # idempotent
    assert no_process == ["start"]


@pytest.mark.anyio
async def test_enable_times_out_to_error_and_stops_the_server(runtime, ai_db, fast, no_process, fake_llama):
    fake_llama.healthy = False
    snap = await enable_ai(runtime, ai_db, wait=True)
    assert snap["state"] == "error" and "did not become ready" in snap["message"]
    assert no_process == ["start", "stop"]
    assert get_setting(ai_db, SETTING_ENABLED) is None


@pytest.mark.anyio
async def test_enable_reports_a_missing_binary(runtime, ai_db, fast, monkeypatch):
    monkeypatch.setattr(rt_mod, "llama_argv", lambda settings: ["/nonexistent/llama-server"])
    snap = await enable_ai(runtime, ai_db, wait=True)
    assert snap["state"] == "error" and "could not start llama-server" in snap["message"]
    assert runtime.model is None


@pytest.mark.anyio
async def test_disable_reasons_set_state_message_and_setting(runtime, ai_db, fast, no_process):
    await enable_ai(runtime, ai_db, wait=True)
    snap = await disable_ai(runtime, ai_db, "thermal", message="Turned off automatically at 81°C (limit 80°C)")
    assert snap == {"state": "off-thermal", "model": None, "message": "Turned off automatically at 81°C (limit 80°C)"}
    assert get_setting(ai_db, SETTING_ENABLED) == "0"
    await enable_ai(runtime, ai_db, wait=True)                 # the owner may turn it back on by hand
    assert runtime.state == "ready"
    assert (await disable_ai(runtime, ai_db, "power")) == {"state": "off", "model": None, "message": "Turned off by low power mode"}
    await enable_ai(runtime, ai_db, wait=True)
    assert (await disable_ai(runtime, ai_db)) == {"state": "off", "model": None, "message": None}
    assert no_process.count("stop") == 3


@pytest.mark.anyio
async def test_disable_while_starting_cancels_the_poller(runtime, ai_db, fast, no_process, fake_llama):
    fake_llama.healthy = False
    await enable_ai(runtime, ai_db)
    assert runtime.state == "starting"
    await disable_ai(runtime, ai_db)
    assert runtime.state == "off" and runtime.starter.done()
    assert no_process == ["start", "stop"]


@pytest.mark.anyio
async def test_shutdown_stops_a_dev_server(runtime, ai_db, fast, no_process):
    await enable_ai(runtime, ai_db, wait=True)
    await shutdown(runtime)
    assert no_process == ["start", "stop"]


@pytest.mark.anyio
async def test_production_uses_systemctl_and_writes_ai_env(prod_settings, ai_db, fake_llama, fast, monkeypatch):
    calls = []

    def fake_run_cmd(argv, timeout=30):
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(rt_mod, "run_cmd", fake_run_cmd)
    rt = AiRuntime(settings=prod_settings, llama=LlamaClient(prod_settings.llama_url))
    await enable_ai(rt, ai_db, wait=True)
    assert rt.state == "ready"
    assert calls == [["sudo", "-n", "systemctl", "start", UNIT]]
    assert (Path(prod_settings.state) / "config" / "ai.env").read_text(encoding="utf-8") == "SOS_MODEL=gemma-4-E2B-it-Q4_K_M.gguf\n"
    await disable_ai(rt, ai_db)
    assert calls[-1] == ["sudo", "-n", "systemctl", "stop", UNIT]


@pytest.mark.anyio
async def test_production_systemctl_failure_becomes_error_state(prod_settings, ai_db, fake_llama, fast, monkeypatch):
    monkeypatch.setattr(rt_mod, "run_cmd", lambda argv, timeout=30: subprocess.CompletedProcess(
        argv, 1, "", "Failed to start sos-llama.service: Unit not found."))
    rt = AiRuntime(settings=prod_settings, llama=LlamaClient(prod_settings.llama_url))
    snap = await enable_ai(rt, ai_db, wait=True)
    assert snap["state"] == "error" and "Failed to start" in snap["message"]


@pytest.mark.anyio
async def test_restore_on_startup_only_in_production_when_previously_enabled(prod_settings, ai_db, fake_llama, fast, monkeypatch):
    monkeypatch.setattr(rt_mod, "run_cmd", lambda argv, timeout=30: subprocess.CompletedProcess(argv, 0, "", ""))
    rt = AiRuntime(settings=prod_settings, llama=LlamaClient(prod_settings.llama_url))
    await restore_on_startup(rt, ai_db)
    assert rt.state == "off"                                   # nothing recorded
    set_setting(ai_db, SETTING_ENABLED, "1")
    await restore_on_startup(rt, ai_db)
    await rt.starter
    assert rt.state == "ready"


@pytest.mark.anyio
async def test_restore_on_startup_never_spawns_in_dev(runtime, ai_db, fast, no_process):
    set_setting(ai_db, SETTING_ENABLED, "1")
    await restore_on_startup(runtime, ai_db)
    assert runtime.state == "off" and no_process == []


@pytest.mark.anyio
async def test_stop_ai_for_is_the_single_exit_used_by_system(runtime, ai_db, fast, no_process):
    from sos.system import stop_ai_for
    app = SimpleNamespace(state=SimpleNamespace(ai_runtime=runtime, conn=ai_db))
    await stop_ai_for(app, "thermal", message="Turned off automatically at 82°C (limit 80°C)")
    assert runtime.state == "off" and no_process == []        # was already off: nothing to do
    await enable_ai(runtime, ai_db, wait=True)
    await stop_ai_for(app, "thermal", message="Turned off automatically at 82°C (limit 80°C)")
    assert runtime.snapshot() == {"state": "off-thermal", "model": None,
                                  "message": "Turned off automatically at 82°C (limit 80°C)"}
    await enable_ai(runtime, ai_db, wait=True)
    await stop_ai_for(app, "power")
    assert runtime.snapshot()["message"] == "Turned off by low power mode"

@pytest.mark.anyio
async def test_disable_waits_for_an_inflight_process_start(runtime, ai_db, monkeypatch):
    import asyncio
    entered, release = asyncio.Event(), asyncio.Event()
    calls = []
    async def start(rt):
        entered.set()
        await release.wait()
        calls.append('started')
    async def stop(rt):
        calls.append('stopped')
    monkeypatch.setattr(rt_mod, '_start_process', start)
    monkeypatch.setattr(rt_mod, '_stop_process', stop)
    enabling = asyncio.create_task(enable_ai(runtime, ai_db))
    await entered.wait()
    disabling = asyncio.create_task(disable_ai(runtime, ai_db))
    await asyncio.sleep(0)
    assert not disabling.done()
    release.set()
    await asyncio.gather(enabling, disabling)
    assert calls == ['started', 'stopped']
    assert runtime.state == 'off'
    assert runtime.starter.done()
