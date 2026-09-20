"""index_books against a ZIM in the real scraper's layout (built by the books_zim fixture), the catalogue parser,
and the /api/books and /api/reading endpoints."""
import logging
import os
from pathlib import Path

import pytest

from sos import books, db
from sos.books import BOOK_ZIMS, entry_slug, index_books, parse_catalogue


def _conn(tmp_path):
    conn = db.connect(tmp_path / "sos.db")
    db.init_schema(conn)
    return conn


def _add_item(conn, zim_path: Path | None, available: int = 1, item_id: str = "gutenberg_en_all"):
    conn.execute(
        "INSERT INTO library_items (id, title, kind, tier, category, dest, priority, available, local_path) "
        "VALUES (?, 'Project Gutenberg (English)', 'zim', 'core', 'books', ?, 100, ?, ?)",
        (item_id, f"zim/{item_id}.zim", available, str(zim_path) if zim_path else None))
    conn.commit()


def test_entry_slug_matches_the_scraper():
    assert entry_slug("Aesop's Fables / A New Translation") == "Aesop's Fables - A New Translation"
    assert entry_slug("  Padded  ") == "Padded"
    assert len(entry_slug("x" * 300)) == 230


def test_parse_catalogue_reads_the_javascript_array():
    raw = b'var json_data = [["Pride and Prejudice", "Jane Austen", "110", 1342, "PR"], ["No Shelf", "", "100", 5, ""]];'
    rows = parse_catalogue(raw)
    assert rows[0] == books.CatalogueEntry(title="Pride and Prejudice", author="Jane Austen", flags="110", id=1342, shelf="PR")
    assert rows[1].author == "" and rows[1].shelf == ""


@pytest.mark.parametrize("raw", [b"", b"var json_data = ;", b"var json_data = [[1]];", b"var json_data = {};"])
def test_parse_catalogue_rejects_garbage(raw):
    with pytest.raises(ValueError):
        parse_catalogue(raw)


def test_index_books_populates_books_and_fts(tmp_path, books_zim):
    conn = _conn(tmp_path)
    _add_item(conn, books_zim)
    assert index_books(conn) == 6
    rows = {r["id"]: r for r in conn.execute("SELECT * FROM books WHERE zim='gutenberg_en_all'")}
    assert rows[1342]["title"] == "Pride and Prejudice" and rows[1342]["author"] == "Jane Austen" and rows[1342]["shelf"] == "PR"
    assert rows[1342]["epub_path"] == "Pride and Prejudice.1342.epub"
    assert rows[1342]["html_path"] == "Pride and Prejudice.1342"          # the scraper stores the article without .html
    assert rows[1342]["cover_path"] == "covers/1342_cover_image.jpg"
    assert rows[1342]["popularity"] == 6 and rows[2641]["popularity"] == 1   # position in full_by_popularity.js
    assert rows[11339]["epub_path"] is None                                  # flags say html only
    assert rows[11339]["html_path"] == "Aesop's Fables - A New Translation.11339"
    assert rows[147]["epub_path"] is None                                    # flagged, but the entry is not in the ZIM
    assert rows[1232]["cover_path"] is None                                  # no cover entry
    assert rows[2641]["shelf"] is None and rows[2641]["author"] == "E. M. Forster"
    hit = conn.execute("SELECT b.title FROM books b JOIN fts_books f ON f.rowid=b.rowid WHERE fts_books MATCH 'austen'").fetchone()
    assert hit["title"] == "Pride and Prejudice"


def test_index_books_is_a_noop_without_the_zim(tmp_path, books_zim):
    conn = _conn(tmp_path)
    assert index_books(conn) == 0                       # not in library_items at all
    _add_item(conn, None, available=0)
    assert index_books(conn) == 0                       # listed, not on the box
    assert conn.execute("SELECT count(*) AS n FROM books").fetchone()["n"] == 0


