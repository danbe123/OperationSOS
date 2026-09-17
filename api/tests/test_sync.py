import hashlib
import http.server
import json
import os
import shutil
import subprocess
import threading
from pathlib import Path

import httpx
import pytest
import respx

from sos import db, sync
from sos.manifest import load_manifests

FX = Path(__file__).parent / "fixtures"
WATER_ZIM_URL = "https://lb.download.kiwix.org/zim/other/zimgit-water_en_2024-08.zim"


def test_parse_opds_entry():
    r = sync.parse_opds_entry((FX / "opds" / "catalog.xml").read_text())
    assert r.url == WATER_ZIM_URL
    assert r.name == "zimgit-water_en_2024-08" and r.size == 20925440 and r.as_at == "2024-08-29" and r.sha256 is None
    assert sync.parse_opds_entry((FX / "opds" / "empty.xml").read_text()) is None


def test_parse_meta4():
    size, sha, mirrors = sync.parse_meta4((FX / "opds" / "zimgit-water_en_2024-08.zim.meta4").read_text())
    assert size == 20924451
    assert sha == "392c7bc970a44fddd61dd17f6eabf1f4e21936f2d5c27c83093e1dc475cb56b6"
    assert mirrors == ["https://ftp.nluug.nl/pub/kiwix/zim/other/zimgit-water_en_2024-08.zim",
                       "https://mirror.download.kiwix.org/zim/other/zimgit-water_en_2024-08.zim"]


@respx.mock
def test_resolve_kiwix_uses_meta4_when_available(respx_mock):
    respx_mock.get(sync.OPDS_URL, params={"name": "zimgit-water_en", "count": "1"}).mock(
        return_value=httpx.Response(200, text=(FX / "opds" / "catalog.xml").read_text()))
    respx_mock.get(WATER_ZIM_URL + ".meta4").mock(
        return_value=httpx.Response(200, text=(FX / "opds" / "zimgit-water_en_2024-08.zim.meta4").read_text()))
    with httpx.Client() as client:
        r = sync.resolve_kiwix("zimgit-water_en", client)
    assert r.size == 20924451 and r.sha256.startswith("392c7bc9") and len(r.mirrors) == 2 and r.as_at == "2024-08-29"


@respx.mock
def test_resolve_kiwix_without_meta4_and_unknown_name(respx_mock):
    respx_mock.get(sync.OPDS_URL, params={"name": "zimgit-water_en", "count": "1"}).mock(
        return_value=httpx.Response(200, text=(FX / "opds" / "catalog.xml").read_text()))
    respx_mock.get(WATER_ZIM_URL + ".meta4").mock(return_value=httpx.Response(404))
    respx_mock.get(sync.OPDS_URL, params={"name": "nope", "count": "1"}).mock(
        return_value=httpx.Response(200, text=(FX / "opds" / "empty.xml").read_text()))
    with httpx.Client() as client:
        r = sync.resolve_kiwix("zimgit-water_en", client)
        assert r.size == 20925440 and r.sha256 is None
        with pytest.raises(sync.SyncError):
            sync.resolve_kiwix("nope", client)


class _RangeHandler(http.server.BaseHTTPRequestHandler):
    data = b""
    hits: list[str] = []

    def do_GET(self):
        total = len(self.data)
        rng = self.headers.get("Range")
        self.hits.append(rng or "full")
        if rng:
            start = int(rng.split("=")[1].split("-")[0])
            if start >= total:
                self.send_response(416)
                self.end_headers()
                return
            body = self.data[start:]
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{total - 1}/{total}")
        else:
            body = self.data
            self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def range_server():
    _RangeHandler.data = os.urandom(100_000)
    _RangeHandler.hits = []
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _RangeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}/file.zim"
    server.shutdown()


def test_stream_download_resumes_with_range(tmp_path, range_server):
    target = tmp_path / "file.zim.part"
    target.write_bytes(_RangeHandler.data[:40_000])
    sync.stream_download(range_server, target)
    assert target.read_bytes() == _RangeHandler.data
    assert _RangeHandler.hits == ["bytes=40000-"]
    sync.stream_download(range_server, target)
    assert _RangeHandler.hits == ["bytes=40000-", "bytes=100000-"]
    assert target.read_bytes() == _RangeHandler.data
    fresh = tmp_path / "fresh.part"
    sync.stream_download(range_server, fresh)
    assert fresh.read_bytes() == _RangeHandler.data and _RangeHandler.hits[-1] == "full"


