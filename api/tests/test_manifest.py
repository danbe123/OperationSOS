import json
import shutil
from pathlib import Path

import pytest

from sos.manifest import Item, load_manifests, validate_manifests

FIXTURES = Path(__file__).parent / "fixtures"


def _tree(tmp_path: Path, items: list[dict], name="core.json") -> Path:
    d = tmp_path / "manifest"
    d.mkdir()
    shutil.copy(FIXTURES / "manifest" / "schema.json", d / "schema.json")
    (d / name).write_text(json.dumps({"items": items}), encoding="utf-8")
    return d


def _zim(id_: str, **over) -> dict:
    base = {
        "id": id_, "title": id_, "kind": "zim", "tier": "core", "category": "reference",
        "source": {"type": "kiwix", "name": id_}, "dest": f"zim/{id_}.zim", "size_bytes": 1,
    }
    base.update(over)
    return base


def test_fixture_manifest_is_valid():
    assert validate_manifests(FIXTURES / "manifest") == []


def test_repo_manifest_is_valid(repo_root):
    assert validate_manifests(repo_root / "manifest") == []


def test_dev_manifest_is_valid(repo_root):
    d = repo_root / "dev" / "manifest"
    errors = validate_manifests(d) if (d / "schema.json").exists() else _validate_with_repo_schema(repo_root, d)
    assert errors == []
    ids = {i.id for i in load_manifests(d)}
    assert "wikipedia_en_100_mini_2026-01" in ids
    assert "gemma-4-E2B-it-Q4_K_M" in ids


def _validate_with_repo_schema(repo_root, d):
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        shutil.copy(repo_root / "manifest" / "schema.json", t / "schema.json")
        for p in d.glob("*.json"):
            shutil.copy(p, t / p.name)
        return validate_manifests(t)


def test_schema_and_fixture_schema_identical(repo_root):
    a = (repo_root / "manifest" / "schema.json").read_text()
    b = (FIXTURES / "manifest" / "schema.json").read_text()
    assert a == b


def test_load_applies_defaults():
    items = load_manifests(FIXTURES / "manifest")
    wiki = next(i for i in items if i.id == "wikipedia_en_100_mini_2026-01")
    assert wiki.search_weight == 1.0 and wiki.suggest is True and wiki.overlay is None
    noindex = next(i for i in items if i.id == "sos-test-noindex")
    assert noindex.suggest is False and noindex.priority == 100 and noindex.scenarios == []
    health = next(i for i in items if i.id == "health")
    assert health.overlay is not None and health.overlay.kind == "geojson" and health.overlay.default_on is False


def test_zim_dest_invariant(tmp_path):
    d = _tree(tmp_path, [_zim("wiki", dest="zim/other.zim")])
    errors = validate_manifests(d)
    assert any("zim dest must be 'zim/wiki.zim'" in e for e in errors)


def test_duplicate_ids_and_dests(tmp_path):
    d = _tree(tmp_path, [_zim("a"), _zim("a"), _zim("b", dest="zim/a.zim")])
    errors = validate_manifests(d)
    assert any("duplicate id 'a'" in e for e in errors)
    assert any("duplicate dest 'zim/a.zim'" in e for e in errors)


def test_build_item_needs_artifact(tmp_path):
    item = _zim("prepare_uk", source={"type": "build", "tool": "zimit"})
    d = _tree(tmp_path, [item])
    errors = validate_manifests(d)
    assert any("artifact" in e for e in errors)


def test_schema_rejects_unknown_kind_and_bad_as_at(tmp_path):
    d = _tree(tmp_path, [_zim("x", kind="tarball"), _zim("y", as_at="Jan 2026")])
    errors = validate_manifests(d)
    assert any("kind" in e for e in errors)
    assert any("as_at" in e for e in errors)


def test_invalid_json_reported(tmp_path):
    d = tmp_path / "manifest"
    d.mkdir()
    shutil.copy(FIXTURES / "manifest" / "schema.json", d / "schema.json")
    (d / "core.json").write_text("{not json", encoding="utf-8")
    errors = validate_manifests(d)
    assert errors and "invalid JSON" in errors[0]


def test_item_model_rejects_extra_fields():
    with pytest.raises(Exception):
        Item.model_validate(_zim("z", bogus=1))
