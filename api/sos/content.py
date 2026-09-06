"""Authored Markdown (playbooks, modules, cards, pages): parsing, rendering and validation (spec section 10)."""
from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass, field, replace
from html import escape
from pathlib import Path
from typing import TYPE_CHECKING, Callable
from urllib.parse import parse_qs

import frontmatter
import jsonschema
from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin

from sos import directives

if TYPE_CHECKING:
    from sos.kits import Kit

KIND_BY_DIR = {"scenarios": "scenario", "modules": "module", "cards": "card", "pages": "page"}
DIR_BY_KIND = {v: k for k, v in KIND_BY_DIR.items()}
SCENARIO_HEADINGS: list[tuple[str, str]] = [
    ("right-now", "Right now"), ("first-72-hours", "First 72 hours"), ("first-month", "First month"),
    ("long-term", "Long term"), ("uk-specifics", "UK specifics"), ("checklist", "Checklist"), ("go-deeper", "Go deeper"),
]
SCENARIO_SLUGS = [
    "nuclear-war", "nuclear-accident", "pandemic", "grid-collapse", "solar-storm", "emp", "cyber-attack", "invasion",
    "civil-unrest", "economic-collapse", "supply-chain", "storms-flooding", "severe-winter", "heat-drought", "volcanic",
    "chemical", "famine", "impact-winter", "terrorism", "long-rebuild",
]
LINK_ROUTES = {"kiwix": "/read/", "doc": "/doc/", "playbook": "/s/", "module": "/m/", "card": "/medical/card/", "page": "/p/"}

TASK_RE = re.compile(r"^\s*[-*+] \[([ xX])\] (.*?)(?:\s*\{#([A-Za-z0-9][A-Za-z0-9_/-]*)\})?\s*$")
INCLUDE_RE = re.compile(r"^\s*\{\{module:([a-z0-9-]+)\}\}\s*$")
H2_RE = re.compile(r"^## (.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
# the `{#id}` marker is checklist-id syntax, not prose: it is stripped before rendering
TASK_ID_MARKER_RE = re.compile(r"^(\s*[-*+] \[[ xX]\] .*?)\s*\{#[A-Za-z0-9][A-Za-z0-9_/-]*\}\s*$")
_TASK_LI = '<li class="task-list-item">'


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:60].rstrip("-")


def resolve_link(href: str) -> str:
    scheme, sep, rest = (href or "").partition(":")
    if not sep:
        return href
    if scheme == "map":
        if not rest:
            return "/map"
        return "/map" + (rest if rest.startswith("?") else "?" + rest)
    if scheme == "doc":
        doc_id, hash_, frag = rest.partition("#")
        return f"/doc/{doc_id}" + (f"#{frag}" if hash_ else "")
    if scheme in LINK_ROUTES:
        return LINK_ROUTES[scheme] + rest
    return href


def make_renderer(resolver: Callable[[str], str] = resolve_link) -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})
    md.enable(["table", "strikethrough"]).use(tasklists_plugin)

    def link_open(self, tokens, idx, options, env):
        href = tokens[idx].attrGet("href")
        if href:
            tokens[idx].attrSet("href", resolver(href))
        return self.renderToken(tokens, idx, options, env)

    md.add_render_rule("link_open", link_open)
    return md


def strip_task_id_markers(md_text: str) -> str:
    """Remove the trailing `{#id}` checklist-id marker from task-list lines so it never reaches the reader."""
    return "\n".join(TASK_ID_MARKER_RE.sub(r"\1", line) for line in (md_text or "").splitlines())


def _render(md: MarkdownIt, md_text: str) -> str:
    return md.render(strip_task_id_markers(md_text))


def render_markdown(md_text: str, link_resolver: Callable[[str], str] = resolve_link) -> str:
    return _render(make_renderer(link_resolver), md_text or "")


@dataclass
class Document:
    id: str
    title: str
    icon: str
    order: int
    summary: str
    kind: str
    modules: list[str]
    overlays: list[str]
    reviewed: str | None
    sources: list[dict]
    sections: list[tuple[str, str, str]]
    checklist: list[tuple[str, str]]
    category: str | None
    path: Path
    mtime: float
    meta: dict = field(default_factory=dict)
    body: str = ""


