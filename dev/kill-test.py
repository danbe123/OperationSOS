#!/usr/bin/env python3
"""End-to-end crash test of the real API: make state over HTTP, kill -9 uvicorn, start it again, check nothing was lost.

Runs the real `uvicorn sos.main:app` with dev settings against a SCRATCH state directory (never the dev or the box's
database), on a port of 8100 or above, with no kiwix-serve and no embedding server (search must still answer, with
what the box itself holds). Prints how long the API took to answer after each kill.

    PYTHONPATH=api api/.venv/bin/python dev/kill-test.py [--port 8100] [--rounds 3] [--keep]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def call(base: str, method: str, path: str, body=None, timeout=5):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read() or b"null")


def start(base_env: dict, port: int, log: Path) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "sos.main:app", "--host", "127.0.0.1", "--port", str(port), "--workers", "1"],
        env=base_env, cwd=REPO / "api", stdout=log.open("ab"), stderr=subprocess.STDOUT)


def wait_up(base: str, proc: subprocess.Popen, limit=60.0) -> float:
    began = time.monotonic()
    while time.monotonic() - began < limit:
        if proc.poll() is not None:
            raise SystemExit(f"the API exited with {proc.returncode} while starting")
        try:
            if call(base, "GET", "/api/status", timeout=1)[0] == 200:
                return time.monotonic() - began
        except (urllib.error.URLError, OSError, ValueError):
            pass
        time.sleep(0.05)
    raise SystemExit("the API did not answer within a minute")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8100)
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    if args.port < 8100:
        raise SystemExit("use a port of 8100 or above: 8090 and 8091 belong to kiwix-serve and the embedding server")
    scratch = Path(tempfile.mkdtemp(prefix="kill-test-", dir=os.environ.get("SOS_KILL_TEST_DIR", "/tmp/recovery-scratch")))
    state, core = scratch / "state", scratch / "core"
    for d in (state / "config", core / "zim", core / "docs", core / "maps", core / "models"):
        d.mkdir(parents=True)
    dead = args.port + 9  # nothing listens here: no kiwix-serve, no embedding server
    env = {**os.environ, "PYTHONPATH": str(REPO / "api"), "SOS_DEV": "1", "SOS_STATE": str(state), "SOS_CORE": str(core),
           "SOS_EXT": str(scratch / "ext"), "SOS_WEB": str(scratch / "web"), "SOS_PORT": str(args.port),
           "SOS_MANIFEST_DIR": str(REPO / "dev" / "manifest"), "SOS_PLAYBOOKS_DIR": str(REPO / "playbooks"),
           "SOS_KIWIX_URL": f"http://127.0.0.1:{dead}/kiwix", "SOS_EMBED_URL": f"http://127.0.0.1:{dead + 1}",
           "SOS_LLAMA_URL": f"http://127.0.0.1:{dead + 2}", "SOS_SENSORS": "0"}
    log = scratch / "api.log"
    base = f"http://127.0.0.1:{args.port}"
    print(f"scratch state: {scratch}")
    subprocess.run([sys.executable, "-m", "sos.cli", "index"], env=env, cwd=REPO / "api", check=True, capture_output=True)
    proc = start(env, args.port, log)
    timings = [("cold start (first boot, index built)", wait_up(base, proc))]
    problems: list[str] = []
    try:
        slug = next(p["slug"] for p in call(base, "GET", "/api/playbooks")[1] if call(base, "GET", f"/api/playbooks/{p['slug']}")[1]["checklist"])
        item = call(base, "GET", f"/api/playbooks/{slug}")[1]["checklist"][0]["id"]
        acked_notes: list[str] = []
        for rnd in range(1, args.rounds + 1):
            tag = f"round{rnd}"
            call(base, "PUT", f"/api/playbooks/{slug}/checklist/{item}", {"checked": rnd % 2 == 1})
            acked_notes.append(f"{tag}-note")
            call(base, "POST", "/api/notes", {"kind": "note", "title": f"{tag}-note", "body": "written before the kill"})
            acked_notes.append(f"{tag}-pin")
            call(base, "POST", "/api/notes", {"kind": "pin", "title": f"{tag}-pin", "body": "", "lat": 51.5, "lon": -0.12})
            call(base, "PUT", "/api/conditions/power", {"state": "off" if rnd % 2 else "working", "note": tag})
            call(base, "PUT", "/api/settings/people", {"people": 2 + rnd})

            # a burst of writes in flight when the kill lands: every one the API answered 200 to must survive
            stop = threading.Event()

            def burst():
                i = 0
                while not stop.is_set():
                    i += 1
                    title = f"{tag}-burst{i}"
                    try:
                        if call(base, "POST", "/api/notes", {"kind": "note", "title": title, "body": "x"}, timeout=2)[0] == 200:
                            acked_notes.append(title)
                    except (urllib.error.URLError, OSError, ValueError):
                        return

            worker = threading.Thread(target=burst)
            worker.start()
            time.sleep(0.6)
            killed_at = time.monotonic()
            os.kill(proc.pid, signal.SIGKILL)
            proc.wait()
            stop.set()
            worker.join(10)
            proc = start(env, args.port, log)
            up = wait_up(base, proc)
            timings.append((f"round {rnd}: kill -9 to first answer (including {len(acked_notes)} notes so far)", time.monotonic() - killed_at))
            timings.append((f"round {rnd}: process start to first answer", up))

            titles = {n["title"] for n in call(base, "GET", "/api/notes")[1]}
            lost = [t for t in acked_notes if t not in titles]
            if lost:
                problems.append(f"round {rnd}: {len(lost)} acknowledged notes lost, e.g. {lost[:3]}")
            checked = [i for i in call(base, "GET", f"/api/playbooks/{slug}")[1]["checklist"] if i["id"] == item][0]["checked"]
            if checked != (rnd % 2 == 1):
                problems.append(f"round {rnd}: the tick on {slug}/{item} is {checked}")
            power = call(base, "GET", "/api/conditions")[1]["power"]
            if power["state"] != ("off" if rnd % 2 else "working") or power.get("note") != tag:
                problems.append(f"round {rnd}: the power condition came back as {power}")
            people = call(base, "GET", "/api/settings/people")[1]["people"]
            if people != 2 + rnd:
                problems.append(f"round {rnd}: people is {people}")
            began = time.monotonic()
            status, found = call(base, "GET", "/api/search?q=water")
            timings.append((f"round {rnd}: search 'water' with no kiwix and no embedding server ({len(found['results'])} results)", time.monotonic() - began))
            if status != 200 or not found["results"]:
                problems.append(f"round {rnd}: degraded search returned {status} with {len(found.get('results', []))} results")
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(10)
    print()
    for label, seconds in timings:
        print(f"{seconds:7.2f} s  {label}")
    print()
    if problems:
        print("FAILED:")
        for p in problems:
            print("  " + p)
    else:
        print(f"OK: {args.rounds} kill -9 rounds, every acknowledged write present, API answering each time")
    if not args.keep:
        shutil.rmtree(scratch, ignore_errors=True)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
