"""Condition directives: resolving them, rendering with them, caching them and validating every branch."""
import shutil
from pathlib import Path

import pytest

from sos import content, directives

FIXTURES = Path(__file__).parent / "fixtures"
REPO = Path(__file__).resolve().parents[2]
OVERLAYS = {"health", "nuclear-sites", "water"}

WATER_BRANCH = ("{{#if water}}Fill the bath now.{{else}}The water is off: draw from the tank "
                "and read the [water module](module:water).{{/if}}")


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "playbooks"
    shutil.copytree(FIXTURES / "playbooks", root)
    shutil.copy(REPO / "playbooks" / "schema.json", root / "schema.json")
    (root / "pages" / "no-phones.md").write_text(
        "---\nid: no-phones\ntitle: Getting help without phones\nicon: phone\norder: 9\n"
        "summary: What to do when no number will connect.\ncategory: comms\n---\n\n## Go on foot\nSend a runner.\n",
        encoding="utf-8")
    return root


@pytest.fixture
def items():
    from sos.manifest import load_manifests
    return load_manifests(FIXTURES / "manifest")


def append(path: Path, text: str) -> None:
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


# --- the directive language ----------------------------------------------------------------------------------

def test_if_else_branches_on_a_flag():
    flags = directives.default_flags()
    assert directives.resolve(WATER_BRANCH, flags) == "Fill the bath now."
    assert "draw from the tank" in directives.resolve(WATER_BRANCH, flags | {"water": False})


def test_unless_and_nesting():
    text = "{{#unless power}}No power.{{#if gas}} The gas hob still lights.{{/if}}{{/unless}}"
    flags = directives.default_flags()
    assert directives.resolve(text, flags) == ""
    assert directives.resolve(text, flags | {"power": False}) == "No power. The gas hob still lights."
    assert directives.resolve(text, flags | {"power": False, "gas": False}) == "No power."


NESTED = ("{{#if power}}Boil the kettle{{#if water}} and fill the bath{{else}} with bottled water{{/if}}, then rest."
          "{{else}}No power: {{#unless gas}}light the stove{{else}}use the gas hob{{/unless}}.{{/if}}")


def test_blocks_nest_two_deep_in_both_branches():
    flags = directives.default_flags()
    assert directives.resolve(NESTED, flags) == "Boil the kettle and fill the bath, then rest."
    assert directives.resolve(NESTED, flags | {"water": False}) == "Boil the kettle with bottled water, then rest."
    assert directives.resolve(NESTED, flags | {"power": False}) == "No power: use the gas hob."
    assert directives.resolve(NESTED, flags | {"power": False, "gas": False}) == "No power: light the stove."


def test_a_nested_flag_is_found_by_the_validator_and_the_branch_sets():
    assert directives.flag_names(NESTED) == {"power", "water", "gas"}
    assert len(directives.branch_flag_sets(NESTED)) == 8
    assert directives.check_flags(directives.flag_names("{{#if power}}{{#if broadband}}x{{/if}}{{/if}}")) == ["broadband"]


def test_a_typo_inside_a_branch_nobody_is_reading_is_still_an_error():
    with pytest.raises(directives.DirectiveError):
        directives.resolve("{{#if power}}fine{{else}}{{#if watr}}oops{{/if}}{{/if}}", directives.default_flags())


@pytest.mark.parametrize("text,fragment", [
    ("{{#if power}}x", "unbalanced"),
    ("x{{/if}}", "unbalanced"),
    ("{{else}}x", "outside"),
    ("{{#if power}}a{{else}}b{{else}}c{{/if}}", "two {{else}}"),
    ("{{#if power}}a{{/unless}}", "closed by"),
])
def test_malformed_directives_are_refused(text, fragment):
    with pytest.raises(directives.DirectiveError) as exc:
        directives.resolve(text, directives.default_flags())
    assert fragment in str(exc.value)


def test_inline_call_swaps_for_the_alternative():
    assert directives.resolve("[[call 999]] now.", {"phones": True}) == "call 999 now."
    out = directives.resolve("[[call 999]] now.", {"phones": False})
    assert out == "999 will not connect while the phones are down: [get help without phones](page:no-phones) now."


