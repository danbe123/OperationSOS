"""The sensor drivers, what the box concludes from them, and bulletin recording. No hardware, no subprocesses."""
import struct
import wave
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from sos import db, sensors

FIXTURE_CSV = Path(__file__).parent / "fixtures" / "sensors" / "rtl_power.csv"


@pytest.fixture
def conn(env):
    c = db.connect(env.db_path)
    db.init_schema(c)
    yield c
    c.close()


def ago(minutes: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).replace(microsecond=0).isoformat()


class FakeRunner:
    """A stand-in for the subprocess: hands back canned stdout and remembers what it was asked to run."""

    def __init__(self, stdout: str = "", raw: bytes | None = None):
        self.stdout, self.raw, self.calls = stdout, raw, []

    def __call__(self, args, timeout):
        self.calls.append((list(args), timeout))
        if self.raw is not None:
            Path(args[-1]).write_bytes(self.raw)
        return self.stdout


# --- storing readings ---------------------------------------------------------------------------------------

def test_readings_are_stored_and_the_latest_of_each_comes_back(conn):
    sensors.record(conn, "cpu_temp", 45.2, "C", ago(10))
    sensors.record(conn, "cpu_temp", 51.0, "C", ago(1))
    sensors.record(conn, "internet", 0.0, "up", ago(2))
    rows = sensors.latest(conn)
    assert [r["sensor"] for r in rows] == ["cpu_temp", "internet"]
    assert rows[0]["value"] == 51.0 and rows[0]["unit"] == "C"
    assert [r["value"] for r in sensors.history(conn, "cpu_temp", limit=5)] == [51.0, 45.2]


def test_prune_drops_readings_older_than_a_fortnight(conn):
    sensors.record(conn, "cpu_temp", 40.0, "C", ago(60 * 24 * 20))
    sensors.record(conn, "cpu_temp", 41.0, "C", ago(1))
    sensors.prune(conn, keep_days=14)
    assert [r["value"] for r in sensors.history(conn, "cpu_temp")] == [41.0]


# --- the cheap drivers ---------------------------------------------------------------------------------------

def test_internet_probe_needs_both_dns_and_http(env):
    ok_dns = lambda *a, **k: [("info",)]                                         # noqa: E731
    assert sensors.probe_internet(env, resolve=ok_dns, fetch=lambda url, t: True) == 1.0
    assert sensors.probe_internet(env, resolve=ok_dns, fetch=lambda url, t: False) == 0.0

    def no_dns(*a, **k):
        raise OSError("Name or service not known")

    assert sensors.probe_internet(env, resolve=no_dns, fetch=lambda url, t: True) == 0.0
    assert sensors.probe_internet(env, resolve=lambda *a, **k: [], fetch=lambda url, t: True) == 0.0


def test_the_probe_passes_the_configured_host_url_and_timeout(env):
    env.sensor_probe_host, env.sensor_probe_url, env.sensor_probe_timeout_s = "example.test", "http://example.test/x", 2.5
    seen = {}

    def fetch(url, timeout):
        seen.update(url=url, timeout=timeout)
        return True

    sensors.probe_internet(env, resolve=lambda host, *a, **k: seen.setdefault("host", host) or [("i",)], fetch=fetch)
    assert seen == {"host": "example.test", "url": "http://example.test/x", "timeout": 2.5}


def test_mains_reads_the_power_supply_files(env, tmp_path):
    supply = tmp_path / "power_supply"
    (supply / "ac").mkdir(parents=True)
    (supply / "ac" / "online").write_text("1\n")
    env.sensor_mains_glob = str(supply / "*" / "online")
    assert sensors.probe_mains(env) == 1.0
    (supply / "ac" / "online").write_text("0\n")
    assert sensors.probe_mains(env) == 0.0


def test_mains_is_none_when_nothing_on_the_box_can_tell(env, tmp_path):
    env.sensor_mains_glob = str(tmp_path / "nothing" / "*" / "online")
    assert sensors.probe_mains(env) is None


