"""install/ and dev/ stay valid (spec section 14, "Install"): shellcheck, the dry-run golden, the unit
files against spec section 5, `systemd-analyze verify`, `caddy validate`, and a live Caddy on ephemeral
ports answering the probe paths, range requests and the SPA fallback exactly as the spec says."""
from __future__ import annotations

import configparser
import http.server
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
INSTALL = REPO / "install"
DEV = REPO / "dev"
SCRIPTS = [INSTALL / "install.sh", DEV / "run-dev.sh", DEV / "smoke.sh", DEV / "smoke-selftest.sh",
           INSTALL / "kiosk" / "sos-kiosk-app"]
UNIT_NAMES = ["caddy.service", "kiwix-serve.service", "sos-api.service", "sos-llama.service", "sos-kiosk.service",
              "srv-sos-extended.mount", "sos-extended-rescan.service", "sos-embed.service"]
UNITS = [INSTALL / "systemd" / name for name in UNIT_NAMES]
PROBES = ["/generate_204", "/gen_204", "/hotspot-detect.html", "/library/test/success.html", "/connecttest.txt",
          "/ncsi.txt", "/canonical.html", "/success.txt"]
GOLDEN = REPO / "api" / "tests" / "golden" / "install-dry-run.txt"
GOLDEN_ENV = {"SOS_ARCH": "aarch64", "SOS_WEB_DIST": "/nonexistent/web/dist"}
CADDYFILE = INSTALL / "caddy" / "Caddyfile"


def shellcheck_bin() -> str | None:
    """shellcheck-py (a dev dependency) drops the binary next to the venv's python."""
    beside_python = Path(sys.executable).with_name("shellcheck")
    return str(beside_python) if beside_python.exists() else shutil.which("shellcheck")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def dry_run(*flags: str, env: dict | None = None) -> str:
    proc = subprocess.run(["bash", str(INSTALL / "install.sh"), "--dry-run", *flags], capture_output=True, text=True,
                          env={**os.environ, **GOLDEN_ENV, **(env or {})}, cwd=REPO)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def unit(name: str) -> str:
    return (INSTALL / "systemd" / name).read_text(encoding="utf-8")


# --- scripts -----------------------------------------------------------------------------------------

def test_scripts_have_bash_shebang_and_exec_bit():
    for script in SCRIPTS:
        assert script.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash\n"), script
        assert os.access(script, os.X_OK), f"{script} is not executable (git update-index --chmod=+x)"


@pytest.mark.skipif(shellcheck_bin() is None, reason="shellcheck not installed (pip install shellcheck-py)")
def test_shellcheck_clean():
    proc = subprocess.run([shellcheck_bin(), "--shell=bash", "--severity=style", *map(str, SCRIPTS)],
                          capture_output=True, text=True, cwd=REPO)
    assert proc.returncode == 0, proc.stdout


# --- install.sh --------------------------------------------------------------------------------------

def test_dry_run_matches_golden():
    out = dry_run()
    assert out == GOLDEN.read_text(encoding="utf-8"), (
        "install.sh --dry-run output changed; if that is intended, refresh the golden with:\n"
        "  SOS_ARCH=aarch64 SOS_WEB_DIST=/nonexistent/web/dist bash install/install.sh --dry-run "
        "> api/tests/golden/install-dry-run.txt")


def test_dry_run_flags_and_arch():
    base = dry_run()
    assert base.startswith("install.sh --dry-run: arch aarch64, dev 0, skip-llama 0, with-jellyfin 0, pcie-gen3 0\n")
    assert "kiwix-tools_linux-aarch64-3.8.2.tar.gz" in base and "caddy_2.11.4_linux_arm64.tar.gz" in base
    assert "step llama: would clone https://github.com/ggml-org/llama.cpp at v0.3.0" in base
    assert "-DGGML_NATIVE=ON -DGGML_CPU_KLEIDIAI=ON -DLLAMA_BUILD_TESTS=OFF" in base
    assert "install/placeholder -> /srv/sos/web (web/dist absent, placeholder used)" in base
    assert "step jellyfin" not in base and "pciex1_gen=3" not in base
    assert base.rstrip().endswith("dry run complete: nothing was written")
    dev = dry_run("--dev")
    for step in ("hotspot", "mount", "backlight", "kiosk", "boot"):
        assert f"step {step}: skipped (--dev)" in dev, step
    # sos-kiosk.service is still installed unconditionally by step_units (harmless under --dev, since
    # step_enable does not enable it there); the mount units are skipped entirely under --dev.
    assert "write /etc/systemd/system/sos-kiosk.service" in dev
    assert "srv-sos-extended.mount" not in dev
    enable_line = next(line for line in dev.splitlines() if line.startswith("step enable:"))
    assert "sos-kiosk.service" not in enable_line
    assert "step llama: skipped (--skip-llama)" in dry_run("--skip-llama")
    assert "step jellyfin: would add https://repo.jellyfin.org/debian" in dry_run("--with-jellyfin")
    assert "with dtparam=pciex1_gen=3 enabled (--pcie-gen3)" in dry_run("--pcie-gen3")
    x86 = dry_run(env={"SOS_ARCH": "x86_64"})
    assert "kiwix-tools_linux-x86_64-3.8.2.tar.gz" in x86 and "caddy_2.11.4_linux_amd64.tar.gz" in x86


