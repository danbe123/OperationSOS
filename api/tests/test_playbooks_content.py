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
