"""Content decisions for playbooks/ beyond what sos validate-playbooks checks (sub-plan 03)."""
import json
import re
from pathlib import Path

import frontmatter
import pytest
import yaml

from sos import directives

from sos.content import parse_document, validate_tree
from sos.manifest import load_manifests
from tests.conftest import real_tree_errors

REPO = Path(__file__).resolve().parents[2]
PB = REPO / "playbooks"
MANIFEST_DIR = REPO / "manifest"

MODULES = [
    "water", "food", "shelter-heat", "medical", "sanitation", "power", "comms", "security-law",
    "navigation", "community", "mental-health", "radiation", "evacuation", "vehicles-fuel",
    "tools-repair", "growing-food", "livestock", "rebuild",
]
MODULE_HEADINGS = ["## Key facts", "## What to do", "## UK specifics", "## Go deeper"]
# the rebuild module is a timeline rather than a fact sheet, so it carries its own headings and a checklist
REBUILD_MODULE_HEADINGS = [
    "## The first month", "## The first year", "## Years one to three: food and health",
    "## Years three to ten: trades and power", "## The decade after", "## Checklist",
]
MODULE_HEADINGS_BY_SLUG = {"rebuild": REBUILD_MODULE_HEADINGS}
MODULE_CITED_SECTIONS = {
    "rebuild": ("The first year", "Years one to three: food and health",
                "Years three to ten: trades and power"),
}
CITE = re.compile(r"\]\((?:kiwix|doc):[^)]+\)")
ANY_LINK = re.compile(r"\]\(((?:kiwix|doc|module|card|page|playbook|map):[^)]+)\)")
AS_AT = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")

# `- [ ] text {#id}`, with the optional bucket token after the id: `{#id now}`
TASK_LINE = re.compile(r"^- \[ \] \S.*\S \{#([a-z0-9]+(?:-[a-z0-9]+)*)(?: (now|hour|today|week))?\}$")


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
    headings = MODULE_HEADINGS_BY_SLUG.get(slug, MODULE_HEADINGS)
    assert h2(post.content) == headings
    body = sections(post.content)
    for name in MODULE_CITED_SECTIONS.get(slug, ("Key facts", "What to do", "UK specifics")):
        assert len(CITE.findall(body[name])) >= 1, (slug, name)
    if slug in MODULE_HEADINGS_BY_SLUG:
        # a timeline module points at pages instead of a Go deeper list, and carries a bucketed checklist
        assert len(ANY_LINK.findall(post.content)) >= 10, slug
        tasks = [l for l in body["Checklist"].splitlines() if l.strip()]
        assert 10 <= len(tasks) <= 14, slug
        ids = []
        for line in tasks:
            m = TASK_LINE.match(line)
            assert m, (slug, line)
            ids.append(m.group(1))
        assert len(ids) == len(set(ids)), slug
        assert post.content.count("- [ ]") == len(tasks), (slug, "task lines outside the checklist")
    else:
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
    "head-injury", "spinal-injury", "poisoning", "electric-shock", "fever-child", "sepsis",
    "sprains-strains", "frostbite", "bites-stings", "dental-abscess", "wound-closure", "eye-injury",
    "pregnancy-emergencies", "nosebleed",
]
CARD_HEADINGS = ["## When to use", "## Steps", "## Warnings", "## Stop or escalate", "## Source"]
STEP = re.compile(r"^\d+\. (.*)$")


@pytest.mark.parametrize("slug", CARDS)
def test_card_front_matter(slug):
    post = load("cards", slug)
    assert {"id", "title", "icon", "order", "summary"} <= set(post.keys()) <= \
        {"id", "title", "icon", "order", "summary", "conditions", "aliases"}
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
        # the one-screen rule applies to what a reader sees with the phones working, not to directive source
        shown = directives.resolve(s, directives.default_flags())
        assert len(shown) <= 70, (slug, shown)
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
    "fieldcraft-basics": "fieldcraft", "fieldcraft-shelter": "fieldcraft", "fieldcraft-fire": "fieldcraft", "fieldcraft-water": "fieldcraft", "fieldcraft-food": "fieldcraft", "fieldcraft-moving": "fieldcraft", "fieldcraft-weather": "fieldcraft", "fieldcraft-rescue": "fieldcraft", "fieldcraft-hygiene": "fieldcraft", "fieldcraft-rope-tools": "fieldcraft", "no-phones": "comms",
    "chronic-conditions": "reference", "death-and-grief": "reference", "infant-feeding": "reference",
    "fieldcraft-navigation": "fieldcraft", "food-storage": "reference", "fieldcraft-fishing": "fieldcraft",
    "butchery": "reference",
    "rebuild-first-year": "rebuild", "rebuild-keeping-the-box": "rebuild",
    "rebuild-essentials-printed": "rebuild", "rebuild-restarting-science": "rebuild",
    "rebuild-making-things": "rebuild", "rebuild-iron-and-tools": "rebuild", "rebuild-power": "rebuild",
    "rebuild-medicine": "rebuild", "rebuild-farming": "rebuild", "rebuild-law-and-trade": "rebuild",
    "rebuild-library-map": "rebuild",
}
REBUILD_PAGES = [slug for slug, category in PAGES.items() if category == "rebuild"]
REBUILD_ORDER_BASE = 200


