import subprocess
import zipfile
from pathlib import Path

import httpx

from sos import buildbooks
from sos.manifest import load_manifests


def _write_fake_epub(path: Path, words: int) -> None:
    """A tiny but real EPUB (zip with mimetype, container.xml, content.opf, one xhtml) with a single
    spine document holding `words` words, so sos.docs.epub_pages can read it back."""
    body = " ".join(f"w{i}" for i in range(words)) if words else "placeholder"
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


class FakeRun:
    """Records every command; simulates ebook-convert writing a tiny real EPUB, instead of running it."""

    def __init__(self, ok: bool = True, epub_words: int = 10):
        self.calls: list[list[str]] = []
        self.ok = ok
        self.epub_words = epub_words

    def __call__(self, cmd, **kwargs):
        self.calls.append(list(cmd))
        if cmd[0] == "ebook-convert" and self.ok:
            _write_fake_epub(Path(cmd[2]), self.epub_words)
        return subprocess.CompletedProcess(cmd, 0 if self.ok else 1, stdout="",
                                           stderr="" if self.ok else "conversion failed")


def _which_installed(name: str) -> str | None:
    return f"/usr/bin/{name}" if name == "ebook-convert" else None


def _item(env):
    return next(i for i in load_manifests(env.manifests) if i.id == "sos-test-epub")


def _no_text(pdf: Path) -> str:
    """A text_runner standing in for pdftotext on a PDF with no extractable text at all."""
    return ""


def _pdf_words(n: int):
    def runner(pdf: Path) -> str:
        return " ".join(f"pdfword{i}" for i in range(n))
    return runner


def test_convert_one_runs_ebook_convert_with_the_items_title_and_writes_the_epub(env):
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    run = FakeRun(ok=True)
    ok, message = buildbooks.convert_one(item, env, run=run, which=_which_installed, text_runner=_pdf_words(10))
    assert ok, message
    epub_path = env.core / "docs" / "sos-test-converted.epub"
    assert epub_path.exists()
    pdf_path = env.core / "docs" / "sos-test-original.pdf"
    assert run.calls == [["ebook-convert", str(pdf_path), str(epub_path), "--title", item.title,
                          "--enable-heuristics"]]


def test_convert_one_reports_failure_and_leaves_no_partial_epub(env):
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")

    # Custom fake that writes partial bytes before failing (simulates real ebook-convert behavior)
    class FakeRunWritesPartial:
        def __init__(self):
            self.calls = []

        def __call__(self, cmd, **kwargs):
            self.calls.append(list(cmd))
            if cmd[0] == "ebook-convert":
                # Simulate ebook-convert writing partial bytes before failing
                Path(cmd[2]).write_bytes(b"EPUB partial")
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="conversion failed")

    run = FakeRunWritesPartial()
    ok, message = buildbooks.convert_one(item, env, run=run, which=_which_installed)
    assert not ok and "ebook-convert failed" in message
    # This must prove cleanup happened, not pass by construction
    assert not (env.core / "docs" / "sos-test-converted.epub").exists()


def test_convert_one_fails_without_calling_run_when_calibre_is_not_installed(env):
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    run = FakeRun(ok=True)
    ok, message = buildbooks.convert_one(item, env, run=run, which=lambda name: None)
    assert not ok and "Calibre" in message
    assert run.calls == []


def test_convert_one_requires_pdf_dest(env):
    item = _item(env).model_copy(update={"pdf_dest": None})
    run = FakeRun(ok=True)
    ok, message = buildbooks.convert_one(item, env, run=run, which=_which_installed)
    assert not ok and "pdf_dest" in message
    assert run.calls == []


def test_convert_one_fetches_the_source_pdf_when_not_already_on_disk(env):
    item = _item(env)

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == item.source.url
        return httpx.Response(200, content=b"%PDF fetched")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    run = FakeRun(ok=True)
    ok, message = buildbooks.convert_one(item, env, run=run, client=client, which=_which_installed,
                                         use_aria2=False, text_runner=_pdf_words(10))
    assert ok, message
    assert (env.core / "docs" / "sos-test-original.pdf").read_bytes() == b"%PDF fetched"


