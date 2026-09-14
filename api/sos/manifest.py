"""Manifest loading and validation. The manifest is the single description of every
content item; `library.py` mirrors it into the `library_items` table."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import jsonschema
from pydantic import BaseModel, ConfigDict, Field

Kind = Literal["zim", "pmtiles", "geojson", "pdf", "epub", "dir", "model", "mwm", "apk", "style", "glyphs", "sprites", "places"]
Tier = Literal["core", "extended"]
Category = Literal["playbooks", "uk-official", "medical", "survival", "reference", "practical", "maps", "education", "books", "media", "ai"]


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["kiwix", "url", "build"]
    name: str | None = None
    url: str | None = None
    sha256: str | None = None
    mirrors: list[str] = Field(default_factory=list)
    tool: str | None = None
    artifact: str | None = None


class OverlaySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    kind: Literal["geojson", "pmtiles", "style-layer"]
    layer_id: str | None = None
    default_on: bool = False
    coverage: list[str] = Field(default_factory=list)
    color: str = "#ffffff"
    icon: str | None = None
    coverage_note: str | None = None


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    title: str
    kind: Kind
    tier: Tier
    category: Category
    scenarios: list[str] = Field(default_factory=list)
    source: Source
    dest: str
    pdf_dest: str | None = None
    size_bytes: int = 0
    as_at: str | None = None
    licence: str | None = None
    priority: int = 100
    reader_home: str | None = None
    description: str | None = None
    search_weight: float = 1.0
    suggest: bool = False
    overlay: OverlaySpec | None = None


def manifest_files(dir: Path) -> list[Path]:
    """Every *.json in the directory except schema.json, in name order."""
    return [p for p in sorted(Path(dir).glob("*.json")) if p.name != "schema.json"]


def load_manifests(dir: Path) -> list[Item]:
    items: list[Item] = []
    for path in manifest_files(dir):
        data = json.loads(path.read_text(encoding="utf-8"))
        for raw in data.get("items", []):
            items.append(Item.model_validate(raw))
    return items


def load_schema(dir: Path) -> dict:
    return json.loads((Path(dir) / "schema.json").read_text(encoding="utf-8"))


def validate_manifests(dir: Path) -> list[str]:
    """Schema validation plus the cross-item rules. Returns error strings; empty means valid."""
    dir = Path(dir)
    schema_path = dir / "schema.json"
    if not schema_path.exists():
        return [f"{schema_path}: missing schema.json"]
    validator = jsonschema.Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")))
    errors: list[str] = []
    seen_ids: dict[str, str] = {}
    seen_dests: dict[str, str] = {}
    for path in manifest_files(dir):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}: invalid JSON: {exc}")
            continue
        for err in sorted(validator.iter_errors(data), key=lambda e: [str(p) for p in e.path]):
            loc = "/".join(str(p) for p in err.path) or "<root>"
            errors.append(f"{path.name}: {loc}: {err.message}")
        raw_items = data.get("items", []) if isinstance(data, dict) else []
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            iid = str(raw.get("id"))
            dest = str(raw.get("dest"))
            source = raw.get("source") if isinstance(raw.get("source"), dict) else {}
            if iid in seen_ids:
                errors.append(f"{path.name}: duplicate id '{iid}' (also in {seen_ids[iid]})")
            else:
                seen_ids[iid] = path.name
            if dest in seen_dests:
                errors.append(f"{path.name}: duplicate dest '{dest}' (also in {seen_dests[dest]})")
            else:
                seen_dests[dest] = path.name
            pdf_dest = raw.get("pdf_dest")
            if pdf_dest:
                if pdf_dest in seen_dests:
                    errors.append(f"{path.name}: duplicate dest '{pdf_dest}' (also in {seen_dests[pdf_dest]})")
                else:
                    seen_dests[pdf_dest] = path.name
            if raw.get("kind") == "zim" and dest != f"zim/{iid}.zim":
                errors.append(f"{path.name}: {iid}: zim dest must be 'zim/{iid}.zim', got '{dest}'")
            if source.get("type") == "build" and not source.get("artifact"):
                errors.append(f"{path.name}: {iid}: build items need source.artifact")
            if source.get("tool") == "pdf2epub" and not pdf_dest:
                errors.append(f"{path.name}: {iid}: pdf2epub build items need pdf_dest")
            if path.name == "overlays.json" and not raw.get("overlay"):
                errors.append(f"{path.name}: {iid}: overlay object required in overlays.json")
    return errors
