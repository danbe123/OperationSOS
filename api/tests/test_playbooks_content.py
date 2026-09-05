"""Content decisions for playbooks/ beyond what sos validate-playbooks checks (sub-plan 03)."""
import json
import re
from pathlib import Path

import frontmatter
import pytest

from sos.content import parse_document, validate_tree
from sos.manifest import load_manifests

REPO = Path(__file__).resolve().parents[2]
PB = REPO / "playbooks"
MANIFEST_DIR = REPO / "manifest"

MODULES = [
    "water", "food", "shelter-heat", "medical", "sanitation", "power", "comms", "security-law",
    "navigation", "community", "mental-health", "radiation", "evacuation", "vehicles-fuel",
    "tools-repair", "growing-food", "livestock",
]
MODULE_HEADINGS = ["## Key facts", "## What to do", "## UK specifics", "## Go deeper"]
CITE = re.compile(r"\]\((?:kiwix|doc):[^)]+\)")
ANY_LINK = re.compile(r"\]\(((?:kiwix|doc|module|card|page|playbook|map):[^)]+)\)")
AS_AT = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")


def overlay_ids() -> list[str]:
    rows = json.loads((MANIFEST_DIR / "overlays.json").read_text(encoding="utf-8"))["items"]
    return [r["overlay"]["id"] for r in rows]


def load(kind: str, slug: str) -> frontmatter.Post:
    return frontmatter.loads((PB / kind / f"{slug}.md").read_text(encoding="utf-8"))


def h2(body: str) -> list[str]:
    return [line.rstrip() for line in body.splitlines() if line.startswith("## ")]


