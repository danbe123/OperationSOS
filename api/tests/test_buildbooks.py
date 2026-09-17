"""`sos build-books`: the PDF is fetched if missing, the box's own reflow writes the EPUB, and a book whose
text is not worth reflowing is left as a PDF with no file behind."""
import subprocess
from pathlib import Path

import httpx

from sos import buildbooks, docs
from sos.manifest import load_manifests

NOUNS = "fox owl hare stag otter heron badger vole".split()
BOOK = "\f".join(
    "\n".join([
        "FIELD NOTES", "", f"CHAPTER {n}", "",
        f"The quick brown {w} jumps over the lazy dog and keeps",
        f"on running until the river, where the {w} stops to drink.",
        f"It was a long day. The {w} slept.", "", f"{n}. Water for a {w}", "",
        f"Boil it for {n} minutes, says the {w}. A rolling boil is enough at any",
        "height a walker in Britain will reach.", "",
        f"Then let the {w} cool before you drink it, or you will scald",
        "your mouth for nothing.", str(10 + n),
    ]) for n, w in enumerate(NOUNS, 1))


def _text(pdf: Path) -> str:
    return BOOK


def _damaged(pdf: Path) -> str:
    return "‘Jlustration fr0m cnbdr bEfore tbe w4r " * 60


def _which_installed(name: str) -> str | None:
    return f"/usr/bin/{name}" if name == "pdftotext" else None


def _which_nothing(name: str) -> str | None:
    return None


def _item(env):
    return next(i for i in load_manifests(env.manifests) if i.id == "sos-test-epub")


def test_convert_one_reflows_the_pdf_into_an_epub_the_indexer_reads(env):
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    ok, message = buildbooks.convert_one(item, env, which=_which_installed, text_runner=_text)
    assert ok, message
    epub_path = env.core / "docs" / "sos-test-converted.epub"
    assert epub_path.exists() and not epub_path.with_name(epub_path.name + ".part").exists()
    assert "paragraphs" in message and "garbled" in message
    text = " ".join(docs.epub_pages(epub_path))
    assert "fox jumps over the lazy dog and keeps on running until the river" in text   # lines joined
    assert "FIELD NOTES FIELD NOTES" not in text                                        # the running head is gone


def test_convert_one_leaves_a_damaged_scan_as_pdf_with_no_file_behind(env):
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    ok, message = buildbooks.convert_one(item, env, which=_which_installed, text_runner=_damaged)
    assert not ok and "damaged" in message and "left as pdf" in message
    assert not (env.core / "docs" / "sos-test-converted.epub").exists()
    assert not (env.core / "docs" / "sos-test-converted.epub.part").exists()
    ok, message = buildbooks.convert_one(item, env, which=_which_installed, text_runner=lambda p: "")
    assert not ok and "no usable text" in message


def test_convert_one_needs_pdftotext_a_pdf_dest_and_the_right_tool(env):
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    ok, message = buildbooks.convert_one(item, env, which=_which_nothing)
    assert not ok and "pdftotext" in message
    ok, message = buildbooks.convert_one(item.model_copy(update={"pdf_dest": None}), env, which=_which_installed, text_runner=_text)
    assert not ok and "pdf_dest" in message
    other = item.model_copy(update={"source": item.source.model_copy(update={"tool": "manual"})})
    ok, message = buildbooks.convert_one(other, env, which=_which_installed, text_runner=_text)
    assert not ok and "not pdf2epub" in message


def test_convert_one_fetches_the_source_pdf_when_not_already_on_disk(env):
    item = _item(env)

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == item.source.url
        return httpx.Response(200, content=b"%PDF fetched")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    ok, message = buildbooks.convert_one(item, env, client=client, which=_which_installed, use_aria2=False, text_runner=_text)
    assert ok, message
    assert (env.core / "docs" / "sos-test-original.pdf").read_bytes() == b"%PDF fetched"


def test_convert_one_leaves_no_truncated_pdf_when_the_fetch_fails(env):
    """aria2c writes straight to the path it is given. Staged through a `.part` sibling, an interrupted
    fetch cannot leave a truncated file at pdf_path that the next run would take for the download."""
    item = _item(env)
    pdf_path = env.core / "docs" / "sos-test-original.pdf"
    calls: list[list[str]] = []

    def interrupted_aria2c(cmd, **kwargs):
        calls.append(list(cmd))
        directory = next(c for c in cmd if c.startswith("--dir="))[6:]
        name = next(c for c in cmd if c.startswith("--out="))[6:]
        Path(directory, name).write_bytes(b"%PDF trunc")
        return subprocess.CompletedProcess(cmd, 1)

    ok, message = buildbooks.convert_one(item, env, run=interrupted_aria2c, which=_which_installed, use_aria2=True, text_runner=_text)
    assert not ok and "could not fetch" in message
    assert calls[0][0] == "aria2c"
    assert not pdf_path.exists()
    assert pdf_path.with_name(pdf_path.name + ".part").read_bytes() == b"%PDF trunc"


def test_main_reports_ok_returns_nonzero_on_a_failure_and_filters_by_id(env, capsys):
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    assert buildbooks.main(env, which=_which_installed, text_runner=_text) == 0
    assert (env.core / "docs" / "sos-test-converted.epub").exists()
    assert capsys.readouterr().out.startswith("OK   sos-test-epub:")
    assert buildbooks.main(env, which=_which_installed, text_runner=_damaged) == 1
    assert capsys.readouterr().out.startswith("FAIL sos-test-epub:")
    assert buildbooks.main(env, only=["does-not-exist"], which=_which_nothing) == 0
