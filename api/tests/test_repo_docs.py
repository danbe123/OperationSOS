"""The repository's documentation stays in step with the code and the spec it describes."""
from __future__ import annotations

import json
import re
from pathlib import Path

from sos import content

REPO = Path(__file__).resolve().parents[2]

HARDWARE_ITEMS = [
    "captive portal on an iphone and an android", "fallback urls and qr", "sos.local", "direct laptop link",
    "update over ethernet", "hot-plug", "landscape", "backlight device", "low power mode", "idle dim",
    "keyboard usable", "300-page pdf", "nvme boot", "pull the power", "10-minute ai session", "thermal auto-off",
    "zero swap", "five phones", "power-bank", "run twice",
    # phase 4: the sensors, the board, read aloud, a drill and a situation export
    "mains sensor detects a power cut", "internet probe flips within three minutes",
    "board appears on the kiosk when a condition is set off from a phone", "read aloud plays through the speaker",
    "a drill runs end to end", "a situation export scans between two phones",
]

HARDWARE_NOTES = ["rtl-sdr dongle", "ups hat", "speaker for read aloud", "rtl_power", "rtl_fm",
                  "/sys/class/power_supply/", "sos_sensor_files", "piper"]


def test_readme_covers_the_workflow():
    text = (REPO / "README.md").read_text(encoding="utf-8")
    for heading in ("## What it is", "## Hardware", "## Install on the Pi", "## Develop on the PC", "## Content sync",
                    "## Repository structure", "## Plans"):
        assert heading in text, heading
    assert "LD_LIBRARY_PATH=$HOME/.local/chromium-deps/usr/lib/x86_64-linux-gnu" in text
    for command in ("make venv", "make test", "make dev", "dev/smoke.sh", "make build", "make e2e",
                    "make deploy HOST=sos.local", "sudo install/install.sh", "sos sync --tier core",
                    "sos validate-playbooks --deep", "python3 -m venv --without-pip api/.venv"):
        assert command in text, command
    assert "http://10.42.0.1" in text and "http://sos.box" in text and "http://sos.local" in text
    assert "NOMAD" not in text
    for plan in ("00-overview", "01-backend-and-install", "02-frontend", "03-content", "04-maps-pipeline", "05-ai"):
        assert f"2026-09-03-{plan}.md" in text, plan


def test_hardware_checklist_has_every_spec_item_with_date_commit_result():
    text = (REPO / "docs" / "hardware-checklist.md").read_text(encoding="utf-8")
    assert "| # | Item | Date | Commit | Result |" in text
    rows = [line for line in text.splitlines() if re.match(r"^\| \d+ \|", line)]
    assert len(rows) == 26 and [int(r.split("|")[1]) for r in rows] == list(range(1, 27))
    assert all(row.count("|") == 6 for row in rows)
    lowered = text.lower()
    for item in HARDWARE_ITEMS:
        assert item in lowered, item
    for section in ("## What the hardware has to provide", "## Milestone box criteria", "## CI runs", "## Maps"):
        assert section in text, section
    for note in HARDWARE_NOTES:
        assert note in lowered, note


def test_playbooks_readme_matches_the_content_rules():
    text = (REPO / "playbooks" / "README.md").read_text(encoding="utf-8")
    for scheme in list(content.LINK_ROUTES) + ["map"]:
        assert f"`{scheme}:" in text, scheme
    for _, heading in content.SCENARIO_HEADINGS:
        assert f"## {heading}" in text, heading
    assert "{{module:<slug>}}" in text and "{#id}" in text
    assert "Rewording a checklist item without an explicit id changes its id and resets its state" in text
    schema = json.loads((REPO / "playbooks" / "schema.json").read_text(encoding="utf-8"))
    for field in schema["$defs"]["base"]["required"] + schema["$defs"]["scenario"]["required"] + ["category"]:
        assert f"`{field}`" in text, field
    for kind in content.KIND_BY_DIR.values():
        assert f"| {kind} |" in text, kind
    for value in schema["$defs"]["page"]["properties"]["category"]["enum"]:
        assert f"`{value}`" in text, value
    assert "999" in text and "111" in text and "105" in text and "0345 988 1188" in text


def test_playbooks_schema_documents_every_property():
    schema = json.loads((REPO / "playbooks" / "schema.json").read_text(encoding="utf-8"))
    assert set(schema["$defs"]) == {"base", "source", "scenario", "module", "card", "page"}
    assert set(content.KIND_BY_DIR.values()) <= set(schema["$defs"])
    for name, definition in schema["$defs"].items():
        assert definition.get("description"), f"$defs.{name} lacks a description"
        for prop, spec in definition.get("properties", {}).items():
            assert spec.get("description"), f"$defs.{name}.{prop} lacks a description"
    assert schema["$defs"]["base"]["required"] == ["id", "title", "icon", "order", "summary"]
    assert schema["$defs"]["scenario"]["required"] == ["modules", "overlays", "reviewed", "sources"]
    assert schema["$defs"]["page"]["required"] == ["category"]