def test_index_books_warns_and_keeps_the_tables_on_a_bad_catalogue(tmp_path, books_zim, caplog):
    conn = _conn(tmp_path)
    _add_item(conn, books_zim)
    index_books(conn)
    os.utime(books_zim, (3, 3))                           # "replaced" by a file whose catalogue is garbage

    class Broken:
        def read(self, path):
            return b"var json_data = nonsense;"

        def has(self, path):
            return False

    with caplog.at_level(logging.WARNING):
        assert index_books(conn, open_zim=lambda p: Broken()) == 0
    assert "gutenberg_en_all" in caplog.text
    assert conn.execute("SELECT count(*) AS n FROM books").fetchone()["n"] == 6


def test_index_books_warns_when_the_catalogue_entry_is_missing(tmp_path, caplog):
    conn = _conn(tmp_path)
    _add_item(conn, Path("/nonexistent.zim"))

    class Empty:
        def read(self, path):
            return None

        def has(self, path):
            return False

    with caplog.at_level(logging.WARNING):
        assert index_books(conn, open_zim=lambda p: Empty()) == 0
    assert "full_by_popularity.js" in caplog.text


def test_index_books_survives_an_unreadable_file(tmp_path, caplog):
    conn = _conn(tmp_path)
    _add_item(conn, tmp_path / "missing.zim")
    with caplog.at_level(logging.WARNING):
        assert index_books(conn) == 0
    assert "gutenberg_en_all" in caplog.text


def test_index_books_skips_an_unchanged_zim_and_rereads_a_replaced_one(tmp_path, books_zim):
    conn = _conn(tmp_path)
    _add_item(conn, books_zim)
    assert index_books(conn) == 6
    opened = []

    def spy(path):
        opened.append(path)
        return books.open_zim(path)

    assert index_books(conn, open_zim=spy) == 6
    assert opened == []                                   # same size and mtime: nothing re-read
    os.utime(books_zim, (1, 1))                           # a rebuilt file with the same name
    assert index_books(conn, open_zim=spy) == 6
    assert opened == [books_zim]


def test_index_books_survives_a_bad_row_and_a_reader_that_breaks_mid_walk(tmp_path, caplog):
    conn = _conn(tmp_path)
    _add_item(conn, Path("/nonexistent.zim"))

    class Odd:
        def read(self, path): return b'var json_data = [["T", "A", "110", null, "PR"]];'
        def has(self, path): return False

    class Breaks:
        def read(self, path): return b'var json_data = [["T", "A", "110", 1, "PR"]];'
        def has(self, path): raise RuntimeError("bad dirent")

    with caplog.at_level(logging.WARNING):
        assert index_books(conn, open_zim=lambda p: Odd()) == 0
        assert index_books(conn, open_zim=lambda p: Breaks()) == 0
    assert caplog.text.count("gutenberg_en_all") == 2


def test_index_books_rerun_replaces_rows_and_leaves_no_stale_fts(tmp_path, books_zim):
    conn = _conn(tmp_path)
    _add_item(conn, books_zim)
    index_books(conn)
    os.utime(books_zim, (2, 2))                           # the file was replaced, so it is read again

    class OneBook:
        def read(self, path):
            return b'var json_data = [["Only Book", "Nobody", "110", 9, ""]];'

        def has(self, path):
            return False

    assert index_books(conn, open_zim=lambda p: OneBook()) == 1
    assert conn.execute("SELECT count(*) AS n FROM books").fetchone()["n"] == 1
    assert conn.execute("SELECT count(*) AS n FROM fts_books WHERE fts_books MATCH 'austen'").fetchone()["n"] == 0
    assert conn.execute("SELECT b.title FROM books b JOIN fts_books f ON f.rowid=b.rowid WHERE fts_books MATCH 'only'").fetchone()["title"] == "Only Book"


def test_book_zims_is_the_gutenberg_collection():
    assert BOOK_ZIMS == ("gutenberg_en_all",)


def test_libzim_reader_paths_walks_every_real_entry(books_zim):
    """The real libzim.reader.Archive, not a fake: entry_count and _get_entry_by_id (Correction 1 of
    the household-embedding task) actually walk the fixture ZIM's real entries."""
    reader = books.open_zim(books_zim)
    paths = set(reader.paths())
    assert "full_by_popularity.js" in paths
    assert "Pride and Prejudice.1342" in paths            # the bare HTML article
    assert "Pride and Prejudice.1342.epub" in paths
    assert "covers/1342_cover_image.jpg" in paths
    assert "Aesop's Fables - A New Translation.11339.epub" not in paths   # flags say html only: never written


