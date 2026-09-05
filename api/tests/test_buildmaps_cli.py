import json
from pathlib import Path

import pytest

from sos import buildmaps
from sos.mapbuild import common
from sos.mapbuild.common import BuildError, Context, read_versions, lonlat_to_tile
from tests.mapbuild_helpers import FakeRunner, make_ctx


def test_missing_tools_exit_2_with_micromamba_hint(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(buildmaps, "check_tools", lambda: ["tippecanoe", "pmtiles"])
    rc = buildmaps.main(["--out", str(tmp_path)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "tippecanoe" in err and "pmtiles" in err
    assert "micromamba activate sos-maps" in err


def test_check_tools_lists_only_missing():
    missing = common.check_tools(which=lambda t: None if t in ("osmium", "gdalwarp") else "/usr/bin/" + t)
    assert missing == ["osmium", "gdalwarp"]


def test_read_versions_parses_env_file(tmp_path):
    env = tmp_path / "versions.env"
    env.write_text('# comment\nPROTOMAPS_BUILD=20260902\nORGANICMAPS_TAG="2026.08.27-18-android"\n\nBROKEN LINE\n')
    assert read_versions(env) == {"PROTOMAPS_BUILD": "20260902", "ORGANICMAPS_TAG": "2026.08.27-18-android"}
    assert read_versions(tmp_path / "missing.env") == {}


def test_context_version_raises_on_blank(tmp_path):
    ctx = make_ctx(tmp_path, versions={"OSNI_DTM_URL": ""})
    with pytest.raises(BuildError, match="OSNI_DTM_URL"):
        ctx.version("OSNI_DTM_URL")
    assert ctx.version("PROTOMAPS_BUILDS_BASE") == "https://build.protomaps.com"


def test_fixture_context_uses_fixture_bbox_and_name(tmp_path):
    ctx = make_ctx(tmp_path, fixture=True)
    assert ctx.bbox == (-1.56, 50.87, -1.46, 50.97)
    assert ctx.base_name == "test.pmtiles"
    full = make_ctx(tmp_path, fixture=False)
    assert full.bbox == (-11.0, 49.1, 2.2, 61.2)
    assert full.base_name == "uk-ie.pmtiles"
    assert common.bbox_str(full.bbox) == "-11,49.1,2.2,61.2"


def test_stage_then_commit_renames_into_place(tmp_path):
    ctx = make_ctx(tmp_path)
    staged = ctx.stage("overlays/health.geojson")
    assert staged == ctx.incoming / "overlays" / "health.geojson"
    staged.write_text("{}")
    final = ctx.commit("overlays/health.geojson")
    assert final == ctx.out / "overlays" / "health.geojson"
    assert final.read_text() == "{}"
    assert not staged.exists()


def test_commit_replaces_existing_directory(tmp_path):
    ctx = make_ctx(tmp_path)
    (ctx.out / "styles").mkdir()
    (ctx.out / "styles" / "old.json").write_text("old")
    d = ctx.stage("styles")
    d.mkdir()
    (d / "new.json").write_text("new")
    ctx.commit("styles")
    assert sorted(p.name for p in (ctx.out / "styles").iterdir()) == ["new.json"]


def test_sidecar_records_size_and_data(tmp_path):
    ctx = make_ctx(tmp_path)
    ctx.stage("x.pmtiles").write_bytes(b"12345")
    ctx.commit("x.pmtiles")
    side = ctx.write_sidecar("x.pmtiles", {"step": "base"})
    assert side == ctx.out / "x.json"
    data = json.loads(side.read_text())
    assert data["output"] == "x.pmtiles" and data["size_bytes"] == 5 and data["step"] == "base"
    assert "built_at" in data
    assert ctx.sidecar("x.pmtiles")["size_bytes"] == 5
    assert ctx.sidecar("missing.pmtiles") is None
    assert common.sidecar_path(Path("/m/places.csv.gz")) == Path("/m/places.json")
    assert common.sidecar_path(Path("/m/styles")) == Path("/m/styles.json")


def test_download_uses_aria2c_and_caches(tmp_path):
    runner = FakeRunner(files={"a.zip": b"zipbytes"})
    ctx = make_ctx(tmp_path, runner=runner)
    path = ctx.download("https://example.test/a.zip", "a.zip", md5="abc")
    assert path == ctx.src / "a.zip" and path.read_bytes() == b"zipbytes"
    cmd = runner.calls[0]
    assert cmd[0] == "aria2c" and "-c" in cmd and "--checksum=md5=abc" in cmd
    assert cmd[cmd.index("-d") + 1] == str(ctx.src) and cmd[cmd.index("-o") + 1] == "a.zip"
    assert cmd[-1] == "https://example.test/a.zip"
    ctx.download("https://example.test/a.zip", "a.zip")
    assert len(runner.calls) == 1, "second download must be served from the cache"


def test_download_into_subdirectory(tmp_path):
    runner = FakeRunner()
    ctx = make_ctx(tmp_path, runner=runner)
    path = ctx.download("https://example.test/t.tif", "copernicus/t.tif", sha256="ff" * 32)
    assert path == ctx.src / "copernicus" / "t.tif" and path.exists()
    cmd = runner.calls[0]
    assert cmd[cmd.index("-d") + 1] == str(ctx.src / "copernicus")
    assert "--checksum=sha-256=" + "ff" * 32 in cmd


def test_lonlat_to_tile_known_points():
    assert lonlat_to_tile(49.19, -2.11, 12) == (2023, 1403)   # St Helier
    assert lonlat_to_tile(60.15, -1.15, 12) == (2034, 1186)   # Lerwick
    assert lonlat_to_tile(50.9, -1.4, 10) == (508, 343)


def test_pmtiles_helpers_parse_header_metadata_and_tiles(tmp_path):
    header = {"tile_type": "mvt", "minzoom": 0, "maxzoom": 15, "bounds": [-11, 49.1, 2.2, 61.2]}
    meta = {"vector_layers": [{"id": "roads", "fields": {}}, {"id": "water", "fields": {}}]}
    runner = FakeRunner(outputs={
        "pmtiles show": lambda cmd: json.dumps(header if "--header-json" in cmd else meta),
        "pmtiles tile": lambda cmd: b"\x1f\x8b" if cmd[-2:] == ["2023", "1403"] else b"",
    })
    ctx = make_ctx(tmp_path, runner=runner)
    assert common.pmtiles_header(ctx, Path("/x/a.pmtiles"))["maxzoom"] == 15
    assert common.vector_layer_ids(common.pmtiles_metadata(ctx, Path("/x/a.pmtiles"))) == {"roads", "water"}
    assert common.tile_exists(ctx, Path("/x/a.pmtiles"), 12, 2023, 1403) is True
    assert common.tile_exists(ctx, Path("/x/a.pmtiles"), 12, 1, 1) is False
    common.pmtiles_verify(ctx, Path("/x/a.pmtiles"))
    assert runner.find("pmtiles", "verify") == [["pmtiles", "verify", "/x/a.pmtiles"]]


class DummyStep:
    def __init__(self, sid, outputs):
        self.id = sid
        self._outputs = outputs
        self.runs = 0

    def outputs(self, ctx):
        return self._outputs

    def run(self, ctx):
        self.runs += 1
        for name in self._outputs:
            p = ctx.stage(name)
            p.write_text("built")
            ctx.commit(name)


def test_run_steps_skips_up_to_date_and_force_rebuilds(tmp_path, monkeypatch):
    step = DummyStep("base", ["test.pmtiles"])
    monkeypatch.setattr(buildmaps, "all_steps", lambda: [step])
    ctx = make_ctx(tmp_path)
    buildmaps.run_steps(ctx, ["base"])
    buildmaps.run_steps(ctx, ["base"])
    assert step.runs == 1
    ctx.force = True
    buildmaps.run_steps(ctx, ["base"])
    assert step.runs == 2


def test_run_steps_fails_when_step_leaves_outputs_missing(tmp_path, monkeypatch):
    class Lazy(DummyStep):
        def run(self, ctx):
            self.runs += 1
    monkeypatch.setattr(buildmaps, "all_steps", lambda: [Lazy("base", ["test.pmtiles"])])
    with pytest.raises(BuildError, match="did not produce"):
        buildmaps.run_steps(make_ctx(tmp_path), ["base"])


def test_select_steps_keeps_registry_order_and_rejects_unknown(monkeypatch):
    a, b = DummyStep("base", []), DummyStep("verify", [])
    monkeypatch.setattr(buildmaps, "all_steps", lambda: [a, b])
    assert [s.id for s in buildmaps.select_steps(["verify", "base"])] == ["base", "verify"]
    assert [s.id for s in buildmaps.select_steps(None)] == ["base", "verify"]
    with pytest.raises(BuildError, match="hillshade"):
        buildmaps.select_steps(["hillshade"])


def test_run_resolves_defaults_and_runs_selected_steps(tmp_path, monkeypatch):
    monkeypatch.setattr(buildmaps, "check_tools", lambda: [])
    monkeypatch.setattr(buildmaps, "repo_root", lambda: tmp_path)
    (tmp_path / "install").mkdir()
    (tmp_path / "install" / "versions.env").write_text("PROTOMAPS_BUILD=20260902\n")
    monkeypatch.setenv("SOS_MAPS_SRC", str(tmp_path / "cache"))
    seen = {}
    def fake_run_steps(ctx, ids):
        seen["ctx"], seen["ids"] = ctx, ids
    monkeypatch.setattr(buildmaps, "run_steps", fake_run_steps)
    rc = buildmaps.main(["--fixture", "--steps", "base", "verify", "--build", "20260101"])
    assert rc == 0
    ctx = seen["ctx"]
    assert seen["ids"] == ["base", "verify"]
    assert ctx.fixture is True and ctx.build == "20260101"
    assert ctx.out == tmp_path / "api" / "tests" / "fixtures" / "maps"
    assert ctx.src == tmp_path / "cache"
    assert ctx.out.is_dir() and ctx.src.is_dir()


def test_run_returns_1_on_build_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(buildmaps, "check_tools", lambda: [])
    monkeypatch.setattr(buildmaps, "repo_root", lambda: tmp_path)
    (tmp_path / "install").mkdir()
    (tmp_path / "install" / "versions.env").write_text("PROTOMAPS_BUILD=20260902\n")
    def boom(ctx, ids):
        raise BuildError("no z12 tile covering Lerwick")
    monkeypatch.setattr(buildmaps, "run_steps", boom)
    assert buildmaps.main(["--out", str(tmp_path / "o"), "--steps", "base"]) == 1
    assert "Lerwick" in capsys.readouterr().err


def test_cli_exposes_build_maps(capsys):
    from sos import cli
    with pytest.raises(SystemExit) as exc:
        cli.main(["build-maps", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for flag in ("--out", "--steps", "--build", "--fixture", "--force"):
        assert flag in out
