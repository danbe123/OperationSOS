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


def test_page_chunks_splits_an_epub_spine_document_and_caps_a_pdf_page():
    # A PDF "page" is one real, numbered page: one chunk, capped exactly as cap_words caps it, so the
    # fts row's page number stays the PDF's own page number.
    assert docs._page_chunks("a b c d", "pdf") == ["a b c d"]
    long_page = " ".join(f"w{i}" for i in range(1500))
    pdf_chunks = docs._page_chunks(long_page, "pdf")
    assert len(pdf_chunks) == 1 and pdf_chunks[0] == docs.cap_words(long_page)
    assert len(pdf_chunks[0].split()) == docs.PAGE_WORD_CAP

    # An EPUB "page" is a whole spine document: as many chunks as it takes, losing nothing.
    epub_chunks = docs._page_chunks(long_page, "epub")
    assert len(epub_chunks) == 3
    assert [len(c.split()) for c in epub_chunks] == [docs.PAGE_WORD_CAP, docs.PAGE_WORD_CAP, 300]
    assert " ".join(epub_chunks).split() == long_page.split()

    # An exact multiple of the cap leaves no empty trailing chunk, and an empty page is one empty chunk.
    exact = " ".join(["w"] * (docs.PAGE_WORD_CAP * 2))
    assert len(docs._page_chunks(exact, "epub")) == 2
    assert docs._page_chunks("", "epub") == [""] and docs._page_chunks("   ", "epub") == [""]


def _make_long_epub(path: Path, words: int = 1500) -> None:
    """One spine document far longer than PAGE_WORD_CAP: what Calibre's PDF->EPUB output looks like."""
    body = " ".join(f"word{i}" for i in range(words))
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml",
                    '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                    '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        zf.writestr("OEBPS/content.opf",
                    '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
                    '<metadata/><manifest><item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/></manifest>'
                    '<spine><itemref idref="c1"/></spine></package>')
        zf.writestr("OEBPS/ch1.xhtml", f"<html><body><p>{body}</p></body></html>")


def test_index_docs_keeps_a_whole_epub_spine_document(env):
    """The bug this guards: a converted book's spine document was truncated to the first 600 words and
    the rest of the book silently never reached search or AI grounding."""
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    library.upsert_items(conn, load_manifests(env.manifests))
    _make_long_epub(env.core / "docs" / "sos-test-converted.epub")
    library.refresh_items(conn, env)
    n = docs.index_docs(conn)
    rows = conn.execute("SELECT * FROM fts_docs WHERE doc_id LIKE 'sos-test-epub#%' ORDER BY page").fetchall()
    assert n == len(rows) == 3
    assert [r["doc_id"] for r in rows] == ["sos-test-epub#p1", "sos-test-epub#p2", "sos-test-epub#p3"]
    assert [len(r["body"].split()) for r in rows] == [600, 600, 300]
    # every word of the 1500 is indexed, not only the first 600
    assert sum(len(r["body"].split()) for r in rows) == 1500
    for word in ("word0", "word599", "word600", "word1400", "word1499"):
        hit = conn.execute("SELECT doc_id FROM fts_docs WHERE fts_docs MATCH ?", (f'"{word}"',)).fetchone()
        assert hit is not None, f"{word} fell out of the index"
    assert conn.execute("SELECT doc_id FROM fts_docs WHERE fts_docs MATCH '\"word1400\"'").fetchone()["doc_id"] == "sos-test-epub#p3"


def test_index_docs_indexes_a_converted_books_original_pdf_when_present(env):
    """A book converted from PDF (pdf_dest set, pdf_available=1) must index from its original PDF, not
    from the reflowed EPUB's chunk ordinals -- otherwise search results and playbook `#page=N` citations
    land on a chunk number the PDF viewer wrongly treats as a real page."""
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    library.upsert_items(conn, load_manifests(env.manifests))
    _make_long_epub(env.core / "docs" / "sos-test-converted.epub")
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF-1.4\n")
    library.refresh_items(conn, env)
    calls = []
    docs.index_docs(conn, runner=fake_runner(calls))
    rows = conn.execute("SELECT * FROM fts_docs WHERE doc_id LIKE 'sos-test-epub#%' ORDER BY page").fetchall()
    assert len(rows) == 2
    assert [r["doc_id"] for r in rows] == ["sos-test-epub#p1", "sos-test-epub#p2"]
    assert [r["page"] for r in rows] == [1, 2]
    assert [r["url"] for r in rows] == ["/doc/sos-test-epub#page=1", "/doc/sos-test-epub#page=2"]
    assert rows[0]["body"].startswith("PAGE ONE") and rows[1]["body"].startswith("PAGE TWO")
    assert "word0" not in rows[0]["body"] and "word0" not in rows[1]["body"]
    assert calls == [env.core / "docs" / "sos-test-original.pdf"]


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
