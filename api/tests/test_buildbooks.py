import subprocess
from pathlib import Path

import httpx

from sos import buildbooks
from sos.manifest import load_manifests


class FakeRun:
    """Records every command; simulates ebook-convert writing the EPUB, instead of running it."""

    def __init__(self, ok: bool = True):
        self.calls: list[list[str]] = []
        self.ok = ok

    def __call__(self, cmd, **kwargs):
        self.calls.append(list(cmd))
        if cmd[0] == "ebook-convert" and self.ok:
            Path(cmd[2]).write_bytes(b"EPUB fake")
        return subprocess.CompletedProcess(cmd, 0 if self.ok else 1, stdout="",
                                           stderr="" if self.ok else "conversion failed")


def _which_installed(name: str) -> str | None:
    return f"/usr/bin/{name}" if name == "ebook-convert" else None


def _item(env):
    return next(i for i in load_manifests(env.manifests) if i.id == "sos-test-epub")


def test_convert_one_runs_ebook_convert_with_the_items_title_and_writes_the_epub(env):
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    run = FakeRun(ok=True)
    ok, message = buildbooks.convert_one(item, env, run=run, which=_which_installed)
    assert ok, message
    epub_path = env.core / "docs" / "sos-test-converted.epub"
    assert epub_path.read_bytes() == b"EPUB fake"
    pdf_path = env.core / "docs" / "sos-test-original.pdf"
    assert run.calls == [["ebook-convert", str(pdf_path), str(epub_path), "--title", item.title]]


def test_convert_one_reports_failure_and_leaves_no_partial_epub(env):
    item = _item(env)
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    run = FakeRun(ok=False)
    ok, message = buildbooks.convert_one(item, env, run=run, which=_which_installed)
    assert not ok and "ebook-convert failed" in message
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
    ok, message = buildbooks.convert_one(item, env, run=run, client=client, which=_which_installed, use_aria2=False)
    assert ok, message
    assert (env.core / "docs" / "sos-test-original.pdf").read_bytes() == b"%PDF fetched"


def test_main_reports_ok_and_returns_zero(env):
    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF fake")
    run = FakeRun(ok=True)
    code = buildbooks.main(env, run=run, which=_which_installed)
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