# --- the router -------------------------------------------------------------------------------------------------


@pytest.fixture
def populated(client, env, books_zim):
    """The app's own database, with the Gutenberg item on the box and the fixture catalogue indexed."""
    conn = db.connect(env.db_path)
    _add_item(conn, books_zim)
    index_books(conn)
    conn.close()
    return client


def test_books_lists_by_popularity_and_pages(populated):
    r = populated.get("/api/books")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is True and body["total"] == 6
    assert [b["title"] for b in body["items"]][:2] == ["Pride and Prejudice", "Moby-Dick; Or, The Whale"]
    first = body["items"][0]
    assert first["epub_url"] == "/kiwix/content/gutenberg_en_all/Pride%20and%20Prejudice.1342.epub"
    assert first["html_url"] == "/read/gutenberg_en_all/Pride%20and%20Prejudice.1342"
    assert first["cover_url"] == "/kiwix/content/gutenberg_en_all/covers/1342_cover_image.jpg"
    assert first["shelf"] == "PR" and first["shelf_name"] == "English literature"
    page = populated.get("/api/books", params={"limit": 2, "offset": 2}).json()
    assert [b["id"] for b in page["items"]] == [1232, 11339] and page["total"] == 6


def test_books_search_ranks_a_title_hit_first_and_counts_the_matches(populated):
    body = populated.get("/api/books", params={"q": "prince"}).json()
    assert body["total"] == 1 and body["items"][0]["title"] == "The Prince"
    body = populated.get("/api/books", params={"q": "austen"}).json()
    assert body["items"][0]["id"] == 1342


def test_books_filters_by_shelf_and_author_and_sorts_by_title(populated):
    assert [b["id"] for b in populated.get("/api/books", params={"shelf": "PR"}).json()["items"]] == [1342]
    assert [b["id"] for b in populated.get("/api/books", params={"author": "Aesop"}).json()["items"]] == [11339]
    titles = [b["title"] for b in populated.get("/api/books", params={"sort": "title"}).json()["items"]]
    assert titles == sorted(titles, key=str.lower)


def test_books_is_empty_and_unavailable_without_the_zim(client):
    assert client.get("/api/books").json() == {"items": [], "total": 0, "available": False}
    assert client.get("/api/books/shelves").json() == []


def test_book_shelves_carry_names_and_counts(populated):
    shelves = populated.get("/api/books/shelves").json()
    assert shelves[0]["count"] == 1 and {s["code"] for s in shelves} == {"PR", "PS", "J", "PA", "E"}
    assert next(s for s in shelves if s["code"] == "J")["name"] == "Political science"


def test_one_book_with_and_without_an_epub(populated):
    r = populated.get("/api/books/gutenberg/1342")
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Pride and Prejudice" and body["available"] is True and body["position"] is None
    aesop = populated.get("/api/books/gutenberg/11339").json()
    assert aesop["epub_url"] is None
    assert aesop["html_url"] == "/read/gutenberg_en_all/Aesop%27s%20Fables%20-%20A%20New%20Translation.11339"
    assert populated.get("/api/books/gutenberg/999").status_code == 404


def test_one_book_says_unavailable_when_the_zim_has_gone(populated, env):
    conn = db.connect(env.db_path)
    conn.execute("UPDATE library_items SET available=0 WHERE id='gutenberg_en_all'")
    conn.commit()
    conn.close()
    assert populated.get("/api/books/gutenberg/1342").json()["available"] is False