def test_scenario_flags_and_unknown_flags():
    assert directives.resolve("{{#if scenario:grid-collapse}}Grid{{/if}}", {"scenario:grid-collapse": True}) == "Grid"
    assert directives.resolve("{{#if scenario:pandemic}}Flu{{else}}No{{/if}}", {}) == "No"
    with pytest.raises(directives.DirectiveError):
        directives.resolve("{{#if powr}}x{{/if}}", directives.default_flags())


def test_branch_flag_sets_cover_every_combination():
    sets = directives.branch_flag_sets("{{#if water}}a{{/if}} {{#if power}}b{{/if}} [[call 999]]")
    assert len(sets) == 8 and {"water": True, "power": False, "phones": True} in sets
    assert directives.branch_flag_sets("no directives here") == [{}]


# --- rendering -----------------------------------------------------------------------------------------------

def test_rendered_page_follows_the_flags(tree):
    append(tree / "pages" / "pmr446.md", "\n\n" + WATER_BRANCH + "\n\nIn an emergency [[call 999]].\n")
    cache = content.ContentCache(tree)
    flags = directives.default_flags()
    working = cache.rendered("page", "pmr446", flags)
    assert "Fill the bath now." in working.html and "call 999" in working.html
    assert "{{#if" not in working.html and "[[call" not in working.html
    dry = cache.rendered("page", "pmr446", flags | {"water": False, "phones": False})
    assert 'href="/m/water"' in dry.html and "will not connect" in dry.html
    assert 'href="/p/no-phones"' in dry.html


def test_rendered_without_flags_shows_the_everything_works_branch(tree):
    append(tree / "pages" / "pmr446.md", "\n\n" + WATER_BRANCH + "\n")
    assert "Fill the bath now." in content.ContentCache(tree).rendered("page", "pmr446").html


def test_module_include_inside_a_scenario_follows_the_flags(tree):
    append(tree / "modules" / "water.md", "\n\n{{#if power}}Use the electric kettle.{{else}}Boil on the stove.{{/if}}\n")
    cache = content.ContentCache(tree)
    on = cache.rendered("scenario", "grid-collapse", directives.default_flags())
    off = cache.rendered("scenario", "grid-collapse", directives.default_flags() | {"power": False})
    assert "Use the electric kettle." in on.modules[0]["html"]
    assert "Boil on the stove." in off.modules[0]["html"]


def test_a_directive_can_change_the_checklist(tree):
    path = tree / "scenarios" / "grid-collapse.md"
    path.write_text(path.read_text(encoding="utf-8").replace(
        "- [ ] Check on neighbours",
        "{{#if power}}- [ ] Check on neighbours{{else}}- [ ] Knock on every door in the street {#knock}{{/if}}"),
        encoding="utf-8")
    cache = content.ContentCache(tree)
    assert [c["id"] for c in cache.rendered("scenario", "grid-collapse", directives.default_flags()).checklist][2] == "check-on-neighbours"
    dark = cache.rendered("scenario", "grid-collapse", directives.default_flags() | {"power": False})
    assert [c["id"] for c in dark.checklist][2] == "knock"


def test_the_cache_keeps_one_entry_per_flag_set_and_none_when_there_are_no_directives(tree):
    append(tree / "pages" / "pmr446.md", "\n\n" + WATER_BRANCH + "\n")
    cache = content.ContentCache(tree)
    flags = directives.default_flags()
    first = cache.rendered("page", "pmr446", flags)
    assert cache.rendered("page", "pmr446", flags) is first
    other = cache.rendered("page", "pmr446", flags | {"water": False})
    assert other is not first and cache.rendered("page", "pmr446", flags) is first
    # a document with no directives has one entry whatever the flags are
    plain = cache.rendered("card", "bleeding", flags)
    assert cache.rendered("card", "bleeding", flags | {"power": False}) is plain