def test_convert_one_leaves_no_truncated_pdf_when_the_fetch_fails(env):
    """aria2c (the default whenever it is installed) writes straight to the path it is given. Staged
    through a `.part` sibling, an interrupted fetch cannot leave a truncated file at pdf_path — which
    the `exists()` check would otherwise take for the finished download on the next run, converting
    and publishing a corrupt "original layout"."""
    item = _item(env)
    pdf_path = env.core / "docs" / "sos-test-original.pdf"
    calls: list[list[str]] = []

    def interrupted_aria2c(cmd, **kwargs):
        calls.append(list(cmd))
        directory = next(c for c in cmd if c.startswith("--dir="))[6:]
        name = next(c for c in cmd if c.startswith("--out="))[6:]
        Path(directory, name).write_bytes(b"%PDF trunc")  # part-way through, then the transfer dies
        return subprocess.CompletedProcess(cmd, 1)

    ok, message = buildbooks.convert_one(item, env, run=interrupted_aria2c, which=_which_installed, use_aria2=True)
    assert not ok and "could not fetch" in message
    assert calls[0][0] == "aria2c" and [c for c in calls if c[0] == "ebook-convert"] == []
    # the truncated bytes are in the .part file, and a retry sees no PDF and fetches again
    assert not pdf_path.exists()
    assert pdf_path.with_name(pdf_path.name + ".part").read_bytes() == b"%PDF trunc"


def test_main_reports_ok_and_returns_zero(env):
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    run = FakeRun(ok=True)
    code = buildbooks.main(env, run=run, which=_which_installed, text_runner=_pdf_words(10))
    assert code == 0
    assert (env.core / "docs" / "sos-test-converted.epub").exists()


def test_main_returns_nonzero_when_a_conversion_fails(env):
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    run = FakeRun(ok=False)
    code = buildbooks.main(env, run=run, which=_which_installed)
    assert code == 1


def test_main_only_filters_to_the_named_ids(env):
    run = FakeRun(ok=True)
    code = buildbooks.main(env, only=["does-not-exist"], run=run, which=_which_installed)
    assert code == 0
    assert run.calls == []


def test_convert_one_fails_when_conversion_loses_most_of_the_pdfs_text(env):
    """Scanned PDFs with a hidden OCR layer (or odd font encodings) convert to an EPUB that is almost
    all page images or garbage: below MIN_TEXT_COVERAGE, that's worse than the original PDF. FakeRun
    writes the same low word count regardless of input, so the text-fallback retry (see
    test_convert_one_falls_back_to_extracted_text_...) also comes up short, and this book stays a
    genuine, final failure -- exercising two ebook-convert calls, not one."""
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    run = FakeRun(ok=True, epub_words=10)
    ok, message = buildbooks.convert_one(item, env, run=run, which=_which_installed,
                                         text_runner=_pdf_words(100))
    assert not ok
    assert "10%" in message and "even from the extracted text" in message and "left as pdf" in message
    assert item.id in message
    epub_path = env.core / "docs" / "sos-test-converted.epub"
    assert not epub_path.exists()
    pdf_path = env.core / "docs" / "sos-test-original.pdf"
    assert pdf_path.exists() and pdf_path.read_bytes() == b"%PDF fake"
    # the direct PDF attempt, then the text-extracted retry
    assert len([c for c in run.calls if c[0] == "ebook-convert"]) == 2
    assert run.calls[1][1].endswith(".txt")


def test_convert_one_falls_back_to_extracted_text_and_succeeds_when_direct_conversion_has_low_coverage(env):
    """The case this fallback exists for (proven against real books: Kephart's Camping and Woodcraft,
    Hesperian's Where There Is No Doctor -- both over 98% coverage this way): Calibre's PDF input
    plugin pastes a scanned page in as a picture instead of using the very OCR text pdftotext already
    extracts, so the direct conversion fails the coverage gate -- but feeding that same extracted text
    through Calibre's TXT input instead succeeds cleanly."""
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")

    class FakeRunLowFromPdfHighFromText:
        def __init__(self):
            self.calls: list[list[str]] = []

        def __call__(self, cmd, **kwargs):
            self.calls.append(list(cmd))
            if cmd[0] == "ebook-convert":
                _write_fake_epub(Path(cmd[2]), 10 if cmd[1].endswith(".pdf") else 90)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    run = FakeRunLowFromPdfHighFromText()
    ok, message = buildbooks.convert_one(item, env, run=run, which=_which_installed,
                                         text_runner=_pdf_words(100))
    assert ok, message
    assert "90%" in message and "from extracted text" in message
    epub_path = env.core / "docs" / "sos-test-converted.epub"
    assert epub_path.exists()
    ebook_convert_calls = [c for c in run.calls if c[0] == "ebook-convert"]
    assert len(ebook_convert_calls) == 2
    assert ebook_convert_calls[0][1].endswith("sos-test-original.pdf")
    assert ebook_convert_calls[1][1].endswith(".txt")
    # the temp .txt file used for the fallback is cleaned up, not left behind
    assert not Path(ebook_convert_calls[1][1]).exists()


