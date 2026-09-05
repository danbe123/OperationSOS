import json

import pytest

from sos.mapbuild import base
from sos.mapbuild.base import BaseStep, check_base, extract_command, PROBES_FULL, PROBES_FIXTURE
from sos.mapbuild.common import BuildError, SPEC_BBOX, FIXTURE_BBOX
from tests.mapbuild_helpers import FakeRunner, make_ctx

FULL_HEADER = {"tile_compression": "gzip", "tile_type": "mvt", "minzoom": 0, "maxzoom": 15,
               "bounds": [-11.0, 49.1, 2.2, 61.2], "center": [-4.4, 55.15, 0]}
FIXTURE_HEADER = {"tile_compression": "gzip", "tile_type": "mvt", "minzoom": 0, "maxzoom": 15,
                  "bounds": [-1.56, 50.87, -1.46, 50.97], "center": [-1.51, 50.92, 0]}


def test_check_base_passes_on_good_header():
    assert check_base(FULL_HEADER, SPEC_BBOX, PROBES_FULL, lambda z, x, y: True) == []


def test_check_base_reports_missing_probe_tile():
    missing_st_helier = lambda z, x, y: (z, x, y) != (12, 2023, 1403)
    problems = check_base(FULL_HEADER, SPEC_BBOX, PROBES_FULL, missing_st_helier)
    assert len(problems) == 1 and "St Helier" in problems[0] and "z12" in problems[0]


def test_check_base_reports_short_bbox_wrong_zoom_and_tile_type():
    header = dict(FULL_HEADER, bounds=[-11.0, 49.5, 2.2, 61.2], maxzoom=14, tile_type="png")
    problems = check_base(header, SPEC_BBOX, {}, lambda z, x, y: True)
    assert any("49.5" in p for p in problems)
    assert any("maxzoom 14" in p for p in problems)
    assert any("tile type" in p for p in problems)
    assert len(problems) == 3


def test_extract_command_is_the_spec_command(tmp_path):
    ctx = make_ctx(tmp_path, fixture=False)
    cmd = extract_command(ctx, base.build_url(ctx), tmp_path / "uk-ie.pmtiles")
    assert cmd == ["pmtiles", "extract", "https://build.protomaps.com/20260902.pmtiles", str(tmp_path / "uk-ie.pmtiles"),
                   "--bbox=-11,49.1,2.2,61.2", "--download-threads=8"]


def test_base_step_extracts_verifies_commits_and_writes_sidecar(tmp_path):
    runner = FakeRunner(outputs={"pmtiles show": json.dumps(FIXTURE_HEADER), "pmtiles tile": b"\x1f\x8b"},
                        files={"test.pmtiles": b"PMTiles"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    BaseStep().run(ctx)
    extract = runner.find("pmtiles", "extract")[0]
    assert extract[3] == str(ctx.incoming / "test.pmtiles")
    assert "--bbox=-1.56,50.87,-1.46,50.97" in extract
    assert (ctx.out / "test.pmtiles").read_bytes() == b"PMTiles"
    assert not (ctx.incoming / "test.pmtiles").exists()
    probes = runner.find("pmtiles", "tile")
    assert probes == [["pmtiles", "tile", str(ctx.incoming / "test.pmtiles"), "12", "2031", "1372"]]  # OS HQ at z12
    side = json.loads((ctx.out / "test.json").read_text())
    assert side["build"] == "20260902" and side["bbox"] == list(FIXTURE_BBOX) and side["header"]["maxzoom"] == 15
    assert side["source"] == "https://build.protomaps.com/20260902.pmtiles"


def test_base_step_fails_and_leaves_nothing_when_probe_missing(tmp_path):
    runner = FakeRunner(outputs={"pmtiles show": json.dumps(FIXTURE_HEADER), "pmtiles tile": b""},
                        files={"test.pmtiles": b"PMTiles"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    with pytest.raises(BuildError, match="OS HQ"):
        BaseStep().run(ctx)
    assert not (ctx.out / "test.pmtiles").exists()


def test_full_mode_probes_st_helier_and_lerwick(tmp_path):
    runner = FakeRunner(outputs={"pmtiles show": json.dumps(FULL_HEADER), "pmtiles tile": b"\x1f\x8b"},
                        files={"uk-ie.pmtiles": b"PMTiles"})
    ctx = make_ctx(tmp_path, fixture=False, runner=runner)
    BaseStep().run(ctx)
    probed = {tuple(c[-3:]) for c in runner.find("pmtiles", "tile")}
    assert probed == {("12", "2023", "1403"), ("12", "2034", "1186")}
    assert set(PROBES_FULL) == {"St Helier", "Lerwick"} and set(PROBES_FIXTURE) == {"OS HQ Southampton"}
