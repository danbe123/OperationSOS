"""Step `packs`: Organic Maps .mwm files for the 24 UK and Ireland ids, the Android APK and the packs index."""
from __future__ import annotations

import html
import json
import os
import shutil
from pathlib import Path
from urllib.parse import quote

import httpx

from .common import BuildError, Context, log

EXPECTED_PACKS = 24
SINGLE_IDS = ("Isle of Man", "Jersey", "Guernsey")
FIXTURE_IDS = ("Jersey",)
INDEX_URL = "/maps/packs/index.html"


def countries_url(ctx: Context) -> str:
    return f"https://raw.githubusercontent.com/organicmaps/organicmaps/{ctx.version('ORGANICMAPS_TAG')}/data/countries.json"


def fetch_countries(ctx: Context) -> dict:
    url = countries_url(ctx)
    response = httpx.get(url, timeout=60, follow_redirects=True)
    if response.status_code != 200:
        raise BuildError(f"{url} returned {response.status_code}")
    return response.json()


def leaves(node: dict) -> list[dict]:
    if "g" in node:
        return [leaf for child in node["g"] for leaf in leaves(child)]
    return [node]


def pack_ids(countries: dict) -> list[str]:
    ids = sorted(leaf["id"] for leaf in leaves(countries)
                 if leaf["id"].startswith("UK_") or leaf["id"].startswith("Ireland_") or leaf["id"] in SINGLE_IDS)
    if len(ids) != EXPECTED_PACKS:
        raise BuildError(f"expected {EXPECTED_PACKS} Organic Maps pack ids, found {len(ids)}: {ids}")
    return ids


def pack_sizes(countries: dict) -> dict[str, int]:
    return {leaf["id"]: int(leaf.get("s", 0)) for leaf in leaves(countries)}


def data_version(countries: dict) -> str:
    return str(countries["v"])


def pack_title(pack_id: str) -> str:
    if pack_id.startswith("UK_"):
        return pack_id[len("UK_"):].replace("_", " – ")
    if pack_id.startswith("Ireland_"):
        return "Ireland – " + pack_id[len("Ireland_"):].replace("_", " – ")
    return pack_id


def index_json(version: str, packs: list[dict], apk: dict | None) -> dict:
    return {"version": version, "apk": apk, "packs": packs, "index_url": INDEX_URL}


def render_index_html(version: str, packs: list[dict], apk: dict | None) -> str:
    rows = "\n".join(
        f'      <tr><td><a href="{html.escape(p["url"])}">{html.escape(p["file"])}</a></td>'
        f'<td>{html.escape(p["title"])}</td><td>{p["size_bytes"] / 1e6:.0f} MB</td></tr>' for p in packs)
    if apk:
        apk_line = (f'Download <a href="{html.escape(apk["url"])}">{html.escape(apk["file"])}</a> '
                    f'({apk["size_bytes"] / 1e6:.0f} MB) and open it on the phone to install it. '
                    "Allow installs from your browser if Android asks.")
    else:
        apk_line = "The Android app is not included in this build."
    return f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SOS phone map packs</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; }}
  code {{ background: #eee; padding: 0 .25rem; }}
  table {{ border-collapse: collapse; width: 100%; }}
  td, th {{ text-align: left; padding: .4rem .5rem; border-bottom: 1px solid #ccc; }}
  .warn {{ border-left: 4px solid #c8102e; padding-left: .75rem; }}
</style>
</head>
<body>
<h1>Phone map packs (Organic Maps)</h1>
<p>These files give an Android phone its own offline map of the UK, the Republic of Ireland, the Isle of Man and the Channel Islands, usable when the phone cannot reach this box.</p>
<ol>
  <li><strong>Install the app first.</strong> {apk_line}</li>
  <li><strong>Copy the map files from a PC over USB.</strong> Plug the phone into a computer, choose <em>File transfer</em> on the phone, then copy the <code>.mwm</code> files below into <code>Android/data/app.organicmaps/files/{version}/</code> on the phone (create the folder if it is missing). Android 11 and later block the browser from saving into that folder, so downloading a <code>.mwm</code> directly on the phone does not work.</li>
  <li><strong>Getting the files onto the PC:</strong> the intended route is the Ethernet <em>direct laptop link</em> from the System screen: plug a laptop into the box with an Ethernet cable and download the files from this page. <code>adb push</code> works too.</li>
  <li>Open Organic Maps. The maps appear under <em>Downloaded maps</em>.</li>
</ol>
<p class="warn"><strong>iPhone and iPad are not supported.</strong> iOS has no way to load map files from outside the App Store.</p>
<table>
  <thead><tr><th>File</th><th>Area</th><th>Size</th></tr></thead>
  <tbody>
{rows}
  </tbody>
</table>
<p>Map data &copy; OpenStreetMap contributors, &copy; Organic Maps. Data version {version}.</p>
</body>
</html>
"""


def _link_or_copy(src: Path, dst: Path) -> None:
    dst.unlink(missing_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


class PacksStep:
    id = "packs"

    def outputs(self, ctx: Context) -> list[str]:
        return ["packs/index.html", "packs/index.json"]

    def run(self, ctx: Context) -> None:
        countries = fetch_countries(ctx)
        version = data_version(countries)
        ids = pack_ids(countries)
        sizes = pack_sizes(countries)
        wanted = [i for i in ids if i in FIXTURE_IDS] if ctx.fixture else ids
        cdn = ctx.version("ORGANICMAPS_CDN")
        staged = ctx.stage("packs")
        staged.mkdir()
        packs: list[dict] = []
        for pack_id in wanted:
            source = ctx.download(f"{cdn}/{version}/{quote(pack_id)}.mwm", f"packs/{version}/{pack_id}.mwm")
            size = source.stat().st_size
            if size != sizes.get(pack_id, size):
                raise BuildError(f"{pack_id}.mwm is {size} bytes; countries.json says {sizes[pack_id]}")
            target = staged / f"{pack_id}.mwm"
            _link_or_copy(source, target)
            packs.append({"id": pack_id, "title": pack_title(pack_id), "file": f"{pack_id}.mwm",
                          "url": f"/maps/packs/{quote(pack_id)}.mwm", "size_bytes": size,
                          "expected_size_bytes": sizes.get(pack_id, 0)})
        apk: dict | None = None
        if not ctx.fixture:
            apk_url = ctx.version("ORGANICMAPS_APK_URL")
            sha = ctx.version("ORGANICMAPS_APK_SHA256")
            name = apk_url.rsplit("/", 1)[-1]
            source = ctx.download(apk_url, name, sha256=sha)
            _link_or_copy(source, staged / name)
            apk = {"file": name, "url": f"/maps/packs/{name}", "size_bytes": (staged / name).stat().st_size,
                   "sha256": sha, "tag": ctx.version("ORGANICMAPS_TAG")}
        (staged / "index.html").write_text(render_index_html(version, packs, apk))
        (staged / "index.json").write_text(json.dumps(index_json(version, packs, apk), indent=2) + "\n")
        ctx.commit("packs")
        log.info("[packs] data version %s, %d packs%s", version, len(packs), ", APK" if apk else "")
        ctx.write_sidecar("packs", {"step": self.id, "data_version": version, "ids": wanted,
                                    "apk": apk["file"] if apk else None})
