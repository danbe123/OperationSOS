import sys

import pytest

from sos import db, system


@pytest.fixture
def conn(env):
    c = db.connect(env.db_path)
    db.init_schema(c)
    return c


@pytest.fixture
def recorder(monkeypatch):
    calls = []

    def fake_run(args, settings, timeout=30.0, check=False):
        calls.append(list(args))
        return system.FAKE_CMD_OUTPUT.get(tuple(a for a in args if a not in ("sudo", "-n")), "")

    monkeypatch.setattr(system, "run_cmd", fake_run)
    return calls


def test_cpu_temp_dev_fake_and_missing(env, monkeypatch):
    assert system.cpu_temp(env) == 45.0
    monkeypatch.setattr(system, "read_sysfs", lambda path, settings: None)
    assert system.cpu_temp(env) is None


@pytest.mark.parametrize(
    "level,expected_level,raw",
    [(100, 100, "31"), (10, 10, "3"), (5, 10, "3"), (0, 10, "3"), (50, 50, "16"), (150, 100, "31")],
)
def test_backlight_scaled_to_max_brightness(env, level, expected_level, raw):
    assert system.set_backlight(env, level) == expected_level
    assert system.FAKE_SYSFS["/sys/class/backlight/fake/brightness"].strip() == raw


def test_backlight_without_device_returns_none(env, monkeypatch):
    monkeypatch.setattr(system, "backlight_device", lambda settings: None)
    assert system.set_backlight(env, 50) is None


def test_hotspot_info_dev(conn, env):
    info = system.hotspot_info(conn, env)
    assert info == {"ssid": "SOS", "ip": "10.42.0.1", "clients": 2, "enabled": True}


def test_set_hotspot_records_nmcli_sequence(conn, env, recorder):
    system.set_hotspot(conn, env, "Bunker", "letmein123")
    assert recorder == [
        ["sudo", "-n", "nmcli", "con", "modify", "sos-hotspot", "802-11-wireless.ssid", "Bunker"],
        ["sudo", "-n", "nmcli", "con", "modify", "sos-hotspot", "wifi-sec.key-mgmt", "wpa-psk",
         "wifi-sec.psk", "letmein123"],
        ["sudo", "-n", "nmcli", "con", "up", "sos-hotspot"],
    ]
    assert db.get_setting(conn, "ssid") == "Bunker" and db.get_setting(conn, "passphrase") == "letmein123"
    recorder.clear()
    system.set_hotspot(conn, env, "SOS", "")
    assert recorder[1] == ["sudo", "-n", "nmcli", "con", "modify", "sos-hotspot", "remove", "wifi-sec"]
    with pytest.raises(ValueError):
        system.set_hotspot(conn, env, "", None)
    with pytest.raises(ValueError):
        system.set_hotspot(conn, env, "SOS", "short")


def test_set_eth_mode(conn, env, recorder):
    system.set_eth_mode(conn, env, "direct")
    assert recorder == [
        ["sudo", "-n", "nmcli", "con", "modify", "sos-eth-client", "connection.autoconnect", "no"],
        ["sudo", "-n", "nmcli", "con", "modify", "sos-eth-direct", "connection.autoconnect", "yes"],
        ["sudo", "-n", "nmcli", "con", "up", "sos-eth-direct"],
    ]
    assert db.get_setting(conn, "eth_mode") == "direct"
    with pytest.raises(ValueError):
        system.set_eth_mode(conn, env, "bridge")


def test_power_mode_low_stops_ai_and_dims(conn, env, recorder):
    system.set_ai_state(conn, "ready")
    system.set_power_mode(conn, env, "low")
    assert ["sudo", "-n", "systemctl", "stop", "sos-llama.service"] in recorder
    assert system.ai_status(conn, env)["state"] == "off"
    assert system.FAKE_SYSFS["/sys/class/backlight/fake/brightness"].strip() == "9"
    assert db.get_setting(conn, "power_mode") == "low"
    system.set_power_mode(conn, env, "normal")
    assert system.FAKE_SYSFS["/sys/class/backlight/fake/brightness"].strip() == "31"


def test_pin_hash_verify_clear(conn):
    assert system.pin_required(conn) is False
    assert system.verify_pin(conn, "1234") is False
    system.set_pin(conn, "1234")
    assert system.pin_required(conn) is True
    assert db.get_setting(conn, "pin_hash").startswith("scrypt$")
    assert system.verify_pin(conn, "1234") is True
    assert system.verify_pin(conn, "0000") is False
    system.clear_pin(conn)
    assert system.pin_required(conn) is False
    with pytest.raises(ValueError):
        system.set_pin(conn, "12")
    with pytest.raises(ValueError):
        system.set_pin(conn, "abcd")


