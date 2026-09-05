"""Content decisions for the repo manifests (sub-plan 03).

Plan 01's test_manifest.py checks shape against manifest/schema.json.
These tests pin what the manifests say: ids, weights, suggest flags,
source conventions, overlay objects and the nuclear-sites GeoJSON.
"""
import json
import re
from pathlib import Path

import pytest

from sos.manifest import validate_manifests

REPO = Path(__file__).resolve().parents[2]
MANIFEST_DIR = REPO / "manifest"
ZIMIT_DIR = REPO / "tools" / "zimit"

AS_AT = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")
SCENARIOS = [
    "nuclear-war", "nuclear-accident", "pandemic", "grid-collapse", "solar-storm", "emp",
    "cyber-attack", "invasion", "civil-unrest", "economic-collapse", "supply-chain",
    "storms-flooding", "severe-winter", "heat-drought", "volcanic", "chemical", "famine",
    "impact-winter", "terrorism", "long-rebuild",
]

CORE_REQUIRED = {
    # uk-official
    "prepare_uk", "nrr-2025", "resilience-action-plan-2025", "wales-resilience-framework-2025",
    "awhp-2026", "govuk_resilience", "legislation_uk", "ukhsa-radiation-decontamination",
    "nrpb-stable-iodine", "protect-and-survive-1980", "rsgb-band-plan-2026",
    "ofcom-pmr446-ir2009", "ofcom-amateur-licence-2024",
    "hse-indg231", "hse-indg317", "hse-indg258", "hse-indg370",
    "ad-a", "ad-b1", "ad-c", "ad-d", "ad-e", "ad-f1", "ad-g", "ad-h", "ad-j", "ad-k", "ad-l1",
    "ad-m1", "ad-o", "ad-p", "ad-q", "ad-r1", "ad-s", "ad-t", "ad-reg7",
    # medical
    "nhs_uk", "nhs_medicines", "wikipedia_en_medicine_maxi", "wikem_en_all_maxi",
    "mdwiki_en_all_maxi", "medlineplus.gov_en_all", "zimgit-medicine_en",
    "where-there-is-no-doctor", "where-there-is-no-dentist",
    "scmg-ch01", "scmg-ch02", "scmg-ch03", "scmg-ch04", "scmg-ch05", "scmg-ch06", "scmg-ch07",
    "scmg-ch09", "scmg-ch10", "scmg-ch11", "scmg-ch12", "scmg-annex",
    "who-eml-2025", "irp.fas.org_en_military-medicine", "survival-austere-medicine-2017",
    "emergency-war-surgery-2018", "fm-4-25-11-first-aid", "medicalsciences.stackexchange.com_en_all",
    # survival
    "zimgit-water_en", "zimgit-food-preparation_en", "zimgit-knots_en", "zimgit-post-disaster_en",
    "www.ready.gov_en", "appropedia_en_all", "cd3wdproject.org_en_all", "nwss",
    "fema-nuclear-detonation-2022", "fm-21-76-survival", "fm-3-05-70-survival",
    "urban-prepper_en_all", "trueprepper.com_en_all", "lrnselfreliance_en_all",
    "energypedia_en_all_maxi", "solar.lowtechmagazine.com_mul_all", "based.cooking_en_all",
    "foss.cooking_en_all", "usda-2015_en",
    # reference
    "wikipedia_en_all_maxi", "wikipedia_en-simple_all_maxi", "wiktionary_en_all_nopic",
    "wikibooks_en_all_maxi", "wikivoyage_en_all_maxi", "openstreetmap-wiki_en_all_maxi",
    # practical
    "ifixit_en_all",
    "diy.stackexchange.com_en_all", "electronics.stackexchange.com_en_all",
    "gardening.stackexchange.com_en_all", "outdoors.stackexchange.com_en_all",
    "mechanics.stackexchange.com_en_all", "woodworking.stackexchange.com_en_all",
    "cooking.stackexchange.com_en_all", "homebrew.stackexchange.com_en_all",
    "sustainability.stackexchange.com_en_all", "ham.stackexchange.com_en_all",
    "bicycles.stackexchange.com_en_all", "biology.stackexchange.com_en_all",
    "chemistry.stackexchange.com_en_all", "physics.stackexchange.com_en_all",
    "engineering.stackexchange.com_en_all", "earthscience.stackexchange.com_en_all",
    "pets.stackexchange.com_en_all",
    "devdocs_en_python", "devdocs_en_bash", "devdocs_en_sqlite", "devdocs_en_html",
    "devdocs_en_css", "devdocs_en_javascript",
    # ai
    "gemma-4-E2B-it-Q4_K_M", "Qwen3.5-2B-Q4_K_M", "gemma-3-1b-it-Q4_K_M",
}


