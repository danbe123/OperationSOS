import json

import httpx
import pytest
import respx

from sos.mapbuild import packs
from sos.mapbuild.common import BuildError
from tests.mapbuild_helpers import FakeRunner, make_ctx

UK_IDS = ["UK_England_East Midlands", "UK_England_East of England_Essex", "UK_England_East of England_Norfolk", "UK_England_Greater London",
          "UK_England_North East England", "UK_England_North West England_Manchester", "UK_England_North West England_Lancaster",
          "UK_England_South East_Brighton", "UK_England_South East_Oxford", "UK_England_South West England_Bristol",
          "UK_England_South West England_Cornwall", "UK_England_West Midlands", "UK_England_Yorkshire and the Humber",
          "UK_Northern Ireland", "UK_Scotland_North", "UK_Scotland_South", "UK_Wales"]
IE_IDS = ["Ireland_Connacht", "Ireland_Leinster", "Ireland_Munster", "Ireland_Northern Counties"]
COUNTRIES_URL = "https://raw.githubusercontent.com/organicmaps/organicmaps/2026.08.27-18-android/data/countries.json"


def _countries(size=10, drop=None):
    def leaf(i):
        return {"id": i, "s": size, "h": "hash"}
    uk = [leaf(i) for i in UK_IDS if i != drop]
    return {"v": 260826, "id": "Countries", "g": [
        {"id": "United Kingdom", "g": [{"id": "England", "g": uk[:13]}, *uk[13:]]},
        {"id": "Ireland", "g": [leaf(i) for i in IE_IDS]},
        leaf("Isle of Man"), leaf("Jersey"), leaf("Guernsey"),
        {"id": "France", "g": [leaf("France_Paris")]}, leaf("World"),
    ]}


def test_pack_ids_finds_exactly_the_24_uk_and_ireland_ids():
    ids = packs.pack_ids(_countries())
    assert len(ids) == 24 and ids == sorted(UK_IDS + IE_IDS + ["Isle of Man", "Jersey", "Guernsey"])
    assert "World" not in ids and "France_Paris" not in ids
    with pytest.raises(BuildError, match="23"):
        packs.pack_ids(_countries(drop="UK_Wales"))
    assert packs.pack_sizes(_countries(size=7))["Jersey"] == 7
    assert packs.data_version(_countries()) == "260826"


def test_pack_titles_read_naturally():
    assert packs.pack_title("UK_England_South East_Brighton") == "England – South East – Brighton"
    assert packs.pack_title("UK_Northern Ireland") == "Northern Ireland"
    assert packs.pack_title("Ireland_Munster") == "Ireland – Munster"
    assert packs.pack_title("Isle of Man") == "Isle of Man"


def test_index_html_carries_the_spec_instructions_and_no_external_urls():
    pack = {"id": "Jersey", "title": "Jersey", "file": "Jersey.mwm", "url": "/maps/packs/Jersey.mwm", "size_bytes": 2590086, "expected_size_bytes": 2590086}
    apk = {"file": "OrganicMaps-26082718-web-release.apk", "url": "/maps/packs/OrganicMaps-26082718-web-release.apk", "size_bytes": 64193127, "sha256": "ab", "tag": "2026.08.27-18-android"}
    page = packs.render_index_html("260826", [pack], apk)
    for text in ("Install the app first", "Android/data/app.organicmaps/files/260826/", "Android 11 and later block the browser",
                 "direct laptop link", "iPhone and iPad are not supported", 'href="/maps/packs/Jersey.mwm"',
                 'href="/maps/packs/OrganicMaps-26082718-web-release.apk"', "Data version 260826"):
        assert text in page, text
    assert "http://" not in page and "https://" not in page
    without = packs.render_index_html("260826", [pack], None)
    assert "not included in this build" in without and ".apk" not in without


def test_index_json_shape():
    doc = packs.index_json("260826", [{"id": "Jersey"}], None)
    assert doc == {"version": "260826", "apk": None, "packs": [{"id": "Jersey"}], "index_url": "/maps/packs/index.html"}


@respx.mock
def test_packs_step_fixture_downloads_jersey_only_and_no_apk(tmp_path):
    respx.get(COUNTRIES_URL).mock(return_value=httpx.Response(200, json=_countries(size=3)))
    runner = FakeRunner(files={"Jersey.mwm": b"mwm"})
    ctx = make_ctx(tmp_path, fixture=True, runner=runner)
    packs.PacksStep().run(ctx)
    downloads = [c[-1] for c in runner.find("aria2c")]
    assert downloads == ["https://example.test/maps/260826/Jersey.mwm"]
    index = json.loads((ctx.out / "packs" / "index.json").read_text())
    assert index["version"] == "260826" and index["apk"] is None
    assert index["packs"] == [{"id": "Jersey", "title": "Jersey", "file": "Jersey.mwm", "url": "/maps/packs/Jersey.mwm", "size_bytes": 3, "expected_size_bytes": 3}]
    assert (ctx.out / "packs" / "Jersey.mwm").read_bytes() == b"mwm"
    assert "Android/data/app.organicmaps/files/260826/" in (ctx.out / "packs" / "index.html").read_text()
    assert json.loads((ctx.out / "packs.json").read_text())["ids"] == ["Jersey"]


@respx.mock
def test_packs_step_full_downloads_24_packs_and_the_apk_with_sha256(tmp_path):
    respx.get(COUNTRIES_URL).mock(return_value=httpx.Response(200, json=_countries(size=10)))
    runner = FakeRunner()
    ctx = make_ctx(tmp_path, fixture=False, runner=runner)
    packs.PacksStep().run(ctx)
    urls = [c[-1] for c in runner.find("aria2c")]
    assert len(urls) == 25
    assert "https://example.test/maps/260826/UK_England_South%20East_Brighton.mwm" in urls
    assert "https://example.test/maps/260826/Isle%20of%20Man.mwm" in urls
    apk_cmd = next(c for c in runner.find("aria2c") if c[-1].endswith(".apk"))
    assert "--checksum=sha-256=1f19229d95b731862349d504b150dad63eb405caa83e98c96bfe93b7acae3c7a" in apk_cmd
    index = json.loads((ctx.out / "packs" / "index.json").read_text())
    assert len(index["packs"]) == 24 and index["apk"]["file"] == "OrganicMaps-26082718-web-release.apk"
    assert index["packs"][0]["url"] == "/maps/packs/Guernsey.mwm"
    assert (ctx.out / "packs" / "OrganicMaps-26082718-web-release.apk").exists()


@respx.mock
def test_packs_step_rejects_size_mismatch(tmp_path):
    respx.get(COUNTRIES_URL).mock(return_value=httpx.Response(200, json=_countries(size=99)))
    ctx = make_ctx(tmp_path, fixture=True, runner=FakeRunner(files={"Jersey.mwm": b"short"}))
    with pytest.raises(BuildError, match="Jersey.*99"):
        packs.PacksStep().run(ctx)
    assert not (ctx.out / "packs").exists()