def test_convert_one_ok_message_reports_text_coverage_at_the_threshold(env):
    """Coverage at or above MIN_TEXT_COVERAGE (0.5) is a pass, not just above it."""
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    run = FakeRun(ok=True, epub_words=50)
    ok, message = buildbooks.convert_one(item, env, run=run, which=_which_installed,
                                         text_runner=_pdf_words(100))
    assert ok, message
    assert "50%" in message and "of the PDF's text" in message
    assert (env.core / "docs" / "sos-test-converted.epub").exists()


def test_convert_one_fails_when_the_pdf_has_no_extractable_text(env):
    """migration-brief-3: st-31-91b-sf-medical-handbook.pdf is a pure image scan (pdftotext gives 0
    words); Calibre still produces an EPUB of near-empty page-image paragraphs, and the old behavior
    ("no gate" when pdf_word_count is 0) reported that as OK. A PDF with no extractable text can never
    yield a reflowable EPUB, so this must FAIL and leave the item as pdf (spec section 4)."""
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    run = FakeRun(ok=True, epub_words=5)
    ok, message = buildbooks.convert_one(item, env, run=run, which=_which_installed, text_runner=_no_text)
    assert not ok
    assert message == f"{item.id}: the PDF has no extractable text (image-only scan); left as pdf"
    epub_path = env.core / "docs" / "sos-test-converted.epub"
    assert not epub_path.exists()
    pdf_path = env.core / "docs" / "sos-test-original.pdf"
    assert pdf_path.exists() and pdf_path.read_bytes() == b"%PDF fake"

    code = buildbooks.main(env, run=FakeRun(ok=True, epub_words=5), which=_which_installed, text_runner=_no_text)
    assert code == 1


def test_main_threads_text_runner_and_returns_nonzero_on_a_coverage_failure(env):
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    run = FakeRun(ok=True, epub_words=1)
    code = buildbooks.main(env, run=run, which=_which_installed, text_runner=_pdf_words(100))
    assert code == 1
    assert not (env.core / "docs" / "sos-test-converted.epub").exists()


def test_convert_one_reports_a_corrupt_epub_as_fail_without_crashing(env):
    """A real Calibre crash mode: ebook-convert exits 0 but writes a corrupt or non-zip EPUB. The
    coverage gate's `docs.epub_pages` read of that file must never propagate: a FAIL is never
    batch-blocking (spec section 4). Garbage from both the direct and text-fallback attempts is a
    genuine, final failure -- exercising two ebook-convert calls, not one."""
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")

    class FakeRunWritesGarbage:
        def __init__(self):
            self.calls = []

        def __call__(self, cmd, **kwargs):
            self.calls.append(list(cmd))
            if cmd[0] == "ebook-convert":
                Path(cmd[2]).write_bytes(b"not a zip file")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    run = FakeRunWritesGarbage()
    ok, message = buildbooks.convert_one(item, env, run=run, which=_which_installed,
                                         text_runner=_pdf_words(100))
    assert not ok
    assert "0%" in message and "even from the extracted text" in message and item.id in message
    assert not (env.core / "docs" / "sos-test-converted.epub").exists()
    assert len([c for c in run.calls if c[0] == "ebook-convert"]) == 2


