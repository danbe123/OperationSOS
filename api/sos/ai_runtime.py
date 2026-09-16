# api/sos/ai_runtime.py
"""llama-server lifecycle: state machine, enable/disable, dev subprocess, systemd unit, readiness polling.

This is the single disable path: the AI router, the thermal watchdog and low power mode (via
sos.system.stop_ai_for) all call disable_ai(). State is process-local; the `ai_enabled` setting is
persisted so a production box restores the AI after a reboot.
"""
from __future__ import annotations

import asyncio
import logging
import sqlite3
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import urlparse

from sos.ai import LlamaClient
from sos.config import Settings

log = logging.getLogger(__name__)


def run_cmd(args: list[str], timeout: float = 30) -> subprocess.CompletedProcess:
    """Production-only systemd adapter; dev processes use asyncio directly."""
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)

AiState = Literal["off", "starting", "ready", "error", "off-thermal", "busy"]
Reason = Literal["user", "thermal", "power", "error"]
UNIT = "sos-llama.service"
READY_TIMEOUT_S = 120.0
HEALTH_POLL_S = 2.0
STOP_GRACE_S = 10.0
BUSY_RETRY_MIN_S = 10
BUSY_RETRY_MAX_S = 120
SETTING_ENABLED = "ai_enabled"
SETTING_MODEL = "ai_model"
DISABLE_MESSAGES: dict[str, Optional[str]] = {
    "user": None,
    "thermal": "Turned off automatically because the CPU got too hot",
    "power": "Turned off by low power mode",
    "error": None,
}


def model_stem(settings: Settings) -> str:
    return settings.model[:-5] if settings.model.endswith(".gguf") else settings.model


def llama_argv(settings: Settings) -> list[str]:
    """The dev-profile command line: the same flags as install/systemd/sos-llama.service."""
    port = urlparse(settings.llama_url).port or 8081
    return ["llama-server", "-m", str(Path(settings.core) / "models" / settings.model),
            "--host", "127.0.0.1", "--port", str(port), "-c", "4096", "-t", "4", "-ngl", "0", "-fa", "on",
            "-np", "1", "--no-webui", "--reasoning", "off"]


def get_setting(conn: sqlite3.Connection, key: str, default: Optional[str] = None) -> Optional[str]:
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row[0] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                 "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
    conn.commit()


def write_ai_env(settings: Settings) -> Path:
    """The EnvironmentFile read by sos-llama.service; it selects the model file."""
    path = Path(settings.state) / "config" / "ai.env"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"SOS_MODEL={settings.model}\n", encoding="utf-8")
    return path


@dataclass
class AiRuntime:
    settings: Settings
    llama: LlamaClient
    state: str = "off"
    model: Optional[str] = None
    message: Optional[str] = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    lifecycle: asyncio.Lock = field(default_factory=asyncio.Lock)
    busy_since: Optional[float] = None
    process: Optional[asyncio.subprocess.Process] = None       # dev profile only
    starter: Optional["asyncio.Task[None]"] = None

    def snapshot(self) -> dict:
        """The `ai` object of GET /status and the body of GET /ai/status."""
        state = "busy" if self.state == "ready" and self.lock.locked() else self.state
        return {"state": state, "model": self.model, "message": self.message}

    def retry_after(self) -> int:
        elapsed = time.monotonic() - self.busy_since if self.busy_since else 0.0
        return int(min(BUSY_RETRY_MAX_S, max(BUSY_RETRY_MIN_S, BUSY_RETRY_MAX_S - elapsed)))


async def _start_process(rt: AiRuntime) -> None:
    if rt.settings.dev:
        log_dir = Path(rt.settings.state) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_dir / "llama.log", "ab") as logf:
            rt.process = await asyncio.create_subprocess_exec(
                *llama_argv(rt.settings), stdout=logf, stderr=asyncio.subprocess.STDOUT)
        return
    write_ai_env(rt.settings)
    result = await asyncio.to_thread(run_cmd, ["sudo", "-n", "systemctl", "start", UNIT])
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or f"systemctl start {UNIT} failed").strip())


async def _stop_process(rt: AiRuntime) -> None:
    if rt.settings.dev:
        proc, rt.process = rt.process, None
        if proc is not None and proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), STOP_GRACE_S)
            except TimeoutError:
                proc.kill()
                await proc.wait()
        return
    result = await asyncio.to_thread(run_cmd, ["sudo", "-n", "systemctl", "stop", UNIT])
    if result.returncode != 0:
        log.warning("systemctl stop %s failed: %s", UNIT, result.stderr)


async def _wait_ready(rt: AiRuntime, conn: sqlite3.Connection) -> None:
    deadline = time.monotonic() + READY_TIMEOUT_S
    while time.monotonic() < deadline:
        if rt.process is not None and rt.process.returncode is not None:
            rt.state = "error"
            rt.message = f"llama-server exited with code {rt.process.returncode} (see logs/llama.log)"
            rt.process = None
            return
        if await rt.llama.health():
            rt.model = await rt.llama.model_name() or model_stem(rt.settings)
            rt.state, rt.message = "ready", None
            set_setting(conn, SETTING_ENABLED, "1")
            set_setting(conn, SETTING_MODEL, rt.settings.model)
            return
        await asyncio.sleep(HEALTH_POLL_S)
    rt.state, rt.message = "error", f"llama-server did not become ready within {int(READY_TIMEOUT_S)} s"
    await _stop_process(rt)


async def enable_ai(rt: AiRuntime, conn: sqlite3.Connection, wait: bool = False) -> dict:
    """Start llama-server (dev: subprocess; box: systemctl) and poll /health up to READY_TIMEOUT_S."""
    async with rt.lifecycle:
        if rt.state not in ("starting", "ready"):
            rt.state, rt.message, rt.model = "starting", None, model_stem(rt.settings)
            try:
                await _start_process(rt)
            except (OSError, RuntimeError) as exc:
                rt.state, rt.message, rt.model = "error", f"could not start llama-server: {exc}", None
                return rt.snapshot()
            rt.starter = asyncio.create_task(_wait_ready(rt, conn))
        starter = rt.starter
    if wait and starter is not None:
        await starter
    return rt.snapshot()


async def disable_ai(rt: AiRuntime, conn: sqlite3.Connection, reason: Reason = "user",
                     message: Optional[str] = None) -> dict:
    """Stop llama-server. reason 'thermal' leaves the state 'off-thermal'; nothing restarts it automatically."""
    async with rt.lifecycle:
        if rt.starter is not None and not rt.starter.done():
            rt.starter.cancel()
            try:
                await rt.starter
            except asyncio.CancelledError:
                pass
        await _stop_process(rt)
        rt.state = "off-thermal" if reason == "thermal" else "off"
        rt.model = None
        rt.message = message if message is not None else DISABLE_MESSAGES[reason]
        set_setting(conn, SETTING_ENABLED, "0")
        return rt.snapshot()


async def restore_on_startup(rt: AiRuntime, conn: sqlite3.Connection) -> None:
    """Production only: bring the AI back if it was on before the reboot."""
    if not rt.settings.dev and get_setting(conn, SETTING_ENABLED) == "1" and get_setting(conn, "power_mode") != "low":
        await enable_ai(rt, conn)


async def shutdown(rt: AiRuntime) -> None:
    if rt.starter is not None and not rt.starter.done():
        rt.starter.cancel()
        await asyncio.gather(rt.starter, return_exceptions=True)
    if rt.settings.dev:
        await _stop_process(rt)
    await rt.llama.aclose()
