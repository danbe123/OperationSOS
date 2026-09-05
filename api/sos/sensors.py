"""What the box can sense for itself (spec section 2, "Sensors").

Every driver is optional and cheap, and every one of them writes into `sensor_readings` rather than touching the
conditions directly: detection proposes, it never overrules a person. `detected_states` turns the recent readings
into proposals the engine shows next to the implications, so the kiosk can ask "the box has lost the internet, is
the power off in the street too?" instead of quietly deciding.

Nothing here needs hardware to import or to test: the subprocess runner and the file readers are arguments.

On the Pi:
- `internet`  needs nothing; it resolves a name and fetches one fixed page, both on a three-second timeout.
- `mains`     needs a UPS HAT that presents `/sys/class/power_supply/*/online`, or a GPIO pin exported to sysfs
              and named in `SOS_SENSOR_MAINS_GPIO`.
- `hotspot_clients`, `cpu_temp` need only what `sos.system` already reads.
- `file`      needs a script of your own writing one number to each path in `SOS_SENSOR_FILES`.
- `rtl_power` needs `rtl_power` on PATH and an RTL-SDR dongle in a USB socket.
- `rtl_fm`    needs the same dongle; it records a bulletin to `state/recordings/`.
"""
from __future__ import annotations

import asyncio
import glob
import logging
import math
import re
import shutil
import socket
import sqlite3
import subprocess
import urllib.request
import wave
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable, Optional
from zoneinfo import ZoneInfo

from sos import system
from sos.config import Settings
from sos.db import now_iso

log = logging.getLogger(__name__)

Runner = Callable[[list[str], float], str]

# (id, low Hz, high Hz, step Hz) for the rtl_power sweeps. FM and DAB say whether broadcasting is still on the
# air; the two mobile downlink bands say whether the masts near the house are still transmitting.
BANDS: tuple[tuple[str, int, int, int], ...] = (
    ("fm", 87_500_000, 108_000_000, 100_000),
    ("dab", 174_000_000, 240_000_000, 100_000),
    ("mobile_800", 791_000_000, 821_000_000, 200_000),
    ("mobile_900", 925_000_000, 960_000_000, 200_000),
)
MOBILE_BANDS = ("band_mobile_800", "band_mobile_900")
FILE_UNITS = {"temp_in": "C", "temp_out": "C", "humidity": "%", "pressure_hpa": "hPa", "co_ppm": "ppm",
              "radiation_usvh": "uSv/h", "leak": "bool"}
INTERNET_FAILS = 3            # three failed probes running before the box says the internet is off
MOBILE_QUIET_DROP_DB = 10.0   # a mobile band this much below its own recent best counts as gone quiet
MOBILE_MIN_HISTORY = 3        # and only after that many readings, so a cold start never fires
DETECT_WINDOW = timedelta(hours=24)
RECORD_RATE = 22050
PRUNE_INTERVAL_S = 3600.0      # a reading a minute is 20 000 rows a fortnight; tidy up once an hour
_SLUG = re.compile(r"[^a-z0-9]+")


def slug(text: str) -> str:
    return _SLUG.sub("-", (text or "").lower()).strip("-") or "x"


# --- readings ---------------------------------------------------------------------------------------------------

def record(conn: sqlite3.Connection, sensor: str, value: float | None, unit: str = "", at: str | None = None) -> None:
    conn.execute("INSERT INTO sensor_readings(sensor, value, unit, at) VALUES (?,?,?,?)",
                 (sensor, None if value is None else float(value), unit, at or now_iso()))
    conn.commit()


def latest(conn: sqlite3.Connection) -> list[dict]:
    """The newest reading for each sensor, in name order: what `GET /api/sensors` returns."""
    rows = conn.execute(
        "SELECT s.sensor, s.value, s.unit, s.at FROM sensor_readings s JOIN "
        "(SELECT sensor, MAX(at) AS at, MAX(id) AS id FROM sensor_readings GROUP BY sensor) m "
        "ON s.sensor = m.sensor AND s.id = m.id ORDER BY s.sensor").fetchall()
    return [{"sensor": r["sensor"], "value": r["value"], "unit": r["unit"] or "", "at": r["at"]} for r in rows]


def history(conn: sqlite3.Connection, sensor: str, limit: int = 10, since: str | None = None) -> list[dict]:
    """The most recent readings for one sensor, newest first."""
    sql = "SELECT sensor, value, unit, at FROM sensor_readings WHERE sensor=?"
    args: list = [sensor]
    if since:
        sql += " AND at >= ?"
        args.append(since)
    sql += " ORDER BY at DESC, id DESC LIMIT ?"
    args.append(int(limit))
    return [{"sensor": r["sensor"], "value": r["value"], "unit": r["unit"] or "", "at": r["at"]}
            for r in conn.execute(sql, args)]