def test_mains_from_a_gpio_pin_honours_active_low(env, tmp_path):
    pin = tmp_path / "gpio17" / "value"
    pin.parent.mkdir()
    pin.write_text("1\n")
    env.sensor_mains_gpio = str(pin)
    assert sensors.probe_mains(env) == 1.0
    env.sensor_mains_gpio_active_low = True
    assert sensors.probe_mains(env) == 0.0
    pin.write_text("0\n")
    assert sensors.probe_mains(env) == 1.0


def test_file_sensors_are_typed_by_their_name(env, tmp_path):
    (tmp_path / "temp_in").write_text("18.5\n")
    (tmp_path / "co_ppm").write_text("3\n")
    (tmp_path / "broken").write_text("not a number\n")
    env.sensor_files = {"temp_in": str(tmp_path / "temp_in"), "co_ppm": str(tmp_path / "co_ppm"),
                        "leak": str(tmp_path / "missing"), "broken": str(tmp_path / "broken")}
    assert sensors.probe_files(env) == [("co_ppm", 3.0, "ppm"), ("temp_in", 18.5, "C")]


def test_poll_cheap_records_the_box_and_the_probe(conn, env, tmp_path):
    (tmp_path / "humidity").write_text("62\n")
    env.sensor_files = {"humidity": str(tmp_path / "humidity")}
    env.sensor_mains_glob = str(tmp_path / "none" / "*" / "online")
    sensors.poll_cheap(conn, env, resolve=lambda *a, **k: [("i",)], fetch=lambda url, t: True)
    got = {r["sensor"]: r for r in sensors.latest(conn)}
    assert got["internet"]["value"] == 1.0
    assert got["hotspot_clients"]["value"] == 2.0          # the two fake stations SOS_DEV=1 reports
    assert got["cpu_temp"]["value"] == 45.0
    assert got["humidity"]["value"] == 62.0 and got["humidity"]["unit"] == "%"
    assert "mains" not in got                              # no UPS on this box, so nothing is claimed


# --- rtl_power ---------------------------------------------------------------------------------------------------

def test_rtl_power_csv_is_parsed_and_the_bands_averaged():
    rows = sensors.parse_rtl_power(FIXTURE_CSV.read_text(encoding="utf-8"))
    assert len(rows) == 67 and rows[0][0] == 87_500_000 and rows[0][1] == 100_000
    assert sensors.band_energy(rows, 87_500_000, 108_000_000) == pytest.approx(-40.69, abs=0.01)
    assert sensors.band_energy(rows, 174_000_000, 240_000_000) == pytest.approx(-42.44, abs=0.01)
    assert sensors.band_energy(rows, 791_000_000, 821_000_000) == pytest.approx(-33.10, abs=0.01)
    assert sensors.band_energy(rows, 1_800_000_000, 1_900_000_000) is None      # a band the sweep never touched


def test_rubbish_lines_in_the_csv_are_ignored():
    assert sensors.parse_rtl_power("\n# a comment\n2026-09-06, 03:00:00, x, y, z, 1, -30\n") == []
    rows = sensors.parse_rtl_power("2026-09-06, 03:00:00, 1000, 2000, 100.00, 4, -30.0, , -20.0\n")
    assert rows == [(1000.0, 100.0, [-30.0, -20.0])]


def test_sweep_asks_rtl_power_for_the_right_band(env):
    runner = FakeRunner(FIXTURE_CSV.read_text(encoding="utf-8"))
    value = sensors.sweep(env, ("fm", 87_500_000, 108_000_000, 100_000), runner)
    args, timeout = runner.calls[0]
    assert args[0] == "rtl_power" and "-f" in args and args[args.index("-f") + 1] == "87500000:108000000:100000"
    assert timeout > env.rtl_power_dwell_s and value == pytest.approx(-40.69, abs=0.01)