def items(name: str) -> list[dict]:
    return json.loads((MANIFEST_DIR / name).read_text(encoding="utf-8"))["items"]


def by_id(name: str) -> dict[str, dict]:
    rows = items(name)
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), f"duplicate ids in {name}"
    return {r["id"]: r for r in rows}


def test_repo_manifests_validate():
    assert validate_manifests(MANIFEST_DIR) == []


def test_core_required_ids_present():
    core = by_id("core.json")
    assert sorted(CORE_REQUIRED - core.keys()) == []


def test_core_ids_are_all_expected():
    core = by_id("core.json")
    assert sorted(core.keys() - CORE_REQUIRED) == []


def test_core_tier_and_categories():
    for it in items("core.json"):
        assert it["tier"] == "core", it["id"]
        assert it["category"] in {"uk-official", "medical", "survival", "reference", "practical", "ai"}, it["id"]
        assert set(it["scenarios"]) <= set(SCENARIOS), it["id"]


def test_search_weights():
    for it in items("core.json"):
        w = it.get("search_weight", 1.0)
        if it["category"] == "uk-official" or it["id"] in {"nhs_uk", "nhs_medicines"}:
            assert w == 1.4, it["id"]
        elif it["category"] == "medical":
            assert w == 1.2, it["id"]
        else:
            assert w == 1.0, it["id"]


def test_suggest_flags():
    got = {it["id"] for it in items("core.json") if it.get("suggest")}
    assert got == {"wikipedia_en_all_maxi", "wikipedia_en_medicine_maxi", "nhs_uk", "nhs_medicines", "ifixit_en_all"}


def test_zim_dest_invariant_and_kiwix_names():
    for it in items("core.json"):
        if it["kind"] == "zim":
            assert it["dest"] == f"zim/{it['id']}.zim", it["id"]
        if it["source"]["type"] == "kiwix":
            name = it["source"]["name"]
            assert not name.endswith(("_maxi", "_nopic", "_mini")), it["id"]
            if it["id"] == "nhs_medicines":  # the one spec-fixed id that is not the OPDS name
                assert name == "nhs.uk_en_medicines"
                continue
            head, _, tail = it["id"].rpartition("_")
            assert it["id"] == name or (head == name and tail in {"maxi", "nopic", "mini"}), it["id"]


def test_url_items_are_https_with_sha256():
    for it in items("core.json"):
        if it["source"]["type"] == "url":
            assert it["source"]["url"].startswith("https://"), it["id"]
            assert re.fullmatch(r"[0-9a-f]{64}", it["source"].get("sha256", "")), it["id"]
            assert it["size_bytes"] > 0, it["id"]


def test_build_items_have_artifact_and_seed_lists():
    for it in items("core.json"):
        src = it["source"]
        if src["type"] == "build":
            assert src["tool"] in {"zimit", "build-nhs", "manual"}, it["id"]
            assert src["artifact"].endswith((".zim", ".pdf", ".gguf")), it["id"]
            if src["tool"] == "zimit":
                seeds = (ZIMIT_DIR / f"{it['id']}.txt").read_text(encoding="utf-8").split()
                assert seeds and all(s.startswith("https://") for s in seeds), it["id"]


def test_as_at_and_priority():
    for it in items("core.json"):
        assert AS_AT.match(it["as_at"]), it["id"]
        assert isinstance(it["priority"], int) and it["priority"] > 0, it["id"]
    core = by_id("core.json")
    assert core["prepare_uk"]["priority"] == 1
    assert core["nrr-2025"]["priority"] == 2
    assert core["nhs_uk"]["priority"] < core["nhs_medicines"]["priority"] < core["wikipedia_en_all_maxi"]["priority"]


def test_reader_home_only_where_verified():
    core = by_id("core.json")
    assert core["nhs_medicines"]["reader_home"] == "www.nhs.uk/medicines/"
    assert core["nhs_uk"]["reader_home"] == "www.nhs.uk/conditions/"
    assert core["zimgit-water_en"]["reader_home"] == "home"
    assert core["ifixit_en_all"]["reader_home"] == "home/home"
    assert core["homebrew.stackexchange.com_en_all"]["reader_home"] == "questions"
    assert "reader_home" not in core["wikipedia_en_all_maxi"]


def test_core_size_near_target():
    total = sum(it["size_bytes"] for it in items("core.json"))
    assert 150e9 < total < 230e9, total


