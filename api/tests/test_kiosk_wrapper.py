"""The kiosk wrapper (install/kiosk/sos-kiosk-app) as the thing that keeps Chromium up on an unattended
box: the flags a crash-prone kiosk needs, the profile put right before every start, a crash loop that
backs off instead of spinning, and a clean stop. Chromium is a stub on PATH that records how it was started."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path

import pytest

WRAPPER = Path(__file__).resolve().parents[2] / "install" / "kiosk" / "sos-kiosk-app"

STUB = """#!/usr/bin/env bash
# A stand-in for chromium: note how it was started, then behave as the test's MODE says.
d="$STUB_DIR"
n=$(( $(cat "$d/count" 2>/dev/null || echo 0) + 1 ))
echo "$n" > "$d/count"
printf '%s\\n' "$@" > "$d/args-$n"
echo "$EPOCHREALTIME" >> "$d/times"
[ -e "$SOS_KIOSK_PROFILE/SingletonLock" ] && echo present > "$d/lock-$n" || echo absent > "$d/lock-$n"
cp "$SOS_KIOSK_PROFILE/Default/Preferences" "$d/prefs-$n" 2>/dev/null || true
case "$STUB_MODE" in
  die) exit 1 ;;
  live) echo $$ > "$d/pid"; exec sleep 60 ;;
  long_then_stop)
    if [ "$n" -eq 1 ]; then sleep 0.4; exit 0; fi
    kill -TERM "$PPID"; sleep 5 ;;
esac
"""


@pytest.fixture
def kiosk(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "chromium").write_text(STUB)
    (bin_dir / "chromium").chmod(0o755)
    stub_dir = tmp_path / "stub"
    stub_dir.mkdir()
    profile = tmp_path / "profile"
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "STUB_DIR": str(stub_dir),
           "SOS_KIOSK_PROFILE": str(profile), "SOS_KIOSK_CONFIG": str(tmp_path / "absent.env"),
           "HOME": str(tmp_path / "home"), "SOS_KIOSK_MIN_UPTIME_MS": "250", "SOS_KIOSK_BACKOFF_MS": "60",
           "SOS_KIOSK_BACKOFF_MAX_MS": "240", "SOS_KIOSK_RESTART_MS": "30", "SOS_KIOSK_QUICK_DEATHS": "5"}
    env.pop("SOS_KIOSK_PREFS", None)

    class Kiosk:
        pass

    k = Kiosk()
    k.env, k.stub, k.profile = env, stub_dir, profile
    k.run = lambda mode, timeout=20: subprocess.run(["bash", str(WRAPPER)], env={**env, "STUB_MODE": mode},
                                                    capture_output=True, text=True, timeout=timeout)
    k.count = lambda: int((stub_dir / "count").read_text())
    return k


def write_prefs(profile: Path, text: str) -> Path:
    prefs = profile / "Default" / "Preferences"
    prefs.parent.mkdir(parents=True, exist_ok=True)
    prefs.write_text(text)
    return prefs


def test_chromium_starts_with_the_flags_an_unattended_kiosk_needs(kiosk):
    kiosk.run("die")
    args = (kiosk.stub / "args-1").read_text().splitlines()
    for flag in ("--kiosk", "--noerrdialogs", "--no-first-run", "--disable-session-crashed-bubble",
                 "--hide-crash-restore-bubble", "--disable-infobars", "--no-default-browser-check",
                 "--password-store=basic", f"--user-data-dir={kiosk.profile}", "--overscroll-history-navigation=0",
                 "--ozone-platform=wayland"):
        assert flag in args, flag
    assert args[-1] == "http://localhost/starting"


def test_the_profile_is_put_right_before_every_start(kiosk):
    """After a crash or a power cut: Preferences says the last run crashed, and a lock names a dead pid."""
    write_prefs(kiosk.profile, json.dumps({"profile": {"exit_type": "Crashed", "exited_cleanly": False, "name": "x"}, "a": 1}))
    os.symlink("somehost-1", kiosk.profile / "SingletonLock")
    os.symlink("/tmp/.org.chromium.Chromium.gone/SingletonSocket", kiosk.profile / "SingletonSocket")
    kiosk.run("die")
    assert (kiosk.stub / "lock-1").read_text().strip() == "absent"
    seen = json.loads((kiosk.stub / "prefs-1").read_text())
    assert seen == {"profile": {"exit_type": "Normal", "exited_cleanly": True, "name": "x"}, "a": 1}
    assert not (kiosk.profile / "SingletonSocket").is_symlink()


def test_a_preferences_file_torn_by_a_power_cut_is_moved_aside(kiosk):
    prefs = write_prefs(kiosk.profile, '{"profile": {"exit_type": "Cra')
    proc = kiosk.run("die")
    assert not (kiosk.stub / "prefs-1").exists(), "Chromium must start with no damaged Preferences to trip over"
    assert Path(str(prefs) + ".corrupt").read_text().startswith('{"profile"')
    assert "damaged" in proc.stderr


def test_the_old_default_profile_is_adopted_once(kiosk):
    old = Path(kiosk.env["HOME"]) / ".config" / "chromium" / "Default"
    old.mkdir(parents=True)
    (old / "marker").write_text("mine")
    kiosk.run("die")
    assert (kiosk.profile / "Default" / "marker").read_text() == "mine"


def test_a_crash_loop_backs_off_then_leaves_it_to_systemd(kiosk):
    started = time.monotonic()
    proc = kiosk.run("die")
    took = time.monotonic() - started
    assert proc.returncode == 1 and kiosk.count() == 5, proc.stderr
    times = [float(t.replace(",", ".")) for t in (kiosk.stub / "times").read_text().split()]
    gaps = [b - a for a, b in zip(times, times[1:])]
    assert len(gaps) == 4
    assert gaps[0] >= 0.05 and gaps[1] >= 0.11 and gaps[2] >= 0.22 and gaps[3] >= 0.22, gaps  # 60, 120, 240, 240 ms
    assert took < 5
    assert "leaving it to systemd" in proc.stderr


def test_a_long_run_resets_the_backoff_and_restarts_quickly(kiosk):
    proc = kiosk.run("long_then_stop")
    assert proc.returncode == 0, proc.stderr
    assert kiosk.count() == 2
    times = [float(t.replace(",", ".")) for t in (kiosk.stub / "times").read_text().split()]
    assert times[1] - times[0] < 1.2, "a browser that ran fine restarts almost at once, not after a backoff"


def test_sigterm_stops_chromium_and_the_wrapper_promptly(kiosk):
    proc = subprocess.Popen(["bash", str(WRAPPER)], env={**kiosk.env, "STUB_MODE": "live"},
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        if (kiosk.stub / "pid").exists():
            break
        time.sleep(0.05)
    pid = int((kiosk.stub / "pid").read_text())
    proc.send_signal(signal.SIGTERM)
    assert proc.wait(timeout=5) == 0
    time.sleep(0.2)
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
