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
    assert "Restart=on-failure" in kiwix and "RestartSec=2" in kiwix and "User=sos" in kiwix
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
    assert "exec chromium --kiosk --ozone-platform=wayland --force-device-scale-factor=1.5 --noerrdialogs --no-first-run" in kiosk
    assert "--overscroll-history-navigation=0" in kiosk and "http://localhost/starting" in kiosk
    assert '"exit_type": "Normal", "exited_cleanly": True' in kiosk and "python3 -c" in kiosk


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
    env = {**os.environ, "SOS_KIOSK_PREFS": str(prefs), "SOS_KIOSK_CONFIG": str(tmp_path / "absent.env"),
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