def prune(conn: sqlite3.Connection, keep_days: int = 14) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).replace(microsecond=0).isoformat()
    conn.execute("DELETE FROM sensor_readings WHERE at < ?", (cutoff,))
    conn.commit()


# --- the runner -----------------------------------------------------------------------------------------------

def run_tool(args: list[str], timeout: float) -> str:
    """Run a command and return its stdout. A timeout is not a failure: `rtl_fm` is stopped by the clock."""
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.stdout or ""
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout
        return out.decode("utf-8", "replace") if isinstance(out, bytes) else (out or "")
    except OSError as exc:
        log.debug("sensor tool %s failed: %s", args[0], exc)
        return ""


def have(binary: str) -> bool:
    return bool(shutil.which(binary))


# --- the cheap drivers ------------------------------------------------------------------------------------------

def http_ok(url: str, timeout: float) -> bool:
    """A short GET of a fixed well-known page. Any answer at all means something upstream is alive."""
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": "operation-sos"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(64)
            return 200 <= int(getattr(response, "status", 200)) < 500
    except Exception:                              # urllib raises URLError, socket.timeout, ssl errors, ValueError
        return False


def probe_internet(settings: Settings, resolve=socket.getaddrinfo, fetch=http_ok) -> float:
    """1.0 when a DNS lookup and a short HTTP GET of the fixed host both succeed inside the timeout, else 0.0."""
    timeout = float(settings.sensor_probe_timeout_s)
    try:
        infos = resolve(settings.sensor_probe_host, 80, 0, socket.SOCK_STREAM)
    except OSError:
        return 0.0
    if not infos:
        return 0.0
    return 1.0 if fetch(settings.sensor_probe_url, timeout) else 0.0


def _read_first_line(path: str) -> Optional[str]:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def probe_mains(settings: Settings, reader=_read_first_line) -> Optional[float]:
    """1.0 while the house has mains, 0.0 on battery, None when nothing on this box can tell.

    A UPS HAT that registers as a power supply publishes `/sys/class/power_supply/<name>/online`; a HAT that
    only pulls a GPIO pin low is read from the sysfs path in `SOS_SENSOR_MAINS_GPIO`."""
    if settings.sensor_mains_gpio:
        raw = reader(settings.sensor_mains_gpio)
        if raw is None or not raw.strip():
            return None
        on = raw.strip() not in ("0", "")
        return float(on != bool(settings.sensor_mains_gpio_active_low))
    values = []
    for path in sorted(glob.glob(settings.sensor_mains_glob)):
        if "/BAT" in path.upper() or "battery" in path.lower():
            continue
        raw = reader(path)
        if raw is not None and raw.strip() in ("0", "1"):
            values.append(int(raw.strip()))
    if not values:
        return None
    return float(max(values))


def probe_files(settings: Settings, reader=_read_first_line) -> list[tuple[str, float, str]]:
    """`SOS_SENSOR_FILES` maps a sensor name to a path holding one number; the name fixes the unit."""
    out = []
    for name, path in sorted((settings.sensor_files or {}).items()):
        raw = reader(str(path))
        if raw is None:
            continue
        try:
            value = float(raw.split()[0])
        except (ValueError, IndexError):
            continue
        out.append((name, value, FILE_UNITS.get(name, "")))
    return out


def poll_cheap(conn: sqlite3.Connection, settings: Settings, at: str | None = None, *,
               resolve=socket.getaddrinfo, fetch=http_ok, reader=_read_first_line) -> list[tuple[str, float | None, str]]:
    """The drivers that cost nothing: the probe, the mains line, the box itself and any file sensors."""
    at = at or now_iso()
    readings: list[tuple[str, float | None, str]] = [("internet", probe_internet(settings, resolve, fetch), "up")]
    mains = probe_mains(settings, reader)
    if mains is not None:
        readings.append(("mains", mains, "on"))
    readings.append(("hotspot_clients", float(system.hotspot_clients(settings)), "clients"))
    temp = system.cpu_temp(settings)
    if temp is not None:
        readings.append(("cpu_temp", float(temp), "C"))
    readings += list(probe_files(settings, reader))
    for sensor, value, unit in readings:
        record(conn, sensor, value, unit, at)
    return readings


# --- rtl_power --------------------------------------------------------------------------------------------------

def parse_rtl_power(text: str) -> list[tuple[float, float, list[float]]]:
    """rtl_power CSV rows as (low Hz, step Hz, dB values). Blank and short lines are ignored."""
    rows: list[tuple[float, float, list[float]]] = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 7:
            continue
        try:
            low, _high, step = float(parts[2]), float(parts[3]), float(parts[4])
            values = [float(p) for p in parts[6:] if p not in ("", "-")]
        except ValueError:
            continue
        if step > 0 and values:
            rows.append((low, step, values))
    return rows