def test_apt_installs_everything_pip_needs_to_compile_a_wheel_less_dependency():
    """hnswlib (api/pyproject.toml, the household index) publishes no wheels: pip compiles it from its
    C++ sources during step_venv's `pip install -e`, which needs a compiler, cmake AND Python.h. Without
    python3-dev a clean Raspberry Pi install fails at the venv step with "Python.h: No such file or
    directory" -- measured on a real box -- so the apt step, not the person installing, has to supply it."""
    apt_line = next(line for line in dry_run().splitlines() if line.startswith("step apt:"))
    for package in ("build-essential", "cmake", "python3-dev"):
        assert f" {package}" in apt_line, f"{package} is missing from APT_PACKAGES"


def test_dry_run_installs_every_unit_file():
    """Every unit under install/systemd/ (UNIT_NAMES) must actually be copied into $UNIT_DIR by some step
    before step_enable ever runs, in a real (non---dev) install -- a unit file that only exists in the repo
    but is never installed makes `systemctl enable` fail non-zero under `set -euo pipefail`."""
    out = dry_run()
    units_line_index = out.index("step units:")
    enable_line_index = out.index("step enable:")
    for name in UNIT_NAMES:
        assert f"write /etc/systemd/system/{name}" in out, f"{name} is never installed by install.sh"
        # and it must be installed before step_enable tries to enable it
        assert out.index(f"write /etc/systemd/system/{name}") < enable_line_index, name
    assert units_line_index < enable_line_index


def test_install_sh_rejects_bad_option_and_non_root():
    proc = subprocess.run(["bash", str(INSTALL / "install.sh"), "--dry-run", "--bogus"], capture_output=True,
                          text=True, cwd=REPO, env={**os.environ, **GOLDEN_ENV})
    assert proc.returncode == 2 and "unknown option" in proc.stderr
    if os.geteuid() != 0:  # never attempt a real install from the test suite
        proc = subprocess.run(["bash", str(INSTALL / "install.sh")], capture_output=True, text=True, cwd=REPO,
                              env={**os.environ, **GOLDEN_ENV})
        assert proc.returncode == 1 and "run as root" in proc.stderr


def test_versions_env_pins():
    pins = {}
    for line in (INSTALL / "versions.env").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            pins[key] = value
    assert pins["KIWIX_TOOLS"] == "3.8.2" and pins["CADDY"] == "2.11.4"
    assert pins["LLAMA_CPP_TAG"] == "v0.3.0" and pins["LLAMA_CPP_COMMIT"] == "c1d0e7a004015f23bc0233470b747b596f29b264"
    assert pins["PROTOMAPS_BUILD"] == "20260902" and pins["JELLYFIN"] == "10.11.11"


# --- systemd units -----------------------------------------------------------------------------------

def test_units_match_spec_section_5():
    assert sorted(p.name for p in (INSTALL / "systemd").iterdir()) == sorted(UNIT_NAMES)
    kiwix = unit("kiwix-serve.service")
    assert ("ExecStart=/usr/local/bin/kiwix-serve --library /srv/sos/state/library.xml --monitorLibrary --address all "
            "--port 8090 --urlRootLocation /kiwix --nosearchbar --nolibrarybutton --blockexternal") in kiwix
    assert "Restart=always" in kiwix and "RestartSec=2" in kiwix and "User=sos" in kiwix
    llama = unit("sos-llama.service")
    assert ("ExecStart=/usr/local/bin/llama-server -m /srv/sos/core/models/${SOS_MODEL} --host 127.0.0.1 --port 8081 "
            "-c 4096 -t 4 -ngl 0 -fa on -np 1 --no-webui --reasoning off") in llama
    for line in ("EnvironmentFile=/srv/sos/state/config/ai.env", "Nice=10", "CPUWeight=30", "IOWeight=50",
                 "MemoryMax=4500M", "OOMScoreAdjust=500", "User=sos"):
        assert line in llama, line
    assert "ExecStartPre=+" in llama and "performance" in llama
    assert "ExecStopPost=+" in llama and "ondemand" in llama
    assert not re.search(r"^\[Install\]$", llama, re.M)  # off by default: sos-api starts and stops it
    kiosk = unit("sos-kiosk.service")
    for line in ("ExecStart=/usr/bin/cage -- /usr/local/bin/sos-kiosk-app", "PAMName=login", "TTYPath=/dev/tty1",
                 "Conflicts=getty@tty1.service", "User=sos", "Restart=always", "RestartSec=3",
                 "WantedBy=graphical.target", "ExecStartPre=/usr/local/bin/sos-kiosk-app --wait-for-api"):
        assert line in kiosk, line
    assert "After=systemd-user-sessions.service" in kiosk
    api = unit("sos-api.service")
    assert "ExecStart=/srv/sos/api/.venv/bin/uvicorn sos.main:app --host 127.0.0.1 --port 8000" in api
    assert "--proxy-headers --forwarded-allow-ips 127.0.0.1" in api and "User=sos" in api
    caddy = unit("caddy.service")
    assert "ExecStart=/usr/local/bin/caddy run --config /etc/caddy/Caddyfile" in caddy
    assert "AmbientCapabilities=CAP_NET_BIND_SERVICE" in caddy and "User=sos" in caddy
    mount = unit("srv-sos-extended.mount")
    for line in ("What=/dev/disk/by-label/SOS-EXT", "Where=/srv/sos/extended", "Type=ext4", "Options=noatime",
                 "BindsTo=dev-disk-by\\x2dlabel-SOS\\x2dEXT.device", "WantedBy=dev-disk-by\\x2dlabel-SOS\\x2dEXT.device"):
        assert line in mount, line
    rescan = unit("sos-extended-rescan.service")
    for line in ("Type=oneshot", "RemainAfterExit=yes", "ExecStart=/srv/sos/api/.venv/bin/sos storage-event add",
                 "ExecStop=/srv/sos/api/.venv/bin/sos storage-event remove", "BindsTo=srv-sos-extended.mount",
                 "After=srv-sos-extended.mount sos-api.service", "WantedBy=srv-sos-extended.mount"):
        assert line in rescan, line


