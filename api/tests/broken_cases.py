"""One broken authored document per validation rule, each derived from the valid fixture scenario
by a small textual change. `gen_fixtures.py` writes them to fixtures/playbooks-broken/ for reference;
`test_content.py` builds them on the fly and checks the committed copies match."""
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"
VALID_PATH = FIXTURES / "playbooks" / "scenarios" / "grid-collapse.md"
BROKEN_DIR = FIXTURES / "playbooks-broken"

# name -> (list of (old, new) replacements, expected substring in the validator output, is_warning)
CASES: dict[str, tuple[list[tuple[str, str]], str, bool]] = {
    "missing-heading": ([("## First month\n", "## First moon\n")], "missing heading '## First month'", False),
    "wrong-order": ([("## First 72 hours\n", "## TEMP\n"), ("## First month\n", "## First 72 hours\n"), ("## TEMP\n", "## First month\n")],
                    "headings out of order", False),
    "empty-section": ([("Learn the [PMR446 channels](page:pmr446) and re-read the [grid collapse](playbook:grid-collapse) playbook.\n", "\n")],
                      "section '## Long term' is empty", False),
    "module-not-included": ([("{{module:water}}\n", "")], "module 'water' declared but never included", False),
    "include-not-declared": ([("modules: [water]", "modules: []")], "undeclared module 'water'", False),
    "missing-module-file": ([("modules: [water]", "modules: [flood]"), ("{{module:water}}", "{{module:flood}}")], "module 'flood' does not exist", False),
    "unknown-overlay": ([("overlays: [health, water]", "overlays: [health, dragons]")], "overlay 'dragons' not in manifest/overlays.json", False),
    "duplicate-checklist": ([("- [ ] Check on neighbours\n", "- [ ] Check on neighbours {#cooker-off}\n")], "duplicate checklist id 'cooker-off'", False),
    "checklist-not-task": ([("- [ ] Check on neighbours\n", "- [ ] Check on neighbours\nRemember to breathe.\n")], "not a task-list line", False),
    "bad-source": ([("    doc: sos-test-pdf\n    as_at: 2026-09", "    doc: nope\n    as_at: 2026-09")], "source doc 'nope' not in manifest", False),
    "url-only-source": ([("    doc: sos-test-pdf\n    as_at: 2026-09", "    url: https://example.invalid/test.pdf\n    as_at: 2026-09")],
                        "warning: scenarios/grid-collapse.md: source 'Test PDF' is url-only", True),
    "bad-link": ([("(kiwix:wikipedia_en_100_mini_2026-01/Precipitation)", "(kiwix:nope/Precipitation)")], "link kiwix:nope/Precipitation: item 'nope' not in manifest", False),
    "unknown-map-overlay": ([("(map:?overlay=health&overlay=water)", "(map:?overlay=dragons)")], "link map:?overlay=dragons: overlay 'dragons'", False),
    "unknown-module-link": ([("(module:water)", "(module:nope)")], "link module:nope: module 'nope' does not exist", False),
    "bad-front-matter": ([("summary: A weeks-long blackout with water pumps and comms down.\n", "")], "'summary' is a required property", False),
    "id-mismatch": ([("id: grid-collapse", "id: grid-fail")], "id 'grid-fail' must equal the file name 'grid-collapse'", False),
}


def broken_text(name: str) -> str:
    text = VALID_PATH.read_text(encoding="utf-8")
    for old, new in CASES[name][0]:
        assert old in text, f"{name}: pattern not found: {old!r}"
        text = text.replace(old, new, 1)
    return text


def write_all() -> None:
    BROKEN_DIR.mkdir(parents=True, exist_ok=True)
    for name in CASES:
        (BROKEN_DIR / f"{name}.md").write_text(broken_text(name), encoding="utf-8")


if __name__ == "__main__":
    write_all()
    print(f"wrote {len(CASES)} broken examples to {BROKEN_DIR}")