def test_poll_rtl_power_records_every_band_and_a_broadcast_reading(conn, env):
    got = sensors.poll_rtl_power(conn, env, FakeRunner(FIXTURE_CSV.read_text(encoding="utf-8")))
    assert set(got) == {"band_fm", "band_dab", "band_mobile_800", "band_mobile_900", "broadcast"}
    assert got["broadcast"] == max(got["band_fm"], got["band_dab"])
    assert {r["sensor"] for r in sensors.latest(conn)} == set(got)


# --- what the readings say -----------------------------------------------------------------------------------------

def test_nothing_is_detected_from_an_empty_table(conn):
    assert sensors.detected_states(conn) == {}


def test_the_internet_is_off_only_after_three_failed_probes(conn):
    for minutes in (3, 2):
        sensors.record(conn, "internet", 0.0, "up", ago(minutes))
    assert "internet" not in sensors.detected_states(conn)
    sensors.record(conn, "internet", 0.0, "up", ago(1))
    proposal = sensors.detected_states(conn)["internet"]
    assert proposal == {"state": "off", "at": ago(3), "confidence": 0.8, "sensor": "internet"}
    sensors.record(conn, "internet", 1.0, "up", ago(0))
    assert "internet" not in sensors.detected_states(conn)


def test_the_power_is_off_while_the_ups_says_there_is_no_mains(conn):
    sensors.record(conn, "mains", 1.0, "on", ago(5))
    assert "power" not in sensors.detected_states(conn)
    sensors.record(conn, "mains", 0.0, "on", ago(1))
    assert sensors.detected_states(conn)["power"] == {"state": "off", "at": ago(1), "confidence": 0.9,
                                                      "sensor": "mains"}


def test_mobile_is_degraded_when_the_bands_go_quiet_after_being_busy(conn):
    for minutes in (40, 30, 20):
        sensors.record(conn, "band_mobile_800", -33.0, "dB", ago(minutes))
        sensors.record(conn, "band_mobile_900", -34.0, "dB", ago(minutes))
    assert "mobile" not in sensors.detected_states(conn)     # busy bands say nothing
    sensors.record(conn, "band_mobile_800", -55.0, "dB", ago(10))
    assert "mobile" not in sensors.detected_states(conn)     # one band alone is a duff reading, not an outage
    sensors.record(conn, "band_mobile_900", -56.0, "dB", ago(10))
    proposal = sensors.detected_states(conn)["mobile"]
    assert proposal["state"] == "degraded" and proposal["sensor"] == "rtl_power" and proposal["confidence"] == 0.6


def test_a_cold_start_never_proposes_a_mobile_outage(conn):
    sensors.record(conn, "band_mobile_800", -33.0, "dB", ago(20))
    sensors.record(conn, "band_mobile_800", -60.0, "dB", ago(10))
    sensors.record(conn, "band_mobile_900", -33.0, "dB", ago(20))
    sensors.record(conn, "band_mobile_900", -60.0, "dB", ago(10))
    assert "mobile" not in sensors.detected_states(conn)


# --- bulletins ------------------------------------------------------------------------------------------------------

LW = {"station": "BBC Radio 4", "frequency": "198 kHz long wave", "times": ["18:00"], "recordable": False}
FM = {"station": "BBC Radio 4 FM", "frequency": "93.5 MHz", "times": ["18:00"], "record_hz": 93_500_000}


def test_long_wave_is_never_recordable():
    assert sensors.recordable(FM) is True
    assert sensors.recordable(LW) is False
    assert sensors.recordable({"station": "Local", "times": ["07:00"]}) is False    # no record_hz, no recording


def test_due_recordings_opens_a_window_at_the_bulletin_time():
    at_six = datetime(2026, 9, 6, 17, 0, tzinfo=timezone.utc)          # 18:00 British Summer Time
    assert [b["station"] for b, _ in sensors.due_recordings([LW, FM], at_six)] == ["BBC Radio 4 FM"]
    _, start = sensors.due_recordings([FM], at_six)[0]
    assert start == at_six
    assert sensors.due_recordings([FM], at_six + timedelta(minutes=4)) != []
    assert sensors.due_recordings([FM], at_six + timedelta(minutes=6)) == []
    assert sensors.due_recordings([FM], at_six - timedelta(minutes=1)) == []


