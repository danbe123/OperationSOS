import shutil
from pathlib import Path

import pytest

from sos import db, library
from sos.manifest import load_manifests

FIXTURES = Path(__file__).parent / "fixtures"
HAS_KIWIX_MANAGE = shutil.which("kiwix-manage") is not None


@pytest.fixture
def conn(env):
    c = db.connect(env.db_path)
    db.init_schema(c)
    library.upsert_items(c, load_manifests(env.manifests))
    return c


def _install_zims(env, names=("wikipedia_en_100_mini_2026-01", "sos-test-noindex")):
    for n in names:
        shutil.copy(FIXTURES / "library" / f"{n}.zim", env.core / "zim" / f"{n}.zim")


def test_fixture_checksums_match():
    sums = (FIXTURES / "library" / "SHA256SUMS").read_text().split()
    import hashlib
    for digest, name in zip(sums[0::2], sums[1::2]):
        assert hashlib.sha256((FIXTURES / "library" / name).read_bytes()).hexdigest() == digest, name


def test_upsert_mirrors_manifest_and_keeps_runtime_columns(conn, env):
    rows = {r["id"]: r for r in conn.execute("SELECT * FROM library_items")}
    assert rows["wikipedia_en_100_mini_2026-01"]["suggest"] == 1
    assert rows["sos-test-pdf"]["search_weight"] == 1.4
    assert rows["health"]["overlay_json"] is not None
    conn.execute("UPDATE library_items SET available=1, fts=1, resolved_name='x' WHERE id='wikipedia_en_100_mini_2026-01'")
    conn.commit()
    library.upsert_items(conn, load_manifests(env.manifests))
    row = conn.execute("SELECT available, fts, resolved_name FROM library_items WHERE id='wikipedia_en_100_mini_2026-01'").fetchone()
    assert (row["available"], row["fts"], row["resolved_name"]) == (1, 1, "x")


def test_upsert_removes_items_gone_from_manifest(conn, env):
    items = [i for i in load_manifests(env.manifests) if i.id != "sos-test-noindex"]
    library.upsert_items(conn, items)
    assert conn.execute("SELECT count(*) FROM library_items WHERE id='sos-test-noindex'").fetchone()[0] == 0


def test_refresh_availability_and_labels(conn, env):
    _install_zims(env)
    (env.core / "docs" / "sos-test.pdf").write_bytes(b"%PDF-1.4\n")
    total, available = library.refresh_items(conn, env)
    assert total == 27 and available == 3
    rows = {r["id"]: r for r in conn.execute("SELECT * FROM library_items")}
    assert rows["wikipedia_en_100_mini_2026-01"]["local_path"] == str(env.core / "zim" / "wikipedia_en_100_mini_2026-01.zim")
    assert rows["nrr-2025"]["available"] == 0
    assert rows["sos-ext-missing"]["available"] == 0
    assert library.drive_label(rows["sos-ext-missing"], library.ext_mounted(env)) == "On external drive (not connected)"
    assert library.drive_label(rows["wikipedia_en_100_mini_2026-01"], False) == "Core"
    env.ext.mkdir()
    (env.ext / "zim").mkdir()
    shutil.copy(FIXTURES / "library" / "sos-test-noindex.zim", env.ext / "zim" / "sos-ext-missing.zim")
    total, available = library.refresh_items(conn, env)
    assert available == 4
    row = conn.execute("SELECT * FROM library_items WHERE id='sos-ext-missing'").fetchone()
    assert library.drive_label(row, True) == "External drive"


def test_reader_urls(conn, env):
    _install_zims(env)
    (env.core / "docs" / "sos-test.pdf").write_bytes(b"%PDF-1.4\n")
    library.refresh_items(conn, env)
    rows = {r["id"]: r for r in conn.execute("SELECT * FROM library_items")}
    assert library.reader_url(rows["wikipedia_en_100_mini_2026-01"]) == "/read/wikipedia_en_100_mini_2026-01/"
    assert library.reader_url(rows["sos-test-pdf"]) == "/doc/sos-test-pdf"
    assert library.file_url(rows["sos-test-pdf"]) == "/docs/core/" + str(rows["sos-test-pdf"]["dest"]).rsplit("/", 1)[-1]
    assert library.file_url(rows["wikipedia_en_100_mini_2026-01"]) is None
    assert library.reader_url(rows["nrr-2025"]) is None
    assert library.reader_url(rows["uk-ie"]) is None
    conn.execute("UPDATE library_items SET reader_home='A/Main_Page' WHERE id='wikipedia_en_100_mini_2026-01'")
    row = conn.execute("SELECT * FROM library_items WHERE id='wikipedia_en_100_mini_2026-01'").fetchone()
    assert library.reader_url(row) == "/read/wikipedia_en_100_mini_2026-01/A/Main_Page"