def test_the_cache_reloads_when_the_file_changes(tree):
    import os
    path = tree / "pages" / "pmr446.md"
    append(path, "\n\n" + WATER_BRANCH + "\n")
    cache = content.ContentCache(tree)
    flags = directives.default_flags()
    first = cache.rendered("page", "pmr446", flags)
    path.write_text(path.read_text(encoding="utf-8").replace("Fill the bath now.", "Fill everything now."), encoding="utf-8")
    future = path.stat().st_mtime + 5
    os.utime(path, (future, future))
    second = cache.rendered("page", "pmr446", flags)
    assert second is not first and "Fill everything now." in second.html


# --- validation ----------------------------------------------------------------------------------------------

def test_validation_checks_the_links_in_both_branches(tree, items):
    append(tree / "pages" / "pmr446.md",
           "\n\n{{#if water}}Fine{{else}}See the [ghost module](module:ghost).{{/if}}\n")
    out = content.validate_tree(tree, items, OVERLAYS)
    assert any("module 'ghost' does not exist" in e for e in out)
    assert len([e for e in out if "module 'ghost'" in e]) == 1        # reported once, not once per branch


def test_validation_checks_the_link_the_inline_call_expands_to(tree, items):
    append(tree / "cards" / "bleeding.md", "\n\nIf they stop breathing, [[call 999]].\n")
    assert content.validate_tree(tree, items, OVERLAYS) == []
    (tree / "pages" / "no-phones.md").unlink()
    out = content.validate_tree(tree, items, OVERLAYS)
    assert any("page 'no-phones' does not exist" in e for e in out)


def test_validation_rejects_an_unknown_flag(tree, items):
    append(tree / "pages" / "pmr446.md", "\n\n{{#if broadband}}Check the website.{{/if}}\n")
    out = content.validate_tree(tree, items, OVERLAYS)
    assert any("unknown condition flag 'broadband'" in e for e in out)


def test_validation_rejects_an_unknown_scenario_flag(tree, items):
    append(tree / "pages" / "pmr446.md", "\n\n{{#if scenario:alien-invasion}}Hide.{{/if}}\n")
    out = content.validate_tree(tree, items, OVERLAYS)
    assert any("scenario 'alien-invasion' does not exist" in e for e in out)
    (tree / "pages" / "pmr446.md").write_text(
        (tree / "pages" / "pmr446.md").read_text(encoding="utf-8").replace("alien-invasion", "grid-collapse"),
        encoding="utf-8")
    assert content.validate_tree(tree, items, OVERLAYS) == []


def test_validation_rejects_an_unbalanced_directive(tree, items):
    append(tree / "pages" / "pmr446.md", "\n\n{{#if water}}Fill the bath.\n")
    out = content.validate_tree(tree, items, OVERLAYS)
    assert any("unbalanced" in e for e in out)


def test_validation_checks_the_links_inside_a_nested_branch(tree, items):
    append(tree / "pages" / "pmr446.md",
           "\n\n{{#if power}}Fine{{else}}{{#if water}}Boil it{{else}}See the [ghost page](page:ghost).{{/if}}{{/if}}\n")
    out = content.validate_tree(tree, items, OVERLAYS)
    assert any("page 'ghost' does not exist" in e for e in out)


def test_validation_refuses_a_document_with_too_many_flags(tree, items):
    text = "".join("{{#if %s}}x{{/if}}" % f for f in ("power", "water", "gas", "heating", "roads", "shops", "sewage"))
    append(tree / "pages" / "pmr446.md", "\n\n" + text + "\n")
    out = content.validate_tree(tree, items, OVERLAYS)
    assert any("too many condition flags" in e for e in out)


def test_the_repository_content_validates_in_every_branch():
    from sos.manifest import load_manifests
    overlays = {i.overlay.id for i in load_manifests(REPO / "manifest") if i.overlay}
    out = content.validate_tree(REPO / "playbooks", load_manifests(REPO / "manifest"), overlays,
                                require_all_scenarios=True)
    assert [e for e in out if not e.startswith("warning: ")] == []
