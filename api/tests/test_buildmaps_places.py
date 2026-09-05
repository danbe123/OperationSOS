import csv
import gzip
import io
import json
import zipfile

import httpx
import pytest
import respx

from sos.mapbuild import places
from sos.mapbuild.common import BuildError, FIXTURE_BBOX
from tests.mapbuild_helpers import FakeRunner, make_ctx

NAMES_API = "https://api.os.uk/downloads/v1/products/OpenNames/downloads"
NAMES_ENTRIES = [{"md5": "4a7d2d0d24be0470771b9cc170ca2aee", "size": 103259564, "fileName": "opname_csv_gb.zip",
                  "url": "https://api.os.uk/downloads/v1/products/OpenNames/downloads?area=GB&format=CSV&redirect", "format": "CSV", "area": "GB"}]
HEADER = ["ID", "NAMES_URI", "NAME1", "NAME1_LANG", "TYPE", "LOCAL_TYPE", "GEOMETRY_X", "GEOMETRY_Y", "POSTCODE_DISTRICT",
          "POPULATED_PLACE", "DISTRICT_BOROUGH", "COUNTY_UNITARY", "REGION", "COUNTRY"]


def _row(name, local_type, x, y, *, district="SO40", place="", county="Hampshire", region="South East", country="England"):
    return {"ID": "1", "NAMES_URI": "", "NAME1": name, "NAME1_LANG": "", "TYPE": "", "LOCAL_TYPE": local_type, "GEOMETRY_X": str(x),
            "GEOMETRY_Y": str(y), "POSTCODE_DISTRICT": district, "POPULATED_PLACE": place, "DISTRICT_BOROUGH": "",
            "COUNTY_UNITARY": county, "REGION": region, "COUNTRY": country}


class FakeTransformer:
    """27700 -> 4326 stand-in: linear around (440000, 110000) = (-1.5, 50.9)."""

    def __init__(self, inverse=False):
        self.inverse = inverse

    def transform(self, xs, ys):
        if self.inverse:
            return ([440000 + (lon + 1.5) * 70000 for lon in xs], [110000 + (lat - 50.9) * 111000 for lat in ys])
        return ([-1.5 + (x - 440000) / 70000 for x in xs], [50.9 + (y - 110000) / 111000 for y in ys])


def _names_zip(rows):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("Doc/OS_Open_Names_Header.csv", ",".join(HEADER) + "\n")
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=HEADER)
        for row in rows:
            writer.writerow(row)
        zf.writestr("Data/SU41.csv", out.getvalue())
        zf.writestr("Data/readme.txt", "not a csv")
    return buf.getvalue()


SAMPLE_ROWS = [
    _row("Totton", "Town", 436000, 112500, district="SO40"),
    _row("Eling", "Village", 436800, 112200, district="SO40"),
    _row("SO40 3ZZ", "Postcode", 436100, 112600, district="SO40"),
    _row("High Street", "Section Of Named Road", 436000, 112000, place="Totton"),
    _row("High Street", "Section Of Named Road", 436200, 112400, place="Totton"),
    _row("High Street", "Named Road", 700000, 300000, place="Lowestoft", region="East of England"),
    _row("Solent", "Sea", 440000, 100000),
    _row("Somewhere", "Hamlet", 480000, 140000, region="", county="", country="Wales"),
    _row("", "Town", 436000, 112500),
]


def test_read_header_and_rows_come_from_the_zip():
    with zipfile.ZipFile(io.BytesIO(_names_zip(SAMPLE_ROWS))) as zf:
        header = places.read_header(zf)
        assert header == HEADER
        rows = list(places.os_names_rows(zf, header))
    assert len(rows) == len(SAMPLE_ROWS) and rows[0]["NAME1"] == "Totton" and rows[0]["LOCAL_TYPE"] == "Town"


def test_reduce_os_rows_filters_types_collapses_roads_and_sets_postcodes():
    reduced = places.reduce_os_rows(SAMPLE_ROWS)
    by_name = {(r[0], r[1]): r for r in reduced}
    assert set(by_name) == {("Totton", "town"), ("Eling", "village"), ("SO40 3ZZ", "postcode"), ("High Street", "named-road"), ("Somewhere", "hamlet")}
    assert [r for r in reduced if r[0] == "High Street"] == [("High Street", "named-road", 436100.0, 112200.0, "Totton", "SO40"),
                                                            ("High Street", "named-road", 700000.0, 300000.0, "Lowestoft", "SO40")]
    assert by_name[("SO40 3ZZ", "postcode")][5] == "SO40 3ZZ"
    assert by_name[("Totton", "town")][4] == "South East" and by_name[("Totton", "town")][5] == "SO40"
    assert by_name[("Somewhere", "hamlet")][4] == "Wales", "REGION then COUNTY_UNITARY then COUNTRY"
    assert not any(r[0] == "Solent" for r in reduced) and not any(r[0] == "" for r in reduced)


def test_reduce_os_rows_prefilters_on_the_os_bbox():
    reduced = places.reduce_os_rows(SAMPLE_ROWS, os_bbox=(430000, 110000, 450000, 120000))
    assert {r[0] for r in reduced} == {"Totton", "Eling", "SO40 3ZZ", "High Street"}


def test_transform_rows_rounds_and_filters_by_bbox():
    rows = [("Totton", "town", 440000.0, 110000.0, "South East", "SO40"), ("Far", "town", 600000.0, 110000.0, "", "")]
    out = places.transform_rows(rows, FakeTransformer(), bbox=FIXTURE_BBOX)
    assert out == [["Totton", "town", 50.9, -1.5, "South East", "SO40"]]
    assert len(places.transform_rows(rows, FakeTransformer())) == 2


