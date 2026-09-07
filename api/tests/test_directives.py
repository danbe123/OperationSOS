"""Condition directives: resolving them, rendering with them, caching them and validating every branch."""
import shutil
from pathlib import Path

import pytest

from sos import content, directives
from tests.conftest import real_tree_errors

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
    shutil.copy(REPO / "playbooks" / "kits" / "schema.json", root / "kits" / "schema.json")
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


def errors_only(problems: list[str]) -> list[str]:
    return [p for p in problems if not p.startswith("warning: ")]


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


# --- badges: why this passage is showing ----------------------------------------------------------------------

BLOCK = "{{#if power}}\nBoil the kettle.\n{{else}}\nUse the stove.\n{{/if}}\n"
MARKER = "[[because:power-off]]"


def test_a_block_level_branch_is_marked_and_the_normal_branch_is_not():
    flags = directives.default_flags()
    assert MARKER not in directives.resolve(BLOCK, flags)          # the power is on: nothing to explain
    out = directives.resolve(BLOCK, flags | {"power": False})
    assert MARKER in out and out.index(MARKER) < out.index("Use the stove.")


def test_an_inline_branch_is_never_marked():
    flags = directives.default_flags() | {"power": False}
    assert "[[because:" not in directives.resolve("Kettle {{#if power}}on{{else}}off{{/if}}.", flags)
    # opened mid-line, even though its content is on its own lines
    assert "[[because:" not in directives.resolve("Kettle {{#unless power}}\nStove.\n{{/unless}}", flags)
    # opened at the start of a line, but the content runs on from the directive
    assert "[[because:" not in directives.resolve("{{#unless power}}Stove.{{/unless}}", flags)


def test_an_else_on_its_own_line_makes_the_branch_block_level():
    flags = directives.default_flags() | {"power": False}
    assert MARKER in directives.resolve("Kettle {{#if power}}on\n{{else}}\nUse the stove.\n{{/if}}", flags)
    # the {{else}} is at the start of a line but its branch starts on the same line
    assert MARKER not in directives.resolve("{{#if power}}\non\n{{else}}Use the stove.\n{{/if}}", flags)


@pytest.mark.parametrize("text,flags,keys", [
    ("{{#unless water}}\nDraw from the tank.\n{{/unless}}", {"water": False}, ["[[because:water-off]]"]),
    ("{{#if phones}}\nRing.\n{{else}}\nSend a runner.\n{{/if}}", {"phones": False}, ["[[because:phones-off]]"]),
    ("{{#if dark}}\nUse a torch.\n{{/if}}", {"dark": True}, ["[[because:dark]]"]),
    ("{{#unless dark}}\nWork outside.\n{{/unless}}", {"dark": False}, []),
    ("{{#if scenario:grid-collapse}}\nRation it.\n{{/if}}", {"scenario:grid-collapse": True},
     ["[[because:scenario:grid-collapse]]"]),
    ("{{#if scenario:grid-collapse}}\nRation it.\n{{else}}\nCarry on.\n{{/if}}", {}, []),
    ("{{#unless power}}\nStove.\n{{else}}\nKettle.\n{{/unless}}", {"power": True}, []),
])
def test_which_branches_are_marked(text, flags, keys):
    out = directives.resolve(text, directives.default_flags() | flags)
    assert [m.group(0) for m in content.BECAUSE_RE.finditer(out)] == keys


def test_only_the_outermost_block_level_branch_carries_the_badge():
    nested = "{{#unless power}}\nNo power.\n{{#unless water}}\nNo water either.\n{{/unless}}\n{{/unless}}"
    flags = directives.default_flags() | {"power": False, "water": False}
    out = directives.resolve(nested, flags)
    assert [m.group(0) for m in content.BECAUSE_RE.finditer(out)] == ["[[because:power-off]]"]
    # an unbadged outer branch does not silence the branch inside it
    inner = "{{#if power}}\nPower is on.\n{{#unless water}}\nCarry water.\n{{/unless}}\n{{/if}}"
    assert "[[because:water-off]]" in directives.resolve(inner, directives.default_flags() | {"water": False})


@pytest.mark.parametrize("key,wording", [
    ("power-off", "Because the mains power is off"),
    ("water-off", "Because the water supply is off"),
    ("mobile-off", "Because the mobile network is off"),
    ("landline-off", "Because the landline and 999 is off"),
    ("internet-off", "Because the internet is off"),
    ("gas-off", "Because the gas is off"),
    ("heating-off", "Because the heating is off"),
    ("roads-off", "Because the roads and transport is off"),
    ("shops-off", "Because the shops and cash is off"),
    ("sewage-off", "Because the sewage and drains is off"),
    ("phones-off", "Because no phone works"),
    ("dark", "Because it is dark"),
    ("scenario:grid-collapse", "In the grid collapse scenario"),
])
def test_every_badge_wording(key, wording):
    assert content.because_text(key) == wording
    assert content.render_markdown(f"[[because:{key}]]") == f'<p class="because">{wording}</p>\n'


