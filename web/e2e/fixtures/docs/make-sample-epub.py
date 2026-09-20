#!/usr/bin/env python3
"""Write sample.epub: a three-chapter book with one short page per chapter, for the reader specs.

The browser suite serves it for every book the fixture box lists, so the reader can be photographed and
tested opening a book, turning a page and coming back to where it was left. Run it from this directory;
the output is checked in, so nothing needs to run it again unless the book changes."""
import zipfile

CHAPTERS = [
    ("chapter-one", "Chapter One", "The kettle was on the stove before anyone thought to ask why the lights had gone out."),
    ("chapter-two", "Chapter Two", "By the second evening the street had learned to share what it had, and the candles were counted."),
    ("chapter-three", "Chapter Three", "When the power came back nobody switched anything on for an hour, and the quiet was kept."),
]

XHTML = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>{title}</title></head>
<body><h1>{title}</h1><p>{text}</p></body></html>
"""

with zipfile.ZipFile("sample.epub", "w") as z:
    z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip")   # first, and stored, as the format asks
    z.writestr("META-INF/container.xml", """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>
<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>""", zipfile.ZIP_DEFLATED)
    manifest = "".join(f'<item id="{i}" href="{i}.xhtml" media-type="application/xhtml+xml"/>' for i, _, _ in CHAPTERS)
    spine = "".join(f'<itemref idref="{i}"/>' for i, _, _ in CHAPTERS)
    z.writestr("OEBPS/content.opf", f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">sos-fixture-sample</dc:identifier><dc:title>The Lights Went Out</dc:title><dc:language>en</dc:language><meta property="dcterms:modified">2026-09-18T00:00:00Z</meta></metadata>
<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>{manifest}</manifest>
<spine>{spine}</spine></package>""", zipfile.ZIP_DEFLATED)
    toc = "".join(f'<li><a href="{i}.xhtml">{t}</a></li>' for i, t, _ in CHAPTERS)
    z.writestr("OEBPS/nav.xhtml", f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Contents</title></head>
<body><nav epub:type="toc"><ol>{toc}</ol></nav></body></html>""", zipfile.ZIP_DEFLATED)
    for i, title, text in CHAPTERS:
        z.writestr(f"OEBPS/{i}.xhtml", XHTML.format(title=title, text=text), zipfile.ZIP_DEFLATED)
