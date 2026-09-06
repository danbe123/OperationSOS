"""Shared plumbing for `sos build-maps`: context, staging, downloads, tool checks, PMTiles helpers."""
from __future__ import annotations

import json
import logging
import math
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

log = logging.getLogger("sos.buildmaps")

BBox = tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat
SPEC_BBOX: BBox = (-11.0, 49.1, 2.2, 61.2)
# 0.1 degree box over Southampton Water and the New Forest edge; contains OS HQ (50.9379, -1.4708).
# Measured 4.9 MB at z15 on build 20260902 (the city-centre box is 6.8 MB and fails the 5 MiB rule).
FIXTURE_BBOX: BBox = (-1.56, 50.87, -1.46, 50.97)
FIXTURE_MAX_BYTES = 5 * 1024 * 1024
MICROMAMBA_HINT = (
    "activate the maps toolchain first:\n"
    '  export MAMBA_ROOT_PREFIX=$HOME/micromamba; eval "$(micromamba shell hook -s bash)"; '
    "micromamba activate sos-maps\n"
    "  export PATH=$HOME/.local/bin:$PATH   # pmtiles"
)
REQUIRED_TOOLS = (
    "pmtiles", "tippecanoe", "tile-join", "osmium", "ogr2ogr", "gdalwarp", "gdaldem", "gdal_translate",
    "gdaladdo", "gdalbuildvrt", "gdal_contour", "gdal_rasterize", "gdalinfo", "gdal", "aria2c", "node", "pnpm", "tar",
)


class BuildError(RuntimeError):
    """A pipeline failure carrying a message meant for the terminal."""


def bbox_str(bbox: BBox) -> str:
    return ",".join(f"{v:g}" for v in bbox)


def bbox_args(bbox: BBox) -> list[str]:
    return [f"{v:g}" for v in bbox]