def test_token_store_expiry():
    now = [1000.0]
    store = system.TokenStore(ttl=600, clock=lambda: now[0])
    tok = store.issue()
    assert store.valid(tok) is True and store.valid("nope") is False
    now[0] += 599
    assert store.valid(tok) is True
    now[0] += 2
    assert store.valid(tok) is False
    tok2 = store.issue()
    store.revoke_all()
    assert store.valid(tok2) is False


def test_rate_limiter_five_per_minute():
    now = [0.0]
    rl = system.RateLimiter(limit=5, window=60.0, clock=lambda: now[0])
    assert [rl.allow("ip") for _ in range(5)] == [True] * 5
    assert rl.allow("ip") is False
    assert rl.allow("other") is True
    now[0] += 61
    assert rl.allow("ip") is True


def test_thermal_watchdog(conn, env, recorder, monkeypatch):
    temps = {"value": "79000\n"}
    monkeypatch.setattr(
        system, "read_sysfs",
        lambda path, settings: temps["value"] if path == system.THERMAL_PATH else None,
    )
    system.set_ai_state(conn, "ready")
    wd = system.ThermalWatchdog(env, env.db_path)
    assert wd.tick(conn) is None
    assert system.ai_status(conn, env)["state"] == "ready" and recorder == []
    temps["value"] = "80000\n"
    assert wd.tick(conn) == "stopped"
    assert system.ai_status(conn, env)["state"] == "off-thermal"
    assert ["sudo", "-n", "systemctl", "stop", "sos-llama.service"] in recorder
    recorder.clear()
    temps["value"] = "60000\n"
    assert wd.tick(conn) is None
    assert system.ai_status(conn, env)["state"] == "off-thermal"
    assert recorder == []
    db.set_setting(conn, "thermal_ai_off_c", "55")
    system.set_ai_state(conn, "ready")
    assert wd.tick(conn) == "stopped"


def test_update_runner_streams_lines():
    runner = system.UpdateRunner(lambda tier: [sys.executable, "-c", f"print('syncing {tier}'); print('done')"])
    assert runner.progress() == {"running": False, "lines": [], "done": False, "ok": None}
    assert runner.start(["core", "extended"]) is True
    runner.wait(10)
    p = runner.progress()
    assert p["running"] is False and p["done"] is True and p["ok"] is True
    assert p["lines"] == ["== sync core", "syncing core", "done", "== sync extended", "syncing extended", "done"]
    failing = system.UpdateRunner(lambda tier: [sys.executable, "-c", "import sys; print('boom'); sys.exit(3)"])
    failing.start(["core"])
    failing.wait(10)
    assert failing.progress()["ok"] is False and "sync core failed (exit 3)" in failing.progress()["lines"]


def test_update_runner_rejects_concurrent_start():
    runner = system.UpdateRunner(lambda tier: [sys.executable, "-c", "import time; time.sleep(0.5)"])
    assert runner.start(["core"]) is True
    assert runner.start(["core"]) is False
    runner.wait(5)


def test_apply_settings_validation(conn):
    system.apply_settings(conn, {"default_theme": "field", "thermal_ai_off_c": 75, "idle_minutes": 3,
                                 "home_minutes": 20})
    assert db.get_setting(conn, "default_theme") == "field" and db.get_setting(conn, "thermal_ai_off_c") == "75"
    with pytest.raises(ValueError):
        system.apply_settings(conn, {"default_theme": "neon"})
    with pytest.raises(ValueError):
        system.apply_settings(conn, {"thermal_ai_off_c": 120})
    with pytest.raises(ValueError):
        system.apply_settings(conn, {"bogus": 1})


def test_status_shape(conn, env):
    s = system.status(conn, env)
    assert set(s) == {"version", "uptime_s", "cpu_temp_c", "load", "mem", "disks", "hotspot", "eth_mode",
                      "power_mode", "ai", "thermal_ai_off_c", "idle_minutes", "home_minutes", "pin_required",
                      "dev", "default_theme"}
    assert s["dev"] is True and s["cpu_temp_c"] == 45.0 and s["thermal_ai_off_c"] == 80
    assert s["disks"]["core"]["mounted"] is True and s["disks"]["extended"]["mounted"] is False
    assert s["disks"]["extended"] == {"mounted": False, "path": str(env.ext), "total_gb": 0.0, "free_gb": 0.0}
    assert s["ai"] == {"state": "off", "model": env.model, "message": None}
    assert s["default_theme"] == "vault" and s["idle_minutes"] == 5 and s["home_minutes"] == 30
    assert len(s["load"]) == 3 and s["mem"]["total_mb"] > 0
