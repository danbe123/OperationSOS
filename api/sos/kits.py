"""Kits: tiered, tickable lists of things to have (kits spec, 2026-09-06).

A kit is one YAML file under playbooks/kits/. This module loads it, scales an item's quantity to the people
count and a tier's day count, and validates the kit tree for `sos validate-playbooks`. Nothing is typed in
before the box is useful, so every kit is relevant to everybody and the ticks live in the router."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import jsonschema
import yaml

TIERS = ("basic", "serious", "full")
TIER_DAYS = {"basic": 3, "serious": 14, "full": 90}
STOCK_CATEGORIES = ("water", "food", "fuel", "medicine", "other")


@dataclass
class KitItem:
    id: str
    tier: str
    name: str
    qty: dict | None = None        # {amount, unit, per?}
    stock: dict | None = None      # {category, unit}
    why: str = ""
    note: str = ""
    link: str | None = None


@dataclass
class Kit:
    id: str
    title: str
    icon: str
    order: int
    summary: str
    intro: str
    sources: list[dict]
    relevant_when: dict | None
    tiers: dict[str, dict]         # tier id -> {title, days, why}, in TIERS order
    items: list[KitItem]
    path: Path
    mtime: float
    raw: dict = field(default_factory=dict)

    def items_in(self, tier: str) -> list[KitItem]:
        return [i for i in self.items if i.tier == tier]


def _norm(value):
    """YAML dates become ISO strings, as the Markdown front matter loader does."""
    import datetime as dt
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()[:10]
    if isinstance(value, list):
        return [_norm(v) for v in value]
    if isinstance(value, dict):
        return {k: _norm(v) for k, v in value.items()}
    return value


def _raw(path: Path) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: a kit file is a mapping")
    return _norm(data)


def _item(raw: dict) -> KitItem:
    qty = raw.get("qty")
    if isinstance(qty, dict):
        qty = {"amount": qty.get("amount", 1), "unit": str(qty.get("unit", "") or ""), **({"per": qty["per"]} if qty.get("per") else {})}
    return KitItem(
        id=str(raw.get("id", "")), tier=str(raw.get("tier", "")), name=str(raw.get("name", "")),
        qty=qty if isinstance(qty, dict) else None,
        stock=dict(raw["stock"]) if isinstance(raw.get("stock"), dict) else None,
        why=str(raw.get("why", "") or ""), note=str(raw.get("note", "") or ""),
        link=str(raw["link"]) if raw.get("link") else None,
    )


def load_kit(path: Path | str) -> Kit:
    path = Path(path)
    raw = _raw(path)
    tiers_raw = raw.get("tiers") if isinstance(raw.get("tiers"), dict) else {}
    tiers = {t: dict(tiers_raw[t]) for t in TIERS if isinstance(tiers_raw.get(t), dict)}
    try:
        order = int(raw.get("order", 0) or 0)
    except (TypeError, ValueError):
        order = 0
    return Kit(
        id=str(raw.get("id", path.stem)), title=str(raw.get("title", path.stem)), icon=str(raw.get("icon", "")),
        order=order, summary=str(raw.get("summary", "")), intro=str(raw.get("intro", "") or ""),
        sources=[s for s in (raw.get("sources") or []) if isinstance(s, dict)],
        relevant_when=dict(raw["relevant_when"]) if isinstance(raw.get("relevant_when"), dict) else None,
        tiers=tiers, items=[_item(i) for i in (raw.get("items") or []) if isinstance(i, dict)],
        path=path, mtime=path.stat().st_mtime, raw=raw,
    )


def load_kits(folder: Path | str) -> list[Kit]:
    folder = Path(folder)
    if not folder.is_dir():
        return []
    loaded = [load_kit(p) for p in sorted(folder.glob("*.yaml"))]
    return sorted(loaded, key=lambda k: (k.order, k.title))


def _num(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else f"{n:g}"


def scaled(item: KitItem, days: int, people: int) -> dict | None:
    """The quantity this household needs for this tier, and the sentence the screens show."""
    if not item.qty:
        return None
    amount = float(item.qty.get("amount", 1))
    unit = str(item.qty.get("unit", "") or "")
    per = item.qty.get("per")
    people = max(1, int(people))
    who = "1 person" if people == 1 else f"{people} people"
    if per == "person-day":
        total = amount * people * days
        text = f"{_num(total)} {unit} for {who} over {days} days"
    elif per == "person":
        total = amount * people
        text = f"{_num(total)} {unit} for {who}"
    else:
        total = amount
        text = f"{_num(total)} {unit}"
    total = int(total) if float(total).is_integer() else round(total, 2)
    return {"amount": item.qty.get("amount", 1), "unit": unit, "scaled": total, "text": " ".join(text.split())}


def matching_people(kit: Kit, people: int) -> int:
    """How many people this kit is for: the people count, whatever the kit's own gate used to ask.

    With no register there is nothing for `relevant_when` to test, so a gated kit (baby and child)
    scales by the household count like every other. Never less than one, so a quantity always shows."""
    return max(1, int(people))


def relevant(kit: Kit) -> bool:
    """Every kit is relevant: the box knows nothing about who lives here, so it hides nothing (no-setup spec).

    A kit's `relevant_when` stays in its file as content -- it says who the kit is for in words -- but
    nothing reads it any more."""
    return True


# --- validation (called by content.validate_tree) ---------------------------------------------------------------

def _deep_checks(rel: str, kit: Kit, items_by_id: dict, kiwix_check, doc_check) -> list[str]:
    """`--deep` for a kit: every kiwix: link and source actually fetched, every doc: file actually there.

    The same two questions `content._deep_checks` asks of a playbook, asked of the text a kit carries:
    an item's why and link, the intro, and the kit's own sources."""
    from sos import content  # deferred: content imports this module

    errors: list[str] = []
    # The same text the shallow check reads: the intro, each item's why, and each item's link.
    bodies = [kit.intro] + [i.why for i in kit.items] + [f"[x]({i.link})" for i in kit.items if i.link]
    hrefs = [href for body in bodies if body for href in content._links(body)]
    targets = [(href[6:].partition("/")[0], href[6:].partition("/")[2]) for href in hrefs if href.startswith("kiwix:")]
    targets += [(str(s["kiwix"]).partition("/")[0], str(s["kiwix"]).partition("/")[2]) for s in kit.sources if "kiwix" in s]
    if kiwix_check:
        for book, path in dict.fromkeys(targets):
            if book in items_by_id and not kiwix_check(book, path):
                errors.append(f"{rel}: kiwix:{book}/{path} returned non-200")
    if doc_check:
        ids = {href[4:].partition("#")[0] for href in hrefs if href.startswith("doc:")}
        ids |= {str(s["doc"]) for s in kit.sources if "doc" in s}
        for doc_id in sorted(ids):
            item = items_by_id.get(doc_id)
            if item is not None and not doc_check(item):
                errors.append(f"{rel}: doc '{doc_id}' file missing ({item.dest})")
    return errors


def validate_kits(playbooks_dir: Path | str, zim_ids: set[str], doc_ids: set[str], slugs: dict[str, set[str]],
                  overlay_ids: set[str], items_by_id: dict | None = None,
                  kiwix_check=None, doc_check=None) -> list[str]:
    """One line per problem, in the validator's `kits/<slug>.yaml: <problem>` form.

    `kiwix_check` and `doc_check` are `content.validate_tree`'s own deep checkers, threaded through so
    `sos validate-playbooks --deep` reaches the kits as well as the playbooks."""
    from sos import content, directives   # deferred: content imports this module

    folder = Path(playbooks_dir) / "kits"
    if not folder.is_dir():
        return []
    schema_path = folder / "schema.json"
    if not schema_path.exists():
        return [f"{schema_path}: missing schema.json"]
    validator = jsonschema.Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")))
    errors: list[str] = []
    for path in sorted(folder.glob("*.yaml")):
        rel = f"kits/{path.name}"
        try:
            kit = load_kit(path)
        except Exception as exc:
            errors.append(f"{rel}: cannot parse: {exc}".splitlines()[0])
            continue
        for err in sorted(validator.iter_errors(kit.raw), key=lambda e: [str(p) for p in e.path]):
            loc = "/".join(str(p) for p in err.path) or "file"
            errors.append(f"{rel}: {loc}: {err.message}")
        if kit.id != path.stem:
            errors.append(f"{rel}: id '{kit.id}' must equal the file name '{path.stem}'")
        days = [kit.tiers[t]["days"] for t in TIERS if t in kit.tiers and isinstance(kit.tiers[t].get("days"), int)]
        if len(days) == 3 and not (days[0] < days[1] < days[2]):
            errors.append(f"{rel}: tiers: days must increase from basic to serious to full")
        seen: set[str] = set()
        for item in kit.items:
            if item.id in seen:
                errors.append(f"{rel}: item '{item.id}': duplicate id")
            seen.add(item.id)
            if item.tier not in kit.tiers:
                errors.append(f"{rel}: item '{item.id}': unknown tier '{item.tier}'")
            if item.stock and item.stock.get("category") not in STOCK_CATEGORIES:
                errors.append(f"{rel}: item '{item.id}': category '{item.stock.get('category')}' is not one of "
                              f"{', '.join(STOCK_CATEGORIES)}")
            if not (item.why or item.link):
                errors.append(f"{rel}: item '{item.id}': needs a why or a link")
            if item.link:
                errors += content._check_links(rel, f"[x]({item.link})", zim_ids, doc_ids, slugs, overlay_ids)
            errors += content._check_links(rel, item.why, zim_ids, doc_ids, slugs, overlay_ids)
        if kit.intro:
            for name in sorted(directives.check_flags(directives.flag_names(kit.intro))):
                errors.append(f"{rel}: unknown condition flag '{name}' in a {{{{#if}}}} directive")
            errors += content._check_links(rel, kit.intro, zim_ids, doc_ids, slugs, overlay_ids)
        for src in kit.sources:
            title = src.get("title", "?")
            if "doc" in src:
                if src["doc"] not in doc_ids:
                    errors.append(f"{rel}: source doc '{src['doc']}' not in manifest")
            elif "kiwix" in src:
                if str(src["kiwix"]).partition("/")[0] not in zim_ids:
                    errors.append(f"{rel}: source kiwix '{src['kiwix']}': item not in manifest")
            elif "url" in src:
                errors.append(f"warning: {rel}: source '{title}' is url-only (provenance only, not linked)")
            else:
                errors.append(f"{rel}: source '{title}' needs doc, kiwix or url")
        if kiwix_check or doc_check:
            errors += _deep_checks(rel, kit, items_by_id or {}, kiwix_check, doc_check)
    return list(dict.fromkeys(errors))