def unit_sections(name: str) -> dict[str, dict[str, list[str]]]:
    """A unit file as {section: {key: [values]}}: systemd keys may repeat, so nothing is squashed."""
    sections: dict[str, dict[str, list[str]]] = {}
    current = None
    for raw in unit(name).splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = sections.setdefault(line[1:-1], {})
        elif current is not None and "=" in line:
            key, value = line.split("=", 1)
            current.setdefault(key.strip(), []).append(value.strip())
    return sections


CORE_UNITS = ["caddy.service", "sos-api.service", "kiwix-serve.service", "sos-embed.service", "sos-kiosk.service"]


@pytest.mark.parametrize("name", CORE_UNITS)
def test_core_units_keep_retrying_forever(name):
    """An unattended box has nobody to `systemctl reset-failed`. Restart=on-failure is not enough: it does not
    restart after SIGTERM (an out-of-memory daemon, a stray `kill`), measured with a real user unit, and
    systemd's default start limit (5 starts in 10 s) parks a unit in `failed` for good after a burst of
    restarts. So: Restart=always and no start limit, in [Unit] where systemd reads StartLimitIntervalSec."""
    sections = unit_sections(name)
    assert sections["Service"]["Restart"] == ["always"], name
    assert sections["Unit"]["StartLimitIntervalSec"] == ["0"], name
    assert "StartLimitIntervalSec" not in sections["Service"], "systemd only reads it from [Unit]"
    assert int(sections["Service"]["RestartSec"][0]) <= 5, name


@pytest.mark.parametrize("name", CORE_UNITS)
def test_core_units_back_off_in_a_crash_loop_but_stay_quick_for_one_crash(name):
    """A flat RestartSec=2 meant a broken sos-api restarted every three seconds for ever, about a third of a
    core. RestartSec is now only the first delay: RestartSteps grows it exponentially to RestartMaxDelaySec (systemd
    254 and later; Trixie has 257), so a loop settles at 20 to 30 s (about 4 per cent of a core). The steps are never
    reset by a healthy run (measured with a real unit), so the ceiling stays low.
    StartLimitIntervalSec=0 stays, so it never gives up."""
    service = unit_sections(name)["Service"]
    assert int(service["RestartSec"][0]) <= 5, name
    assert 3 <= int(service["RestartSteps"][0]) <= 10, name
    assert 15 <= int(service["RestartMaxDelaySec"][0].rstrip("s")) <= 60, name   # systemd never resets the steps after a healthy run, so this is also the wait after a lone crash
    assert unit_sections(name)["Unit"]["StartLimitIntervalSec"] == ["0"], name


def test_sos_llama_stays_off_unless_asked():
    sections = unit_sections("sos-llama.service")
    assert sections["Service"]["Restart"] == ["no"]
    assert "StartLimitIntervalSec" not in sections["Unit"]
    assert "Install" not in sections


def test_service_graph_survives_a_restart_of_any_one_service():
    """A restarted sos-api must not take Caddy or the kiosk browser with it, and none of them may be left
    waiting for a service that is not there: Wants= and After= only, never Requires=, BindsTo= or PartOf= among
    the long-running units (those propagate a stop or restart to the dependent)."""
    strong = ("Requires", "Requisite", "BindsTo", "PartOf", "Upholds")
    for name in CORE_UNITS + ["sos-llama.service"]:
        unit_section = unit_sections(name)["Unit"]
        for key in strong:
            assert key not in unit_section, f"{name} has {key}=: a restart would propagate"
    kiosk = unit_sections("sos-kiosk.service")["Unit"]
    assert set(" ".join(kiosk["Wants"]).split()) >= {"caddy.service", "sos-api.service"}
    assert set(" ".join(kiosk["After"]).split()) >= {"caddy.service", "sos-api.service"}
    assert "sos-api.service" in " ".join(unit_sections("caddy.service")["Unit"]["After"])
    assert "kiwix-serve.service" in " ".join(unit_sections("sos-api.service")["Unit"]["Wants"])


def test_sos_api_is_killed_quickly_when_a_stream_holds_shutdown_open():
    """uvicorn waits for open connections (an assistant stream) before it exits; without a bound the restart
    waits out systemd's 90 s stop timeout with the whole box answering nothing."""
    sections = unit_sections("sos-api.service")["Service"]
    assert "--timeout-graceful-shutdown" in sections["ExecStart"][0]
    assert int(sections["TimeoutStopSec"][0].rstrip("s")) <= 15


@pytest.mark.skipif(shutil.which("systemd-analyze") is None, reason="systemd-analyze not available")
def test_systemd_analyze_verify():
    proc = subprocess.run(["systemd-analyze", "verify", "--recursive-errors=no", *map(str, UNITS)],
                          capture_output=True, text=True)
    # The binaries the units start live on the box, not on the PC: only that message is tolerated.
    problems = [line for line in (proc.stdout + proc.stderr).splitlines()
                if line.strip() and "is not executable" not in line]
    assert problems == [], problems


