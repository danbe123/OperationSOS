"""Step `base`: extract the pinned Protomaps build over the UK and Ireland bbox and verify it."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from .common import BBox, BuildError, Context, bbox_str, lonlat_to_tile, pmtiles_header, tile_exists

PROBES_FULL: dict[str, tuple[float, float]] = {"St Helier": (49.19, -2.11), "Lerwick": (60.15, -1.15)}
PROBES_FIXTURE: dict[str, tuple[float, float]] = {"OS HQ Southampton": (50.9379, -1.4708)}
PROBE_ZOOM = 12
BASE_MAXZOOM = 15


def build_url(ctx: Context) -> str:
    return f"{ctx.version('PROTOMAPS_BUILDS_BASE')}/{ctx.build}.pmtiles"


def extract_command(ctx: Context, url: str, out_path: Path) -> list[str]:
    return ["pmtiles", "extract", url, str(out_path), f"--bbox={bbox_str(ctx.bbox)}", "--download-threads=8"]


def check_base(header: dict, bbox: BBox, probes: dict[str, tuple[float, float]],
               has_tile: Callable[[int, int, int], bool], *, maxzoom: int = BASE_MAXZOOM) -> list[str]:
    problems: list[str] = []
    bounds = header.get("bounds") or []
    eps = 1e-6
    covers = (len(bounds) == 4 and bounds[0] <= bbox[0] + eps and bounds[1] <= bbox[1] + eps
              and bounds[2] >= bbox[2] - eps and bounds[3] >= bbox[3] - eps)
    if not covers:
        problems.append(f"bounds {bounds} do not cover {list(bbox)}")
    if header.get("maxzoom") != maxzoom:
        problems.append(f"maxzoom {header.get('maxzoom')} is not {maxzoom}")
    if header.get("tile_type") != "mvt":
        problems.append(f"tile type {header.get('tile_type')!r} is not mvt")
    for name, (lat, lon) in probes.items():
        x, y = lonlat_to_tile(lat, lon, PROBE_ZOOM)
        if not has_tile(PROBE_ZOOM, x, y):
            problems.append(f"no z{PROBE_ZOOM} tile covering {name} ({lat}, {lon}) at {x}/{y}")
    return problems


class BaseStep:
    id = "base"

    def outputs(self, ctx: Context) -> list[str]:
        return [ctx.base_name]

    def run(self, ctx: Context) -> None:
        staged = ctx.stage(ctx.base_name)
        url = build_url(ctx)
        ctx.run(extract_command(ctx, url, staged))
        header = pmtiles_header(ctx, staged)
        probes = PROBES_FIXTURE if ctx.fixture else PROBES_FULL
        problems = check_base(header, ctx.bbox, probes, lambda z, x, y: tile_exists(ctx, staged, z, x, y))
        if problems:
            raise BuildError("base map failed verification:\n  " + "\n  ".join(problems))
        ctx.commit(ctx.base_name)
        ctx.write_sidecar(ctx.base_name, {"step": self.id, "source": url, "build": ctx.build,
                                          "bbox": list(ctx.bbox), "header": header})