def test_builtin_download_verifies_sha256(tmp_path, range_server):
    good = hashlib.sha256(_RangeHandler.data).hexdigest()
    target = tmp_path / "a.part"
    assert sync.download(range_server, target, sha256=good, use_aria2=False) == target
    bad = tmp_path / "b.part"
    with pytest.raises(sync.ChecksumError):
        sync.download(range_server, bad, sha256="0" * 64, use_aria2=False)
    assert not bad.exists()


def test_builtin_download_resumes_on_mirror_after_network_failure(tmp_path, respx_mock):
    target = tmp_path / "mirror.part"
    target.write_bytes(b"start")
    respx_mock.get("https://primary.test/file").mock(side_effect=httpx.ReadError("disconnected"))
    mirror = respx_mock.get("https://mirror.test/file").mock(
        return_value=httpx.Response(206, content=b"finish", headers={"Content-Range": "bytes 5-10/11"}))
    sync.download("https://primary.test/file", target, mirrors=["https://mirror.test/file"],
                  sha256=hashlib.sha256(b"startfinish").hexdigest(), use_aria2=False)
    assert target.read_bytes() == b"startfinish"
    assert mirror.calls[0].request.headers["Range"] == "bytes=5-"


def test_aria2c_command_line(tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        Path(cmd[[c.startswith("--dir=") for c in cmd].index(True)][6:]).joinpath(
            next(c for c in cmd if c.startswith("--out="))[6:]).write_bytes(b"zim")
        return subprocess.CompletedProcess(cmd, 0)

    target = tmp_path / "x.zim.part"
    sync.download("https://h.test/x.zim", target, sha256="ab" * 32, mirrors=["https://m.test/x.zim"], use_aria2=True, run=fake_run)
    cmd = calls[0]
    assert cmd[0] == "aria2c" and "--continue=true" in cmd and f"--dir={tmp_path}" in cmd and "--out=x.zim.part" in cmd
    assert "--checksum=sha-256=" + "ab" * 32 in cmd
    assert "--header=Accept: application/octet-stream" in cmd and "--follow-metalink=false" in cmd
    assert cmd[-2:] == ["https://h.test/x.zim", "https://m.test/x.zim"]
    assert target.exists()

    def failing(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1)

    with pytest.raises(sync.SyncError):
        sync.download("https://h.test/y.zim", tmp_path / "y.part", use_aria2=True, run=failing)


def _manifest(tmp_path, items):
    d = tmp_path / "manifest"
    d.mkdir()
    shutil.copy(FX / "manifest" / "schema.json", d / "schema.json")
    (d / "core.json").write_text(json.dumps({"items": items}), encoding="utf-8")
    return d


NOINDEX_SHA = hashlib.sha256((FX / "library" / "sos-test-noindex.zim").read_bytes()).hexdigest()
ITEMS = [
    {"id": "zimgit-water_en_2024-08", "title": "Water", "kind": "zim", "tier": "core", "category": "survival",
     "source": {"type": "kiwix", "name": "zimgit-water_en"}, "dest": "zim/zimgit-water_en_2024-08.zim", "priority": 1},
    {"id": "sos-test-pdf", "title": "Test PDF", "kind": "pdf", "tier": "core", "category": "uk-official",
     "source": {"type": "url", "url": "https://files.test/sos-test.pdf",
                "sha256": hashlib.sha256((FX / "docs" / "sos-test.pdf").read_bytes()).hexdigest()},
     "dest": "docs/sos-test.pdf", "priority": 2},
    {"id": "prepare_uk", "title": "Prepare", "kind": "zim", "tier": "core", "category": "uk-official",
     "source": {"type": "build", "tool": "build-nhs", "artifact": "prepare_uk.zim"}, "dest": "zim/prepare_uk.zim", "priority": 3},
    {"id": "sos-ext", "title": "Ext", "kind": "zim", "tier": "extended", "category": "books",
     "source": {"type": "kiwix", "name": "sos-ext"}, "dest": "zim/sos-ext.zim", "priority": 4},
]


# A converted book: built by `sos build-books` (not `sos pdf2epub`, which is not a command), and it
# carries a second file — the original PDF the reader falls back to — that also has to reach the box.
CONVERTED_BOOK = {
    "id": "sos-test-epub", "title": "Test book", "kind": "epub", "tier": "core", "category": "books",
    "source": {"type": "build", "tool": "pdf2epub", "artifact": "docs/sos-test-converted.epub",
               "url": "https://files.test/sos-test-original.pdf"},
    "dest": "docs/sos-test-converted.epub", "pdf_dest": "docs/sos-test-original.pdf", "priority": 5,
}


def test_sync_build_line_names_build_books_and_the_fallback_pdf(env, tmp_path, monkeypatch):
    """`source.tool` names the builder, not the command. A pdf2epub item must send the operator to
    `sos build-books` and tell them the fallback PDF is a second file to copy — without it the
    reader's "Original PDF layout" toggle never appears on the box."""
    monkeypatch.setattr(env, "manifest_dir", _manifest(tmp_path, [ITEMS[2], CONVERTED_BOOK]))
    lines = []
    with httpx.Client() as client:
        rc = sync.sync(env, "core", dry_run=True, out=lines.append, client=client)
    assert rc == 0
    assert [line for line in lines if line.startswith("BUILD")] == [
        # unchanged for a tool that is its own command and has no second file
        "BUILD prepare_uk: run `sos build-nhs` on the PC and copy prepare_uk.zim to "
        + str(env.core / "zim" / "prepare_uk.zim"),
        "BUILD sos-test-epub: run `sos build-books` on the PC and copy docs/sos-test-converted.epub to "
        + str(env.core / "docs" / "sos-test-converted.epub")
        + " (and docs/sos-test-original.pdf to " + str(env.core / "docs" / "sos-test-original.pdf") + ")",
    ]


def _meta4_for(sha: str, size: int) -> str:
    text = (FX / "opds" / "zimgit-water_en_2024-08.zim.meta4").read_text()
    return text.replace("392c7bc970a44fddd61dd17f6eabf1f4e21936f2d5c27c83093e1dc475cb56b6", sha).replace("<size>20924451</size>", f"<size>{size}</size>")


@respx.mock
def test_sync_dry_run_lists_without_downloading(respx_mock, env, tmp_path, monkeypatch):
    monkeypatch.setattr(env, "manifest_dir", _manifest(tmp_path, ITEMS))
    respx_mock.get(sync.OPDS_URL).mock(return_value=httpx.Response(200, text=(FX / "opds" / "catalog.xml").read_text()))
    respx_mock.get(WATER_ZIM_URL + ".meta4").mock(return_value=httpx.Response(404))
    lines = []
    with httpx.Client() as client:
        rc = sync.sync(env, "core", dry_run=True, out=lines.append, client=client)
    assert rc == 0
    assert any(line.startswith("GET  zimgit-water_en_2024-08: " + WATER_ZIM_URL) and "0.02 GB" in line for line in lines)
    assert any(line.startswith("GET  sos-test-pdf: https://files.test/sos-test.pdf") for line in lines)
    assert any(line.startswith("BUILD prepare_uk: run `sos build-nhs`") and "prepare_uk.zim" in line for line in lines)
    assert not any("sos-ext" in line for line in lines)
    assert not (env.core / "zim" / "zimgit-water_en_2024-08.zim").exists()
    assert not env.db_path.exists()


@respx.mock
def test_sync_downloads_verifies_renames_records_and_indexes(respx_mock, env, tmp_path, monkeypatch):
    monkeypatch.setattr(env, "manifest_dir", _manifest(tmp_path, ITEMS))
    zim_bytes = (FX / "library" / "sos-test-noindex.zim").read_bytes()
    respx_mock.get(sync.OPDS_URL).mock(return_value=httpx.Response(200, text=(FX / "opds" / "catalog.xml").read_text()))
    respx_mock.get(WATER_ZIM_URL + ".meta4").mock(return_value=httpx.Response(200, text=_meta4_for(NOINDEX_SHA, len(zim_bytes))))
    respx_mock.get(WATER_ZIM_URL).mock(return_value=httpx.Response(200, content=zim_bytes))
    respx_mock.get("https://files.test/sos-test.pdf").mock(return_value=httpx.Response(200, content=(FX / "docs" / "sos-test.pdf").read_bytes()))
    respx_mock.post("http://127.0.0.1:8000/api/system/rescan").mock(return_value=httpx.Response(200, json={"items": 4, "available": 2}))
    lines = []
    with httpx.Client() as client:
        rc = sync.sync(env, "core", out=lines.append, client=client, use_aria2=False)
    assert rc == 0, lines
    zim = env.core / "zim" / "zimgit-water_en_2024-08.zim"
    assert zim.exists() and zim.read_bytes() == zim_bytes and not zim.with_name(zim.name + ".part").exists()
    assert (env.core / "docs" / "sos-test.pdf").exists()
    conn = db.connect(env.db_path)
    row = conn.execute("SELECT * FROM library_items WHERE id='zimgit-water_en_2024-08'").fetchone()
    assert (row["resolved_name"], row["resolved_size"], row["resolved_as_at"], row["available"]) == ("zimgit-water_en_2024-08", len(zim_bytes), "2024-08-29", 1)
    assert conn.execute("SELECT count(*) FROM fts_docs WHERE kind='playbook'").fetchone()[0] >= 6
    assert conn.execute("SELECT count(*) FROM fts_docs WHERE kind='item'").fetchone()[0] == 4
    assert json.loads(db.get_setting(conn, "overlay_scenarios")) == {"health": ["grid-collapse"], "water": ["grid-collapse"]}
    assert any(line.startswith("DONE zimgit-water_en_2024-08") for line in lines)
    # second run: already present, nothing downloaded
    with httpx.Client() as client:
        rc = sync.sync(env, "core", out=lines.append, client=client, use_aria2=False)
    assert rc == 0 and any(line.startswith("OK   zimgit-water_en_2024-08: present") for line in lines)


@respx.mock
def test_sync_checksum_mismatch_fails_item(respx_mock, env, tmp_path, monkeypatch):
    monkeypatch.setattr(env, "manifest_dir", _manifest(tmp_path, [ITEMS[1]]))
    respx_mock.get("https://files.test/sos-test.pdf").mock(return_value=httpx.Response(200, content=b"tampered"))
    respx_mock.post("http://127.0.0.1:8000/api/system/rescan").mock(return_value=httpx.Response(200, json={}))
    lines = []
    with httpx.Client() as client:
        rc = sync.sync(env, "core", out=lines.append, client=client, use_aria2=False)
    assert rc == 1
    assert any(line.startswith("FAIL sos-test-pdf: sha256 mismatch") for line in lines)
    assert not (env.core / "docs" / "sos-test.pdf").exists() and not (env.core / "docs" / "sos-test.pdf.part").exists()


@respx.mock
def test_sync_only_filter_and_extended_requires_drive(respx_mock, env, tmp_path, monkeypatch):
    monkeypatch.setattr(env, "manifest_dir", _manifest(tmp_path, ITEMS))
    lines = []
    with httpx.Client() as client:
        rc = sync.sync(env, "core", only=["prepare_uk", "ghost"], dry_run=True, out=lines.append, client=client)
    assert rc == 0
    assert [line for line in lines if line.startswith(("GET", "BUILD"))] == [
        "BUILD prepare_uk: run `sos build-nhs` on the PC and copy prepare_uk.zim to " + str(env.core / "zim" / "prepare_uk.zim")]
    assert any("ghost" in line and "not in manifest" in line for line in lines)
    with pytest.raises(sync.SyncError):
        with httpx.Client() as client:
            sync.sync(env, "extended", out=lines.append, client=client)


def test_strip_markdown():
    md = "## Right now\nCall **105** now. See [bleeding](card:bleeding).\n\n{{module:water}}\n- [ ] Fill bottles {#fill}\n| a | b |\n|---|---|"
    text = sync.strip_markdown(md)
    assert text == "Right now Call 105 now. See bleeding. Fill bottles a b"


def test_index_reports_books(env):
    """index() counts the Gutenberg books when the ZIM is on the box; without it the count is 0 and nothing fails."""
    assert sync.index(env, out=lambda *_: None)["books"] == 0


def test_index_content_rows(env):
    conn = db.connect(env.db_path)
    db.init_schema(conn)
    n = sync.index_content(conn, env.playbooks)
    rows = conn.execute("SELECT title, kind, url, scenarios FROM fts_docs ORDER BY rowid").fetchall()
    assert n == len(rows) and n >= 9
    playbook_rows = [r for r in rows if r["kind"] == "playbook"]
    assert playbook_rows[0]["url"] == "/s/grid-collapse#right-now" and playbook_rows[0]["scenarios"] == "grid-collapse"
    assert {r["kind"] for r in rows} == {"playbook", "module", "card", "page"}
    hit = conn.execute("SELECT url FROM fts_docs WHERE fts_docs MATCH '\"bleach\"'").fetchone()
    assert hit["url"].startswith("/m/water")
