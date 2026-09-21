#!/usr/bin/env python3
"""Write sample.epub: a three-chapter book, each chapter eight numbered paragraphs long, for the reader specs.

The browser suite serves it for every book the fixture box lists, so the reader can be photographed and
tested opening a book, turning a page and coming back to where it was left. Run it from this directory;
the output is checked in, so nothing needs to run it again unless the book changes."""
import zipfile

FILLER = "The kettle was on the stove, the candles were counted, and the street had learned to share what it had."
CHAPTERS = [
    ("chapter-one", "Chapter One"),
    ("chapter-two", "Chapter Two"),
    ("chapter-three", "Chapter Three"),
]
# Long enough that a chapter is several screens, so a place in the middle of one is a real place.
PARAGRAPHS = 8

XHTML = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>{title}</title></head>
<body><h1>{title}</h1>{paragraphs}</body></html>
"""

with zipfile.ZipFile("sample.epub", "w") as z:
    z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip")   # first, and stored, as the format asks
    z.writestr("META-INF/container.xml", """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>
<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>""", zipfile.ZIP_DEFLATED)
    manifest = "".join(f'<item id="{i}" href="{i}.xhtml" media-type="application/xhtml+xml"/>' for i, _ in CHAPTERS)
    spine = "".join(f'<itemref idref="{i}"/>' for i, _ in CHAPTERS)
    z.writestr("OEBPS/content.opf", f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">sos-fixture-sample</dc:identifier><dc:title>The Lights Went Out</dc:title><dc:language>en</dc:language><meta property="dcterms:modified">2026-09-18T00:00:00Z</meta></metadata>
<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>{manifest}</manifest>
<spine>{spine}</spine></package>""", zipfile.ZIP_DEFLATED)
    toc = "".join(f'<li><a href="{i}.xhtml">{t}</a></li>' for i, t in CHAPTERS)
    z.writestr("OEBPS/nav.xhtml", f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Contents</title></head>
<body><nav epub:type="toc"><ol>{toc}</ol></nav></body></html>""", zipfile.ZIP_DEFLATED)
    for i, title in CHAPTERS:
        paragraphs = "".join(f"<p>{title}, paragraph {n}. {FILLER}</p>" for n in range(1, PARAGRAPHS + 1))
        z.writestr(f"OEBPS/{i}.xhtml", XHTML.format(title=title, paragraphs=paragraphs), zipfile.ZIP_DEFLATED)
