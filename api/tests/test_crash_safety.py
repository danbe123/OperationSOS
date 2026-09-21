"""What a kill, or a power cut, leaves of the household's state.

`synchronous=NORMAL` (the default here) in WAL mode never corrupts the database but can lose the last commits
of a power cut: the WAL is synced only when it is checkpointed. Ticks, notes, conditions and pins are small and
rare, so their connections are `durable` (synchronous=FULL); the search cache and the index rebuild are not.

Two kinds of kill are exercised, each ROUNDS times against a scratch database, each time with a writer killed
at a random moment and every acknowledged commit checked afterwards:
  * SIGKILL of the process: the kernel keeps the process's writes, so this is the crash the app itself suffers;
  * a power cut, by tests/support/lossydisk.c: every write not yet fsynced is undone after the kill.
"""
from __future__ import annotations

import os
import random
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from sos import db
from tests.support import lossydisk

ROUNDS = int(os.environ.get("SOS_CRASH_ROUNDS", "30"))
WRITER = Path(__file__).with_name("support") / "crash_writer.py"
API_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def lossy_so(tmp_path_factory):
    so = lossydisk.build(tmp_path_factory.mktemp("lossy"))
    if so is None:
        pytest.skip("no C compiler for the lossy-disk shim")
    return so


def fresh_db(path: Path) -> None:
    conn = db.connect(path)
    db.init_schema(conn)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()


def run_writer(path: Path, mode: str, rng: random.Random, extra_env: dict | None = None) -> int:
    """Start the writer, let it acknowledge some commits for a random while, SIGKILL it; return the last acknowledged number."""
    env = {**os.environ, "PYTHONPATH": str(API_DIR), **(extra_env or {})}
    proc = subprocess.Popen([sys.executable, str(WRITER), str(path), mode], stdout=subprocess.PIPE, env=env, cwd=API_DIR)
    acked: list[int] = []

    def read():
        for line in proc.stdout:
            if line.endswith(b"\n"):
                acked.append(int(line))

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    deadline = time.monotonic() + 10
    while not acked and time.monotonic() < deadline:
        time.sleep(0.005)
    assert acked, "the writer never acknowledged a commit"
    time.sleep(rng.uniform(0.0, 0.25))
    proc.kill()
    proc.wait()
    reader.join(5)
    return acked[-1]


def check(path: Path, last_acked: int) -> tuple[str, int]:
    conn = sqlite3.connect(path)
    try:
        verdict = conn.execute("PRAGMA integrity_check").fetchone()[0]
        present = {int(r[0][1:]) for r in conn.execute("SELECT title FROM notes")}
    finally:
        conn.close()
    missing = [i for i in range(1, last_acked + 1) if i not in present]
    return verdict, len(missing)


@pytest.mark.parametrize("mode", ["durable", "normal"])
def test_sigkill_at_random_moments_never_corrupts_or_loses_an_acknowledged_row(tmp_path, mode):
    rng = random.Random(20260921)
    for round_no in range(ROUNDS):
        path = tmp_path / f"{mode}-{round_no}" / "sos.db"
        path.parent.mkdir()
        fresh_db(path)
        last = run_writer(path, mode, rng)
        verdict, missing = check(path, last)
        assert verdict == "ok", (mode, round_no, verdict)
        assert missing == 0, f"{mode} round {round_no}: {missing} acknowledged rows missing after SIGKILL"


def power_loss_round(tmp_path, lossy_so, mode: str, round_no: int, rng: random.Random) -> tuple[str, int, int]:
    path = tmp_path / f"{mode}-{round_no}" / "sos.db"
    path.parent.mkdir()
    fresh_db(path)
    log = path.parent / "lossy.log"
    last = run_writer(path, mode, rng, lossydisk.env_for(lossy_so, path, log))
    lossydisk.power_cut(log)
    verdict, missing = check(path, last)
    return verdict, missing, last


def test_a_power_cut_loses_no_acknowledged_row_on_a_durable_connection(tmp_path, lossy_so):
    rng = random.Random(7)
    total = 0
    for round_no in range(ROUNDS):
        verdict, missing, last = power_loss_round(tmp_path, lossy_so, "durable", round_no, rng)
        total += last
        assert verdict == "ok", (round_no, verdict)
        assert missing == 0, f"round {round_no}: {missing} of {last} acknowledged rows lost to the power cut"
    assert total > ROUNDS  # the writer did real work in every round


def test_a_power_cut_can_lose_acknowledged_rows_on_a_normal_connection_but_never_corrupts(tmp_path, lossy_so):
    """The gap the durable connection closes, shown with the same disk: synchronous=NORMAL acknowledges a commit
    before the WAL is synced, so the last commits of a power cut are gone (the database is still intact)."""
    rng = random.Random(11)
    lost_rounds = 0
    for round_no in range(12):
        verdict, missing, _ = power_loss_round(tmp_path, lossy_so, "normal", round_no, rng)
        assert verdict == "ok", (round_no, verdict)
        lost_rounds += missing > 0
    assert lost_rounds > 0, "expected NORMAL to lose acknowledged rows to a power cut; the lossy disk is not biting"


# --- which routes are durable ---------------------------------------------------------------------------