# --- NetworkManager, udev, sudoers, kiosk, boot, placeholder --------------------------------------------

def test_networkmanager_profiles_and_dnsmasq():
    expectations = {
        "sos-hotspot": {("connection", "type"): "wifi", ("connection", "interface-name"): "wlan0",
                        ("connection", "autoconnect"): "true", ("wifi", "mode"): "ap", ("wifi", "ssid"): "SOS",
                        ("ipv4", "method"): "shared", ("ipv4", "address1"): "10.42.0.1/24"},
        "sos-eth-client": {("connection", "type"): "ethernet", ("connection", "interface-name"): "eth0",
                           ("connection", "autoconnect"): "true", ("ipv4", "method"): "auto"},
        "sos-eth-direct": {("connection", "type"): "ethernet", ("connection", "interface-name"): "eth0",
                           ("connection", "autoconnect"): "false", ("ipv4", "method"): "shared",
                           ("ipv4", "address1"): "10.43.0.1/24"},
    }
    uuids = set()
    for name, expect in expectations.items():
        cp = configparser.ConfigParser(interpolation=None)
        cp.read(INSTALL / "nm" / f"{name}.nmconnection")
        assert cp["connection"]["id"] == name
        uuids.add(cp["connection"]["uuid"])
        for (section, key), value in expect.items():
            assert cp[section][key] == value, (name, section, key)
    assert len(uuids) == 3
    assert "[wifi-security]" not in (INSTALL / "nm" / "sos-hotspot.nmconnection").read_text(encoding="utf-8")
    conf = (INSTALL / "nm" / "dnsmasq-shared.d" / "sos.conf").read_text(encoding="utf-8")
    assert [line for line in conf.splitlines() if line and not line.startswith("#")] == ["address=/#/10.42.0.1"]


def test_udev_sudoers_boot_and_placeholder_files():
    rule = (INSTALL / "udev" / "90-sos-backlight.rules").read_text(encoding="utf-8")
    assert 'SUBSYSTEM=="backlight"' in rule and 'ACTION=="add"' in rule
    assert "chgrp video" in rule and "chmod g+w" in rule and "brightness" in rule
    sudoers = (INSTALL / "sudoers" / "sos").read_text(encoding="utf-8")
    for cmd in ("/usr/bin/systemctl start sos-llama.service", "/usr/bin/systemctl stop sos-llama.service",
                "/usr/bin/nmcli con modify sos-hotspot *", "/usr/bin/nmcli con up sos-hotspot",
                "/usr/bin/nmcli con modify sos-eth-client connection.autoconnect *",
                "/usr/bin/nmcli con modify sos-eth-direct connection.autoconnect *",
                "/usr/bin/nmcli con up sos-eth-client", "/usr/bin/nmcli con up sos-eth-direct",
                "/usr/bin/umount -l /srv/sos/extended"):
        assert cmd in sudoers, cmd
    assert "sos ALL=(root) NOPASSWD:" in sudoers and "systemctl start sos-api" not in sudoers
    if shutil.which("visudo"):
        proc = subprocess.run(["visudo", "-cf", str(INSTALL / "sudoers" / "sos")], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stdout + proc.stderr
    boot = (INSTALL / "boot" / "config.txt.d" / "sos.txt").read_text(encoding="utf-8")
    assert "\ndtparam=pciex1\n" in boot and "\n#dtparam=pciex1_gen=3\n" in boot
    welcome = (INSTALL / "placeholder" / "welcome.html").read_text(encoding="utf-8")
    assert len(welcome.encode("utf-8")) < 20 * 1024 and "<script" not in welcome
    assert welcome.index("http://10.42.0.1") < welcome.index("http://sos.box")
    assert "turn mobile data off" in welcome and "Tap Done or Cancel" in welcome
    starting = (INSTALL / "placeholder" / "starting.html").read_text(encoding="utf-8")
    assert "/api/status" in starting and "/?kiosk=1" in starting
    assert "Operation SOS" in (INSTALL / "placeholder" / "index.html").read_text(encoding="utf-8")
    example = (INSTALL / "answers.env.example").read_text(encoding="utf-8")
    assert "SOS_PIN=" in example and "SOS_SSID=SOS" in example and "SOS_PASSPHRASE=" in example


def test_kiosk_wrapper_text():
    kiosk = (INSTALL / "kiosk" / "sos-kiosk-app").read_text(encoding="utf-8")
    assert "wlr-randr --output" in kiosk and "--transform" in kiosk
    assert "chromium --kiosk --ozone-platform=wayland --force-device-scale-factor=1.5 --noerrdialogs --no-first-run" in kiosk
    assert "--overscroll-history-navigation=0" in kiosk and "http://localhost/starting" in kiosk
    assert '"exit_type": "Normal", "exited_cleanly": True' in kiosk and "python3" in kiosk


# --- live pieces: the kiosk wrapper's modes and Caddy ----------------------------------------------------

class _Upstream(http.server.BaseHTTPRequestHandler):
    """Echoes the request path and the two headers Caddy must handle correctly."""
    seen: list[dict] = []

    def do_GET(self):
        _Upstream.seen.append({"path": self.path, "xff": self.headers.get("X-Forwarded-For"), "host": self.headers.get("Host")})
        body = f"upstream saw {self.path}".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def upstream():
    _Upstream.seen = []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Upstream)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_kiosk_wrapper_modes(tmp_path, upstream):
    prefs = tmp_path / "Preferences"
    prefs.write_text('{"profile": {"exit_type": "Crashed", "exited_cleanly": false, "name": "x"}, "other": 1}')
    env = {**os.environ, "SOS_KIOSK_PREFS": str(prefs), "SOS_KIOSK_PROFILE": str(tmp_path / "profile"), "SOS_KIOSK_CONFIG": str(tmp_path / "absent.env"),
           "SOS_KIOSK_API": f"http://{upstream}/api/status"}
    wrapper = str(INSTALL / "kiosk" / "sos-kiosk-app")
    proc = subprocess.run(["bash", wrapper, "--reset-prefs"], env=env, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    data = json.loads(prefs.read_text())
    assert data == {"profile": {"exit_type": "Normal", "exited_cleanly": True, "name": "x"}, "other": 1}
    started = time.monotonic()
    proc = subprocess.run(["bash", wrapper, "--wait-for-api"], env=env, capture_output=True, text=True)
    assert proc.returncode == 0 and "sos-api ready after 1s" in proc.stdout and time.monotonic() - started < 10
    assert subprocess.run(["bash", wrapper, "--bogus"], env=env, capture_output=True).returncode == 2


def caddy_env(port: int, admin: int, roots: dict[str, Path], upstream: str) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("SOS_")}
    env.update({"SOS_HTTP_PORT": str(port), "SOS_WEB_ROOT": str(roots["web"]), "SOS_MAPS_ROOT": str(roots["maps"]),
                "SOS_DOCS_CORE": str(roots["docs_core"]), "SOS_DOCS_EXT": str(roots["docs_ext"]),
                "SOS_API_UPSTREAM": upstream, "SOS_KIWIX_UPSTREAM": upstream, "CADDY_ADMIN": f"localhost:{admin}"})
    return env


