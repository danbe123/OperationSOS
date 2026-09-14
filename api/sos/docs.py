"""PDF and EPUB text extraction into per-page fts_docs rows. Sidecar `.txt` files next to each document
hold the extracted pages separated by form feeds so the Pi never re-runs pdftotext for an unchanged file.

A book converted from a PDF (`pdf_dest`/`pdf_available` on its `library_items` row, set by
`sos.buildbooks`) is indexed from that original PDF, not from the reflowed EPUB: search hits and
playbook citations both address `#page=N` as a real PDF page, and the reflowed EPUB -- deliberately
just a word stream, split into PAGE_WORD_CAP chunks for search -- has no page concept a citation could
target. Falling back to the EPUB's own chunk ordinals here would make `#page=N` a chunk number that
`web/src/screens/Doc.tsx` then wrongly opens as a page of the original PDF."""
from __future__ import annotations

import json
import logging
import sqlite3
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Callable

from sos.config import Settings, get_settings
from sos.kiwix import extract_text

log = logging.getLogger(__name__)
PAGE_WORD_CAP = 600
OPF_NS = "{http://www.idpf.org/2007/opf}"
CONTAINER_NS = "{urn:oasis:names:tc:opendocument:xmlns:container}"


def run_pdftotext(pdf: Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout


def pdf_pages(pdf: Path, runner: Callable[[Path], str] | None = None) -> list[str]:
    text = (runner or run_pdftotext)(Path(pdf))
    pages = [p.strip() for p in text.split("\f")]
    while pages and not pages[-1]:
        pages.pop()
    return pages


def epub_pages(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        container = ET.fromstring(zf.read("META-INF/container.xml"))
        rootfile = container.find(f".//{CONTAINER_NS}rootfile")
        opf_path = rootfile.get("full-path") if rootfile is not None else "content.opf"
        base = opf_path.rsplit("/", 1)[0] + "/" if "/" in opf_path else ""
        opf = ET.fromstring(zf.read(opf_path))
        hrefs = {item.get("id"): item.get("href") for item in opf.iter(f"{OPF_NS}item")}
        pages: list[str] = []
        for ref in opf.iter(f"{OPF_NS}itemref"):
            href = hrefs.get(ref.get("idref"))
            if not href:
                continue
            try:
                html = zf.read(base + href).decode("utf-8", errors="replace")
            except KeyError:
                continue
            paras = extract_text(html)
            if paras:
                pages.append("\n".join(paras))
    return pages


def cap_words(text: str, n: int = PAGE_WORD_CAP) -> str:
    return " ".join((text or "").split()[:n])


def _page_chunks(page: str, kind: str) -> list[str]:
    """A PDF page is already one real, page-numbered unit: always exactly one (capped) chunk, so the fts
    row's page number stays the PDF's own page number — playbooks cite `#page=N` against it. An EPUB
    "page" is a whole spine document, often far longer than PAGE_WORD_CAP words: split it into as many
    chunks as it takes so no part of the book falls out of search, instead of keeping only the first
    PAGE_WORD_CAP words and discarding the rest."""
    if kind != "epub":
        return [cap_words(page)]
    words = (page or "").split()
    if not words:
        return [""]
    return [" ".join(words[i:i + PAGE_WORD_CAP]) for i in range(0, len(words), PAGE_WORD_CAP)]


def sidecar_path(file: Path) -> Path:
    file = Path(file)
    return file.with_name(file.name + ".txt")


def extract_pages(file: Path, kind: str, runner: Callable[[Path], str] | None = None, force: bool = False) -> list[str]:
    file = Path(file)
    side = sidecar_path(file)
    if not force and side.exists() and side.stat().st_mtime >= file.stat().st_mtime:
        return side.read_text(encoding="utf-8").split("\f")
    pages = pdf_pages(file, runner) if kind == "pdf" else epub_pages(file)
    side.write_text("\f".join(pages), encoding="utf-8")
    return pages


def index_docs(conn: sqlite3.Connection, runner: Callable[[Path], str] | None = None, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    rows = conn.execute("SELECT * FROM library_items WHERE kind IN ('pdf','epub') AND available=1 ORDER BY priority").fetchall()
    conn.execute("DELETE FROM fts_docs WHERE kind='doc'")
    count = 0
    for row in rows:
        file = Path(row["local_path"] or "")
        kind = row["kind"]
        # Same resolution refresh_items/pdf_fallback_url use for pdf_dest (sos/library.py): the tier root
        # joined with the manifest-relative pdf_dest. pdf_available already confirms it exists as of the
        # last rescan; re-check here too since index can run a while after rescan.
        if kind == "epub" and row["pdf_dest"] and row["pdf_available"]:
            pdf_path = settings.tier_root(row["tier"]) / row["pdf_dest"]
            if pdf_path.exists():
                file, kind = pdf_path, "pdf"
        try:
            pages = extract_pages(file, kind, runner)
        except (OSError, subprocess.CalledProcessError, zipfile.BadZipFile, ET.ParseError) as exc:
            log.warning("skipping %s: %s", row["id"], exc)
            continue
        scenarios = " ".join(json.loads(row["scenarios_json"] or "[]"))
        n = 0
        for page in pages:
            for body in _page_chunks(page, kind):
                n += 1
                if not body:
                    continue
                conn.execute(
                    "INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)",
                    (row["title"], body, f"{row['id']}#p{n}", "doc", row["category"], scenarios, n, f"/doc/{row['id']}#page={n}"),
                )
                count += 1
    conn.commit()
    return count
