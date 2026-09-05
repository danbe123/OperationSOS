import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from sos import db, docs, library
from sos.manifest import load_manifests

FIXTURES = Path(__file__).parent / "fixtures"
HAS_PDFTOTEXT = shutil.which("pdftotext") is not None
FAKE_TEXT = "PAGE ONE Operation SOS test document\nBoil water for one minute.\n\x0cPAGE TWO Severe bleeding\nPress hard on the wound and call 999.\n\x0c"


def fake_runner(calls):
    def run(pdf):
        calls.append(pdf)
        return FAKE_TEXT
    return run


def test_pdf_pages_splits_on_form_feed(tmp_path):
    calls = []
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    pages = docs.pdf_pages(pdf, runner=fake_runner(calls))
    assert len(pages) == 2 and pages[0].startswith("PAGE ONE") and pages[1].startswith("PAGE TWO")
    assert calls == [pdf]


def test_cap_words():
    assert docs.cap_words("a b c d", 2) == "a b"
    assert len(docs.cap_words(" ".join(["w"] * 1000)).split()) == 600


def test_extract_pages_writes_and_reuses_sidecar(tmp_path):
    calls = []
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    first = docs.extract_pages(pdf, "pdf", runner=fake_runner(calls))
    assert len(first) == 2
    assert docs.sidecar_path(pdf) == tmp_path / "x.pdf.txt" and docs.sidecar_path(pdf).exists()
    second = docs.extract_pages(pdf, "pdf", runner=fake_runner(calls))
    assert second == first and len(calls) == 1
    docs.extract_pages(pdf, "pdf", runner=fake_runner(calls), force=True)
    assert len(calls) == 2


@pytest.mark.skipif(not HAS_PDFTOTEXT, reason="pdftotext not installed")
def test_real_pdftotext_on_fixture(tmp_path):
    pdf = tmp_path / "sos-test.pdf"
    shutil.copy(FIXTURES / "docs" / "sos-test.pdf", pdf)
    pages = docs.pdf_pages(pdf)
    assert len(pages) == 2
    assert "PAGE ONE" in pages[0] and "PAGE TWO" in pages[1]


def _make_epub(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml",
                    '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                    '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        zf.writestr("OEBPS/content.opf",
                    '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
                    '<metadata/><manifest><item id="c2" href="ch2.xhtml" media-type="application/xhtml+xml"/>'
                    '<item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/></manifest>'
                    '<spine><itemref idref="c1"/><itemref idref="c2"/></spine></package>')
        zf.writestr("OEBPS/ch1.xhtml", "<html><body><nav>skip</nav><h1>Chapter one</h1><p>Store water in clean containers.</p></body></html>")
        zf.writestr("OEBPS/ch2.xhtml", "<html><body><h1>Chapter two</h1><p>Boil it for one minute.</p></body></html>")


def test_epub_pages_follow_spine_order(tmp_path):
    epub = tmp_path / "b.epub"
    _make_epub(epub)
    pages = docs.epub_pages(epub)
    assert len(pages) == 2
    assert pages[0].startswith("Chapter one") and "Store water" in pages[0] and "skip" not in pages[0]
    assert pages[1].startswith("Chapter two")


def test_index_docs_rows_and_shapes(env):
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    library.upsert_items(conn, load_manifests(env.manifests))
    shutil.copy(FIXTURES / "docs" / "sos-test.pdf", env.core / "docs" / "sos-test.pdf")
    library.refresh_items(conn, env)
    calls = []
    n = docs.index_docs(conn, runner=fake_runner(calls))
    assert n == 2
    rows = conn.execute("SELECT * FROM fts_docs WHERE kind='doc' ORDER BY page").fetchall()
    assert [r["doc_id"] for r in rows] == ["sos-test-pdf#p1", "sos-test-pdf#p2"]
    assert rows[1]["url"] == "/doc/sos-test-pdf#page=2" and rows[1]["category"] == "uk-official"
    assert rows[0]["scenarios"] == "grid-collapse" and rows[0]["title"] == "SOS test document"
    hit = conn.execute("SELECT doc_id FROM fts_docs WHERE fts_docs MATCH '\"bleeding\"'").fetchone()
    assert hit["doc_id"] == "sos-test-pdf#p2"
    assert docs.index_docs(conn, runner=fake_runner(calls)) == 2 and len(calls) == 1


def test_index_docs_skips_unreadable_file(env):
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    library.upsert_items(conn, load_manifests(env.manifests))
    (env.core / "docs" / "sos-test.pdf").write_bytes(b"not a pdf")
    library.refresh_items(conn, env)

    def failing(pdf):
        raise subprocess.CalledProcessError(1, "pdftotext")

    assert docs.index_docs(conn, runner=failing) == 0