def band_energy(rows: Iterable[tuple[float, float, list[float]]], low_hz: float, high_hz: float) -> Optional[float]:
    """The mean power in dB of every bin whose centre falls inside the band, or None when the sweep missed it."""
    total = count = 0.0
    for low, step, values in rows:
        for index, value in enumerate(values):
            centre = low + step * (index + 0.5)
            if low_hz <= centre <= high_hz and math.isfinite(value):
                total += value
                count += 1
    return round(total / count, 2) if count else None


def sweep(settings: Settings, band: tuple[str, int, int, int], runner: Runner = run_tool) -> Optional[float]:
    name, low, high, step = band
    dwell = max(1, int(settings.rtl_power_dwell_s))
    args = [settings.rtl_power_bin, "-f", f"{low}:{high}:{step}", "-i", f"{dwell}s", "-e", f"{dwell}s", "-g", "20", "-"]
    rows = parse_rtl_power(runner(args, dwell * 4 + 10))
    return band_energy(rows, low, high)


def poll_rtl_power(conn: sqlite3.Connection, settings: Settings, runner: Runner = run_tool,
                   at: str | None = None) -> dict[str, float]:
    """One sweep per band, recorded as `band_<id>` in dB, plus a `broadcast` reading (the louder of FM and DAB)."""
    at = at or now_iso()
    out: dict[str, float] = {}
    for band in BANDS:
        value = sweep(settings, band, runner)
        if value is not None:
            out[f"band_{band[0]}"] = value
            record(conn, f"band_{band[0]}", value, "dB", at)
    broadcast = [out[k] for k in ("band_fm", "band_dab") if k in out]
    if broadcast:
        out["broadcast"] = max(broadcast)
        record(conn, "broadcast", out["broadcast"], "dB", at)
    return out


# --- what the readings say --------------------------------------------------------------------------------------

def _iso(value: str | None) -> Optional[datetime]:
    from sos.conditions import parse_iso

    return parse_iso(value)


def detected_states(conn: sqlite3.Connection, now: Optional[datetime] = None) -> dict[str, dict]:
    """Condition proposals from the readings: `{condition: {state, at, confidence, sensor}}`.

    The engine takes these as proposals with source `detected`; a state a person set after the reading always wins.
    - internet off after three failed probes running (spec section 2);
    - power off while the UPS says there is no mains;
    - mobile degraded when both mobile bands have dropped well below their own recent best."""
    now = now or datetime.now(timezone.utc)
    since = (now - DETECT_WINDOW).replace(microsecond=0).isoformat()
    out: dict[str, dict] = {}

    probes = history(conn, "internet", limit=INTERNET_FAILS)
    if len(probes) >= INTERNET_FAILS and all((p["value"] or 0.0) < 0.5 for p in probes):
        out["internet"] = {"state": "off", "at": probes[-1]["at"], "confidence": 0.8, "sensor": "internet"}

    mains = history(conn, "mains", limit=1)
    if mains and (mains[0]["value"] or 0.0) < 0.5:
        out["power"] = {"state": "off", "at": mains[0]["at"], "confidence": 0.9, "sensor": "mains"}

    watched, quiet = 0, []
    for sensor in MOBILE_BANDS:
        rows = history(conn, sensor, limit=48, since=since)
        if len(rows) < MOBILE_MIN_HISTORY:
            continue
        newest, earlier = rows[0], [r["value"] for r in rows[1:] if r["value"] is not None]
        if newest["value"] is None or not earlier:
            continue
        watched += 1
        if max(earlier) - newest["value"] >= MOBILE_QUIET_DROP_DB:
            quiet.append(newest)
    if watched and len(quiet) == watched:          # every band the box can watch has gone quiet at once
        newest = max(quiet, key=lambda r: r["at"])
        out["mobile"] = {"state": "degraded", "at": newest["at"], "confidence": 0.6, "sensor": "rtl_power"}
    return out


# --- bulletins (spec section 6, "Radio") ---------------------------------------------------------------------------

def recordable(bulletin: dict) -> bool:
    """A bulletin the dongle can actually record: an FM frequency, and not one marked unrecordable."""
    return bool(bulletin.get("record_hz")) and bulletin.get("recordable", True) is not False


def recording_name(bulletin: dict, at: datetime) -> str:
    return f"{slug(bulletin['station'])}-{at.astimezone(timezone.utc).strftime('%Y%m%dT%H%MZ')}.wav"


