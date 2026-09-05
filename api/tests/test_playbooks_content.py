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