def test_the_routes_that_take_what_people_enter_use_a_durable_connection(client, monkeypatch):
    """Notes, ticks, conditions, settings: FULL. The search cache and the rescan: NORMAL, so they stay fast."""
    opened: list[bool] = []
    real_connect = db.connect

    def spy(path, *, durable=False):
        opened.append(durable)
        return real_connect(path, durable=durable)

    monkeypatch.setattr(db, "connect", spy)

    def durable_of(call) -> set[bool]:
        opened.clear()
        response = call()
        assert response.status_code < 400, response.text
        return set(opened)

    writes = {
        "note": lambda: client.post("/api/notes", json={"kind": "note", "title": "t", "body": "b"}),
        "checklist tick": lambda: client.put("/api/playbooks/grid-collapse/checklist/cooker-off", json={"checked": True}),
        "condition": lambda: client.put("/api/conditions/power", json={"state": "off"}),
        "people": lambda: client.put("/api/settings/people", json={"people": 3}),
    }
    for name, call in writes.items():
        assert durable_of(call) == {True}, f"{name} must be committed with synchronous=FULL"
    assert durable_of(lambda: client.get("/api/library")) == {False}
    assert durable_of(lambda: client.post("/api/system/rescan")) == {False}


def test_a_durable_connection_reports_full_and_the_default_reports_normal(tmp_path):
    for durable, expected in ((True, 2), (False, 1)):
        conn = db.connect(tmp_path / f"{durable}.db", durable=durable)
        assert conn.execute("PRAGMA synchronous").fetchone()[0] == expected  # 2 FULL, 1 NORMAL
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        conn.close()


# --- starting on what a crash left ---------------------------------------------------------------------------

def start_api(env):
    from fastapi.testclient import TestClient
    from sos.main import create_app
    return TestClient(create_app(env, background=False), client=("127.0.0.1", 50000))


def assert_api_answers(env, minimum_notes: int):
    with start_api(env) as api:
        notes = api.get("/api/notes", params={"kind": "note"})
        assert notes.status_code == 200 and len(notes.json()) >= minimum_notes
        assert api.get("/api/status").status_code == 200
        assert api.get("/api/playbooks").status_code == 200
        assert api.get("/api/search", params={"q": "water"}).status_code == 200
        assert api.post("/api/notes", json={"kind": "note", "title": "after", "body": "still writable"}).status_code == 200


def test_the_api_starts_on_a_database_left_mid_wal_by_a_killed_writer(env):
    rng = random.Random(5)
    for _ in range(5):
        for suffix in ("", "-wal", "-shm"):
            Path(str(env.db_path) + suffix).unlink(missing_ok=True)
        fresh_db(env.db_path)
        last = run_writer(env.db_path, "durable", rng)
        assert Path(str(env.db_path) + "-wal").exists(), "the killed writer should have left a WAL behind"
        assert_api_answers(env, minimum_notes=last)


def test_the_api_starts_on_a_copy_of_a_database_taken_while_a_writer_was_active(env, tmp_path):
    rng = random.Random(9)
    source = tmp_path / "live" / "sos.db"
    source.parent.mkdir()
    fresh_db(source)
    proc = subprocess.Popen([sys.executable, str(WRITER), str(source), "durable"], stdout=subprocess.DEVNULL,
                            env={**os.environ, "PYTHONPATH": str(API_DIR)}, cwd=API_DIR)
    try:
        time.sleep(0.4)
        for _ in range(12):
            time.sleep(rng.uniform(0.0, 0.15))
            for suffix in ("", "-wal", "-shm"):
                Path(str(env.db_path) + suffix).unlink(missing_ok=True)
            # a plain copy, wal last: what somebody rescuing files from a running box would do
            for suffix in ("", "-shm", "-wal"):
                if Path(str(source) + suffix).exists():
                    shutil.copy(str(source) + suffix, str(env.db_path) + suffix)
            check_conn = sqlite3.connect(env.db_path)
            try:
                assert check_conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            finally:
                check_conn.close()
            assert_api_answers(env, minimum_notes=1)
    finally:
        proc.kill()
        proc.wait()


# --- `sos index` killed part-way ----------------------------------------------------------------------------

def run_index(env, rng: random.Random | None) -> int:
    """Run `sos index` in a subprocess; with `rng`, SIGKILL it at a random moment. Returns the exit code (-9 when killed)."""
    child_env = {**os.environ, "PYTHONPATH": str(API_DIR), "SOS_STATE": str(env.state), "SOS_CORE": str(env.core),
                 "SOS_EXT": str(env.ext), "SOS_PLAYBOOKS_DIR": str(env.playbooks), "SOS_MANIFEST_DIR": str(env.manifests),
                 "SOS_DEV": "1", "SOS_PORT": "9"}
    proc = subprocess.Popen([sys.executable, "-m", "sos.cli", "index"], env=child_env, cwd=API_DIR,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if rng is not None:
        time.sleep(rng.uniform(0.25, 0.9))
        proc.kill()
    return proc.wait(timeout=120)


def fts_rows(env) -> int:
    conn = sqlite3.connect(env.db_path)
    try:
        return conn.execute("SELECT count(*) FROM fts_docs").fetchone()[0]
    finally:
        conn.close()


def test_sos_index_killed_part_way_leaves_a_usable_database_and_a_rerun_completes(env):
    assert run_index(env, None) == 0
    complete = fts_rows(env)
    assert complete > 0
    rng = random.Random(3)
    killed = 0
    for _ in range(min(ROUNDS, 8)):
        code = run_index(env, rng)
        killed += code == -9
        conn = sqlite3.connect(env.db_path)
        try:
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        finally:
            conn.close()
        assert_api_answers(env, minimum_notes=0)   # the search and the guides answer on a half-built index
        assert run_index(env, None) == 0
        assert fts_rows(env) == complete, "a rerun after a killed index must end where an uninterrupted one does"
    assert killed > 0, "no round killed the index mid-run; lengthen the delay"