def expected_page_order(slug: str) -> int:
    """Pages are numbered 1..n in the order they were written; the Rebuilding section starts again at 200."""
    if PAGES[slug] == "rebuild":
        return REBUILD_ORDER_BASE + REBUILD_PAGES.index(slug)
    return list(PAGES).index(slug) + 1


@pytest.mark.parametrize("slug", sorted(PAGES))
def test_page_front_matter_and_body(slug):
    post = load("pages", slug)
    assert set(post.keys()) == {"id", "title", "icon", "order", "summary", "category"}
    assert post["id"] == slug
    assert post["category"] == PAGES[slug]
    assert post["order"] == expected_page_order(slug)
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
INCLUDE = re.compile(r"^\{\{module:([a-z0-9-]+)\}\}$", re.M)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WRITTEN = SCENARIOS


def checklist_items(slug: str) -> list[tuple[str, str]]:
    """(id, bucket) for each checklist line, the bucket defaulting to `today` as the parser does."""
    lines = sections(load("scenarios", slug).content)["Checklist"].splitlines()
    return [(m.group(1), m.group(2) or "today") for m in (TASK_LINE.match(l) for l in lines) if m]


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
def test_scenario_checklist_leads_with_at_least_three_now_items(slug):
    """The first actions lead the list: a household reads from the top and does what it says."""
    buckets = [b for _, b in checklist_items(slug)]
    assert buckets.count("now") >= 3, (slug, buckets)
    assert buckets[:3] == ["now", "now", "now"], (slug, buckets)


@pytest.mark.parametrize("slug", WRITTEN)
def test_scenario_parses_and_validates(slug):
    doc = parse_document(PB / "scenarios" / f"{slug}.md")
    assert doc.kind == "scenario" and doc.id == slug
    assert [t for _, t, _ in doc.sections if t] == [h[3:] for h in SCENARIO_HEADINGS]
    assert [(i["id"], i["bucket"]) for i in doc.checklist] == checklist_items(slug)
    errors = validate_tree(PB, load_manifests(MANIFEST_DIR), overlay_ids())
    mine = [e for e in errors if e.startswith(f"scenarios/{slug}.md")]
    pending = re.compile(r"playbook '(" + "|".join(SCENARIOS) + r")' does not exist")
    assert [e for e in real_tree_errors(mine) if not pending.search(e)] == [], mine


def all_scenarios() -> dict[str, frontmatter.Post]:
    return {s: load("scenarios", s) for s in SCENARIOS}


PLAYBOOK_LINK = re.compile(r"\]\(playbook:([a-z0-9-]+)\)")


def test_every_scenario_present_and_tree_validates():
    assert sorted(p.stem for p in (PB / "scenarios").glob("*.md")) == sorted(SCENARIOS)
    errors = validate_tree(PB, load_manifests(MANIFEST_DIR), overlay_ids(), require_all_scenarios=True)
    assert real_tree_errors(errors) == []


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


KITS = [
    "medical", "water", "food", "power-light", "comms", "sanitation-hygiene", "warmth-shelter", "fallout-cbrn",
    "grab-bag", "car", "baby-child", "pets-livestock", "documents-cash", "tools-repair", "growing-food",
]
WORD = re.compile(r"[A-Za-z']+")