@pytest.mark.skipif(shutil.which("caddy") is None, reason="caddy not installed")
def test_caddy_validate_with_defaults_and_with_overrides(tmp_path):
    cmd = ["caddy", "validate", "--config", str(CADDYFILE), "--adapter", "caddyfile"]
    plain = {k: v for k, v in os.environ.items() if not k.startswith("SOS_")}
    proc = subprocess.run(cmd, capture_output=True, text=True, env=plain)
    assert proc.returncode == 0, proc.stderr
    roots = {"web": tmp_path, "maps": tmp_path, "docs_core": tmp_path, "docs_ext": tmp_path}
    proc = subprocess.run(cmd, capture_output=True, text=True, env=caddy_env(8080, 2019, roots, "127.0.0.1:8000"))
    assert proc.returncode == 0, proc.stderr


@pytest.fixture
def caddy(tmp_path, upstream):
    if shutil.which("caddy") is None:
        pytest.skip("caddy not installed")
    roots = {"web": tmp_path / "web", "maps": tmp_path / "maps", "docs_core": tmp_path / "core-docs",
             "docs_ext": tmp_path / "ext-docs"}
    (roots["web"] / "assets").mkdir(parents=True)
    for r in ("maps", "docs_core", "docs_ext"):
        roots[r].mkdir()
    (roots["web"] / "index.html").write_text("<!doctype html><title>SOS app</title>")
    shutil.copy(INSTALL / "placeholder" / "welcome.html", roots["web"] / "welcome.html")
    shutil.copy(INSTALL / "placeholder" / "starting.html", roots["web"] / "starting.html")
    (roots["web"] / "assets" / "index-abc123.js").write_text("console.log('sos')")
    (roots["maps"] / "test.pmtiles").write_bytes(bytes(range(256)) * 4)
    (roots["docs_core"] / "a.pdf").write_bytes(b"%PDF-1.4 core")
    (roots["docs_ext"] / "b.pdf").write_bytes(b"%PDF-1.4 ext")
    port = free_port()
    proc = subprocess.Popen(["caddy", "run", "--config", str(CADDYFILE), "--adapter", "caddyfile"],
                            env=caddy_env(port, free_port(), roots, upstream), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(base + "/welcome", timeout=1)
                break
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.1)
        else:
            proc.terminate()
            pytest.fail("caddy did not start: " + proc.stderr.read())
        yield base
    finally:
        proc.terminate()
        proc.wait(5)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def get(url: str, headers: dict | None = None) -> tuple[int, dict, bytes]:
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.build_opener(_NoRedirect).open(request, timeout=5) as response:
            return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read()
    except urllib.error.HTTPError as err:
        return err.code, {k.lower(): v for k, v in err.headers.items()}, err.read()


def test_caddy_probe_paths_redirect_to_welcome(caddy):
    for path in PROBES:
        status, headers, _ = get(caddy + path)
        assert (status, headers.get("location")) == (302, "http://10.42.0.1/welcome"), path


def test_caddy_welcome_and_starting_are_static(caddy):
    status, headers, body = get(caddy + "/welcome")
    assert status == 200 and "http://10.42.0.1" in body.decode() and headers["cache-control"] == "no-cache"
    assert headers["content-type"].startswith("text/html")
    status, _, body = get(caddy + "/starting")
    assert status == 200 and b"/api/status" in body


def test_caddy_spa_fallback_and_cache_headers(caddy):
    status, headers, body = get(caddy + "/s/nuclear-war")
    assert status == 200 and b"SOS app" in body and headers["cache-control"] == "no-cache"
    status, headers, _ = get(caddy + "/index.html")
    assert status == 200 and headers["cache-control"] == "no-cache"
    status, headers, _ = get(caddy + "/assets/index-abc123.js")
    assert status == 200 and headers["cache-control"] == "public, max-age=31536000, immutable"
    assert get(caddy + "/assets/missing.js")[0] == 404