def due_recordings(bulletins: Iterable[dict], now: datetime, tz: str = "Europe/London",
                   window_s: int = 300) -> list[tuple[dict, datetime]]:
    """The bulletins whose window contains `now`, with the UTC time the window opened."""
    try:
        zone = ZoneInfo(tz)
    except Exception:
        zone = timezone.utc
    local = now.astimezone(zone)
    due: list[tuple[dict, datetime]] = []
    for bulletin in bulletins:
        if not recordable(bulletin):
            continue
        for text in bulletin.get("times") or []:
            try:
                hour, minute = (int(x) for x in str(text).split(":"))
            except ValueError:
                continue
            for day in (0, -1):                    # a window that opened just before midnight is still open
                start = (local + timedelta(days=day)).replace(hour=hour, minute=minute, second=0, microsecond=0)
                start_utc = start.astimezone(timezone.utc)
                if 0 <= (now - start_utc).total_seconds() < window_s:
                    due.append((bulletin, start_utc))
    return due


def write_wav(raw: bytes, path: Path, rate: int = RECORD_RATE) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(raw)
    return path


def record_frequency(settings: Settings, hz: int, seconds: int, path: Path, runner: Runner = run_tool) -> Optional[Path]:
    """`rtl_fm` a wide-FM station into a raw stream for `seconds`, then wrap it as a WAV. None if nothing came out."""
    raw_path = path.with_suffix(".raw")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    runner([settings.rtl_fm_bin, "-f", str(int(hz)), "-M", "wbfm", "-s", "200k", "-r", str(RECORD_RATE),
            "-g", "20", "-E", "deemp", "-l", "0", str(raw_path)], float(seconds))
    try:
        raw = raw_path.read_bytes()
    except OSError:
        return None
    finally:
        raw_path.unlink(missing_ok=True)
    if not raw:
        return None
    return write_wav(raw, path)


def record_due(settings: Settings, bulletins: Iterable[dict], now: Optional[datetime] = None, tz: str = "Europe/London",
               runner: Runner = run_tool) -> list[Path]:
    """Record every bulletin whose window is open and that has not been recorded already."""
    now = now or datetime.now(timezone.utc)
    made: list[Path] = []
    for bulletin, start in due_recordings(bulletins, now, tz, int(settings.bulletin_window_s)):
        path = settings.recordings / recording_name(bulletin, start)
        if path.exists():
            continue
        remaining = int(settings.bulletin_window_s - (now - start).total_seconds())
        if remaining < 10:
            continue
        made_path = record_frequency(settings, int(bulletin["record_hz"]), remaining, path, runner)
        if made_path is not None:
            made.append(made_path)
            log.info("recorded %s to %s", bulletin["station"], made_path.name)
    return made


def wav_seconds(path: Path) -> Optional[float]:
    try:
        with wave.open(str(path), "rb") as fh:
            rate = fh.getframerate() or RECORD_RATE
            return round(fh.getnframes() / rate, 1)
    except (OSError, wave.Error):
        return None


def list_recordings(settings: Settings) -> list[dict]:
    """Everything in `state/recordings/`, newest first."""
    directory = settings.recordings
    if not directory.is_dir():
        return []
    out = []
    for path in sorted(directory.glob("*.wav")):
        st = path.stat()
        station, _, stamp = path.stem.rpartition("-")
        out.append({"name": path.name, "station": station.replace("-", " ") or path.stem, "stamp": stamp,
                    "size_bytes": st.st_size, "seconds": wav_seconds(path),
                    "at": datetime.fromtimestamp(st.st_mtime, timezone.utc).replace(microsecond=0).isoformat(),
                    "url": f"/api/recordings/{path.name}"})
    out.sort(key=lambda r: r["at"], reverse=True)
    return out


# --- the background task -------------------------------------------------------------------------------------------

async def run(settings: Settings, db_path: Path, tz: str = "Europe/London") -> None:
    """Poll the cheap drivers every minute and the dongle every ten, and record a bulletin when one is due."""
    from sos.db import connect
    from sos.rules import RulesError, load as load_rules

    conn = connect(db_path)
    last_rtl = last_prune = 0.0
    try:
        while True:
            loop = asyncio.get_running_loop()
            try:
                await asyncio.to_thread(poll_cheap, conn, settings)
                now = loop.time()
                if now - last_prune >= PRUNE_INTERVAL_S:
                    last_prune = now
                    await asyncio.to_thread(prune, conn)
                if have(settings.rtl_power_bin) and (last_rtl == 0.0 or now - last_rtl >= settings.rtl_interval_s):
                    last_rtl = now
                    await asyncio.to_thread(poll_rtl_power, conn, settings)
                if have(settings.rtl_fm_bin):
                    try:
                        bulletins = load_rules(settings.playbooks / "rules").bulletins
                    except (RulesError, OSError):
                        bulletins = ()
                    if bulletins:
                        await asyncio.to_thread(record_due, settings, bulletins, None, tz)
            except asyncio.CancelledError:
                raise
            except Exception:                       # a sensor must never take the API down
                log.exception("sensor poll failed")
            await asyncio.sleep(settings.sensor_interval_s)
    finally:
        conn.close()