def test_pdf_fallback_url_only_appears_once_the_fallback_file_is_present(conn, env):
    total, available = library.refresh_items(conn, env)
    row = conn.execute("SELECT * FROM library_items WHERE id='sos-test-epub'").fetchone()
    assert library.pdf_fallback_url(row) is None  # neither file exists yet

    (env.core / "docs" / "sos-test-converted.epub").write_bytes(b"EPUB")
    library.refresh_items(conn, env)
    row = conn.execute("SELECT * FROM library_items WHERE id='sos-test-epub'").fetchone()
    assert library.file_url(row) == "/docs/core/sos-test-converted.epub"
    assert library.pdf_fallback_url(row) is None  # epub present, but not the fallback PDF yet

    (env.core / "docs" / "sos-test-original.pdf").write_bytes(b"%PDF-1.4\n")
    library.refresh_items(conn, env)
    row = conn.execute("SELECT * FROM library_items WHERE id='sos-test-epub'").fetchone()
    assert library.pdf_fallback_url(row) == "/docs/core/sos-test-original.pdf"


def test_pdf_fallback_url_is_none_for_a_book_that_was_never_a_pdf(conn, env):
    library.refresh_items(conn, env)
    row = conn.execute("SELECT * FROM library_items WHERE id='wikipedia_en_100_mini_2026-01'").fetchone()
    assert row["pdf_dest"] is None
    assert library.pdf_fallback_url(row) is None


def test_library_response_groups_by_category_in_order(conn, env):
    _install_zims(env)
    library.refresh_items(conn, env)
    resp = library.library_response(conn, env)
    ids = [c["id"] for c in resp["categories"]]
    assert ids == [c for c in library.CATEGORY_ORDER if c in ids]
    assert ids[0] == "uk-official"
    ref = next(c for c in resp["categories"] if c["id"] == "reference")
    item = ref["items"][0]
    assert set(item) == {"id", "title", "kind", "tier", "category", "scenarios", "size_bytes", "as_at", "licence",
                         "available", "url", "file_url", "pdf_fallback_url", "description", "drive_label"}
    assert item["available"] is True and item["url"].startswith("/read/")


@pytest.mark.skipif(not HAS_KIWIX_MANAGE, reason="kiwix-manage not on PATH")
def test_write_library_xml_and_flags(conn, env):
    _install_zims(env)
    library.refresh_items(conn, env)
    path = library.write_library_xml(conn, env)
    assert path == env.library_xml and path.exists()
    info = library.parse_library_xml(path)
    assert info["wikipedia_en_100_mini_2026-01"]["fts"] is True
    assert info["wikipedia_en_100_mini_2026-01"]["language"] == "eng"
    assert info["sos-test-noindex"]["fts"] is False
    library.apply_library_flags(conn, info)
    rows = {r["id"]: r["fts"] for r in conn.execute("SELECT id, fts FROM library_items")}
    assert rows["wikipedia_en_100_mini_2026-01"] == 1 and rows["sos-test-noindex"] == 0
    # regenerated from scratch: removing a file removes its book
    (env.core / "zim" / "sos-test-noindex.zim").unlink()
    library.refresh_items(conn, env)
    library.write_library_xml(conn, env)
    assert "sos-test-noindex" not in library.parse_library_xml(path)


@pytest.mark.skipif(not HAS_KIWIX_MANAGE, reason="kiwix-manage not on PATH")
def test_rescan_with_extended_missing_flushes_cache(conn, env):
    _install_zims(env)
    conn.execute("INSERT INTO search_cache(q, results_json, created_at) VALUES ('water','[]','2026-01-01')")
    conn.commit()
    result = library.rescan(conn, env)
    assert result == {"items": 27, "available": 2}
    assert conn.execute("SELECT count(*) FROM search_cache").fetchone()[0] == 0
    assert db.get_setting(conn, "zim_languages") is not None
    assert not env.ext.exists()


@pytest.mark.skipif(not HAS_KIWIX_MANAGE, reason="kiwix-manage not on PATH")
def test_corrupt_zim_is_skipped_and_marked_unavailable(conn, env):
    _install_zims(env, names=("wikipedia_en_100_mini_2026-01",))
    (env.core / "zim" / "sos-test-noindex.zim").write_bytes(b"not a zim")
    library.refresh_items(conn, env)
    path = library.write_library_xml(conn, env)
    info = library.parse_library_xml(path)
    assert "wikipedia_en_100_mini_2026-01" in info and "sos-test-noindex" not in info
    assert conn.execute("SELECT available FROM library_items WHERE id='sos-test-noindex'").fetchone()[0] == 0


def test_write_library_xml_without_zims_writes_empty_library(conn, env, tmp_path):
    path = library.write_library_xml(conn, env)
    assert "<library" in path.read_text()
    assert library.parse_library_xml(path) == {}
