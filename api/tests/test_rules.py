"""The rules files: they load, they validate, and every citation in them points at something that exists."""
import json
from datetime import timedelta
from pathlib import Path

import pytest
import yaml

from sos import conditions, rules
from sos.content import ContentCache
from sos.manifest import load_manifests

REPO = Path(__file__).resolve().parents[2]
RULES_DIR = REPO / "playbooks" / "rules"
EXPECTED_FILES = ["bulletins.yaml", "consequences.yaml", "implications.yaml", "modes.yaml", "reading.yaml", "tasks.yaml"]


@pytest.fixture(scope="module")
def loaded() -> rules.Rules:
    return rules.load(RULES_DIR)


@pytest.fixture(scope="module")
def content() -> ContentCache:
    return ContentCache(REPO / "playbooks")


@pytest.fixture(scope="module")
def doc_ids() -> set[str]:
    return {i.id for i in load_manifests(REPO / "manifest")}


@pytest.fixture
def rules_dir(tmp_path):
    """A throwaway rules directory with the real schema and no rules."""
    (tmp_path / "schema.json").write_text((RULES_DIR / "schema.json").read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def write(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize("text,seconds", [("30m", 1800), ("4h", 14400), ("2d", 172800), ("0h", 0), ("1.5h", 5400)])
def test_parse_duration(text, seconds):
    assert rules.parse_duration(text) == timedelta(seconds=seconds)


@pytest.mark.parametrize("text", ["", "4", "h", "4w", "-1h", "four hours"])
def test_parse_duration_rejects_nonsense(text):
    with pytest.raises(rules.RulesError):
        rules.parse_duration(text)


def test_the_repository_rules_load(loaded):
    assert list(loaded.files) == EXPECTED_FILES
    counts = rules.counts(loaded)
    assert counts["implication"] >= 8 and counts["consequence"] >= 6 and counts["task"] >= 12
    assert counts["mode"] >= 4 and counts["reading"] >= 8 and counts["bulletins"] >= 3
    assert loaded.get("fill-bath").bucket == "now" and loaded.get("fill-bath").kind == "task"
    assert loaded.get("freezer").after_td == timedelta(hours=48)
    assert loaded.get("power-off-mobile-degraded").expect["condition"] == "mobile"


def test_every_rule_has_an_id_a_why_and_a_source(loaded):
    for rule in loaded.all:
        assert rule.id and rule.why.strip() and rule.source, rule


def test_implications_target_real_conditions(loaded):
    for rule in loaded.implications:
        assert rule.expect["condition"] in conditions.IDS, rule.id
        assert 0 < rule.confidence <= 1


def test_when_clauses_use_known_states(loaded):
    for rule in loaded.all:
        for clause in (rule.when, rule.until or {}):
            for key, value in clause.items():
                if key in conditions.IDS:
                    states = value if isinstance(value, list) else [value]
                    assert set(states) <= set(conditions.STATES), (rule.id, key, value)


@pytest.mark.parametrize("rule_id,link", [
    (rule.id, link) for rule in rules.load(RULES_DIR).all for link in rule.links()
])
def test_every_rule_link_resolves(rule_id, link, content, doc_ids):
    """Every source, link and reading target names a playbook, module, page, card, document or the map."""
    scheme, rest = rules.link_targets([link])[0]
    kinds = {"playbook": "scenario", "module": "module", "page": "page", "card": "card"}
    if scheme in kinds:
        assert content.document(kinds[scheme], rest) is not None, f"{rule_id}: {link}"
    elif scheme in ("doc", "kiwix"):
        assert rest.partition("/")[0] in doc_ids, f"{rule_id}: {link}"
    else:
        assert scheme == "map", f"{rule_id}: unknown link scheme in {link}"


def test_bulletins_are_real_times(loaded):
    for bulletin in loaded.bulletins:
        assert bulletin["station"] and bulletin["times"]
        for time_text in bulletin["times"]:
            hour, minute = (int(x) for x in time_text.split(":"))
            assert 0 <= hour < 24 and 0 <= minute < 60


def test_schema_violation_names_the_file_and_the_rule(rules_dir):
    write(rules_dir, "broken.yaml", 'rules:\n  - id: no-bucket\n    kind: task\n    when: {power: "off"}\n'
                                    "    title: Something\n    why: Because\n    source: module:water\n")
    with pytest.raises(rules.RulesError) as exc:
        rules.load(rules_dir)
    assert "broken.yaml" in str(exc.value) and "no-bucket" in str(exc.value) and "bucket" in str(exc.value)


def test_a_rule_without_a_why_is_refused(rules_dir):
    write(rules_dir, "nowhy.yaml", 'rules:\n  - id: silent\n    kind: mode\n    when: {power: "off"}\n'
                                   "    set: {dim: true}\n    source: module:power\n")
    with pytest.raises(rules.RulesError) as exc:
        rules.load(rules_dir)
    assert "nowhy.yaml: rule 'silent': every rule needs a 'why'" in str(exc.value)


def test_bad_link_scheme_is_refused(rules_dir):
    write(rules_dir, "badlink.yaml", "rules:\n  - id: off-site\n    kind: reading\n    when: {}\n"
                                     "    open: [module:water]\n    why: Because\n    source: https://example.org/x\n")
    with pytest.raises(rules.RulesError) as exc:
        rules.load(rules_dir)
    assert "badlink.yaml" in str(exc.value) and "off-site" in str(exc.value)


def test_duplicate_ids_across_files_are_refused(rules_dir):
    body = ("rules:\n  - id: twice\n    kind: mode\n    when: {}\n    set: {dim: true}\n"
            "    why: Because\n    source: module:power\n")
    write(rules_dir, "a.yaml", body)
    write(rules_dir, "b.yaml", body)
    with pytest.raises(rules.RulesError) as exc:
        rules.load(rules_dir)
    assert "duplicate id" in str(exc.value)


def test_unparseable_yaml_names_the_file(rules_dir):
    write(rules_dir, "mangled.yaml", "rules:\n  - id: [unclosed\n")
    with pytest.raises(rules.RulesError) as exc:
        rules.load(rules_dir)
    assert "mangled.yaml: cannot parse" in str(exc.value)


def test_missing_schema_is_an_error(tmp_path):
    with pytest.raises(rules.RulesError) as exc:
        rules.load(tmp_path)
    assert "missing schema.json" in str(exc.value)


def test_load_is_cached_by_mtime(rules_dir):
    write(rules_dir, "one.yaml", "rules:\n  - id: r1\n    kind: mode\n    when: {}\n    set: {dim: true}\n"
                                 "    why: Because\n    source: module:power\n")
    first = rules.load(rules_dir)
    assert rules.load(rules_dir) is first
    import os
    path = write(rules_dir, "one.yaml", "rules:\n  - id: r2\n    kind: mode\n    when: {}\n    set: {dim: false}\n"
                                        "    why: Because\n    source: module:power\n")
    os.utime(path, (path.stat().st_mtime + 5, path.stat().st_mtime + 5))
    second = rules.load(rules_dir)
    assert second is not first and second.get("r2") is not None and second.get("r1") is None


def test_schema_file_is_valid_json_schema():
    schema = json.loads((RULES_DIR / "schema.json").read_text(encoding="utf-8"))
    assert set(schema["$defs"]["rule"]["properties"]["kind"]["enum"]) == set(rules.KINDS)


def test_the_fixture_rules_use_the_committed_schema():
    """The API tests load their own small rule set; it must be validated by the same schema as the real one."""
    fixture = Path(__file__).parent / "fixtures" / "playbooks" / "rules" / "schema.json"
    assert fixture.read_text(encoding="utf-8") == (RULES_DIR / "schema.json").read_text(encoding="utf-8")


# --- no setup: the register fields are gone (no-setup spec section 2) ------------------------------------

@pytest.mark.parametrize("field,value", [("needs", "oxygen"), ("who", "neighbours"), ("skills", "nurse"),
                                         ("stock", "{category: water, days_lt: 3}")])
def test_a_rule_that_reads_a_register_is_refused(rules_dir, field, value):
    write(rules_dir, "old.yaml", 'rules:\n  - id: old\n    kind: task\n    when: {power: "off"}\n'
                                 f"    {field}: {value}\n"
                                 "    title: T\n    bucket: now\n    why: W\n    source: module:water\n")
    with pytest.raises(rules.RulesError) as exc:
        rules.load(rules_dir)
    assert "old.yaml" in str(exc.value) and field in str(exc.value)


def test_no_repository_rule_reads_a_register():
    """Read the files themselves, not the loaded rules: the loader drops what it does not know about,
    so a `who:` left in a YAML file would pass a test that only asked the dataclass."""
    for path in sorted(RULES_DIR.glob("*.yaml")):
        for rule in yaml.safe_load(path.read_text(encoding="utf-8")).get("rules") or []:
            gone = sorted({"needs", "who", "skills", "stock"} & set(rule))
            assert not gone, f"{path.name}: {rule.get('id')}: {', '.join(gone)}"


def test_no_rule_title_has_a_name_shaped_hole_in_it(loaded):
    """`{name}` and `{at_address}` used to be filled in from the register. Nothing fills them now."""
    for rule in loaded.all:
        assert "{" not in rule.title, rule.id