def test_convert_one_retries_with_flow_splitting_off_after_a_split_error(env):
    """Calibre's flow splitter can crash on a book it cannot find a reasonable split point for
    (calibre.ebooks.oeb.transforms.split.SplitError). That's a Calibre limitation, not a property of
    the book -- the same PDF converts cleanly with --flow-size 0 -- so the tool retries once with flow
    splitting off rather than reporting a permanent failure."""
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")

    class FakeRunSplitErrorThenOk:
        def __init__(self):
            self.calls: list[list[str]] = []

        def __call__(self, cmd, **kwargs):
            self.calls.append(list(cmd))
            if len(self.calls) == 1:
                return subprocess.CompletedProcess(cmd, 1, stdout="", stderr=(
                    "calibre.ebooks.oeb.transforms.split.SplitError: Could not find reasonable "
                    "point at which to split: index.html Sub-tree size: 347 KB"))
            _write_fake_epub(Path(cmd[2]), 10)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    run = FakeRunSplitErrorThenOk()
    ok, message = buildbooks.convert_one(item, env, run=run, which=_which_installed, text_runner=_pdf_words(10))
    assert ok, message
    assert "(flow splitting off)" in message
    epub_path = env.core / "docs" / "sos-test-converted.epub"
    assert epub_path.exists()
    pdf_path = env.core / "docs" / "sos-test-original.pdf"
    base_cmd = ["ebook-convert", str(pdf_path), str(epub_path), "--title", item.title, "--enable-heuristics"]
    assert run.calls == [base_cmd, base_cmd + ["--flow-size", "0"]]


def test_convert_one_does_not_retry_a_non_split_error_failure(env):
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    run = FakeRun(ok=False)
    ok, message = buildbooks.convert_one(item, env, run=run, which=_which_installed)
    assert not ok and "ebook-convert failed" in message
    assert len(run.calls) == 1


def test_convert_one_fails_when_the_retry_also_hits_a_split_error(env):
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")

    class FakeRunSplitErrorTwice:
        def __init__(self):
            self.calls: list[list[str]] = []

        def __call__(self, cmd, **kwargs):
            self.calls.append(list(cmd))
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr=(
                "calibre.ebooks.oeb.transforms.split.SplitError: Could not find reasonable point "
                "at which to split: index.html Sub-tree size: 347 KB"))

    run = FakeRunSplitErrorTwice()
    ok, message = buildbooks.convert_one(item, env, run=run, which=_which_installed)
    assert not ok and "ebook-convert failed" in message
    assert len(run.calls) == 2
    assert not (env.core / "docs" / "sos-test-converted.epub").exists()


def test_main_continues_past_a_corrupt_epub_and_still_converts_the_next_item(env, monkeypatch):
    """The bug this guards: an unguarded epub_pages() read let a BadZipFile/ParseError propagate out of
    convert_one, and main()'s loop has no per-item try/except -- so the whole batch aborted and every
    remaining item was skipped. Two items: the fixture manifest only carries one pdf2epub item, so the
    second is a synthesized copy (via monkeypatch on load_manifests) rather than a fixture edit.

    Item 1 writes garbage on both its direct-PDF attempt AND its text-fallback retry (a genuinely
    unconvertible book), so the fake distinguishes attempts by call order rather than by path -- the
    fallback's temp .txt file has a random name unrelated to the original PDF's."""
    item1 = _item(env)
    item2 = item1.model_copy(update={"id": "sos-test-epub-2", "dest": "docs/sos-test-converted-2.epub",
                                     "pdf_dest": "docs/sos-test-original-2.pdf"})
    monkeypatch.setattr(buildbooks, "load_manifests", lambda paths: [item1, item2])
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    (env.core / "docs" / "sos-test-original-2.pdf").write_bytes(b"%PDF fake 2")

    class FakeRunFirstCorruptSecondOk:
        def __init__(self):
            self.calls = []
            self.ebook_convert_calls = 0

        def __call__(self, cmd, **kwargs):
            self.calls.append(list(cmd))
            if cmd[0] == "ebook-convert":
                self.ebook_convert_calls += 1
                if self.ebook_convert_calls <= 2:  # item 1: direct attempt, then its text fallback
                    Path(cmd[2]).write_bytes(b"not a zip file")
                else:  # item 2: succeeds on its first (direct) attempt
                    _write_fake_epub(Path(cmd[2]), 60)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    run = FakeRunFirstCorruptSecondOk()
    code = buildbooks.main(env, run=run, which=_which_installed, text_runner=_pdf_words(100))
    assert code == 1
    # item 1's two attempts (direct + fallback), then item 2's one successful attempt
    assert run.ebook_convert_calls == 3
    assert not (env.core / "docs" / "sos-test-converted.epub").exists()
    assert (env.core / "docs" / "sos-test-converted-2.epub").exists()
