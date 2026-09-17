"""System control for the box. Every subprocess, sysfs and NetworkManager access goes through run_cmd(),
read_sysfs() and write_sysfs(), which return fakes under SOS_DEV=1 and are monkeypatched in tests."""
from __future__ import annotations

import asyncio
import glob
import hashlib
import hmac
import os
import secrets
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Callable

from sos import __version__
from sos.config import Settings
from sos.db import connect, get_setting, set_setting

THERMAL_PATH = "/sys/class/thermal/thermal_zone0/temp"
BACKLIGHT_GLOB = "/sys/class/backlight/*"
HOTSPOT_PROFILE = "sos-hotspot"
ETH_PROFILES = {"client": "sos-eth-client", "direct": "sos-eth-direct"}
HOTSPOT_IP = "10.42.0.1"
LLAMA_UNIT = "sos-llama.service"
TOKEN_TTL = 600
PIN_ATTEMPTS = 5
PIN_WINDOW = 60.0
MIN_BACKLIGHT_LEVEL = 10
LOW_POWER_BACKLIGHT = 30
DEFAULTS = {
    "default_theme": "field", "thermal_ai_off_c": "80", "idle_minutes": "5", "home_minutes": "30",
    "power_mode": "normal", "eth_mode": "client", "ssid": "SOS", "passphrase": "", "ai_state": "off",
    "people": "2",
}
PEOPLE_RANGE = (1, 20)                       # the only number a household is ever asked for
THEMES = ("field", "mono")
AI_RUNNING_STATES = ("starting", "ready", "busy")

FAKE_CMD_OUTPUT: dict[tuple[str, ...], str] = {
    ("nmcli", "-t", "-f", "NAME", "con", "show", "--active"): "sos-hotspot\nsos-eth-client\n",
    ("iw", "dev", "wlan0", "station", "dump"):
        "Station aa:bb:cc:dd:ee:01 (on wlan0)\n\tinactive time:\t10 ms\n"
        "Station aa:bb:cc:dd:ee:02 (on wlan0)\n\tinactive time:\t20 ms\n",
}
FAKE_SYSFS: dict[str, str] = {
    THERMAL_PATH: "45000\n",
    "/sys/class/backlight/fake/max_brightness": "31\n",
    "/sys/class/backlight/fake/brightness": "31\n",
}


def _strip_sudo(args: list[str]) -> tuple[str, ...]:
    out = list(args)
    while out and out[0] in ("sudo", "-n"):
        out.pop(0)
    return tuple(out)