def test_caddy_maps_range_requests_without_compression(caddy):
    status, headers, body = get(caddy + "/maps/test.pmtiles", {"Range": "bytes=10-19", "Accept-Encoding": "gzip"})
    assert status == 206 and body == bytes(range(10, 20)) and headers["content-range"] == "bytes 10-19/1024"
    assert "content-encoding" not in headers and headers["cache-control"] == "no-cache"
    assert get(caddy + "/maps/nope.pmtiles")[0] == 404


def test_caddy_docs_roots(caddy):
    assert get(caddy + "/docs/core/a.pdf")[2] == b"%PDF-1.4 core"
    assert get(caddy + "/docs/extended/b.pdf")[2] == b"%PDF-1.4 ext"
    assert get(caddy + "/docs/core/b.pdf")[0] == 404


def test_caddy_proxies_keep_paths_and_fix_forwarded_headers(caddy):
    status, _, body = get(caddy + "/api/status", {"X-Forwarded-For": "1.2.3.4"})
    assert status == 200 and body == b"upstream saw /api/status"
    _, _, body = get(caddy + "/kiwix/content/wikipedia_en_100_mini_2026-01/Precipitation", {"Host": "sos.box"})
    assert body == b"upstream saw /kiwix/content/wikipedia_en_100_mini_2026-01/Precipitation"
    api_hit = next(h for h in _Upstream.seen if h["path"] == "/api/status")
    assert api_hit["xff"] == "127.0.0.1"  # a spoofed header is replaced, so require_localhost stays honest
    kiwix_hit = next(h for h in _Upstream.seen if h["path"].startswith("/kiwix/"))
    assert kiwix_hit["host"] == "sos.box"  # Host passes through, so kiwix-serve redirects to the typed address


# --- install.sh after an interrupted run ------------------------------------------------------------------
# "A second run reports unchanged" must not mean "a second run trusts what a first run left half done". Each
# test sources install.sh (its steps only run from main), points PREFIX at a scratch tree and stubs the
# things that need root, the network or a build, then plays a first run that dies and a second that must
# finish the job.

def run_install_steps(tmp_path: Path, body: str, *, expect_ok: bool = True, with_tree: bool = True) -> subprocess.CompletedProcess:
    log = tmp_path / "calls.log"
    if with_tree:
        (tmp_path / "srv" / "api").mkdir(parents=True, exist_ok=True)   # step_tree makes it in a real run
    script = f"""
set -euo pipefail
source {INSTALL / 'install.sh'}
PREFIX={tmp_path}/srv; BUILD_DIR=$PREFIX/build; UNIT_DIR={tmp_path}/units; SCRIPT_DIR={INSTALL}
SOS_USER=$(id -un); LOG={log}
say() {{ printf 'step %s: %s\\n' "$1" "$2"; }}
systemctl() {{ echo "systemctl $*" >> "$LOG"; }}
# the real sync_tree (its rsync options are what is under test); only its --chown needs a group named like the user
getent group "$SOS_USER" >/dev/null || sync_tree() {{ local out; out=$("${{RSYNC_TREE[@]}}" "$1/" "$2/") || {{ echo "install.sh: rsync of $1 to $2 failed" >&2; exit 1; }}; [ -n "$out" ]; }}
ldconfig() {{ :; }}
cmake() {{ echo "cmake $*" >> "$LOG"; }}
git() {{
  case "$*" in
    *clone*) [ -z "${{STUB_CLONE_FAIL:-}}" ] || return 1
             target=${{@: -1}}; mkdir -p "$target/.git"; touch "$target/.git/HEAD"; echo "clone -> $target" >> "$LOG" ;;
    *"rev-parse --git-dir"*) [ -d "$2/.git" ] && echo .git || {{ echo "fatal: not a git repository" >&2; return 128; }} ;;
    *"cat-file -e"*) return 0 ;;
    *rev-parse*) [ -e "${{2:-}}/.git/HEAD" ] && echo "$LLAMA_CPP_COMMIT" || return 1 ;;
    *) return 1 ;;
  esac
}}
as_sos() {{
  case "$1" in
    */pip) echo "pip $*" >> "$LOG"; [ -z "${{STUB_PIP_FAIL:-}}" ] || return 1
           [ "$2" != install ] || {{ touch "$PREFIX/api/.venv/bin/sos" "$PREFIX/api/.venv/bin/uvicorn"; chmod +x "$PREFIX/api/.venv/bin/sos" "$PREFIX/api/.venv/bin/uvicorn"
             mkdir -p "$PREFIX/api/sos.egg-info" "$PREFIX/api/build/lib"; echo "Name: sos" > "$PREFIX/api/sos.egg-info/PKG-INFO"; }} ;;
    */sos) echo "sos $*" >> "$LOG"; [ -z "${{STUB_INDEX_FAIL:-}}" ] || return 1 ;;
    python3) mkdir -p "$4/bin"; touch "$4/bin/python" "$4/bin/pip"; chmod +x "$4/bin/python" "$4/bin/pip" ;;
    *) "$@" ;;
  esac
}}
{body}
"""
    proc = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env={**os.environ, **GOLDEN_ENV})
    if expect_ok:
        assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc


