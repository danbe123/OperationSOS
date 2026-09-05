import shutil
import time
from pathlib import Path

import pytest

from sos import content
from sos.manifest import load_manifests
from tests import broken_cases

FIXTURES = Path(__file__).parent / "fixtures"
REPO = Path(__file__).resolve().parents[2]
OVERLAYS = {"health", "nuclear-sites", "water"}


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "playbooks"
    shutil.copytree(FIXTURES / "playbooks", root)
    shutil.copy(REPO / "playbooks" / "schema.json", root / "schema.json")
    return root


@pytest.fixture
def items():
    return load_manifests(FIXTURES / "manifest")


def test_slugify():
    assert content.slugify("Fill every bottle and the bath") == "fill-every-bottle-and-the-bath"
    assert content.slugify("  Turn OFF, the cooker!  ") == "turn-off-the-cooker"
    assert len(content.slugify("x" * 100)) == 60


@pytest.mark.parametrize("href,expected", [
    ("kiwix:wikipedia_en_100_mini_2026-01/Precipitation", "/read/wikipedia_en_100_mini_2026-01/Precipitation"),
    ("kiwix:nhs_uk/www.nhs.uk/conditions/burns/", "/read/nhs_uk/www.nhs.uk/conditions/burns/"),
    ("doc:nrr-2025", "/doc/nrr-2025"),
    ("doc:nrr-2025#page=12", "/doc/nrr-2025#page=12"),
    ("map:?overlay=nuclear-sites&overlay=health", "/map?overlay=nuclear-sites&overlay=health"),
    ("map:", "/map"),
    ("playbook:nuclear-war", "/s/nuclear-war"),
    ("module:water", "/m/water"),
    ("card:cpr-adult", "/medical/card/cpr-adult"),
    ("page:pmr446", "/p/pmr446"),
    ("https://example.org/x", "https://example.org/x"),
    ("#top", "#top"),
])
def test_resolve_link(href, expected):
    assert content.resolve_link(href) == expected


def test_render_markdown_rewrites_links_and_escapes_html():
    html = content.render_markdown("See [water](module:water) and <script>x</script>\n\n| a | b |\n|---|---|\n| 1 | 2 |")
    assert '<a href="/m/water">water</a>' in html
    assert "&lt;script&gt;" in html and "<script>" not in html
    assert "<table>" in html


def test_render_markdown_strips_checklist_id_marker():
    html = content.render_markdown("- [ ] Label treated water {#label-treated}\n- [ ] Plain item")
    assert "{#label-treated}" not in html and "Label treated water" in html
    assert content.strip_task_id_markers("- [ ] a {#x}\ntext {#not-a-task}") == "- [ ] a\ntext {#not-a-task}"


def test_parse_scenario(tree):
    doc = content.parse_document(tree / "scenarios" / "grid-collapse.md")
    assert doc.kind == "scenario" and doc.id == "grid-collapse" and doc.order == 4
    assert doc.modules == ["water"] and doc.overlays == ["health", "water"]
    assert doc.reviewed == "2026-09-01"
    assert doc.sources[0]["kiwix"] == "wikipedia_en_100_mini_2026-01/Precipitation" and doc.sources[0]["as_at"] == "2026-01"
    assert [s[1] for s in doc.sections] == [t for _, t in content.SCENARIO_HEADINGS]
    assert [s[0] for s in doc.sections] == [i for i, _ in content.SCENARIO_HEADINGS]
    assert doc.checklist == [
        ("fill-every-bottle-and-the-bath", "Fill every bottle and the bath"),
        ("cooker-off", "Turn off the cooker at the wall"),
        ("check-on-neighbours", "Check on neighbours"),
    ]


def test_parse_page_and_card(tree):
    page = content.parse_document(tree / "pages" / "pmr446.md")
    assert page.kind == "page" and page.category == "comms"
    card = content.parse_document(tree / "cards" / "bleeding.md")
    assert card.kind == "card" and card.sections[0][1] == "" and "Press hard" in card.sections[0][2]