@dataclass
class RenderedDocument:
    slug: str
    title: str
    icon: str
    order: int
    summary: str
    kind: str
    category: str | None
    reviewed: str | None
    overlays: list[str]
    sources: list[dict]
    sections: list[dict]
    checklist: list[dict]
    modules: list[dict]
    html: str


def _norm(value):
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()[:10]
    if isinstance(value, list):
        return [_norm(v) for v in value]
    if isinstance(value, dict):
        return {k: _norm(v) for k, v in value.items()}
    return value


def split_sections(body: str) -> list[tuple[str, str, str]]:
    sections: list[tuple[str, str, str]] = []
    title = ""
    buf: list[str] = []
    in_fence = False
    for line in body.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
        m = None if in_fence else H2_RE.match(line)
        if m:
            sections.append((slugify(title), title, "\n".join(buf).strip("\n")))
            title = m.group(1).strip()
            buf = []
        else:
            buf.append(line)
    sections.append((slugify(title), title, "\n".join(buf).strip("\n")))
    if len(sections) > 1 and sections[0][1] == "" and not sections[0][2].strip():
        sections.pop(0)
    return sections


def parse_checklist(md_text: str) -> tuple[list[tuple[str, str]], list[str]]:
    items: list[tuple[str, str]] = []
    errors: list[str] = []
    for line in md_text.splitlines():
        if not line.strip():
            continue
        m = TASK_RE.match(line)
        if not m:
            errors.append(f"not a task-list line: {line.strip()!r}")
            continue
        text = m.group(2).strip()
        items.append((m.group(3) or slugify(text), text))
    return items, errors