def test_os_bbox_for_uses_the_inverse_transformer_with_a_margin():
    xmin, ymin, xmax, ymax = places.os_bbox_for(FIXTURE_BBOX, FakeTransformer(inverse=True), margin_m=1000)
    assert xmin == pytest.approx(440000 + (-1.56 + 1.5) * 70000 - 1000)
    assert xmax == pytest.approx(440000 + (-1.46 + 1.5) * 70000 + 1000)
    assert ymin == pytest.approx(110000 + (50.87 - 50.9) * 111000 - 1000)
    assert ymax == pytest.approx(110000 + (50.97 - 50.9) * 111000 + 1000)


def test_osm_place_rows_keeps_named_place_nodes_only():
    features = [
        {"type": "Feature", "properties": {"name": "Newry", "place": "city"}, "geometry": {"type": "Point", "coordinates": [-6.34, 54.1753]}},
        {"type": "Feature", "properties": {"place": "village"}, "geometry": {"type": "Point", "coordinates": [-6.0, 54.0]}},
        {"type": "Feature", "properties": {"name": "Islet", "place": "island"}, "geometry": {"type": "Point", "coordinates": [-6.0, 54.0]}},
        {"type": "Feature", "properties": {"name": "Area", "place": "town"}, "geometry": {"type": "Polygon", "coordinates": []}},
    ]
    assert places.osm_place_rows(features, "Northern Ireland") == [["Newry", "city", 54.1753, -6.34, "Northern Ireland", ""]]


def test_write_places_writes_gzip_csv_with_header(tmp_path):
    path = tmp_path / "places.csv.gz"
    n = places.write_places(path, [["Totton", "town", 50.9, -1.5, "South East", "SO40"], ["Newry", "city", 54.1753, -6.34, "Northern Ireland", ""]])
    assert n == 2
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == ["name", "kind", "lat", "lon", "region", "postcode"]
    assert rows[1] == ["Totton", "town", "50.9", "-1.5", "South East", "SO40"] and rows[2][5] == ""


def test_osm_places_full_mode_clips_per_region(tmp_path):
    seq = json.dumps({"type": "Feature", "properties": {"name": "Newry", "place": "city"}, "geometry": {"type": "Point", "coordinates": [-6.34, 54.1753]}}) + "\n"
    runner = FakeRunner(files={"places_ni.geojsonseq": seq.encode(), "places_roi.geojsonseq": b""})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner)
    regions = ctx.src / "regions"
    regions.mkdir()
    for region in ("roi", "iom", "jersey", "guernsey", "ni"):
        feats = [] if region in ("iom", "jersey", "guernsey") else [{"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [[[-8, 54], [-5, 54], [-5, 55.5], [-8, 54]]]}}]
        (regions / f"{region}.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    work = tmp_path / "work"
    work.mkdir()
    rows = places.osm_places(ctx, work)
    assert rows == [["Newry", "city", 54.1753, -6.34, "Northern Ireland", ""]]
    tags = runner.find("osmium", "tags-filter")[0]
    assert tags[-1] == "n/place=city,town,village,hamlet,suburb,locality"
    export = runner.find("osmium", "export")[0]
    assert "--geometry-types=point" in export and export[export.index("-c") + 1].endswith("export/places.json")
    clips = runner.find("ogr2ogr")
    assert [c[c.index("-clipsrc") + 1] for c in clips] == [str(regions / "roi.geojson"), str(regions / "ni.geojson")], "regions without a polygon are skipped"
    assert clips[0][1:3] == ["-f", "GeoJSONSeq"]


def test_osm_places_fixture_mode_runs_osmium_but_adds_no_rows(tmp_path):
    runner = FakeRunner(files={"fixture.osm.pbf": b"pbf"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    assert places.osm_places(ctx, tmp_path / "work") == []
    assert len(runner.find("osmium")) == 3 and not runner.find("ogr2ogr")  # extract, tags-filter, export


@respx.mock
def test_places_step_fixture_end_to_end(tmp_path, monkeypatch):
    respx.get(NAMES_API).mock(return_value=httpx.Response(200, json=NAMES_ENTRIES))
    monkeypatch.setattr(places, "make_transformer", lambda inverse=False: FakeTransformer(inverse))
    runner = FakeRunner(files={"opname_csv_gb.zip": _names_zip(SAMPLE_ROWS), "fixture.osm.pbf": b"pbf"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    places.PlacesStep().run(ctx)
    with gzip.open(ctx.out / "places.csv.gz", "rt", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    names = sorted((r["name"], r["kind"]) for r in rows)
    assert names == [("Eling", "village"), ("High Street", "named-road"), ("SO40 3ZZ", "postcode"), ("Totton", "town")], "rows outside the fixture bbox are dropped"
    totton = next(r for r in rows if r["name"] == "Totton")
    assert -1.56 <= float(totton["lon"]) <= -1.46 and 50.87 <= float(totton["lat"]) <= 50.97
    side = json.loads((ctx.out / "places.json").read_text())
    assert side["rows"] == 4 and side["gb_rows"] == 4 and side["osm_rows"] == 0 and side["columns"] == list(places.COLUMNS)
    assert runner.find("aria2c")[0][-1] == NAMES_ENTRIES[0]["url"]


def test_make_transformer_needs_pyproj(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def no_pyproj(name, *args, **kwargs):
        if name == "pyproj":
            raise ImportError("no pyproj")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_pyproj)
    with pytest.raises(BuildError, match=r"api\[maps\]"):
        places.make_transformer()