def test_render_document_includes_module_and_prefixes_module_checklist(tree):
    doc = content.parse_document(tree / "scenarios" / "grid-collapse.md")
    water = content.parse_document(tree / "modules" / "water.md")
    r = content.render_document(doc, content.resolve_link, {"water": water})
    assert [s["id"] for s in r.sections] == ["right-now", "first-72-hours", "first-month", "long-term", "uk-specifics", "go-deeper"]
    s72 = next(s for s in r.sections if s["id"] == "first-72-hours")
    assert '<section class="module" data-module="water"><h3>Water</h3>' in s72["html"]
    assert 'data-item-id="water/fill-clean-containers"' in s72["html"]
    assert 'data-item-id="water/label-treated"' in s72["html"]
    assert "{#label-treated}" not in s72["html"] and "{#" not in s72["html"]
    assert "{{module:water}}" not in s72["html"]
    assert [m["slug"] for m in r.modules] == ["water"]
    assert [c["id"] for c in r.checklist] == [
        "fill-every-bottle-and-the-bath", "cooker-off", "check-on-neighbours", "water/fill-clean-containers", "water/label-treated",
    ]
    assert '<a href="/medical/card/bleeding">' in r.sections[0]["html"]
    assert '<a href="/doc/sos-test-pdf#page=2">' in next(s for s in r.sections if s["id"] == "uk-specifics")["html"]
    assert r.reviewed == "2026-09-01" and r.overlays == ["health", "water"] and r.sources[1]["doc"] == "sos-test-pdf"


def test_render_missing_module_is_visible_not_fatal(tree):
    doc = content.parse_document(tree / "scenarios" / "grid-collapse.md")
    r = content.render_document(doc, content.resolve_link, {})
    assert "module-missing" in r.sections[1]["html"]
    assert r.modules == [] and len(r.checklist) == 3


def test_render_standalone_module_and_card(tree):
    water = content.parse_document(tree / "modules" / "water.md")
    r = content.render_document(water, content.resolve_link, {})
    assert r.kind == "module" and 'data-item-id="water/label-treated"' in r.html and r.sections == []
    assert "{#" not in r.html and "Label treated water</li>" in r.html
    card = content.parse_document(tree / "cards" / "bleeding.md")
    rc = content.render_document(card, content.resolve_link, {})
    assert "<ol>" in rc.html and "<blockquote>" in rc.html


def test_validate_valid_tree(tree, items):
    assert content.validate_tree(tree, items, OVERLAYS) == []


@pytest.mark.parametrize("name", list(broken_cases.CASES))
def test_validate_broken_examples(tree, items, name):
    replacements, fragment, is_warning = broken_cases.CASES[name]
    text = broken_cases.broken_text(name)
    committed = broken_cases.BROKEN_DIR / f"{name}.md"
    assert committed.read_text(encoding="utf-8") == text, f"run: python -m tests.broken_cases ({name})"
    (tree / "scenarios" / "grid-collapse.md").write_text(text, encoding="utf-8")
    out = content.validate_tree(tree, items, OVERLAYS)
    assert any(fragment in line for line in out), out
    errors = [line for line in out if not line.startswith("warning: ")]
    if is_warning:
        assert errors == []
    else:
        assert errors


def test_validate_deep_checks(tree, items):
    seen = []

    def kiwix_check(book, path):
        seen.append((book, path))
        return path != "Precipitation"

    def doc_check(item):
        return item.id != "sos-test-pdf"

    out = content.validate_tree(tree, items, OVERLAYS, kiwix_check=kiwix_check, doc_check=doc_check)
    assert ("wikipedia_en_100_mini_2026-01", "Precipitation") in seen
    assert any("kiwix:wikipedia_en_100_mini_2026-01/Precipitation returned non-200" in e for e in out)
    assert any("doc 'sos-test-pdf' file missing" in e for e in out)


def test_validate_require_all_scenarios(tree, items):
    out = content.validate_tree(tree, items, OVERLAYS, require_all_scenarios=True)
    assert len([e for e in out if e.endswith(": missing")]) == 19
    assert "scenarios/nuclear-war.md: missing" in out


def test_validate_reports_unparseable_file(tree, items):
    (tree / "cards" / "broken.md").write_text("---\nid: [unclosed\n---\nx", encoding="utf-8")
    out = content.validate_tree(tree, items, OVERLAYS)
    assert any(e.startswith("cards/broken.md: cannot parse") for e in out)


def test_content_cache_reloads_on_mtime(tree):
    cache = content.ContentCache(tree)
    assert cache.document("card", "missing") is None
    r1 = cache.rendered("scenario", "grid-collapse")
    assert cache.rendered("scenario", "grid-collapse") is r1
    path = tree / "modules" / "water.md"
    path.write_text(path.read_text(encoding="utf-8").replace("Rainwater", "Snowmelt"), encoding="utf-8")
    future = time.time() + 5
    import os
    os.utime(path, (future, future))
    r2 = cache.rendered("scenario", "grid-collapse")
    assert r2 is not r1 and "Snowmelt" in r2.modules[0]["html"]
    assert [d.id for d in cache.list("card")] == ["bleeding"]
    assert cache.list("nonexistent-kind") == []
