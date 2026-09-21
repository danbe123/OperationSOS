import gzip
import shutil
from pathlib import Path

from sos import db, places

FIXTURES = Path(__file__).parent / "fixtures"


def _conn():
    conn = db.connect(":memory:")
    db.init_schema(conn)
    return conn


def test_import_places_csv_and_gzip(tmp_path):
    conn = _conn()
    n = places.import_places(conn, FIXTURES / "places.csv")
    assert n == 200
    gz = tmp_path / "places.csv.gz"
    with open(FIXTURES / "places.csv", "rb") as src, gzip.open(gz, "wb") as dst:
        shutil.copyfileobj(src, dst)
    assert places.import_places(conn, gz) == 200
    assert conn.execute("SELECT count(*) FROM fts_places").fetchone()[0] == 200


def test_import_skips_when_unchanged_and_reimports_on_change(tmp_path):
    conn = _conn()
    csv = tmp_path / "places.csv"
    shutil.copy(FIXTURES / "places.csv", csv)
    assert places.import_places(conn, csv) == 200
    assert places.import_places(conn, csv) is None
    csv.write_text(csv.read_text(encoding="utf-8") + "Newtown,town,52.0,-1.0,England,\n", encoding="utf-8")
    assert places.import_places(conn, csv) == 201
    assert places.import_places(conn, csv, force=True) == 201


def test_import_missing_file_returns_zero(tmp_path):
    conn = _conn()
    assert places.import_places(conn, tmp_path / "nope.csv.gz") == 0


def test_query_places_prefix_min_three_chars():
    conn = _conn()
    places.import_places(conn, FIXTURES / "places.csv")
    assert places.query_places(conn, "ox") == []
    names = [p["name"] for p in places.query_places(conn, "oxf")]
    assert names[0] == "Oxford"
    names = [p["name"] for p in places.query_places(conn, "ox")]
    assert names == []
    names = [p["name"] for p in places.query_places(conn, "oxt")]
    assert names == ["Oxted"]
    both = [p["name"] for p in places.query_places(conn, "burn")]
    assert both[:2] == ["Burnley", "Burnham-on-Sea"]
    assert len(places.query_places(conn, "test hamlet", limit=100)) == 25
    assert len(places.query_places(conn, "test hamlet", limit=5)) == 5
    p = places.query_places(conn, "st hel")[0]
    assert p == {"name": "St Helier", "kind": "town", "lat": 49.1858, "lon": -2.1069, "region": "Jersey", "postcode": None}


def test_exact_place_and_postcode():
    conn = _conn()
    places.import_places(conn, FIXTURES / "places.csv")
    assert places.exact_place(conn, "oxford")["name"] == "Oxford"
    assert places.exact_place(conn, "Oxf") is None
    assert places.exact_place(conn, "SW1A 1AA")["postcode"] == "SW1A 1AA"
    assert places.exact_place(conn, "sw1a1aa")["name"] == "SW1A 1AA"
    assert places.exact_place(conn, "") is None


def test_only_a_postcode_pays_for_the_table_scan():
    """Every search asks for its exact place; the fallback that scans the whole 2.7-million-row table for a
    squashed name is for postcodes ("sw1a1aa") alone, so an ordinary query costs one indexed lookup."""
    conn = _conn()
    places.import_places(conn, FIXTURES / "places.csv")
    statements: list[str] = []
    conn.set_trace_callback(statements.append)
    assert places.exact_place(conn, "how do I make water safe to drink") is None
    assert places.exact_place(conn, "water") is None
    assert not [s for s in statements if "REPLACE(" in s]
    assert places.exact_place(conn, "sw1a1aa")["name"] == "SW1A 1AA"
    assert [s for s in statements if "REPLACE(" in s]