def load_kit(slug: str) -> dict:
    return yaml.safe_load((PB / "kits" / f"{slug}.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("slug", KITS)
def test_kit_shape(slug):
    kit = load_kit(slug)
    assert kit["id"] == slug and kit["order"] == KITS.index(slug) + 1
    assert 20 <= len(kit["summary"]) <= 160
    assert 60 <= len(WORD.findall(kit["intro"])) <= 250, slug
    assert len(CITE.findall(kit["intro"])) >= 2, slug
    assert len(kit["sources"]) >= 2 and all(("doc" in s or "kiwix" in s) and AS_AT.match(str(s["as_at"])) for s in kit["sources"]), slug
    assert [kit["tiers"][t]["days"] for t in ("basic", "serious", "full")] == [3, 14, 90]
    by_tier = {t: [i for i in kit["items"] if i["tier"] == t] for t in ("basic", "serious", "full")}
    assert 4 <= len(by_tier["basic"]) <= 8 and 4 <= len(by_tier["serious"]) <= 10 and 3 <= len(by_tier["full"]) <= 10, slug
    for item in kit["items"]:
        assert item.get("why") or item.get("link"), (slug, item["id"])
        if item.get("stock"):
            assert item.get("qty"), (slug, item["id"])
    assert "NOMAD" not in (PB / "kits" / f"{slug}.yaml").read_text(encoding="utf-8")


def test_kit_relevance_clauses():
    assert load_kit("baby-child")["relevant_when"] == {"age_under": 2}
    assert "dog" in load_kit("pets-livestock")["relevant_when"]["needs_any"]
    assert all("relevant_when" not in load_kit(s) for s in KITS if s not in ("baby-child", "pets-livestock"))


def test_kit_tree_validates():
    items = load_manifests(MANIFEST_DIR)
    assert real_tree_errors(validate_tree(PB, items, overlay_ids())) == []


# --- injury subjects (task 25): what a card is about, for search, not for display ------------------------------------

INJURY_CARDS = {
    "severe-bleeding": ["bleeding", "open_wound"], "wound-cleaning": ["open_wound"], "wound-closure": ["open_wound"],
    "burns": ["burn"], "broken-bones": ["fracture"], "sprains-strains": ["sprain"], "head-injury": ["head_injury"],
    "eye-injury": ["eye_injury"], "nosebleed": ["nosebleed"], "bites-stings": ["bite_sting"],
    "spinal-injury": ["spinal_injury"],
}


def test_the_injury_cards_carry_their_conditions_and_every_condition_has_a_card():
    from sos import query
    for slug in CARDS:
        assert load("cards", slug).get("conditions") == INJURY_CARDS.get(slug), slug
    assert {c for conds in INJURY_CARDS.values() for c in conds} == set(query.CONDITION_IDS)


def test_the_schema_condition_ids_are_the_search_vocabulary():
    from sos import query
    schema = json.loads((PB / "schema.json").read_text(encoding="utf-8"))
    assert schema["$defs"]["card"]["properties"]["conditions"]["items"]["enum"] == list(query.CONDITION_IDS)


def test_the_schema_accepts_conditions_and_aliases_and_rejects_an_unknown_condition():
    import jsonschema
    schema = json.loads((PB / "schema.json").read_text(encoding="utf-8"))
    v = jsonschema.Draft202012Validator({"$ref": "#/$defs/card", "$defs": schema["$defs"]})
    base = {"id": "x", "title": "X", "icon": "a", "order": 1, "summary": "s"}
    assert not list(v.iter_errors({**base, "conditions": ["open_wound"], "aliases": ["gash", "deep cut"]}))
    assert list(v.iter_errors({**base, "conditions": ["gash"]}))
    assert list(v.iter_errors({**base, "aliases": "gash"}))
    assert list(v.iter_errors({**base, "aliases": ["Gash!"]}))
    page = jsonschema.Draft202012Validator({"$ref": "#/$defs/page", "$defs": schema["$defs"]})
    assert list(page.iter_errors({**base, "category": "reference", "aliases": ["gash"]}))   # cards only


@pytest.mark.parametrize("slug", sorted(INJURY_CARDS))
def test_an_alias_never_describes_an_injury_its_card_is_not_about(slug):
    """An alias is a way a household words this card's own subject. Read as a query, it may name no condition at all
    ("stitches"), but never one the card does not treat: Broken bones gets no wound words for the bleeding its
    warnings mention, and Severe bleeding no "gash" (a gash is a wound first; not every gash is a haemorrhage)."""
    from sos import query
    post = load("cards", slug)
    aliases = post.get("aliases") or []
    assert aliases, slug
    for alias in aliases:
        read = query.analyse_injury(alias)
        assert set(read.conditions) <= set(post["conditions"]), (slug, alias, read.conditions)


def test_broken_bones_has_no_wound_aliases():
    aliases = " ".join(load("cards", "broken-bones")["aliases"])
    for word in ("wound", "cut", "gash", "bleed", "blood", "laceration", "graze"):
        assert word not in aliases