def run_cmd(args: list[str], settings: Settings, timeout: float = 30.0, check: bool = False) -> str:
    if settings.dev:
        return FAKE_CMD_OUTPUT.get(_strip_sudo(args), "")
    proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    if check and proc.returncode != 0:
        raise RuntimeError(f"{' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def sudo(args: list[str], settings: Settings) -> str:
    return run_cmd(["sudo", "-n", *args], settings)


def read_sysfs(path: str, settings: Settings) -> str | None:
    if settings.dev:
        return FAKE_SYSFS.get(path)
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return None


def write_sysfs(path: str, value, settings: Settings) -> bool:
    if settings.dev:
        FAKE_SYSFS[path] = f"{value}\n"
        return True
    try:
        Path(path).write_text(f"{value}\n", encoding="utf-8")
        return True
    except OSError:
        return False


def cpu_temp(settings: Settings) -> float | None:
    raw = read_sysfs(THERMAL_PATH, settings)
    try:
        return round(int(raw.strip()) / 1000, 1) if raw else None
    except ValueError:
        return None


def disk_info(path: Path, mounted: bool) -> dict:
    if mounted and Path(path).exists():
        usage = shutil.disk_usage(path)
        return {"mounted": True, "path": str(path), "total_gb": round(usage.total / 1e9, 1),
                "free_gb": round(usage.free / 1e9, 1)}
    return {"mounted": False, "path": str(path), "total_gb": 0.0, "free_gb": 0.0}


def mem_info() -> dict:
    total = avail = 0
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                total = int(line.split()[1])
            elif line.startswith("MemAvailable:"):
                avail = int(line.split()[1])
    except OSError:
        pass
    return {"total_mb": total // 1024, "used_mb": max(0, total - avail) // 1024}


def uptime_s() -> int:
    try:
        return int(float(Path("/proc/uptime").read_text().split()[0]))
    except (OSError, ValueError, IndexError):
        return 0


def hotspot_clients(settings: Settings) -> int:
    out = run_cmd(["iw", "dev", "wlan0", "station", "dump"], settings)
    return sum(1 for line in out.splitlines() if line.startswith("Station "))


def hotspot_enabled(settings: Settings) -> bool:
    out = run_cmd(["nmcli", "-t", "-f", "NAME", "con", "show", "--active"], settings)
    return HOTSPOT_PROFILE in [line.strip() for line in out.splitlines()]


def hotspot_info(conn: sqlite3.Connection, settings: Settings) -> dict:
    return {"ssid": get_setting(conn, "ssid", DEFAULTS["ssid"]), "ip": HOTSPOT_IP,
            "clients": hotspot_clients(settings), "enabled": hotspot_enabled(settings)}


def set_hotspot(conn: sqlite3.Connection, settings: Settings, ssid: str,
                passphrase: str | None = None) -> None:
    ssid = (ssid or "").strip()
    if not 1 <= len(ssid.encode("utf-8")) <= 32:
        raise ValueError("SSID must be 1 to 32 bytes")
    passphrase = passphrase or ""
    if passphrase and not 8 <= len(passphrase) <= 63:
        raise ValueError("Passphrase must be 8 to 63 characters (or empty for an open network)")
    sudo(["nmcli", "con", "modify", HOTSPOT_PROFILE, "802-11-wireless.ssid", ssid], settings)
    if passphrase:
        sudo(["nmcli", "con", "modify", HOTSPOT_PROFILE, "wifi-sec.key-mgmt", "wpa-psk",
              "wifi-sec.psk", passphrase], settings)
    else:
        sudo(["nmcli", "con", "modify", HOTSPOT_PROFILE, "remove", "wifi-sec"], settings)
    sudo(["nmcli", "con", "up", HOTSPOT_PROFILE], settings)
    set_setting(conn, "ssid", ssid)
    set_setting(conn, "passphrase", passphrase)


def set_eth_mode(conn: sqlite3.Connection, settings: Settings, mode: str) -> None:
    if mode not in ETH_PROFILES:
        raise ValueError("mode must be 'client' or 'direct'")
    other = ETH_PROFILES["direct" if mode == "client" else "client"]
    sudo(["nmcli", "con", "modify", other, "connection.autoconnect", "no"], settings)
    sudo(["nmcli", "con", "modify", ETH_PROFILES[mode], "connection.autoconnect", "yes"], settings)
    sudo(["nmcli", "con", "up", ETH_PROFILES[mode]], settings)
    set_setting(conn, "eth_mode", mode)


def backlight_device(settings: Settings) -> str | None:
    if settings.dev:
        return "/sys/class/backlight/fake"
    devices = sorted(glob.glob(BACKLIGHT_GLOB))
    return devices[0] if devices else None


def set_backlight(settings: Settings, level: int) -> int | None:
    device = backlight_device(settings)
    if device is None:
        return None
    level = max(MIN_BACKLIGHT_LEVEL, min(100, int(level)))
    raw_max = read_sysfs(f"{device}/max_brightness", settings)
    max_brightness = int(raw_max.strip()) if raw_max and raw_max.strip().isdigit() else 255
    raw = max(1, round(level * max_brightness / 100))
    if not write_sysfs(f"{device}/brightness", raw, settings):
        return None
    return level


def ai_status(conn: sqlite3.Connection, settings: Settings) -> dict:
    return {"state": get_setting(conn, "ai_state", DEFAULTS["ai_state"]), "model": settings.model,
            "message": get_setting(conn, "ai_message")}


def set_ai_state(conn: sqlite3.Connection, state: str, message: str | None = None) -> None:
    set_setting(conn, "ai_state", state)
    set_setting(conn, "ai_message", message)


def stop_ai(conn: sqlite3.Connection, settings: Settings, state: str = "off",
            message: str | None = None) -> None:
    sudo(["systemctl", "stop", LLAMA_UNIT], settings)
    set_ai_state(conn, state, message)


def set_power_mode(conn: sqlite3.Connection, settings: Settings, mode: str) -> None:
    if mode not in ("normal", "low"):
        raise ValueError("mode must be 'normal' or 'low'")
    set_setting(conn, "power_mode", mode)
    if mode == "low":
        if get_setting(conn, "ai_state", DEFAULTS["ai_state"]) in AI_RUNNING_STATES:
            stop_ai(conn, settings, "off", "Turned off by low power mode")
        set_backlight(settings, LOW_POWER_BACKLIGHT)
    else:
        set_backlight(settings, 100)


def apply_settings(conn: sqlite3.Connection, patch: dict) -> None:
    for key, value in patch.items():
        if value is None:
            continue
        if key == "default_theme":
            if value not in THEMES:
                raise ValueError("default_theme must be field or mono")
            set_setting(conn, key, value)
        elif key in ("thermal_ai_off_c", "idle_minutes", "home_minutes", "people"):
            lo, hi = {"thermal_ai_off_c": (50, 95), "idle_minutes": (1, 120),
                      "home_minutes": (1, 600), "people": PEOPLE_RANGE}[key]
            try:
                number = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{key} must be a whole number") from exc
            if not lo <= number <= hi:
                raise ValueError(f"{key} must be between {lo} and {hi}")
            set_setting(conn, key, str(number))
        else:
            raise ValueError(f"unknown setting {key}")


def hash_pin(pin: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(pin.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_pin(conn: sqlite3.Connection, pin: str) -> bool:
    stored = get_setting(conn, "pin_hash")
    if not stored:
        return False
    try:
        _, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    digest = hashlib.scrypt((pin or "").encode("utf-8"), salt=bytes.fromhex(salt_hex),
                            n=16384, r=8, p=1, dklen=32)
    return hmac.compare_digest(digest.hex(), digest_hex)


def pin_required(conn: sqlite3.Connection) -> bool:
    return bool(get_setting(conn, "pin_hash"))


def set_pin(conn: sqlite3.Connection, pin: str) -> None:
    if not (pin and pin.isdigit() and 4 <= len(pin) <= 12):
        raise ValueError("PIN must be 4 to 12 digits")
    set_setting(conn, "pin_hash", hash_pin(pin))


def clear_pin(conn: sqlite3.Connection) -> None:
    set_setting(conn, "pin_hash", None)


class TokenStore:
    """Bearer tokens for the PIN gate, held in memory so a restart revokes every session."""

    def __init__(self, ttl: int = TOKEN_TTL, clock: Callable[[], float] = time.monotonic) -> None:
        self.ttl = ttl
        self.clock = clock
        self._tokens: dict[str, float] = {}

    def issue(self) -> str:
        now = self.clock()
        self._tokens = {t: exp for t, exp in self._tokens.items() if exp > now}
        token = secrets.token_urlsafe(24)
        self._tokens[token] = now + self.ttl
        return token

    def valid(self, token: str | None) -> bool:
        if not token:
            return False
        exp = self._tokens.get(token)
        return exp is not None and exp > self.clock()

    def revoke_all(self) -> None:
        self._tokens.clear()


class RateLimiter:
    """Sliding-window limiter: at most `limit` hits per key per `window` seconds."""

    def __init__(self, limit: int = PIN_ATTEMPTS, window: float = PIN_WINDOW,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.limit = limit
        self.window = window
        self.clock = clock
        self._hits: dict[str, deque] = {}

    def allow(self, key: str) -> bool:
        now = self.clock()
        q = self._hits.setdefault(key, deque())
        while q and q[0] <= now - self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


async def stop_ai_for(app, reason: str, message: str | None = None) -> None:
    from sos.ai_runtime import disable_ai
    if app.state.ai_runtime.state in {"starting", "ready", "busy"}:
        await disable_ai(app.state.ai_runtime, app.state.conn, reason, message)


class ThermalWatchdog:
    """Polls the SoC temperature; at or above thermal_ai_off_c with the AI on it stops llama and sets
    off-thermal. It never restarts the AI."""

    def __init__(self, settings: Settings, db_path, interval: float = 10.0) -> None:
        self.settings = settings
        self.db_path = db_path
        self.interval = interval
        self.app = None

    def tick(self, conn: sqlite3.Connection) -> str | None:
        temp = cpu_temp(self.settings)
        if temp is None:
            return None
        threshold = float(get_setting(conn, "thermal_ai_off_c", DEFAULTS["thermal_ai_off_c"]))
        state = get_setting(conn, "ai_state", DEFAULTS["ai_state"])
        if temp >= threshold and state in AI_RUNNING_STATES:
            stop_ai(conn, self.settings, "off-thermal",
                    f"AI stopped at {temp:.0f} C (limit {threshold:.0f} C)")
            return "stopped"
        return None

    async def run(self) -> None:
        while True:
            conn = connect(self.db_path)
            try:
                if self.app is None:
                    self.tick(conn)
                else:
                    temp = cpu_temp(self.settings)
                    threshold = float(get_setting(conn, "thermal_ai_off_c", DEFAULTS["thermal_ai_off_c"]))
                    if temp is not None and temp >= threshold and self.app.state.ai_runtime.state in AI_RUNNING_STATES:
                        await stop_ai_for(self.app, "thermal", f"AI stopped at {temp:.0f} C (limit {threshold:.0f} C)")
            except Exception:  # the watchdog must survive transient errors
                pass
            finally:
                conn.close()
            await asyncio.sleep(self.interval)


def default_sync_command(tier: str, only: list[str] | None = None) -> list[str]:
    cmd = [sys.executable, "-m", "sos.cli", "sync", "--tier", tier]
    return cmd + ["--only", ",".join(only)] if only else cmd


class UpdateRunner:
    """Runs `sos sync` per tier in a background thread and keeps the last 500 output lines."""

    def __init__(self, command_factory: Callable[..., list[str]] = default_sync_command) -> None:
        self.factory = command_factory
        self.lines: deque[str] = deque(maxlen=500)
        self.running = False
        self.done = False
        self.ok: bool | None = None
        self.only: list[str] = []
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def start(self, tiers: list[str], only: list[str] | None = None) -> bool:
        """A whole tier, or with `only` just those items (the Library's "Get it")."""
        with self._lock:
            if self.running:
                return False
            self.running, self.done, self.ok = True, False, None
            self.only = list(only or [])
            self.lines.clear()
            self._thread = threading.Thread(target=self._run, args=(list(tiers), self.only), daemon=True)
            self._thread.start()
            return True

    def _run(self, tiers: list[str], only: list[str]) -> None:
        ok = True
        try:
            for tier in tiers:
                self.lines.append(f"== sync {tier}" + (f" ({', '.join(only)})" if only else ""))
                try:
                    with subprocess.Popen(self.factory(tier, only) if only else self.factory(tier), stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT, text=True) as proc:
                        for line in proc.stdout:
                            self.lines.append(line.rstrip("\n"))
                        rc = proc.wait()
                    if rc != 0:
                        ok = False
                        self.lines.append(f"sync {tier} failed (exit {rc})")
                except OSError as exc:
                    ok = False
                    self.lines.append(f"sync {tier} failed: {exc}")
        except BaseException:  # a stuck running=True would block every later update
            ok = False
            raise
        finally:
            with self._lock:
                self.ok, self.done, self.running = ok, True, False

    def progress(self) -> dict:
        return {"running": self.running, "lines": list(self.lines), "done": self.done, "ok": self.ok, "only": list(self.only)}

    def wait(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)


def status(conn: sqlite3.Connection, settings: Settings) -> dict:
    from sos.library import ext_mounted

    ext_ok = ext_mounted(settings)
    return {
        "version": __version__,
        "uptime_s": uptime_s(),
        "cpu_temp_c": cpu_temp(settings),
        "load": [round(x, 2) for x in os.getloadavg()],
        "mem": mem_info(),
        "disks": {"core": disk_info(settings.core, True), "extended": disk_info(settings.ext, ext_ok)},
        "hotspot": hotspot_info(conn, settings),
        "eth_mode": get_setting(conn, "eth_mode", DEFAULTS["eth_mode"]),
        "power_mode": get_setting(conn, "power_mode", DEFAULTS["power_mode"]),
        "ai": ai_status(conn, settings),
        "thermal_ai_off_c": int(get_setting(conn, "thermal_ai_off_c", DEFAULTS["thermal_ai_off_c"])),
        "idle_minutes": int(get_setting(conn, "idle_minutes", DEFAULTS["idle_minutes"])),
        "home_minutes": int(get_setting(conn, "home_minutes", DEFAULTS["home_minutes"])),
        "people": people_count(conn),
        "pin_required": pin_required(conn),
        "dev": settings.dev,
        # A box upgraded from the three-theme world still holds "vault" or "blackout" in its
        # settings row. Serving that would stamp <html> with a theme that has no palette and no map
        # style, so an unknown value reads as the default until somebody saves a new one.
        "default_theme": known_theme(get_setting(conn, "default_theme", DEFAULTS["default_theme"])),
    }


def known_theme(value: str) -> str:
    return value if value in THEMES else DEFAULTS["default_theme"]


def people_count(conn: sqlite3.Connection) -> int:
    """How many people the kits scale for. A stored value from outside the range, or no value at all,
    reads as the default rather than failing every screen that asks."""
    lo, hi = PEOPLE_RANGE
    try:
        return max(lo, min(hi, int(get_setting(conn, "people", DEFAULTS["people"]))))
    except (TypeError, ValueError):
        return int(DEFAULTS["people"])


def rescan(conn: sqlite3.Connection, settings: Settings) -> dict:
    from sos.library import rescan as library_rescan

    return library_rescan(conn, settings)