def bbox_intersects(a: BBox, b: BBox) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def bbox_polygon(bbox: BBox) -> dict:
    x0, y0, x1, y1 = bbox
    ring = [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": [ring]}}]}


def lonlat_to_tile(lat: float, lon: float, z: int) -> tuple[int, int]:
    n = 2 ** z
    x = int((lon + 180.0) / 360.0 * n)
    lat_r = math.radians(lat)
    y = int((1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n)
    return x, y


def check_tools(which: Callable[[str], str | None] = shutil.which) -> list[str]:
    return [tool for tool in REQUIRED_TOOLS if which(tool) is None]


def read_versions(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def repo_root() -> Path:
    env = os.environ.get("SOS_REPO")
    root = Path(env).resolve() if env else Path(__file__).resolve().parents[3]
    if not (root / "install" / "versions.env").exists():
        raise BuildError(f"{root} is not the Operation SOS checkout (no install/versions.env); set SOS_REPO")
    return root


def dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def sidecar_path(final: Path) -> Path:
    """`uk-ie.pmtiles` -> `uk-ie.json`, `places.csv.gz` -> `places.json`, `styles/` -> `styles.json`."""
    return final.with_name(final.name.split(".", 1)[0] + ".json")


def real_runner(cmd: list[str], *, cwd: Path | None = None, capture: bool = False,
                binary: bool = False) -> subprocess.CompletedProcess:
    log.info("$ %s", shlex.join(cmd))
    try:
        return subprocess.run(
            cmd, cwd=cwd, check=True, text=not binary,
            stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None)
    except subprocess.CalledProcessError as exc:
        err = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode(errors="replace")
        raise BuildError(f"command failed (exit {exc.returncode}): {shlex.join(cmd)}\n{err[-2000:]}") from exc
    except FileNotFoundError as exc:
        raise BuildError(f"tool not found: {cmd[0]}\n{MICROMAMBA_HINT}") from exc


@dataclass
class Context:
    out: Path
    src: Path
    fixture: bool
    force: bool
    build: str
    versions: dict[str, str]
    repo: Path
    runner: Callable[..., subprocess.CompletedProcess] = real_runner

    @property
    def bbox(self) -> BBox:
        return FIXTURE_BBOX if self.fixture else SPEC_BBOX

    @property
    def base_name(self) -> str:
        return "test.pmtiles" if self.fixture else "uk-ie.pmtiles"

    @property
    def incoming(self) -> Path:
        return self.out / ".incoming"

    def version(self, key: str) -> str:
        value = self.versions.get(key, "")
        if not value:
            raise BuildError(f"install/versions.env has no value for {key}")
        return value

    def run(self, cmd: Iterable[object], *, cwd: Path | None = None, capture: bool = False,
            binary: bool = False) -> subprocess.CompletedProcess:
        return self.runner([str(c) for c in cmd], cwd=cwd, capture=capture, binary=binary)

    def output(self, name: str) -> Path:
        return self.out / name

    def stage(self, name: str) -> Path:
        path = self.incoming / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
        return path

    def commit(self, name: str) -> Path:
        staged = self.incoming / name
        final = self.out / name
        if not staged.exists():
            raise BuildError(f"nothing staged at {staged}")
        final.parent.mkdir(parents=True, exist_ok=True)
        if final.is_dir():
            shutil.rmtree(final)
        os.replace(staged, final)
        return final

    def write_sidecar(self, name: str, data: dict) -> Path:
        final = self.out / name
        side = sidecar_path(final)
        payload = {
            "output": name,
            "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "size_bytes": final.stat().st_size if final.is_file() else dir_size(final),
        }
        payload.update(data)
        side.write_text(json.dumps(payload, indent=2) + "\n")
        return side

    def sidecar(self, name: str) -> dict | None:
        side = sidecar_path(self.out / name)
        return json.loads(side.read_text()) if side.exists() else None

    def download(self, url: str, name: str, *, sha256: str | None = None, md5: str | None = None) -> Path:
        dest = self.src / name
        # aria2c leaves a <file>.aria2 control file next to its target while a download is in progress,
        # and removes it only on successful completion. If one is present, a prior download was
        # interrupted and dest is incomplete -- fall through to aria2c so its own -c flag resumes it.
        if dest.exists() and not dest.with_name(dest.name + ".aria2").exists():
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["aria2c", "-x", "8", "-s", "8", "-c", "--auto-file-renaming=false", "--allow-overwrite=true",
               "-d", str(dest.parent), "-o", dest.name]
        if sha256:
            cmd.append(f"--checksum=sha-256={sha256}")
        elif md5:
            cmd.append(f"--checksum=md5={md5}")
        cmd.append(url)
        self.run(cmd)
        if not dest.exists():
            raise BuildError(f"download of {url} did not produce {dest}")
        return dest


def fetch_github_tarball(ctx: Context, owner_repo: str, sha: str) -> Path:
    """Download and unpack https://github.com/<owner>/<repo>/archive/<sha>.tar.gz into the source cache."""
    repo = owner_repo.split("/")[1]
    target = ctx.src / f"{repo}-{sha}"
    if target.is_dir():
        return target
    tgz = ctx.download(f"https://github.com/{owner_repo}/archive/{sha}.tar.gz", f"{repo}-{sha}.tar.gz")
    ctx.run(["tar", "-xzf", str(tgz), "-C", str(ctx.src)])
    if not target.is_dir():
        raise BuildError(f"{tgz.name} did not unpack to {target}")
    return target


def pmtiles_header(ctx: Context, path: Path) -> dict:
    return json.loads(ctx.run(["pmtiles", "show", "--header-json", str(path)], capture=True).stdout)


def pmtiles_metadata(ctx: Context, path: Path) -> dict:
    return json.loads(ctx.run(["pmtiles", "show", "--metadata", str(path)], capture=True).stdout)


def vector_layer_ids(metadata: dict) -> set[str]:
    return {layer["id"] for layer in metadata.get("vector_layers", [])}


def tile_exists(ctx: Context, path: Path, z: int, x: int, y: int) -> bool:
    # `pmtiles tile` writes the tile bytes to stdout and nothing at all (exit 0) for an absent tile.
    proc = ctx.run(["pmtiles", "tile", str(path), str(z), str(x), str(y)], capture=True, binary=True)
    return bool(proc.stdout)


def pmtiles_verify(ctx: Context, path: Path) -> None:
    ctx.run(["pmtiles", "verify", str(path)])


def read_geojsonseq(path: Path) -> list[dict]:
    """osmium's geojsonseq lines start with an RS (0x1e) record separator."""
    features = []
    for line in path.read_text().splitlines():
        line = line.lstrip("\x1e").strip()
        if line:
            features.append(json.loads(line))
    return features


def validate_geojson(obj: object) -> list[str]:
    if not isinstance(obj, dict) or obj.get("type") != "FeatureCollection":
        return ["not a FeatureCollection"]
    problems = []
    features = obj.get("features")
    if not isinstance(features, list):
        return ["features is not a list"]
    for i, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            problems.append(f"feature {i} is not a Feature")
            continue
        geom = feature.get("geometry")
        if not isinstance(geom, dict) or "type" not in geom or "coordinates" not in geom:
            problems.append(f"feature {i} has no geometry")
        if not isinstance(feature.get("properties"), dict):
            problems.append(f"feature {i} has no properties object")
    return problems