def calls(tmp_path: Path) -> list[str]:
    log = tmp_path / "calls.log"
    return log.read_text().splitlines() if log.exists() else []


def test_install_sh_can_be_sourced_without_running():
    proc = subprocess.run(["bash", "-c", f"source {INSTALL / 'install.sh'}; type step_venv >/dev/null && echo sourced"],
                          capture_output=True, text=True, env={**os.environ, **GOLDEN_ENV})
    assert proc.returncode == 0 and proc.stdout.strip() == "sourced", proc.stderr


@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync not installed")
def test_venv_step_is_a_no_op_on_the_second_run(tmp_path):
    """Making the venv inside the copied api/ tree moves that directory's mtime; rsync then reported a change
    on the next run and pip-installed again, so 'a second run reports unchanged' was not true."""
    run_install_steps(tmp_path, "step_venv")
    (tmp_path / "calls.log").write_text("")
    second = run_install_steps(tmp_path, "step_venv")
    assert "step venv: unchanged" in second.stdout and calls(tmp_path) == []


@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync not installed")
def test_venv_step_finishes_a_pip_install_that_was_interrupted(tmp_path):
    """The package files were copied and the venv exists, then the network dropped mid `pip install`. The
    next run must not see 'nothing changed' and leave the box without uvicorn."""
    interrupted = run_install_steps(tmp_path, "STUB_PIP_FAIL=1; step_venv", expect_ok=False)
    assert interrupted.returncode != 0
    os.utime(tmp_path / "srv" / "api", (REPO.stat().st_atime, (REPO / "api").stat().st_mtime))  # rsync sees a settled tree
    (tmp_path / "calls.log").write_text("")
    second = run_install_steps(tmp_path, "step_venv")
    assert "installed the sos package" in second.stdout and "unchanged" not in second.stdout, second.stdout
    assert any(line.startswith("pip ") and " -e " in line for line in calls(tmp_path))
    (tmp_path / "calls.log").write_text("")
    third = run_install_steps(tmp_path, "step_venv")
    assert "step venv: unchanged" in third.stdout and calls(tmp_path) == []


@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync not installed")
def test_venv_step_rebuilds_a_venv_that_died_before_pip_existed(tmp_path):
    (tmp_path / "srv" / "api" / ".venv" / "bin").mkdir(parents=True)
    python = tmp_path / "srv" / "api" / ".venv" / "bin" / "python"
    python.write_text("#!/bin/sh\n")
    python.chmod(0o755)
    run_install_steps(tmp_path, "step_venv")
    assert (tmp_path / "srv" / "api" / ".venv" / "bin" / "pip").exists()
    assert any(line.startswith("pip ") and " -e " in line for line in calls(tmp_path))


def test_llama_step_recovers_from_a_clone_that_never_finished(tmp_path):
    """A killed `git clone` leaves a .git with no commit in it; the old step trusted the directory, then
    failed on rev-parse under `set -e`, on every run, until somebody deleted it by hand."""
    (tmp_path / "srv" / "build" / "llama.cpp" / ".git").mkdir(parents=True)
    run_install_steps(tmp_path, "step_llama")
    log = calls(tmp_path)
    assert any(line.startswith("clone -> ") and line.endswith(".partial") for line in log), log
    assert any(line.startswith("cmake ") for line in log)
    assert (tmp_path / "srv" / "build" / "llama.cpp").is_dir()


def test_llama_clone_is_renamed_into_place_only_when_whole(tmp_path):
    proc = run_install_steps(tmp_path, "STUB_CLONE_FAIL=1; step_llama", expect_ok=False)
    assert proc.returncode != 0
    assert not (tmp_path / "srv" / "build" / "llama.cpp").exists(), "a failed clone must not leave a directory step_llama trusts"


def test_unit_steps_reload_systemd_even_when_the_files_already_match(tmp_path):
    """Interrupted between copying a unit and `daemon-reload`, the next run finds the files identical and
    used to skip the reload, leaving systemd running the old definition until the next boot."""
    units = tmp_path / "units"
    units.mkdir()
    for name in ("caddy.service", "kiwix-serve.service", "sos-api.service", "sos-llama.service", "sos-embed.service",
                 "sos-kiosk.service", "srv-sos-extended.mount", "sos-extended-rescan.service"):
        shutil.copy(INSTALL / "systemd" / name, units / name)
    run_install_steps(tmp_path, "step_units; step_mount")
    assert calls(tmp_path).count("systemctl daemon-reload") == 2


@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync not installed")
def test_content_step_reruns_an_index_that_was_killed(tmp_path):
    state = tmp_path / "srv" / "state"
    (state / "config").mkdir(parents=True)
    (state / "sos.db").write_text("")
    (state / "config" / "index.running").write_text("")   # left by an index that never finished
    proc = run_install_steps(tmp_path, "sync_tree() { return 1; }; step_content")
    assert "ran sos index" in proc.stdout
    assert not (state / "config" / "index.running").exists()
    (tmp_path / "calls.log").write_text("")
    again = run_install_steps(tmp_path, "sync_tree() { return 1; }; step_content")
    assert "step content: unchanged" in again.stdout and calls(tmp_path) == []
    killed = run_install_steps(tmp_path, "sync_tree() { return 1; }; STUB_INDEX_FAIL=1; touch $PREFIX/state/config/index.running; step_content",
                               expect_ok=False)
    assert killed.returncode != 0 and (state / "config" / "index.running").exists()