def module_tasks(md_text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for line in md_text.splitlines():
        m = TASK_RE.match(line)
        if m:
            text = m.group(2).strip()
            out.append((m.group(3) or slugify(text), text))
    return out


def parse_document(path: Path) -> Document:
    path = Path(path)
    post = frontmatter.load(str(path))
    meta = {k: _norm(v) for k, v in post.metadata.items()}
    kind = KIND_BY_DIR.get(path.parent.name, "page")
    body = post.content
    sections = split_sections(body)
    checklist: list[tuple[str, str]] = []
    if kind == "scenario":
        for sid, _, md_text in sections:
            if sid == "checklist":
                checklist, _ = parse_checklist(md_text)
    try:
        order = int(meta.get("order", 0) or 0)
    except (TypeError, ValueError):
        order = 0
    return Document(
        id=str(meta.get("id", path.stem)), title=str(meta.get("title", path.stem)), icon=str(meta.get("icon", "")),
        order=order, summary=str(meta.get("summary", "")), kind=kind,
        modules=[str(m) for m in (meta.get("modules") or [])], overlays=[str(o) for o in (meta.get("overlays") or [])],
        reviewed=meta.get("reviewed"), sources=[s for s in (meta.get("sources") or []) if isinstance(s, dict)],
        sections=sections, checklist=checklist, category=meta.get("category"), path=path, mtime=path.stat().st_mtime,
        meta=meta, body=body,
    )


def _inject_item_ids(html_text: str, ids: list[str]) -> str:
    parts = html_text.split(_TASK_LI)
    out = [parts[0]]
    for i, part in enumerate(parts[1:]):
        item_id = ids[i] if i < len(ids) else ""
        out.append(f'<li class="task-list-item" data-item-id="{escape(item_id)}">{part}')
    return "".join(out)


def apply_directives(doc: Document, flags: dict[str, bool] | None) -> Document:
    """Resolve `{{#if …}}` and `[[call 999]]` against the situation before anything is parsed or rendered."""
    body = directives.resolve(doc.body, directives.default_flags() if flags is None else flags)
    if body == doc.body:
        return doc
    sections = split_sections(body)
    checklist = doc.checklist
    if doc.kind == "scenario":
        checklist = []
        for sid, _, md_text in sections:
            if sid == "checklist":
                checklist, _ = parse_checklist(md_text)
    return replace(doc, body=body, sections=sections, checklist=checklist)


def directive_signature(doc: Document, modules: dict[str, Document] | None, flags: dict[str, bool] | None) -> str:
    """A cache key covering only the flags this document (and anything it includes) actually reads."""
    bodies = [doc.body] + [m.body for m in (modules or {}).values()]
    used: set[str] = set()
    for body in bodies:
        used |= directives.flag_names(body)
        if directives.has_inline_calls(body):
            used.add("phones")
    if not used:
        return ""
    flags = directives.default_flags() if flags is None else flags
    # an absent flag means "working" for a service but "not this scenario" for a scenario flag
    explicit = {name: bool(flags.get(name, not name.startswith("scenario:"))) for name in used}
    return directives.signature(explicit, used)


def render_module(mod: Document, md: MarkdownIt, flags: dict[str, bool] | None = None) -> dict:
    mod = apply_directives(mod, flags)
    tasks = [(f"{mod.id}/{i}", t) for i, t in module_tasks(mod.body)]
    html_text = _inject_item_ids(_render(md, mod.body), [i for i, _ in tasks])
    return {"slug": mod.id, "title": mod.title, "html": html_text, "checklist": tasks}


def render_document(doc: Document, resolver: Callable[[str], str] = resolve_link,
                    modules: dict[str, Document] | None = None,
                    flags: dict[str, bool] | None = None) -> RenderedDocument:
    modules = modules or {}
    doc = apply_directives(doc, flags)
    md = make_renderer(resolver)
    common = dict(slug=doc.id, title=doc.title, icon=doc.icon, order=doc.order, summary=doc.summary, kind=doc.kind,
                  category=doc.category, reviewed=doc.reviewed, overlays=list(doc.overlays), sources=list(doc.sources))
    if doc.kind != "scenario":
        html_text = render_module(doc, md, flags)["html"] if doc.kind == "module" else _render(md, doc.body)
        return RenderedDocument(**common, sections=[], checklist=[], modules=[], html=html_text)
    sections: list[dict] = []
    included: list[dict] = []
    seen: set[str] = set()
    for sid, title, md_text in doc.sections:
        if sid == "checklist" or not title:
            continue
        parts: list[str] = []
        chunk: list[str] = []
        for line in md_text.splitlines():
            m = INCLUDE_RE.match(line)
            if not m:
                chunk.append(line)
                continue
            if chunk:
                parts.append(_render(md, "\n".join(chunk)))
                chunk = []
            slug = m.group(1)
            mod = modules.get(slug)
            if mod is None:
                parts.append(f'<p class="module-missing">Module "{escape(slug)}" is missing.</p>')
                continue
            rendered = render_module(mod, md, flags)
            if slug not in seen:
                included.append(rendered)
                seen.add(slug)
            parts.append(f'<section class="module" data-module="{escape(slug)}"><h3>{escape(mod.title)}</h3>{rendered["html"]}</section>')
        if chunk:
            parts.append(_render(md, "\n".join(chunk)))
        sections.append({"id": sid, "title": title, "html": "".join(parts)})
    checklist = [{"id": i, "text": t} for i, t in doc.checklist]
    for r in included:
        checklist += [{"id": i, "text": t} for i, t in r["checklist"]]
    return RenderedDocument(
        **common, sections=sections, checklist=checklist,
        modules=[{"slug": r["slug"], "title": r["title"], "html": r["html"]} for r in included],
        html="".join(s["html"] for s in sections),
    )


def load_tree(playbooks_dir: Path) -> dict[str, dict[str, Document]]:
    tree: dict[str, dict[str, Document]] = {k: {} for k in KIND_BY_DIR.values()}
    for dirname, kind in KIND_BY_DIR.items():
        for path in sorted((Path(playbooks_dir) / dirname).glob("*.md")):
            tree[kind][path.stem] = parse_document(path)
    return tree


def _links(body: str) -> list[str]:
    return LINK_RE.findall(body)


def _includes(body: str) -> list[str]:
    return [m.group(1) for m in (INCLUDE_RE.match(line) for line in body.splitlines()) if m]


def _check_scenario(rel: str, doc: Document, module_slugs: set[str], overlay_ids: set[str],
                    module_docs: dict[str, Document]) -> list[str]:
    errors: list[str] = []
    expected = [t for _, t in SCENARIO_HEADINGS]
    titles = [t for _, t, _ in doc.sections if t]
    for t in expected:
        if t not in titles:
            errors.append(f"{rel}: missing heading '## {t}'")
    for t in titles:
        if t not in expected:
            errors.append(f"{rel}: unexpected heading '## {t}'")
    if sorted(titles) == sorted(expected) and titles != expected:
        errors.append(f"{rel}: headings out of order: expected {', '.join(expected)}")
    for sid, title, md_text in doc.sections:
        if title and title in expected and not md_text.strip():
            errors.append(f"{rel}: section '## {title}' is empty")
    checklist_md = next((md_text for sid, _, md_text in doc.sections if sid == "checklist"), "")
    items, cl_errors = parse_checklist(checklist_md)
    errors += [f"{rel}: checklist: {e}" for e in cl_errors]
    declared = set(doc.modules)
    included = _includes(doc.body)
    for slug in sorted(declared - set(included)):
        errors.append(f"{rel}: module '{slug}' declared but never included ({{{{module:{slug}}}}})")
    for slug in included:
        if slug not in declared:
            errors.append(f"{rel}: include of undeclared module '{slug}'")
        if slug not in module_slugs:
            errors.append(f"{rel}: module '{slug}' does not exist")
    all_ids = [i for i, _ in items]
    for slug in included:
        mod = module_docs.get(slug)
        if mod:
            all_ids += [f"{slug}/{i}" for i, _ in module_tasks(mod.body)]
    seen: set[str] = set()
    for item_id in all_ids:
        if item_id in seen:
            errors.append(f"{rel}: duplicate checklist id '{item_id}'")
        seen.add(item_id)
    for ov in doc.overlays:
        if ov not in overlay_ids:
            errors.append(f"{rel}: overlay '{ov}' not in manifest/overlays.json")
    return errors


def _check_links(rel: str, body: str, zim_ids: set[str], doc_ids: set[str],
                 slugs: dict[str, set[str]], overlay_ids: set[str]) -> list[str]:
    errors: list[str] = []
    for href in _links(body):
        scheme, sep, rest = href.partition(":")
        if not sep:
            continue
        if scheme == "kiwix":
            book, slash, path = rest.partition("/")
            if not slash or not path:
                errors.append(f"{rel}: link {href}: needs <id>/<path>")
            elif book not in zim_ids:
                errors.append(f"{rel}: link {href}: item '{book}' not in manifest")
        elif scheme == "doc":
            doc_id = rest.partition("#")[0]
            if doc_id not in doc_ids:
                errors.append(f"{rel}: link {href}: document '{doc_id}' not in manifest")
        elif scheme == "map":
            for ov in parse_qs(rest.lstrip("?")).get("overlay", []):
                if ov not in overlay_ids:
                    errors.append(f"{rel}: link {href}: overlay '{ov}' not in manifest/overlays.json")
        elif scheme in ("module", "card", "page", "playbook"):
            kind = "scenario" if scheme == "playbook" else scheme
            if rest not in slugs[kind]:
                errors.append(f"{rel}: link {href}: {scheme} '{rest}' does not exist")
    return errors


def _check_branches(rel: str, doc: Document, zim_ids: set[str], doc_ids: set[str],
                    slugs: dict[str, set[str]], overlay_ids: set[str]) -> list[str]:
    """Render the document for every combination of the condition flags it uses and check the links in each,
    so advice that only appears when the water is off is checked as hard as the advice that is always there."""
    errors: list[str] = []
    for name in sorted(directives.check_flags(directives.flag_names(doc.body))):
        errors.append(f"{rel}: unknown condition flag '{name}' in a {{{{#if}}}} directive")
    for name in sorted(directives.flag_names(doc.body)):
        if name.startswith("scenario:") and name[len("scenario:"):] not in slugs["scenario"]:
            errors.append(f"{rel}: {{{{#if {name}}}}}: scenario '{name[len('scenario:'):]}' does not exist")
    if errors:
        return errors
    try:
        flag_sets = directives.branch_flag_sets(doc.body)
    except directives.DirectiveError as exc:
        return [f"{rel}: {exc}"]
    for flags in flag_sets:
        try:
            body = directives.resolve(doc.body, flags)
        except directives.DirectiveError as exc:
            errors.append(f"{rel}: {exc}")
            break
        errors += _check_links(rel, body, zim_ids, doc_ids, slugs, overlay_ids)
    return list(dict.fromkeys(errors))


def _check_sources(rel: str, doc: Document, zim_ids: set[str], doc_ids: set[str]) -> list[str]:
    out: list[str] = []
    for src in doc.sources:
        title = src.get("title", "?")
        if "doc" in src:
            if src["doc"] not in doc_ids:
                out.append(f"{rel}: source doc '{src['doc']}' not in manifest")
        elif "kiwix" in src:
            book = str(src["kiwix"]).partition("/")[0]
            if book not in zim_ids:
                out.append(f"{rel}: source kiwix '{src['kiwix']}': item '{book}' not in manifest")
        elif "url" in src:
            out.append(f"warning: {rel}: source '{title}' is url-only (provenance only, not linked)")
        else:
            out.append(f"{rel}: source '{title}' needs doc, kiwix or url")
    return out


def _deep_checks(rel: str, doc: Document, items_by_id: dict, kiwix_check, doc_check) -> list[str]:
    errors: list[str] = []
    targets: list[tuple[str, str]] = []
    for href in _links(doc.body):
        if href.startswith("kiwix:"):
            book, _, path = href[6:].partition("/")
            targets.append((book, path))
    for src in doc.sources:
        if "kiwix" in src:
            book, _, path = str(src["kiwix"]).partition("/")
            targets.append((book, path))
    if kiwix_check:
        for book, path in dict.fromkeys(targets):
            if book in items_by_id and not kiwix_check(book, path):
                errors.append(f"{rel}: kiwix:{book}/{path} returned non-200")
    if doc_check:
        doc_ids = {href[4:].partition("#")[0] for href in _links(doc.body) if href.startswith("doc:")}
        doc_ids |= {str(s["doc"]) for s in doc.sources if "doc" in s}
        for doc_id in sorted(doc_ids):
            item = items_by_id.get(doc_id)
            if item is not None and not doc_check(item):
                errors.append(f"{rel}: doc '{doc_id}' file missing ({item.dest})")
    return errors


def validate_tree(playbooks_dir: Path, manifest_items: list, overlay_ids: set[str] | list[str],
                  kiwix_check: Callable[[str, str], bool] | None = None,
                  doc_check: Callable[[object], bool] | None = None,
                  require_all_scenarios: bool = False) -> list[str]:
    playbooks_dir = Path(playbooks_dir)
    overlay_ids = set(overlay_ids)
    schema_path = playbooks_dir / "schema.json"
    if not schema_path.exists():
        return [f"{schema_path}: missing schema.json"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validators = {
        kind: jsonschema.Draft202012Validator({"$ref": f"#/$defs/{kind}", "$defs": schema["$defs"]})
        for kind in KIND_BY_DIR.values()
    }
    zim_ids = {i.id for i in manifest_items if i.kind == "zim"}
    doc_ids = {i.id for i in manifest_items if i.kind in ("pdf", "epub")}
    items_by_id = {i.id: i for i in manifest_items}
    errors: list[str] = []
    tree: dict[str, dict[str, Document]] = {k: {} for k in KIND_BY_DIR.values()}
    for dirname, kind in KIND_BY_DIR.items():
        for path in sorted((playbooks_dir / dirname).glob("*.md")):
            rel = f"{dirname}/{path.name}"
            try:
                doc = parse_document(path)
            except Exception as exc:  # malformed YAML or unreadable file
                errors.append(f"{rel}: cannot parse: {exc}".splitlines()[0])
                continue
            tree[kind][path.stem] = doc
            for err in sorted(validators[kind].iter_errors(doc.meta), key=lambda e: [str(p) for p in e.path]):
                loc = "/".join(str(p) for p in err.path) or "front matter"
                errors.append(f"{rel}: {loc}: {err.message}")
            if doc.id != path.stem:
                errors.append(f"{rel}: id '{doc.id}' must equal the file name '{path.stem}'")
    slugs = {kind: set(docs) for kind, docs in tree.items()}
    for kind, docs in tree.items():
        for slug, doc in docs.items():
            rel = f"{DIR_BY_KIND[kind]}/{slug}.md"
            if kind == "scenario":
                errors += _check_scenario(rel, doc, slugs["module"], overlay_ids, tree["module"])
            errors += _check_branches(rel, doc, zim_ids, doc_ids, slugs, overlay_ids)
            errors += _check_sources(rel, doc, zim_ids, doc_ids)
            if kiwix_check or doc_check:
                errors += _deep_checks(rel, doc, items_by_id, kiwix_check, doc_check)
    from sos import kits as kits_mod  # deferred: kits imports content for the link checks

    errors += kits_mod.validate_kits(playbooks_dir, zim_ids, doc_ids, slugs, overlay_ids)

    if require_all_scenarios:
        errors += [f"scenarios/{s}.md: missing" for s in SCENARIO_SLUGS if s not in tree["scenario"]]
    return errors


class ContentCache:
    """Documents parsed on demand and cached by file mtime; rendered output cached by the mtimes of the
    document and every included module."""

    def __init__(self, root: Path, resolver: Callable[[str], str] = resolve_link) -> None:
        self.root = Path(root)
        self.resolver = resolver
        self._docs: dict[tuple[str, str], Document] = {}
        self._rendered: dict[tuple, RenderedDocument] = {}
        self._kits: dict[str, Kit] = {}

    def _path(self, kind: str, slug: str) -> Path:
        return self.root / DIR_BY_KIND[kind] / f"{slug}.md"

    @staticmethod
    def _fresh(store: dict, key, path: Path, load: Callable[[Path], object]):
        """The cached object at `key` if `path` still has the mtime it was cached with; otherwise a fresh
        load (stored under `key`), or `None` (and `key` evicted) if `path` no longer exists."""
        if not path.is_file():
            store.pop(key, None)
            return None
        mtime = path.stat().st_mtime
        cached = store.get(key)
        if cached is not None and cached.mtime == mtime:
            return cached
        value = load(path)
        store[key] = value
        return value

    def document(self, kind: str, slug: str) -> Document | None:
        if kind not in DIR_BY_KIND or "/" in slug or slug.startswith("."):
            return None
        return self._fresh(self._docs, (kind, slug), self._path(kind, slug), parse_document)

    def list(self, kind: str) -> list[Document]:
        if kind not in DIR_BY_KIND:
            return []
        folder = self.root / DIR_BY_KIND[kind]
        docs = [self.document(kind, p.stem) for p in sorted(folder.glob("*.md"))] if folder.is_dir() else []
        return sorted([d for d in docs if d is not None], key=lambda d: (d.order, d.title))

    def kit(self, slug: str) -> Kit | None:
        """One kit, parsed on demand and cached by mtime, like documents."""
        from sos import kits as kits_mod

        if "/" in slug or slug.startswith(".") or not slug:
            return None
        path = self.root / "kits" / f"{slug}.yaml"
        return self._fresh(self._kits, slug, path, kits_mod.load_kit)

    def kits(self) -> list[Kit]:
        folder = self.root / "kits"
        found = [self.kit(p.stem) for p in sorted(folder.glob("*.yaml"))] if folder.is_dir() else []
        return sorted([k for k in found if k is not None], key=lambda k: (k.order, k.title))

    def rendered(self, kind: str, slug: str, flags: dict[str, bool] | None = None) -> RenderedDocument | None:
        """The rendered document for one situation. The cache key carries the mtimes and the flags it reads."""
        doc = self.document(kind, slug)
        if doc is None:
            return None
        modules = {m: self.document("module", m) for m in doc.modules}
        modules = {k: v for k, v in modules.items() if v is not None}
        mtimes = (doc.mtime, tuple(sorted((m, d.mtime) for m, d in modules.items())))
        key = (kind, slug, *mtimes, directive_signature(doc, modules, flags))
        hit = self._rendered.get(key)
        if hit is not None:
            return hit
        rendered = render_document(doc, self.resolver, modules, flags)
        # keep the other flag variants of this document, drop anything rendered from older files
        self._rendered = {k: v for k, v in self._rendered.items() if k[:2] != (kind, slug) or k[2:4] == mtimes}
        self._rendered[key] = rendered
        return rendered