def test_a_marker_never_survives_rendering():
    assert content.because_text("smoke-signals") is None
    html = content.render_markdown("[[because:smoke-signals]]\n\nA [[because:dark]] mid-sentence.")
    assert "[[because" not in html and 'class="because"' not in html
    assert "<p>smoke-signals</p>" in html and "A Because it is dark mid-sentence." in html


def test_a_scenario_badge_uses_the_playbook_title_when_there_is_one(tree):
    cache = content.ContentCache(tree)
    assert content.render_markdown("[[because:grid-collapse]]", scenario_title=cache.scenario_title) == (
        "<p>grid-collapse</p>\n")
    html = content.render_markdown("[[because:scenario:grid-collapse]]", scenario_title=cache.scenario_title)
    assert html == '<p class="because">In the National grid collapse scenario</p>\n'


def test_a_card_shows_the_badge_above_the_branch_it_explains(tree):
    append(tree / "cards" / "bleeding.md", "\n\n" + BLOCK)
    cache = content.ContentCache(tree)
    flags = directives.default_flags()
    on = cache.rendered("card", "bleeding", flags)
    assert "because" not in on.html and "Boil the kettle." in on.html
    off = cache.rendered("card", "bleeding", flags | {"power": False})
    assert '<p class="because">Because the mains power is off</p>' in off.html
    assert off.html.index('class="because"') < off.html.index("Use the stove.")
    assert "[[because" not in off.html


def test_a_marked_branch_inside_a_checklist_does_not_become_an_item(tree):
    path = tree / "scenarios" / "grid-collapse.md"
    path.write_text(path.read_text(encoding="utf-8").replace(
        "- [ ] Check on neighbours",
        "{{#if power}}\n- [ ] Check on neighbours\n{{else}}\n- [ ] Knock on every door {#knock}\n{{/if}}"),
        encoding="utf-8")
    cache = content.ContentCache(tree)
    dark = cache.rendered("scenario", "grid-collapse", directives.default_flags() | {"power": False})
    assert [c["id"] for c in dark.checklist][2] == "knock"
    assert all("because" not in c["id"] for c in dark.checklist)


# --- situational coverage warnings ----------------------------------------------------------------------------

def test_a_card_without_a_phones_or_power_branch_warns(tree, items):
    out = content.validate_tree(tree, items, OVERLAYS)
    assert "warning: cards/bleeding.md: no situational branch on phones" in out
    assert "warning: cards/bleeding.md: no situational branch on power" in out
    assert errors_only(out) == []                                   # a warning, not a failure


def test_a_card_that_branches_is_not_warned_about(tree, items):
    append(tree / "cards" / "bleeding.md",
           "\n\n{{#unless power}}\nWork by torchlight.\n{{/unless}}\n"
           "\n{{#unless phones}}\nSend a runner to the surgery.\n{{/unless}}\n")
    out = content.validate_tree(tree, items, OVERLAYS)
    assert not [e for e in out if e.startswith("warning: cards/bleeding.md")]


def test_an_inline_call_alone_does_not_count_as_covering_the_phones(tree, items):
    append(tree / "cards" / "bleeding.md", "\n\nIf they stop breathing, [[call 999]].\n")
    out = content.validate_tree(tree, items, OVERLAYS)
    assert "warning: cards/bleeding.md: no situational branch on phones" in out


def test_the_coverage_line_counts_documents_by_kind(tree, items):
    append(tree / "cards" / "bleeding.md", "\n\n{{#unless power}}\nWork by torchlight.\n{{/unless}}\n")
    line = [e for e in content.validate_tree(tree, items, OVERLAYS) if e.startswith("warning: situational coverage:")]
    assert line == ["warning: situational coverage: cards 0/1 phones, 1/1 power; modules 0/1 phones, 0/1 power; "
                    "pages 0/2 phones, 0/2 power; scenarios 0/1 phones, 0/1 power"]


# --- validation ----------------------------------------------------------------------------------------------

def test_validation_checks_the_links_in_both_branches(tree, items):
    append(tree / "pages" / "pmr446.md",
           "\n\n{{#if water}}Fine{{else}}See the [ghost module](module:ghost).{{/if}}\n")
    out = content.validate_tree(tree, items, OVERLAYS)
    assert any("module 'ghost' does not exist" in e for e in out)
    assert len([e for e in out if "module 'ghost'" in e]) == 1        # reported once, not once per branch


def test_validation_checks_the_link_the_inline_call_expands_to(tree, items):
    append(tree / "cards" / "bleeding.md", "\n\nIf they stop breathing, [[call 999]].\n")
    assert errors_only(content.validate_tree(tree, items, OVERLAYS)) == []
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
    assert errors_only(content.validate_tree(tree, items, OVERLAYS)) == []


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
    assert real_tree_errors(out) == []