def sections(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    current = None
    for line in body.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            out[current] = ""
        elif current is not None:
            out[current] += line + "\n"
    return out


@pytest.mark.parametrize("slug", MODULES)
def test_module_front_matter(slug):
    post = load("modules", slug)
    assert set(post.keys()) == {"id", "title", "icon", "order", "summary", "sources"}
    assert post["id"] == slug
    assert post["order"] == MODULES.index(slug) + 1
    assert 20 <= len(post["summary"]) <= 160
    assert len(post["sources"]) >= 3
    for s in post["sources"]:
        assert "title" in s and ("doc" in s or "kiwix" in s), (slug, s)
        if "as_at" in s:
            assert AS_AT.match(str(s["as_at"])), (slug, s)


@pytest.mark.parametrize("slug", MODULES)
def test_module_headings_citations_and_no_task_lines(slug):
    post = load("modules", slug)
    assert h2(post.content) == MODULE_HEADINGS
    body = sections(post.content)
    for name in ("Key facts", "What to do", "UK specifics"):
        assert len(CITE.findall(body[name])) >= 1, (slug, name)
    assert len(ANY_LINK.findall(body["Go deeper"])) >= 4, slug
    assert "- [ ]" not in post.content, slug
    assert "NOMAD" not in post.content


@pytest.mark.parametrize("slug", MODULES)
def test_module_parses_with_sos_content(slug):
    doc = parse_document(PB / "modules" / f"{slug}.md")
    assert doc.id == slug
    assert doc.kind == "module"


CARDS = [
    "cpr-adult", "cpr-child", "severe-bleeding", "choking", "burns", "hypothermia", "heat-stroke",
    "broken-bones", "radiation-sickness", "chemical-exposure", "childbirth", "dehydration",
    "wound-cleaning", "shock", "drowning", "seizures", "anaphylaxis", "carbon-monoxide", "stroke",
    "heart-attack", "recovery-position", "low-blood-sugar", "asthma-attack",
]
CARD_HEADINGS = ["## When to use", "## Steps", "## Warnings", "## Stop or escalate", "## Source"]
STEP = re.compile(r"^\d+\. (.*)$")


@pytest.mark.parametrize("slug", CARDS)
def test_card_front_matter(slug):
    post = load("cards", slug)
    assert set(post.keys()) == {"id", "title", "icon", "order", "summary"}
    assert post["id"] == slug
    assert post["order"] == CARDS.index(slug) + 1
    assert len(post["title"]) <= 40
    assert parse_document(PB / "cards" / f"{slug}.md").kind == "card"


@pytest.mark.parametrize("slug", CARDS)
def test_card_structure_and_screen_rule(slug):
    post = load("cards", slug)
    assert h2(post.content) == CARD_HEADINGS
    body = sections(post.content)
    when = body["When to use"].strip()
    assert 0 < len(when) <= 110, (slug, len(when))
    steps = [STEP.match(l).group(1) for l in body["Steps"].splitlines() if STEP.match(l)]
    assert len(steps) >= 4, slug
    for s in steps[:3]:
        assert len(s) <= 70, (slug, s)
    warnings = [l for l in body["Warnings"].splitlines() if l.strip()]
    assert warnings and all(l.startswith("**Warning:**") for l in warnings), slug
    assert "999" in body["Stop or escalate"], slug
    assert len(CITE.findall(body["Source"])) >= 1, slug
    assert "NOMAD" not in post.content


PAGES = {
    "pmr446": "comms", "amateur-bands": "comms", "uk-numbers": "reference", "what-still-works": "comms",
    "household-plan": "plan", "water-disinfection": "reference", "mains-electricity": "reference",
    "solar-islanding": "reference", "knife-firearms-law": "reference", "foraging-law": "reference",
    "ticks-adders": "reference", "about-sos": "about",
    "fieldcraft-basics": "fieldcraft", "fieldcraft-shelter": "fieldcraft", "fieldcraft-fire": "fieldcraft", "fieldcraft-water": "fieldcraft", "fieldcraft-food": "fieldcraft", "fieldcraft-moving": "fieldcraft", "fieldcraft-weather": "fieldcraft", "fieldcraft-rescue": "fieldcraft", "fieldcraft-hygiene": "fieldcraft", "fieldcraft-rope-tools": "fieldcraft",
}


@pytest.mark.parametrize("slug", sorted(PAGES))
def test_page_front_matter_and_body(slug):
    post = load("pages", slug)
    assert set(post.keys()) == {"id", "title", "icon", "order", "summary", "category"}
    assert post["id"] == slug
    assert post["category"] == PAGES[slug]
    assert post["order"] == list(PAGES).index(slug) + 1
    assert len(h2(post.content)) >= 2, slug
    assert len(CITE.findall(post.content)) >= 2, slug
    assert "NOMAD" not in post.content
    doc = parse_document(PB / "pages" / f"{slug}.md")
    assert doc.kind == "page" and doc.category == PAGES[slug]


def test_uk_numbers_page_has_the_mandatory_numbers():
    body = load("pages", "uk-numbers").content
    for n in ("999", "111", "105", "0345 988 1188", "0800 111 999", "116 123", "0300 2000 100", "03457 643 643"):
        assert n in body, n


def test_pmr446_page_has_all_16_channels_and_38_tones():
    body = load("pages", "pmr446").content
    for ch in ("446.00625", "446.09375", "446.19375"):
        assert ch in body, ch
    assert body.count("| 446.") == 16
    for tone in ("67.0", "100.0", "250.3"):
        assert tone in body, tone


SCENARIOS = [
    "nuclear-war", "nuclear-accident", "pandemic", "grid-collapse", "solar-storm", "emp",
    "cyber-attack", "invasion", "civil-unrest", "economic-collapse", "supply-chain",
    "storms-flooding", "severe-winter", "heat-drought", "volcanic", "chemical", "famine",
    "impact-winter", "terrorism", "long-rebuild",
]
SCENARIO_ICONS = dict(zip(SCENARIOS, [
    "radiation", "atom", "virus", "bolt", "sun", "zap", "laptop", "flag", "fire", "coins",
    "truck", "waves", "snowflake", "thermometer", "mountain", "flask", "wheat", "cloud", "alert", "hammer",
]))
SCENARIO_HEADINGS = [
    "## Right now", "## First 72 hours", "## First month", "## Long term", "## UK specifics",
    "## Checklist", "## Go deeper",
]
TASK_LINE = re.compile(r"^- \[ \] \S.*\S \{#([a-z0-9]+(?:-[a-z0-9]+)*)\}$")
INCLUDE = re.compile(r"^\{\{module:([a-z0-9-]+)\}\}$", re.M)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WRITTEN = SCENARIOS


def checklist_ids(slug: str) -> list[str]:
    lines = sections(load("scenarios", slug).content)["Checklist"].splitlines()
    return [m.group(1) for m in (TASK_LINE.match(l) for l in lines) if m]


@pytest.mark.parametrize("slug", WRITTEN)
def test_scenario_front_matter(slug):
    post = load("scenarios", slug)
    assert set(post.keys()) == {"id", "title", "icon", "order", "summary", "modules", "overlays", "reviewed", "sources"}
    assert post["id"] == slug
    assert post["order"] == SCENARIOS.index(slug) + 1
    assert post["icon"] == SCENARIO_ICONS[slug]
    assert 30 <= len(post["summary"]) <= 160, slug
    assert post["reviewed"] is None or DATE.match(str(post["reviewed"])), slug
    assert len(post["modules"]) >= 4 and len(set(post["modules"])) == len(post["modules"]), slug
    assert set(post["modules"]) <= set(MODULES), slug
    assert post["overlays"] and set(post["overlays"]) <= set(overlay_ids()), slug
    assert len(post["sources"]) >= 4, slug
    for s in post["sources"]:
        assert "title" in s and ("doc" in s or "kiwix" in s), (slug, s)
        assert AS_AT.match(str(s["as_at"])), (slug, s)


@pytest.mark.parametrize("slug", WRITTEN)
def test_scenario_sections_citations_checklist_and_includes(slug):
    post = load("scenarios", slug)
    assert h2(post.content) == SCENARIO_HEADINGS, slug
    body = sections(post.content)
    for name in ("Right now", "First 72 hours", "First month", "Long term", "UK specifics"):
        assert len(CITE.findall(body[name])) >= 1, (slug, name)
    assert len(ANY_LINK.findall(body["Go deeper"])) >= 5, slug
    tasks = [l for l in body["Checklist"].splitlines() if l.strip()]
    assert 6 <= len(tasks) <= 20, slug
    ids = []
    for line in tasks:
        m = TASK_LINE.match(line)
        assert m, (slug, line)
        assert 3 <= len(m.group(1)) <= 40, (slug, line)
        ids.append(m.group(1))
    assert len(ids) == len(set(ids)), slug
    assert "- [ ]" not in post.content.replace(body["Checklist"], ""), slug
    includes = INCLUDE.findall(post.content)
    assert includes == list(dict.fromkeys(includes)), (slug, "a module is included twice")
    assert set(includes) == set(post["modules"]), (slug, set(includes) ^ set(post["modules"]))
    for name in ("Checklist", "Go deeper"):
        assert "{{module:" not in body[name], (slug, name)
    assert "NOMAD" not in post.content


@pytest.mark.parametrize("slug", WRITTEN)
def test_scenario_parses_and_validates(slug):
    doc = parse_document(PB / "scenarios" / f"{slug}.md")
    assert doc.kind == "scenario" and doc.id == slug
    assert [t for _, t, _ in doc.sections if t] == [h[3:] for h in SCENARIO_HEADINGS]
    assert [i for i, _ in doc.checklist] == checklist_ids(slug)
    errors = validate_tree(PB, load_manifests(MANIFEST_DIR), overlay_ids())
    mine = [e for e in errors if e.startswith(f"scenarios/{slug}.md")]
    pending = re.compile(r"playbook '(" + "|".join(SCENARIOS) + r")' does not exist")
    assert [e for e in mine if not pending.search(e)] == [], mine


def all_scenarios() -> dict[str, frontmatter.Post]:
    return {s: load("scenarios", s) for s in SCENARIOS}


PLAYBOOK_LINK = re.compile(r"\]\(playbook:([a-z0-9-]+)\)")


def test_every_scenario_present_and_tree_validates():
    assert sorted(p.stem for p in (PB / "scenarios").glob("*.md")) == sorted(SCENARIOS)
    assert validate_tree(PB, load_manifests(MANIFEST_DIR), overlay_ids(), require_all_scenarios=True) == []


def test_every_module_used_by_at_least_two_scenarios():
    use = {m: [s for s, p in all_scenarios().items() if m in p["modules"]] for m in MODULES}
    thin = {m: s for m, s in use.items() if len(s) < 2}
    assert thin == {}, thin


def test_every_overlay_used_by_a_scenario():
    used = {o for p in all_scenarios().values() for o in p["overlays"]}
    assert set(overlay_ids()) <= used, set(overlay_ids()) - used


def test_scenario_cross_links():
    inbound = {s: 0 for s in SCENARIOS}
    for slug, post in all_scenarios().items():
        targets = set(PLAYBOOK_LINK.findall(post.content))
        assert targets, (slug, "no playbook: links")
        assert targets <= set(SCENARIOS), (slug, targets - set(SCENARIOS))
        assert slug not in targets, (slug, "links to itself")
        for t in targets:
            inbound[t] += 1
    assert [s for s, n in inbound.items() if n == 0] == []


def test_every_card_and_page_is_linked():
    link_re = re.compile(r"\]\((card|page):([a-z0-9-]+)\)")
    linked = {kind: set() for kind in ("card", "page")}
    for kind in ("modules", "scenarios", "cards", "pages"):
        for path in (PB / kind).glob("*.md"):
            body = path.read_text(encoding="utf-8")
            for target_kind, slug in link_re.findall(body):
                linked[target_kind].add(slug)
    unlinked_cards = set(CARDS) - linked["card"]
    unlinked_pages = set(PAGES) - linked["page"]
    assert unlinked_cards == set(), unlinked_cards
    assert unlinked_pages == set(), unlinked_pages
