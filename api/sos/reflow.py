"""Reflow: a PDF's extracted text into a real book.

`pdftotext` (reading order, no `-layout`) gives the words page by page, but a page's lines are still the
PDF's lines: running heads and page numbers sit among them, sentences break at the right margin and
hyphenate, columns follow one another. This module turns that into headings, paragraphs and lists, and
writes them as an EPUB the reader paginates itself. Calibre used to do this job and kept every PDF line
as its own paragraph; this is the box's own reflow so it can be tested and tuned line by line.

Everything here is pure Python on text; the one subprocess is `pdftotext`, on the PC only.
"""
from __future__ import annotations

import re
import subprocess
import uuid
import zipfile
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Callable

# --- from the PDF ----------------------------------------------------------------------------------


def run_pdftotext(pdf: Path) -> str:
    """The text in reading order: columns one after another, which `-layout` (the search index's
    extraction) does not give."""
    return subprocess.run(["pdftotext", "-enc", "UTF-8", str(pdf), "-"], capture_output=True, text=True, check=True).stdout


def split_pages(text: str) -> list[str]:
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return pages


# --- the page furniture -----------------------------------------------------------------------------

_ROMAN = re.compile(r"^[ivxlcdm]{1,7}$", re.I)
_PAGE_NO = re.compile(r"^(page\s+)?\d{1,4}(\s+of\s+\d{1,4})?$", re.I)
EDGE_LINES = 4          # how many lines at the top and bottom of a page can be furniture (a head can take three)
FURNITURE_SHARE = 0.25  # a line at a page's edge on this share of pages (and at least three) is furniture