def test_recording_writes_a_wav_and_lists_it(env, tmp_path):
    runner = FakeRunner(raw=struct.pack("<2h", 0, 1000) * sensors.RECORD_RATE)   # one second of audio
    at = datetime(2026, 9, 6, 17, 0, tzinfo=timezone.utc)
    made = sensors.record_due(env, [LW, FM], now=at, runner=runner)
    assert len(made) == 1 and made[0].name == "bbc-radio-4-fm-20260906T1700Z.wav"
    args, timeout = runner.calls[0]
    assert args[0] == "rtl_fm" and args[args.index("-f") + 1] == "93500000" and timeout == env.bulletin_window_s
    with wave.open(str(made[0]), "rb") as fh:
        assert fh.getnchannels() == 1 and fh.getsampwidth() == 2 and fh.getframerate() == sensors.RECORD_RATE
        assert fh.getnframes() == 2 * sensors.RECORD_RATE
    assert not made[0].with_suffix(".raw").exists()

    listed = sensors.list_recordings(env)
    assert [r["name"] for r in listed] == [made[0].name]
    assert listed[0]["station"] == "bbc radio 4 fm" and listed[0]["seconds"] == 2.0
    assert listed[0]["url"] == f"/api/recordings/{made[0].name}"

    assert sensors.record_due(env, [FM], now=at, runner=FakeRunner(raw=b"x")) == []   # already recorded


def test_a_dongle_that_produces_nothing_leaves_no_file(env):
    at = datetime(2026, 9, 6, 17, 0, tzinfo=timezone.utc)
    assert sensors.record_due(env, [FM], now=at, runner=FakeRunner(raw=b"")) == []
    assert sensors.list_recordings(env) == []


# --- the endpoints ------------------------------------------------------------------------------------------------

def test_sensors_endpoint(client, env):
    c = db.connect(env.db_path)
    for minutes in (3, 2, 1):
        sensors.record(c, "internet", 0.0, "up", ago(minutes))
    sensors.record(c, "cpu_temp", 47.0, "C", ago(1))
    c.close()
    body = client.get("/api/sensors").json()
    assert [r["sensor"] for r in body["readings"]] == ["cpu_temp", "internet"]
    assert body["detected"]["internet"]["state"] == "off"
    assert set(body["drivers"]) == {"rtl_power", "rtl_fm", "piper", "enabled"} and body["drivers"]["enabled"] is True


def test_recordings_endpoint_lists_and_serves(client, env):
    path = sensors.write_wav(b"\x00\x01" * 100, env.recordings / "bbc-radio-4-fm-20260906T1700Z.wav")
    listed = client.get("/api/recordings").json()
    assert [r["name"] for r in listed] == [path.name]
    served = client.get(f"/api/recordings/{path.name}")
    assert served.status_code == 200 and served.headers["content-type"] == "audio/wav"
    assert client.get("/api/recordings/nothing.wav").status_code == 404
    assert client.get("/api/recordings/..%2Fsos.db").status_code == 404


def test_a_detected_state_proposes_and_never_overrides_a_later_manual_one(client, env):
    """The box has lost the internet, but somebody has since said the internet is working: they win."""
    c = db.connect(env.db_path)
    for minutes in (3, 2, 1):
        sensors.record(c, "internet", 0.0, "up", ago(minutes))
    c.close()
    view = client.get("/api/situation/view").json()
    assert view["conditions"]["internet"]["state"] == "working"
    proposal = next(i for i in view["inferred"] if i["condition"] == "internet")
    assert proposal["rule"] == "sensor:internet" and proposal["state"] == "off"

    client.put("/api/conditions/internet", json={"state": "working"})
    after = client.get("/api/situation/view").json()
    assert after["conditions"]["internet"]["state"] == "working"
    assert [i for i in after["inferred"] if i["rule"] == "sensor:internet"] == []