OVERLAY_IDS = [
    "footpaths", "access-land", "flood-zones", "health", "fuel", "water", "rail",
    "nuclear-sites", "chemical-sites", "airports-military",
]
REGIONS = ["england", "wales", "scotland", "ni", "roi", "iom", "ci"]
EXTENDED_REQUIRED = {
    "gutenberg_en_all", "stackoverflow.com_en_all", "khanacademy_en_all", "survivorlibrary.com_en_all",
    "wikipedia_cy_all_maxi", "libretexts.org_en_med", "libretexts.org_en_bio", "openstax-biology-2e",
    "openstax-anatomy-physiology-2e", "s2underground_en_all", "canadian-prepper_en_winterprepping",
    "media-films", "media-music", "media-audiobooks", "owner-books",
}


def test_extended_tier_and_required_ids():
    ext = by_id("extended.json")
    assert sorted(EXTENDED_REQUIRED - ext.keys()) == []
    for it in ext.values():
        assert it["tier"] == "extended", it["id"]
        assert it["category"] in {"practical", "education", "books", "media", "reference"}, it["id"]
        assert AS_AT.match(it["as_at"]), it["id"]
        if it["kind"] == "zim":
            assert it["dest"] == f"zim/{it['id']}.zim", it["id"]
        if it["kind"] == "dir":
            assert it["source"] == {"type": "build", "tool": "manual", "artifact": it["dest"]}, it["id"]
        if it["source"]["type"] == "url":
            assert it["source"]["url"].startswith("https://") and it["size_bytes"] > 0, it["id"]


def test_extended_holds_every_stack_exchange_site_not_in_core():
    core = by_id("core.json")
    ext = by_id("extended.json")
    se_ext = [i for i in ext if i.endswith(".stackexchange.com_en_all")]
    assert len(se_ext) == 140
    assert not (set(se_ext) & set(core))
    for i in se_ext:
        assert ext[i]["reader_home"] == "questions"


def test_overlay_ids_and_objects():
    rows = items("overlays.json")
    assert [r["id"] for r in rows] == OVERLAY_IDS
    for r in rows:
        assert r["tier"] == "core" and r["category"] == "maps", r["id"]
        assert r["kind"] in {"pmtiles", "geojson"}, r["id"]
        assert r["dest"] == f"maps/overlays/{r['id']}.{r['kind']}", r["id"]
        assert r["source"] == {"type": "build", "tool": "build-maps", "artifact": f"overlays/{r['id']}.{r['kind']}"}, r["id"]
        ov = r["overlay"]
        assert ov["id"] == r["id"] and ov["kind"] == r["kind"], r["id"]
        assert isinstance(ov["default_on"], bool), r["id"]
        assert ov["coverage"] and set(ov["coverage"]) <= set(REGIONS), r["id"]
        assert re.fullmatch(r"#[0-9a-f]{6}", ov["color"]), r["id"]
        assert ov["icon"] is None or isinstance(ov["icon"], str), r["id"]
        assert "layer_id" not in ov, r["id"]
    ov = {r["id"]: r["overlay"] for r in rows}
    assert [i for i in OVERLAY_IDS if ov[i]["default_on"]] == ["footpaths"]
    assert ov["footpaths"]["coverage"] == REGIONS
    assert ov["access-land"]["coverage"] == ["england", "wales"]
    assert ov["flood-zones"]["coverage"] == ["england", "wales", "scotland", "ni"]
    for i in ("health", "fuel", "water", "rail", "nuclear-sites", "chemical-sites", "airports-military"):
        assert ov[i]["coverage"] == REGIONS, i


def test_nuclear_sites_geojson():
    path = REPO / "tools" / "map-styles" / "data" / "nuclear-sites.geojson"
    g = json.loads(path.read_text(encoding="utf-8"))
    assert g["type"] == "FeatureCollection"
    feats = g["features"]
    assert len(feats) >= 20
    names: set[str] = set()
    for f in feats:
        assert f["type"] == "Feature"
        assert f["geometry"]["type"] == "Point"
        lon, lat = f["geometry"]["coordinates"]
        pr = f["properties"]
        assert -8.7 <= lon <= 2.0 and 49.8 <= lat <= 60.9, pr["name"]
        assert pr["type"] in {"power-station", "reprocessing", "fuel", "weapons", "naval", "research"}, pr["name"]
        assert pr["status"] in {"operating", "construction", "defuelling", "decommissioning"}, pr["name"]
        assert isinstance(pr["note"], str) and pr["note"], pr["name"]
        assert pr["name"] not in names, pr["name"]
        names.add(pr["name"])
    must = {
        "Sellafield", "AWE Aldermaston", "AWE Burghfield", "HMNB Clyde (Faslane)", "RNAD Coulport",
        "HMNB Devonport", "Barrow-in-Furness shipyard", "Rosyth dockyard", "Dounreay", "Harwell",
        "Winfrith", "Springfields", "Capenhurst", "Hinkley Point C", "Sizewell B", "Heysham 1",
        "Heysham 2", "Hartlepool", "Torness",
    }
    assert sorted(must - names) == []
