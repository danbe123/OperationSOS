"""Map places: what to expect at each kind of place on the map (map places spec, 2026-09-07).

One YAML file, playbooks/map/places.yaml, loaded here, validated for `sos validate-playbooks` and served by
GET /api/map/places as HTML the frontend never has to parse."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import jsonschema
import yaml

KINDS = ("hospital", "pharmacy", "gp", "clinic", "fuel", "water-works", "reservoir", "spring", "rail-station",
         "airport", "military", "nuclear", "chemical", "flood-zone", "footpath", "access-land")


@dataclass(frozen=True)
class PlaceKind:
    kind: str
    title: str
    expect: str
    link: str


def load_places(path: Path | str) -> dict[str, PlaceKind]:
    """The place kinds in `places.yaml`, or an empty mapping if the file is missing or empty."""
    path = Path(path)
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {k: PlaceKind(k, str(v.get("title", "")), str(v.get("expect", "")), str(v.get("link", "")))
            for k, v in (raw.get("places") or {}).items() if isinstance(v, dict)}


def validate_places(playbooks_dir, zim_ids, doc_ids, slugs, overlay_ids,
                    items_by_id=None, kiwix_check=None, doc_check=None) -> list[str]:
    """The schema, the sixteen kinds and every link in the guidance, the same way a playbook is checked."""
    from sos import content  # deferred: content calls this module

    folder = Path(playbooks_dir) / "map"
    path = folder / "places.yaml"
    if not path.exists():
        return []
    rel = "map/places.yaml"
    schema_path = folder / "schema.json"
    if not schema_path.exists():
        return [f"{schema_path}: missing schema.json"]
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # malformed YAML or unreadable file
        return [f"{rel}: cannot parse: {exc}".splitlines()[0]]
    validator = jsonschema.Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8")))
    errors = [f"{rel}: {'/'.join(str(p) for p in e.path) or 'file'}: {e.message}"
              for e in sorted(validator.iter_errors(raw), key=lambda e: [str(p) for p in e.path])]
    places = load_places(path)
    errors += [f"{rel}: places: '{k}' is missing" for k in KINDS if k not in places]
    for kind, place in places.items():
        # The paragraph almost always ends with a citation to its own `link`, so checking the link separately
        # would report the same broken target twice; only check it when the paragraph does not carry it.
        body = place.expect
        if f"]({place.link})" not in place.expect:
            body = f"{body}\n\n[{place.title}]({place.link})"
        errors += [e.replace(rel, f"{rel}: {kind}", 1)
                   for e in content._check_links(rel, body, zim_ids, doc_ids, slugs, overlay_ids)]
    return errors
