"""Test doubles for the build-maps pipeline: a recording runner and a Context factory."""
from __future__ import annotations

import subprocess
from pathlib import Path

from sos.mapbuild.common import Context

REPO = Path(__file__).resolve().parents[2]

DEFAULT_VERSIONS = {
    "PROTOMAPS_BUILD": "20260902",
    "PROTOMAPS_BUILDS_BASE": "https://build.protomaps.com",
    "PROTOMAPS_BASEMAPS_NPM": "5.7.2",
    "BASEMAPS_ASSETS_COMMIT": "028c18f713baecad011301ff7a69acc39bcc2ae7",
    "OS_ZOOMSTACK_STYLES_COMMIT": "d23143b4a36435680eda99b4febb3187398f594f",
    "OS_DOWNLOADS_API": "https://api.os.uk/downloads/v1",
    "GEOFABRIK_PBF_URL": "https://example.test/britain-and-ireland-latest.osm.pbf",
    "GEOFABRIK_FIXTURE_PBF_URL": "https://example.test/hampshire-latest.osm.pbf",
    "COPERNICUS_DEM_BASE": "https://example.test/dem",
    "OSNI_DTM_URL": "",
    "ORGANICMAPS_TAG": "2026.08.27-18-android",
    "ORGANICMAPS_CDN": "https://example.test/maps",
    "ORGANICMAPS_APK_URL": "https://example.test/OrganicMaps-26082718-web-release.apk",
    "ORGANICMAPS_APK_SHA256": "1f19229d95b731862349d504b150dad63eb405caa83e98c96bfe93b7acae3c7a",
    "FLOOD_EN_URL": "",
    "FLOOD_WA_URL": "",
    "FLOOD_SC_URL": "",
    "FLOOD_NI_URL": "",
    "FLOOD_IE_URL": "",
    "ACCESS_EN_URL": "",
    "ACCESS_WA_URL": "",
}


class FakeRunner:
    """Records every command. `outputs` maps "tool subcommand" to stdout (str, bytes or a callable of the
    command). `files` maps a path suffix to bytes: any command token ending with that suffix is created
    with those bytes, and an aria2c command creates `-d/-o` with the bytes keyed by the `-o` name."""

    def __init__(self, outputs: dict[str, object] | None = None, files: dict[str, bytes] | None = None):
        self.outputs = outputs or {}
        self.files = files or {}
        self.calls: list[list[str]] = []

    def __call__(self, cmd, *, cwd=None, capture=False, binary=False):
        cmd = [str(c) for c in cmd]
        self.calls.append(cmd)
        if cmd[0] == "aria2c":
            directory = Path(cmd[cmd.index("-d") + 1])
            name = cmd[cmd.index("-o") + 1]
            directory.mkdir(parents=True, exist_ok=True)
            (directory / name).write_bytes(self.files.get(name, b"downloaded"))
        else:
            for token in cmd:
                for suffix, data in self.files.items():
                    if "/" in token and token.endswith(suffix):
                        Path(token).parent.mkdir(parents=True, exist_ok=True)
                        Path(token).write_bytes(data)
        out = self.outputs.get(" ".join(cmd[:2]), "")
        if callable(out):
            out = out(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")

    def find(self, *prefix: str) -> list[list[str]]:
        return [c for c in self.calls if c[: len(prefix)] == list(prefix)]


def make_ctx(tmp_path: Path, *, fixture: bool = True, runner=None, versions: dict[str, str] | None = None,
             force: bool = False, build: str = "20260902") -> Context:
    out = tmp_path / "out"
    src = tmp_path / "src"
    out.mkdir(parents=True, exist_ok=True)
    src.mkdir(parents=True, exist_ok=True)
    merged = dict(DEFAULT_VERSIONS)
    merged.update(versions or {})
    return Context(out=out, src=src, fixture=fixture, force=force, build=build, versions=merged,
                   repo=REPO, runner=runner or FakeRunner())
