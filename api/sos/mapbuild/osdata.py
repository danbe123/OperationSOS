"""OS Data Hub downloads API client and step `os` (OS Open Zoomstack MBTiles -> os-zoomstack.pmtiles)."""
from __future__ import annotations

import zipfile
from pathlib import Path

import httpx

from .common import BuildError, Context, bbox_str, pmtiles_header, pmtiles_metadata, vector_layer_ids

REQUIRED_OS_LAYERS = ("roads", "names", "sea")


def os_downloads(ctx: Context, product: str) -> list[dict]:
    url = f"{ctx.version('OS_DOWNLOADS_API')}/products/{product}/downloads"
    response = httpx.get(url, timeout=60, follow_redirects=True)
    if response.status_code != 200:
        raise BuildError(f"OS downloads API {url} returned {response.status_code}")
    return response.json()


def pick_download(entries: list[dict], file_name: str) -> dict:
    for entry in entries:
        if entry.get("fileName") == file_name:
            return entry
    names = ", ".join(str(e.get("fileName")) for e in entries)
    raise BuildError(f"OS downloads API has no {file_name}; available: {names}")


def os_fetch(ctx: Context, product: str, file_name: str) -> Path:
    entry = pick_download(os_downloads(ctx, product), file_name)
    return ctx.download(entry["url"], file_name, md5=entry.get("md5"))


def unzip_single(zip_path: Path, pattern: str, dest_dir: Path) -> Path:
    """Extract zip_path into dest_dir once (marker file) and return the single member matching the glob."""
    marker = dest_dir / ".extracted"
    if not marker.exists():
        dest_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest_dir)
        marker.touch()
    matches = sorted(p for p in dest_dir.rglob(pattern) if p.is_file())
    if len(matches) != 1:
        raise BuildError(f"expected exactly one {pattern} inside {zip_path.name}, found {len(matches)}")
    return matches[0]


class OsZoomstackStep:
    id = "os"

    def outputs(self, ctx: Context) -> list[str]:
        return ["os-zoomstack.pmtiles"]

    def run(self, ctx: Context) -> None:
        mbtiles = os_fetch(ctx, "OpenZoomstack", "OS_Open_Zoomstack.mbtiles")
        staged = ctx.stage("os-zoomstack.pmtiles")
        if ctx.fixture:
            full = ctx.src / "os-zoomstack-full.pmtiles"
            if not full.exists():
                ctx.run(["pmtiles", "convert", str(mbtiles), str(full)])
            ctx.run(["pmtiles", "extract", str(full), str(staged), f"--bbox={bbox_str(ctx.bbox)}"])
        else:
            ctx.run(["pmtiles", "convert", str(mbtiles), str(staged)])
        header = pmtiles_header(ctx, staged)
        layers = sorted(vector_layer_ids(pmtiles_metadata(ctx, staged)))
        missing = [name for name in REQUIRED_OS_LAYERS if name not in layers]
        if missing:
            raise BuildError(f"os-zoomstack.pmtiles lacks expected source-layers {missing}; found {layers}")
        ctx.commit("os-zoomstack.pmtiles")
        ctx.write_sidecar("os-zoomstack.pmtiles", {"step": self.id, "source": "OS Open Zoomstack (OS Downloads API, MBTiles)",
                                                   "input": mbtiles.name, "header": header, "layers": layers})
