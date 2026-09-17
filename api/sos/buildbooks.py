"""`sos build-books [--only ID...]`: convert every manifest item whose source.tool is "pdf2epub" from
its original PDF into a reflowable EPUB with the box's own reflow (`sos.reflow`; spec
docs/superpowers/specs/2026-09-14-books-reflow-design.md section 4, amended 2026-09-17).

PC only: it needs `pdftotext`, and conversion never happens at request time. A failed conversion is
reported and skipped, leaving no file behind — that item's manifest entry stays (or goes back to)
`kind: "pdf"`; nothing elsewhere needs to know about a partially migrated library. Calibre used to do
the conversion and kept each PDF line as a paragraph of its own; the reflow is ours so it can be
tested line by line and tuned on the box's own books.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable

import httpx

from sos import reflow
from sos.config import Settings
from sos.manifest import Item, load_manifests
from sos.sync import SyncError, download


def convert_one(item: Item, settings: Settings, run: Callable = subprocess.run,
                client: httpx.Client | None = None, which: Callable[[str], str | None] = shutil.which,
                use_aria2: bool | None = None,
                text_runner: Callable[[Path], str] | None = None) -> tuple[bool, str]:
    """Produce `item.dest` (the EPUB) under the item's tier root, fetching `item.pdf_dest` (the
    original) from `item.source.url` first if it is not already on disk. Returns (ok, message).
    `text_runner` stands in for pdftotext in tests."""
    if item.source.tool != "pdf2epub":
        return False, f"{item.id}: source.tool is {item.source.tool!r}, not pdf2epub"
    if not item.pdf_dest:
        return False, f"{item.id}: manifest entry has no pdf_dest"
    if text_runner is None and not which("pdftotext"):
        return False, f"{item.id}: pdftotext is not on PATH (install poppler-utils)"
    root = settings.tier_root(item.tier)
    pdf_path = root / item.pdf_dest
    epub_path = root / item.dest
    if not pdf_path.exists():
        if not item.source.url:
            return False, f"{item.id}: no PDF at {pdf_path} and source has no url to fetch it from"
        # Stage into a `.part` sibling and only rename on success, exactly as `sos.sync.sync()` does:
        # aria2c (on by default when installed) writes straight to the path it is given, so an
        # interrupted fetch would otherwise leave a truncated file at `pdf_path` — which the
        # `exists()` check above then treats as the finished download on the next run.
        part = pdf_path.with_name(pdf_path.name + ".part")
        try:
            download(item.source.url, part, item.source.sha256, item.source.mirrors,
                     use_aria2=use_aria2, run=run, client=client)
        except (SyncError, httpx.HTTPError) as exc:
            return False, f"{item.id}: could not fetch {item.source.url}: {exc}"
        os.replace(part, pdf_path)
    epub_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = epub_path.with_name(epub_path.name + ".part")
    try:
        report = reflow.convert(pdf_path, tmp, item.title, text=text_runner or reflow.run_pdftotext)
    except ValueError as exc:
        # Nothing to read reflowed: an image-only scan, or an OCR layer too damaged. Left as pdf.
        tmp.unlink(missing_ok=True)
        return False, f"{item.id}: {exc}; left as pdf"
    except (OSError, subprocess.CalledProcessError) as exc:
        tmp.unlink(missing_ok=True)
        return False, f"{item.id}: pdftotext failed: {str(exc)[:200]}"
    os.replace(tmp, epub_path)
    q = report.quality
    return True, (f"{item.id}: {epub_path} ({report.paragraphs} paragraphs, median {report.median_paragraph} chars, "
                  f"{report.headings} headings, {report.chapters} chapters; {q.words} words, {q.garble:.1%} garbled)")


def main(settings: Settings, only: list[str] | None = None, run: Callable = subprocess.run,
         client: httpx.Client | None = None, which: Callable[[str], str | None] = shutil.which,
         use_aria2: bool | None = None,
         text_runner: Callable[[Path], str] | None = None) -> int:
    items = [i for i in load_manifests(settings.manifests) if i.source.tool == "pdf2epub"]
    if only:
        wanted = set(only)
        items = [i for i in items if i.id in wanted]
    failures = 0
    for item in items:
        ok, message = convert_one(item, settings, run=run, client=client, which=which, use_aria2=use_aria2,
                                  text_runner=text_runner)
        print(("OK   " if ok else "FAIL ") + message)
        if not ok:
            failures += 1
    return 1 if failures else 0
