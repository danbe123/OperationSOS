import sqlite3

from sos import db


def _tables(conn):
    return {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}


def test_schema_creates_every_table(tmp_path):
    conn = db.connect(tmp_path / "sos.db")
    db.init_schema(conn)
    names = _tables(conn)
    for t in ("library_items", "fts_docs", "fts_places", "checklist_state", "notes", "settings", "search_cache", "places_meta",
              "books", "fts_books", "reading"):
        assert t in names, t
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert isinstance(conn.execute("SELECT 1 AS one").fetchone(), sqlite3.Row)


def test_books_fts_is_external_content_and_reading_round_trips(tmp_path):
    conn = db.connect(tmp_path / "sos.db")
    db.init_schema(conn)
    conn.execute("INSERT INTO books (zim, id, title, author, shelf, popularity, epub_path, html_path, cover_path) VALUES "
                 "('gutenberg_en_all', 1342, 'Pride and Prejudice', 'Jane Austen', 'PR', 100, "
                 "'Pride and Prejudice.1342.epub', 'Pride and Prejudice.1342.html', 'covers/1342_cover_image.jpg')")
    conn.execute("INSERT INTO fts_books(fts_books) VALUES('rebuild')")
    hit = conn.execute("SELECT b.title FROM books b JOIN fts_books f ON f.rowid = b.rowid WHERE fts_books MATCH 'austen'").fetchone()
    assert hit["title"] == "Pride and Prejudice"
    conn.execute("INSERT INTO reading (key, title, author, cover_url, cfi, percent, updated_at) VALUES "
                 "('gutenberg:1342', 'Pride and Prejudice', 'Jane Austen', NULL, 'epubcfi(/6/4!/4/2/2)', 12.5, '2026-09-17T10:00:00Z')")
    assert conn.execute("SELECT percent FROM reading WHERE key='gutenberg:1342'").fetchone()["percent"] == 12.5


def test_init_schema_is_idempotent(tmp_path):
    conn = db.connect(tmp_path / "sos.db")
    db.init_schema(conn)
    db.init_schema(conn)
    db.set_setting(conn, "ssid", "SOS")
    db.init_schema(conn)
    assert db.get_setting(conn, "ssid") == "SOS"


def test_fts5_available():
    conn = db.connect(":memory:")
    assert db.fts5_available(conn) is True


def test_bm25_title_weight_ranks_title_hit_first():
    conn = db.connect(":memory:")
    db.init_schema(conn)
    conn.execute(
        "INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)",
        ("Heating without power", "keep warm water bottles blankets water water", "m1", "module", "playbooks", "", None, "/m/heat"),
    )
    conn.execute(
        "INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)",
        ("Water", "finding and treating it", "m2", "module", "playbooks", "", None, "/m/water"),
    )
    rows = conn.execute(
        "SELECT doc_id FROM fts_docs WHERE fts_docs MATCH ? ORDER BY bm25(fts_docs, 5.0, 1.0)", ('"water"',)
    ).fetchall()
    assert [r["doc_id"] for r in rows] == ["m2", "m1"]


def test_porter_stemming_and_diacritics():
    conn = db.connect(":memory:")
    db.init_schema(conn)
    conn.execute(
        "INSERT INTO fts_docs(title, body, doc_id, kind, category, scenarios, page, url) VALUES (?,?,?,?,?,?,?,?)",
        ("Éowyn storm outages", "restoring power", "p1", "playbook", "playbooks", "", None, "/s/grid"),
    )
    assert conn.execute("SELECT count(*) FROM fts_docs WHERE fts_docs MATCH '\"outage\"'").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM fts_docs WHERE fts_docs MATCH '\"eowyn\"'").fetchone()[0] == 1


def test_places_prefix_index():
    conn = db.connect(":memory:")
    db.init_schema(conn)
    conn.execute("INSERT INTO fts_places(name, kind, lat, lon, region, postcode) VALUES (?,?,?,?,?,?)",
                 ("Oxford", "city", 51.752, -1.258, "England", None))
    conn.execute("INSERT INTO fts_places(name, kind, lat, lon, region, postcode) VALUES (?,?,?,?,?,?)",
                 ("Oxted", "town", 51.257, 0.006, "England", None))
    rows = conn.execute("SELECT name FROM fts_places WHERE fts_places MATCH '\"oxf\"*'").fetchall()
    assert [r["name"] for r in rows] == ["Oxford"]
    rows = conn.execute("SELECT name FROM fts_places WHERE fts_places MATCH '\"ox\"*' ORDER BY name").fetchall()
    assert [r["name"] for r in rows] == ["Oxford", "Oxted"]


def test_settings_helpers():
    conn = db.connect(":memory:")
    db.init_schema(conn)
    assert db.get_setting(conn, "missing") is None
    assert db.get_setting(conn, "missing", "x") == "x"
    db.set_setting(conn, "k", "v")
    db.set_setting(conn, "k", "w")
    assert db.get_setting(conn, "k") == "w"
    db.set_setting(conn, "k", None)
    assert db.get_setting(conn, "k") is None


def test_init_schema_adds_kit_item_to_an_old_stock_table(tmp_path):
    from sos import db

    conn = db.connect(tmp_path / "old.sqlite")
    conn.execute("CREATE TABLE stock (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT NOT NULL, "
                 "quantity REAL NOT NULL, unit TEXT NOT NULL, per_person_day REAL, expires TEXT, notes TEXT, updated_at TEXT)")
    conn.commit()
    db.init_schema(conn)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(stock)")]
    assert "kit_item" in cols
    db.init_schema(conn)          # idempotent
    assert [r[1] for r in conn.execute("PRAGMA table_info(stock)")].count("kit_item") == 1
