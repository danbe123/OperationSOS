"""`sos build-nhs`: drive a zimit crawl of nhs.uk on the PC and verify the result (spec section 13)."""
from __future__ import annotations

import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

SECTIONS = ["conditions", "symptoms", "medicines", "mental-health", "tests-and-treatments", "pregnancy", "live-well"]
EXCLUDE = r"brightcove|players\.brightcove\.net|\.mp4($|\?)|\.m3u8($|\?)"
MIN_ARTICLES = 2700
ARTICLE_RE = re.compile(r"^www\.nhs\.uk/(?:" + "|".join(SECTIONS) + r")/[^?]*$")
EXT_SCRIPT_RE = re.compile(r"<script[^>]+src=[\"']https?://", re.IGNORECASE)
VIDEO_RE = re.compile(r"<video\b", re.IGNORECASE)


def build_command(out_dir: Path, date: str) -> list[str]:
    seeds = ",".join(f"https://www.nhs.uk/{s}/" for s in SECTIONS)
    return [
        "zimit", "--seeds", seeds, "--scopeType", "prefix", "--lang", "eng", "--exclude", EXCLUDE,
        "--name", "nhs_uk", "--title", f"NHS conditions and medicines (as at {date})",
        "--description", "NHS website: conditions, symptoms, medicines, mental health, tests, pregnancy, live well",
        "--creator", "NHS", "--publisher", "Operation SOS", "--zim-file", "nhs_uk.zim",
        "--output", str(out_dir), "--workers", "4",
    ]


def _zimdump(run: Callable, *args: str) -> str:
    proc = run(["zimdump", *args], capture_output=True, text=True, check=False)
    return proc.stdout


def verify(zim: Path, date: str, run: Callable = subprocess.run, sample: int = 200) -> list[str]:
    errors: list[str] = []
    entries = [e.strip() for e in _zimdump(run, "list", str(zim)).splitlines() if e.strip()]
    if any("brightcove" in e.lower() for e in entries):
        errors.append("brightcove entry present")
    articles = [e for e in entries if ARTICLE_RE.match(e)]
    if len(articles) < MIN_ARTICLES:
        errors.append(f"only {len(articles)} articles (need at least {MIN_ARTICLES})")
    zim_date = _zimdump(run, "show", "--url", "M/Date", str(zim)).strip()
    if zim_date != date:
        errors.append(f"ZIM Date is {zim_date or '(missing)'}, expected {date}")
    title = _zimdump(run, "show", "--url", "M/Title", str(zim)).strip()
    if f"as at {date}" not in title:
        errors.append(f"ZIM Title must include 'as at {date}', got '{title}'")
    ext_scripts = videos = 0
    for entry in articles[:: max(1, len(articles) // sample)][:sample]:
        html = _zimdump(run, "show", "--url", entry, str(zim))
        if EXT_SCRIPT_RE.search(html):
            ext_scripts += 1
        if VIDEO_RE.search(html):
            videos += 1
    if ext_scripts:
        errors.append(f"{ext_scripts} sampled articles carry an external <script src>")
    if videos:
        errors.append(f"{videos} sampled articles carry a <video> element")
    return errors


def main(out: str | None = None, run: Callable = subprocess.run, date: str | None = None) -> int:
    if shutil.which("zimit") is None:
        print("zimit is not on PATH (pip install zimit, or use the warc2zim toolchain); nothing built", file=sys.stderr)
        return 2
    out_dir = Path(out or "build-output/nhs")
    out_dir.mkdir(parents=True, exist_ok=True)
    date = date or dt.date.today().isoformat()
    run(build_command(out_dir, date), check=True)
    errors = verify(out_dir / "nhs_uk.zim", date, run)
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    if errors:
        return 1
    print(f"OK {out_dir / 'nhs_uk.zim'} (as at {date}); copy it to /srv/sos/core/zim/nhs_uk.zim")
    return 0
