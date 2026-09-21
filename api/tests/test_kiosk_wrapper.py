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
  stubborn) echo $$ > "$d/pid"; trap '' TERM; while true; do sleep 0.1; done ;;
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


# --- the hung-page watchdog -------------------------------------------------------------------------------------
# The page posts a heartbeat; the API reports its age; the wrapper kills a Chromium whose page has gone quiet, but
# only one whose page has spoken since that Chromium started, and never because the API could not be asked.

import http.server
import json
import threading


class AliveAge:
    """A stand-in for GET /api/kiosk/alive-age whose answer the test sets."""

    def __init__(self):
        self.age_s: float | None = None
        self.api_up_s: float = 10.0
        self.hits = 0
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                outer.hits += 1
                body = json.dumps({"age_s": outer.age_s, "api_up_s": outer.api_up_s}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/api/kiosk/alive-age"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def watched(kiosk):
    alive = AliveAge()
    kiosk.env.update({"SOS_KIOSK_ALIVE_URL": alive.url, "SOS_KIOSK_ALIVE_POLL_MS": "100", "SOS_KIOSK_STALL_MS": "1200",
                      "SOS_KIOSK_KILL_GRACE_MS": "300", "SOS_KIOSK_MIN_UPTIME_MS": "100000"})
    kiosk.alive = alive
    procs = []

    def start(mode: str):
        proc = subprocess.Popen(["bash", str(WRAPPER)], env={**kiosk.env, "STUB_MODE": mode}, stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, text=True)
        procs.append(proc)
        return proc

    def wait_count(n: int, timeout: float = 10.0) -> bool:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if (kiosk.stub / "count").exists() and kiosk.count() >= n:
                return True
            time.sleep(0.05)
        return False

    kiosk.start, kiosk.wait_count = start, wait_count
    yield kiosk
    for proc in procs:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(5)
            except subprocess.TimeoutExpired:
                proc.kill()
    try:
        alive.stop()
    except Exception:
        pass


def test_a_page_that_spoke_and_then_went_quiet_gets_its_chromium_restarted(watched):
    proc = watched.start("live")
    assert watched.wait_count(1)
    time.sleep(0.4)
    watched.alive.age_s = 0.1          # the page has spoken since this Chromium started
    time.sleep(0.5)
    assert watched.count() == 1
    watched.alive.age_s = 30.0         # ...and now it has been quiet far longer than the limit
    assert watched.wait_count(2), "a hung page must get its Chromium killed and started again"
    assert proc.poll() is None, "the wrapper itself carries on"
    proc.send_signal(signal.SIGTERM)
    assert "has not answered" in proc.communicate(timeout=5)[1]


def test_a_new_chromium_is_not_killed_for_the_quiet_of_the_one_before_it(watched):
    """After the kill the API still says 30 s: that is the old page. The new Chromium has not been heard from, so it
    is given all the time a slow boot needs."""
    watched.start("live")
    assert watched.wait_count(1)
    time.sleep(0.4)
    watched.alive.age_s = 0.1
    time.sleep(0.4)
    watched.alive.age_s = 30.0
    assert watched.wait_count(2)
    time.sleep(2.5)                    # twice the stall limit
    assert watched.count() == 2


def test_a_page_never_heard_from_is_never_killed_however_slow_the_boot(watched):
    watched.alive.age_s = None
    watched.alive.api_up_s = 9999.0    # the API has been up for ages and has never heard the kiosk
    watched.start("live")
    assert watched.wait_count(1)
    time.sleep(3.0)
    assert watched.count() == 1
    assert watched.alive.hits >= 5, "it should have been asking"


def test_a_stopped_api_never_causes_a_kill(watched):
    watched.start("live")
    assert watched.wait_count(1)
    time.sleep(0.4)
    watched.alive.age_s = 0.1
    time.sleep(0.4)
    watched.alive.stop()               # the API goes away: no answer, so no news
    time.sleep(3.0)
    assert watched.count() == 1


def test_a_restarted_api_that_has_heard_nothing_for_longer_than_the_limit_counts_as_a_quiet_page(watched):
    watched.start("live")
    assert watched.wait_count(1)
    time.sleep(0.4)
    watched.alive.age_s = 0.1
    time.sleep(0.4)
    watched.alive.age_s = None         # the API restarted and forgot...
    watched.alive.api_up_s = 0.5       # ...but is younger than the stall limit: nothing to conclude yet
    time.sleep(2.0)
    assert watched.count() == 1
    watched.alive.api_up_s = 60.0      # a minute of API uptime (limit here: 1.2 s) and not a word from a page that had been talking
    assert watched.wait_count(2)


def test_a_chromium_that_ignores_sigterm_is_killed_after_the_grace_period(watched):
    watched.start("stubborn")
    assert watched.wait_count(1)
    time.sleep(0.4)
    watched.alive.age_s = 0.1
    time.sleep(0.4)
    watched.alive.age_s = 30.0
    assert watched.wait_count(2, timeout=15), "SIGTERM was ignored; the wrapper must escalate to SIGKILL"