def test_reading_round_trips_newest_first_and_links_each_key(client):
    client.put("/api/reading/gutenberg:1342", json={"title": "Pride and Prejudice", "author": "Jane Austen",
                                                     "cover_url": "/c1.jpg", "cfi": "epubcfi(/6/4)", "percent": 10.0})
    client.put("/api/reading/doc:where-there-is-no-doctor", json={"title": "Where There Is No Doctor", "author": None,
                                                                   "cover_url": None, "cfi": "epubcfi(/6/8)", "percent": 40.0})
    rows = client.get("/api/reading").json()
    assert [r["key"] for r in rows] == ["doc:where-there-is-no-doctor", "gutenberg:1342"]
    assert rows[0]["url"] == "/doc/where-there-is-no-doctor" and rows[1]["url"] == "/book/gutenberg/1342"
    one = client.get("/api/reading/gutenberg:1342")
    assert one.status_code == 200 and one.json()["percent"] == 10.0
    client.put("/api/reading/gutenberg:1342", json={"title": "Pride and Prejudice", "author": "Jane Austen",
                                                     "cover_url": "/c1.jpg", "cfi": "epubcfi(/6/6)", "percent": 20.0})
    assert [r["key"] for r in client.get("/api/reading").json()][0] == "gutenberg:1342"   # an update is a fresh read
    assert client.delete("/api/reading/gutenberg:1342").status_code == 200
    assert client.get("/api/reading/gutenberg:1342").status_code == 404
    assert client.get("/api/reading").json()[0]["key"] == "doc:where-there-is-no-doctor"


def test_reading_rejects_an_empty_place(client):
    r = client.put("/api/reading/gutenberg:1", json={"title": "", "author": None, "cover_url": None, "cfi": "", "percent": 0})
    assert r.status_code == 422


def test_one_book_shows_its_saved_position(populated):
    populated.put("/api/reading/gutenberg:1342", json={"title": "Pride and Prejudice", "author": "Jane Austen",
                                                        "cover_url": None, "cfi": "epubcfi(/6/4!/4/2/2)", "percent": 12.5})
    assert populated.get("/api/books/gutenberg/1342").json()["position"] == {"cfi": "epubcfi(/6/4!/4/2/2)", "percent": 12.5}


def test_recent_is_one_list_across_the_library_newest_first_and_capped(client):
    client.put("/api/recent/gutenberg:1342", json={"kind": "book", "title": "Pride and Prejudice", "url": "/book/gutenberg/1342", "cover_url": "/c1.jpg"})
    client.put("/api/recent/card:cpr-adult", json={"kind": "card", "title": "CPR, adult", "url": "/medical/card/cpr-adult"})
    client.put("/api/recent/article:wikipedia_en_all/A/Water", json={"kind": "article", "title": "Water", "url": "/read/wikipedia_en_all/A/Water"})
    rows = client.get("/api/recent").json()
    assert [r["key"] for r in rows] == ["article:wikipedia_en_all/A/Water", "card:cpr-adult", "gutenberg:1342"]
    assert rows[2]["cover_url"] == "/c1.jpg" and rows[1]["cover_url"] is None and rows[0]["kind"] == "article"
    client.put("/api/recent/gutenberg:1342", json={"kind": "book", "title": "Pride and Prejudice", "url": "/book/gutenberg/1342", "cover_url": "/c1.jpg"})
    assert client.get("/api/recent").json()[0]["key"] == "gutenberg:1342"   # opened again: to the front
    assert [r["key"] for r in client.get("/api/recent?limit=2").json()] == ["gutenberg:1342", "article:wikipedia_en_all/A/Water"]
    assert client.delete("/api/recent/card:cpr-adult").status_code == 200
    assert len(client.get("/api/recent").json()) == 2
    # a kind the Library does not have, an empty title, or an address off the box are refused
    assert client.put("/api/recent/x", json={"kind": "video", "title": "x", "url": "/x"}).status_code == 422
    assert client.put("/api/recent/x", json={"kind": "page", "title": "", "url": "/x"}).status_code == 422
    assert client.put("/api/recent/x", json={"kind": "page", "title": "x", "url": "https://example.com/"}).status_code == 422
    # only the last sixty are kept
    for i in range(70):
        client.put(f"/api/recent/page:p{i}", json={"kind": "page", "title": f"Page {i}", "url": f"/p/p{i}"})
    assert len(client.get("/api/recent?limit=60").json()) == 60
    assert client.get("/api/recent?limit=60").json()[0]["key"] == "page:p69"