def _furniture_key(line: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\d+", "#", line.strip().lower()))


def _is_page_number(line: str) -> bool:
    s = line.strip()
    return bool(s) and (bool(_PAGE_NO.match(s)) or bool(_ROMAN.match(s)))


def strip_furniture(pages: list[str]) -> list[list[str]]:
    """Each page as its lines, minus running heads, running feet and page numbers: a line that recurs at
    the edge of a quarter of the pages is furniture wherever it sits, as is any line that is only a number."""
    split = [[ln.rstrip() for ln in page.split("\n")] for page in pages]
    counts: dict[str, int] = {}
    for lines in split:
        body = [ln for ln in lines if ln.strip()]
        edges = body[:EDGE_LINES] + body[-EDGE_LINES:] if len(body) > 2 * EDGE_LINES else body
        for ln in {_furniture_key(x) for x in edges}:
            counts[ln] = counts.get(ln, 0) + 1
    threshold = max(3, int(FURNITURE_SHARE * len(split)))
    furniture = {k for k, n in counts.items() if n >= threshold and len(k) < 80}
    out: list[list[str]] = []
    previous_top: list[str] = []
    for lines in split:
        kept = [ln for ln in lines if not _is_page_number(ln) and _furniture_key(ln) not in furniture]
        # A chapter title printed at the top of each of its pages recurs on too few pages to count
        # book-wide, but it is the same line at the top of the page before: keep its first appearance
        # (where the chapter starts) and drop the repeats.
        body = [ln for ln in kept if ln.strip()]
        top = [_furniture_key(ln) for ln in body[:EDGE_LINES]]
        repeats = {k for k in top if k in previous_top}
        if repeats:
            seen_top = 0
            trimmed: list[str] = []
            for ln in kept:
                if ln.strip():
                    seen_top += 1
                    if seen_top <= EDGE_LINES and _furniture_key(ln) in repeats:
                        continue
                trimmed.append(ln)
            kept = trimmed
        previous_top = top
        out.append(kept)
    return out


# --- lines into blocks ------------------------------------------------------------------------------


@dataclass(frozen=True)
class Block:
    kind: str   # "h1" | "h2" | "p" | "li"
    text: str


_TERMINAL = tuple(".!?:;\"'”’)]")
_HEADING_WORD = re.compile(r"^(chapter|part|section|appendix|book|volume|lesson|unit)\b", re.I)
_NUMBERED = re.compile(r"^\d{1,3}(\.\d{1,3})*\.?\s+[A-Z]")
# A lettered item is one letter or a small roman numeral: "aft." or "cut." at a line's start is a word.
_BULLET = re.compile(r"^([•·▪■●○\-–—*]|\(?([a-z]|[ivx]{1,3}|\d{1,3})[.)])\s+")
_SYMBOL_BULLET = re.compile(r"^([•·▪■●○\-–—*]|\(?[a-z][.)])\s+")
_NUMBERED_ITEM = re.compile(r"^\(?\d{1,3}[.)]\s+")
SHORT_LINE = 0.55       # a line under this share of the page's typical width ends its paragraph
MAX_HEADING = 90


def _caps_ratio(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    return sum(1 for c in letters if c.isupper()) / len(letters) if letters else 0.0


def looks_like_heading(line: str) -> str | None:
    """`h1` for a chapter or a capitalised title line, `h2` for a numbered or short titled line, else None."""
    s = line.strip()
    if not s or len(s) > MAX_HEADING or s.endswith((".", ",", ";")) or _SYMBOL_BULLET.match(s):
        return None
    letters = sum(1 for c in s if c.isalpha())
    if letters < 3:
        return None
    if _HEADING_WORD.match(s):
        return "h1"
    if _caps_ratio(s) > 0.85 and letters >= 4:
        return "h1"
    if _NUMBERED.match(s) and len(s.split()) <= 12:
        return "h2"
    return None


def _typical_width(lines: list[str]) -> int:
    widths = sorted(len(ln.strip()) for ln in lines if ln.strip())
    return widths[len(widths) // 2] if widths else 0


def _join(prev: str, line: str) -> str:
    """The next line onto its paragraph: a hyphen at the right margin is mended when the continuation
    is lowercase ("wood-" + "craft" → "woodcraft"); a real hyphenated compound keeps its hyphen."""
    if not prev.endswith("-"):
        return f"{prev} {line}"
    last = prev.rsplit(" ", 1)[-1]
    plain_break = len(last) > 1 and last[-2].isalpha() and "-" not in last[:-1]
    if plain_break and line[:1].islower():
        return prev[:-1] + line          # "wood-" + "craft" → "woodcraft"
    return prev + line                   # "fore-and-" + "aft" → "fore-and-aft"; "T-" + "Shirt" → "T-Shirt"


def blocks_from_pages(pages: list[list[str]]) -> list[Block]:
    blocks: list[Block] = []
    open_kind: str | None = None
    open_text = ""

    def close() -> None:
        nonlocal open_kind, open_text
        if open_kind and open_text.strip():
            blocks.append(Block(open_kind, re.sub(r"\s+", " ", open_text).strip()))
        open_kind, open_text = None, ""

    heading_open = False   # the last block is a heading with no blank line after it yet
    closed_short = False   # the last block was closed by the short-line rule

    for lines in pages:
        width = _typical_width(lines)
        stripped = [re.sub(r"\s+", " ", raw.strip()) for raw in lines]
        for i, line in enumerate(stripped):
            if not line:
                close()
                heading_open = closed_short = False
                continue
            heading = looks_like_heading(line)
            if heading == "h2" and _NUMBERED_ITEM.match(line):
                # "2. Choosing a site" above prose is a heading; "2. Turn off the gas" among "1." and "3." is a step.
                following = next((x for x in stripped[i + 1:] if x), "")
                if _NUMBERED_ITEM.match(following) or (open_kind == "li"):
                    heading = None
            if heading and heading_open and blocks and blocks[-1].kind == heading:
                # "SHELTER VENTILATION" / "WITHOUT FILTERS": one title set over two lines.
                blocks[-1] = Block(heading, f"{blocks[-1].text} {line}")
                continue
            if heading and (open_kind is None or open_text.rstrip().endswith(_TERMINAL)):
                close()
                blocks.append(Block(heading, line))
                heading_open, closed_short = True, False
                continue
            heading_open = False
            if _BULLET.match(line):
                close()
                closed_short = False
                open_kind, open_text = "li", _BULLET.sub("", line, count=1)
                continue
            if closed_short and line[:1].islower() and blocks and blocks[-1].kind in ("p", "li"):
                # "ensure your own safety;" was closed as a short line, but "if necessary, ..." carries it on.
                last = blocks.pop()
                open_kind, open_text = last.kind, last.text
            closed_short = False
            if open_kind in ("p", "li"):
                open_text = _join(open_text, line)
            else:
                close()
                open_kind, open_text = "p", line
            # A short line ending in punctuation is a paragraph's last line.
            if width and len(line) < SHORT_LINE * width and line.endswith(_TERMINAL):
                close()
                closed_short = True
        # A paragraph runs across the page break only when the page ended mid-sentence.
        if open_kind and open_text.rstrip().endswith(_TERMINAL):
            close()
    close()
    return blocks


# --- is the text worth reflowing? -----------------------------------------------------------------


@dataclass(frozen=True)
class Quality:
    words: int
    garble: float        # share of word-like tokens that are not plausible words (OCR damage)
    short_share: float   # share of body lines that are under half the page's typical width

    @property
    def damaged(self) -> bool:
        return self.words < MIN_WORDS or self.garble > GARBLE_MAX


GARBLE_MAX = 0.03      # above this share of garbled words the OCR is not worth reading
MIN_WORDS = 120
MIN_MEDIAN_PARAGRAPH = 25   # under this many characters a book has reflowed into fragments: tables, lists, columns
_VOWELS = set("aeiouyAEIOUY")


def _garbled(token: str) -> bool:
    core = token.strip("\"'“”‘’()[]{}.,;:!?-–—*•·/")
    if len(core) < 3 or not any(c.isalpha() for c in core):
        return False
    if re.search(r"[^A-Za-z’'\-]", core):
        return True                               # digits or symbols inside a word
    if re.search(r"[a-z][A-Z]", core):
        return True                               # a case flip mid-word: "‘Jlustration", "bEfore"
    if len(core) >= 4 and not any(c in _VOWELS for c in core):
        return True                               # no vowel at all: "cnbdr"
    return False


def text_quality(pages: list[list[str]]) -> Quality:
    lines = [ln.strip() for page in pages for ln in page if ln.strip()]
    tokens = [t for ln in lines for t in ln.split()]
    wordish = [t for t in tokens if sum(c.isalpha() for c in t) >= 3]
    garbled = sum(1 for t in wordish if _garbled(t))
    widths = sorted(len(ln) for ln in lines)
    typical = widths[len(widths) // 2] if widths else 0
    short = sum(1 for ln in lines if typical and len(ln) < 0.5 * typical)
    return Quality(words=len(tokens), garble=(garbled / len(wordish)) if wordish else 1.0,
                   short_share=(short / len(lines)) if lines else 1.0)


# --- the EPUB ------------------------------------------------------------------------------------

CHAPTER_WORDS = 4000     # split a long run of text at the next h2 once it passes this
MIN_CHAPTER_WORDS = 120  # a heading with almost nothing under it joins the next chapter

STYLE = """body { font-family: Georgia, 'Times New Roman', serif; line-height: 1.45; margin: 0 4%; }
h1 { font-size: 1.5em; margin: 1.2em 0 0.6em; line-height: 1.2; }
h2 { font-size: 1.2em; margin: 1em 0 0.5em; line-height: 1.25; }
p { margin: 0 0 0.7em; text-align: left; }
ul { margin: 0 0 0.7em 1.2em; padding: 0; }
li { margin: 0 0 0.3em; }
"""


def chapters(blocks: list[Block]) -> list[tuple[str, list[Block]]]:
    """Cut the blocks into chapters at h1 headings, and at h2 headings once a chapter runs long; a
    chapter with almost no text folds into the next so the table of contents is not a list of stubs."""
    out: list[tuple[str, list[Block]]] = []
    title = "Start"
    current: list[Block] = []
    words = 0
    for b in blocks:
        cut = b.kind == "h1" or (b.kind == "h2" and words > CHAPTER_WORDS)
        if cut and current:
            out.append((title, current))
            current, words = [], 0
        if cut:
            title = b.text
        current.append(b)
        words += len(b.text.split())
    if current:
        out.append((title, current))
    merged: list[tuple[str, list[Block]]] = []
    for title, blks in out:
        if merged and sum(len(x.text.split()) for x in merged[-1][1]) < MIN_CHAPTER_WORDS:
            prev_title, prev = merged.pop()
            merged.append((prev_title, prev + blks))
        else:
            merged.append((title, blks))
    return merged


def _chapter_xhtml(title: str, blks: list[Block]) -> str:
    body: list[str] = []
    in_list = False
    for b in blks:
        if b.kind == "li":
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{escape(b.text)}</li>")
            continue
        if in_list:
            body.append("</ul>")
            in_list = False
        body.append(f"<{b.kind}>{escape(b.text)}</{b.kind}>")
    if in_list:
        body.append("</ul>")
    return ('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">'
            f'<head><title>{escape(title)}</title><link rel="stylesheet" type="text/css" href="style.css"/></head>'
            f"<body><section epub:type=\"chapter\">{''.join(body)}</section></body></html>")


def write_epub(path: Path, title: str, blocks: list[Block], author: str | None = None, language: str = "en") -> int:
    """Write an EPUB 3 of these blocks. Returns the number of chapters."""
    parts = chapters(blocks)
    book_id = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, 'sos:' + title)}"
    manifest = ['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
                '<item id="css" href="style.css" media-type="text/css"/>']
    spine: list[str] = []
    toc: list[str] = []
    files: list[tuple[str, str]] = []
    for n, (chapter_title, blks) in enumerate(parts, 1):
        name = f"ch{n:03d}.xhtml"
        manifest.append(f'<item id="ch{n}" href="{name}" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="ch{n}"/>')
        toc.append(f'<li><a href="{name}">{escape(chapter_title)}</a></li>')
        files.append((f"OEBPS/{name}", _chapter_xhtml(chapter_title, blks)))
    opf = ('<?xml version="1.0" encoding="utf-8"?>\n<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">'
           '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
           f"<dc:identifier id=\"uid\">{book_id}</dc:identifier><dc:title>{escape(title)}</dc:title><dc:language>{language}</dc:language>"
           + (f"<dc:creator>{escape(author)}</dc:creator>" if author else "")
           + '<meta property="dcterms:modified">2026-01-01T00:00:00Z</meta></metadata>'
           f"<manifest>{''.join(manifest)}</manifest><spine>{''.join(spine)}</spine></package>")
    nav = ('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">'
           f"<head><title>{escape(title)}</title></head><body><nav epub:type=\"toc\"><h1>Contents</h1><ol>{''.join(toc)}</ol></nav></body></html>")
    container = ('<?xml version="1.0" encoding="utf-8"?>\n<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                 '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", container, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/content.opf", opf, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/nav.xhtml", nav, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/style.css", STYLE, compress_type=zipfile.ZIP_DEFLATED)
        for name, content in files:
            zf.writestr(name, content, compress_type=zipfile.ZIP_DEFLATED)
    return len(parts)


# --- the whole conversion -------------------------------------------------------------------------


@dataclass(frozen=True)
class Report:
    quality: Quality
    blocks: int
    paragraphs: int
    headings: int
    chapters: int
    median_paragraph: int


def convert(pdf: Path, epub: Path, title: str, author: str | None = None,
            text: Callable[[Path], str] = run_pdftotext) -> Report:
    """PDF to EPUB, or raise ValueError when the text is not worth reading reflowed (nothing extractable,
    or an OCR layer too damaged), leaving no file behind."""
    pages = strip_furniture(split_pages(text(pdf)))
    quality = text_quality(pages)
    if quality.words < MIN_WORDS:
        raise ValueError(f"no usable text ({quality.words} words)")
    if quality.damaged:
        raise ValueError(f"text layer damaged ({quality.garble:.0%} of words garbled)")
    blocks = blocks_from_pages(pages)
    paras = [b for b in blocks if b.kind == "p"]
    lens = sorted(len(b.text) for b in paras)
    median = lens[len(lens) // 2] if lens else 0
    if median < MIN_MEDIAN_PARAGRAPH:
        raise ValueError(f"reads as fragments (median paragraph {median} chars): tables, lists or columns")
    n = write_epub(epub, title, blocks, author=author)
    return Report(quality=quality, blocks=len(blocks), paragraphs=len(paras),
                  headings=sum(1 for b in blocks if b.kind in ("h1", "h2")), chapters=n,
                  median_paragraph=median)
