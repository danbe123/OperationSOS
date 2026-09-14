"""`sos build-books [--only ID...]`: convert every manifest item whose source.tool is "pdf2epub" from
its original PDF into a reflowable EPUB with Calibre's ebook-convert (spec
docs/superpowers/specs/2026-09-14-books-reflow-design.md section 4).

PC only: Calibre is not installed on the Pi, and conversion never happens at request time. A failed
conversion is reported and skipped — that item's manifest entry is simply left as `kind: "pdf"` until
it is fixed and retried; nothing elsewhere needs to know about a partially migrated library.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Callable

import httpx

from sos.config import Settings
from sos.manifest import Item, load_manifests
from sos.sync import SyncError, download


def convert_one(item: Item, settings: Settings, run: Callable = subprocess.run,
                client: httpx.Client | None = None, which: Callable[[str], str | None] = shutil.which,
                use_aria2: bool | None = None) -> tuple[bool, str]:
    """Produce `item.dest` (the EPUB) under the item's tier root, fetching `item.pdf_dest` (the
    original) from `item.source.url` first if it is not already on disk. Returns (ok, message)."""
    if item.source.tool != "pdf2epub":
        return False, f"{item.id}: source.tool is {item.source.tool!r}, not pdf2epub"
    if not item.pdf_dest:
        return False, f"{item.id}: manifest entry has no pdf_dest"
    if not which("ebook-convert"):
        return False, f"{item.id}: ebook-convert is not on PATH (install Calibre)"
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
    proc = run(["ebook-convert", str(pdf_path), str(epub_path), "--title", item.title],
              capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        # Clean up any partially-written file before returning failure
        epub_path.unlink(missing_ok=True)
        message = (proc.stderr or proc.stdout or "").strip()[:200]
        return False, f"{item.id}: ebook-convert failed: {message}"
    if not epub_path.exists():
        message = (proc.stderr or proc.stdout or "").strip()[:200]
        return False, f"{item.id}: ebook-convert failed: {message}"
    return True, f"{item.id}: {epub_path}"


def main(settings: Settings, only: list[str] | None = None, run: Callable = subprocess.run,
        client: httpx.Client | None = None, which: Callable[[str], str | None] = shutil.which,
        use_aria2: bool | None = None) -> int:
    items = [i for i in load_manifests(settings.manifests) if i.source.tool == "pdf2epub"]
    if only:
        wanted = set(only)
        items = [i for i in items if i.id in wanted]
    failures = 0
    for item in items:
        ok, message = convert_one(item, settings, run=run, client=client, which=which, use_aria2=use_aria2)
        print(("OK   " if ok else "FAIL ") + message)
        if not ok:
            failures += 1
    return 1 if failures else 0