@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync not installed")
def test_a_failed_rsync_stops_the_install_instead_of_reading_as_no_change(tmp_path):
    """sync_tree is called as an `if` condition, where set -e is off: a failed rsync (disk full, the destination
    gone) returned non-zero and the step took that for "nothing changed" and carried on."""
    proc = run_install_steps(tmp_path, "step_venv", expect_ok=False, with_tree=False)
    assert proc.returncode != 0, proc.stdout
    assert "unchanged" not in proc.stdout and "rsync" in proc.stderr


def boot_dir(tmp_path: Path) -> Path:
    boot = tmp_path / "boot"
    boot.mkdir()
    (boot / "config.txt").write_text("arm_64bit=1\n")
    return boot


def test_boot_step_writes_the_fragment_beside_and_renames_it_then_includes_it(tmp_path):
    boot = boot_dir(tmp_path)
    proc = run_install_steps(tmp_path, f"BOOT_DIR={boot}; mv() {{ echo \"mv $*\" >> \"$LOG\"; command mv \"$@\"; }}; step_boot")
    assert "step boot: updated" in proc.stdout
    assert f"mv -f {boot}/sos.txt.new {boot}/sos.txt" in calls(tmp_path), "the fragment must be renamed into place, not written in place"
    assert (boot / "sos.txt").read_text() == (INSTALL / "boot" / "config.txt.d" / "sos.txt").read_text()
    assert not (boot / "sos.txt.new").exists()
    assert "include sos.txt" in (boot / "config.txt").read_text().splitlines()
    again = run_install_steps(tmp_path, f"BOOT_DIR={boot}; step_boot")
    assert "step boot: unchanged" in again.stdout


def test_boot_step_that_cannot_write_the_fragment_fails_instead_of_reporting_updated(tmp_path):
    """`cp ... && sync && mv ...; changed=1` ran changed=1 after a failing cp, said "updated", and went on to add the
    include line for a fragment that was never written."""
    boot = boot_dir(tmp_path)
    proc = run_install_steps(tmp_path, f"BOOT_DIR={boot}; cp() {{ case \"$2\" in *sos.txt.new) return 1;; esac; command cp \"$@\"; }}; step_boot",
                             expect_ok=False)
    assert proc.returncode != 0
    assert "updated" not in proc.stdout and "could not write" in proc.stderr
    assert not (boot / "sos.txt").exists()
    assert "include sos.txt" not in (boot / "config.txt").read_text()


# step_llama used to `rm -rf` the clone whenever `git rev-parse HEAD` failed for ANY reason. The clone is only
# removed when git says the repository itself is broken; every other failure stops the install with git's message.
LLAMA_GIT = r'''
git() {{
  # $1 is -C, $2 the clone, the rest the command; STUB_GIT picks how the clone at $2 answers
  local cmd="${{*:3}}"
  case "$cmd" in
    "rev-parse --git-dir")
      case "$STUB_GIT" in
        dubious) echo "fatal: detected dubious ownership in repository at '$2'" >&2; return 128 ;;
        notrepo) echo "fatal: not a git repository (or any of the parent directories): .git" >&2; return 128 ;;
        *) echo .git ;;
      esac ;;
    "rev-parse -q --verify HEAD") [ "$STUB_GIT" = nohead ] && return 1; echo "$LLAMA_CPP_COMMIT" ;;
    "rev-parse HEAD") echo "$LLAMA_CPP_COMMIT" ;;
    "cat-file -e "*) [ "$STUB_GIT" = stale ] && return 1; return 0 ;;
    clone*|"-C"*) return 1 ;;
  esac
  case "$*" in
    *clone*) target=${{@: -1}}; mkdir -p "$target/.git"; touch "$target/.git/HEAD"; echo "clone -> $target" >> "$LOG" ;;
  esac
}}
'''


def llama_case(tmp_path: Path, mode: str) -> tuple[subprocess.CompletedProcess, Path]:
    src = tmp_path / "srv" / "build" / "llama.cpp"
    src.mkdir(parents=True)
    (src / "precious-local-change.txt").write_text("keep me")
    body = LLAMA_GIT.format() + f"\nSTUB_GIT={mode}; step_llama"
    return run_install_steps(tmp_path, body, expect_ok=False), src


def test_llama_step_never_deletes_a_clone_git_merely_refuses_to_read(tmp_path):
    proc, src = llama_case(tmp_path, "dubious")
    assert proc.returncode != 0
    assert (src / "precious-local-change.txt").exists(), "a 'dubious ownership' clone must not be removed"
    assert "dubious ownership" in proc.stderr
    assert not any(line.startswith("clone ->") for line in calls(tmp_path))


@pytest.mark.parametrize("mode", ["notrepo", "nohead", "stale"])
def test_llama_step_reclones_only_a_genuinely_broken_or_stale_clone(tmp_path, mode):
    proc, src = llama_case(tmp_path, mode)
    assert proc.returncode == 0, proc.stderr
    assert any(line.startswith("clone -> ") for line in calls(tmp_path)), mode
    assert not (src / "precious-local-change.txt").exists()


def test_llama_step_keeps_a_healthy_clone(tmp_path):
    proc, src = llama_case(tmp_path, "healthy")
    assert proc.returncode == 0, proc.stderr
    assert not any(line.startswith("clone ->") for line in calls(tmp_path))
    assert (src / "precious-local-change.txt").exists()
    assert any(line.startswith("cmake ") for line in calls(tmp_path))
