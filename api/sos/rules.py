"""The situation rules: `playbooks/rules/*.yaml`, validated against `playbooks/rules/schema.json`.

Rules are pure data. Each one says when it applies (`when`), what follows (an implication, a consequence, a task,
an interface mode or something to read), why, and where the timing or advice comes from (`source`, a content link).
The loader caches by file mtime so the box parses them once and the engine stays a pure function of the model."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any, Iterable

import jsonschema
import yaml

KINDS = ("implication", "consequence", "task", "mode", "reading")
BUCKETS = ("now", "hour", "today", "week")
_DURATION_UNITS = {"m": 60, "h": 3600, "d": 86400}
_FIELDS = ("expect", "confidence", "title", "after", "severity", "link", "needs", "skills", "who", "stock", "bucket",
           "until", "set", "open")
WHO = ("household", "neighbours")


class RulesError(ValueError):
    """A rules file that will not load: bad YAML, a schema violation or a duplicate id."""


def parse_duration(text: str) -> timedelta:
    """`30m`, `4h`, `2d` (and `1.5h`) to a timedelta."""
    value = str(text).strip()
    if len(value) < 2 or value[-1] not in _DURATION_UNITS:
        raise RulesError(f"bad duration {text!r}: use minutes, hours or days, such as 30m, 4h or 2d")
    try:
        amount = float(value[:-1])
    except ValueError:
        raise RulesError(f"bad duration {text!r}: use minutes, hours or days, such as 30m, 4h or 2d") from None
    if amount < 0:
        raise RulesError(f"bad duration {text!r}: cannot be negative")
    return timedelta(seconds=amount * _DURATION_UNITS[value[-1]])


@dataclass(frozen=True)
class Rule:
    id: str
    kind: str
    when: dict
    source: str
    why: str = ""
    file: str = ""
    expect: dict | None = None
    confidence: float = 1.0
    title: str = ""
    after: str | None = None
    severity: str = "info"
    link: str | None = None
    needs: str | tuple[str, ...] | None = None
    skills: str | tuple[str, ...] | None = None
    who: str = "household"
    stock: dict | None = None
    bucket: str | None = None
    until: dict | None = None
    set: dict = field(default_factory=dict)
    open: tuple[str, ...] = ()

    @property
    def after_td(self) -> timedelta:
        return parse_duration(self.after) if self.after else timedelta(0)

    @property
    def need_terms(self) -> tuple[str, ...]:
        """The `needs:` terms, always a tuple: `*` means anyone with something recorded, `any` means everybody."""
        return _terms(self.needs)

    @property
    def skill_terms(self) -> tuple[str, ...]:
        return _terms(self.skills)

    @property
    def where(self) -> str:
        return str((self.expect or {}).get("where", ""))

    def links(self) -> list[str]:
        """Every content link the rule names, for validation."""
        return [x for x in [self.source, self.link, *self.open] if x]


@dataclass(frozen=True)
class Rules:
    by_kind: dict[str, tuple[Rule, ...]]
    bulletins: tuple[dict, ...] = ()
    files: tuple[str, ...] = ()

    @property
    def implications(self) -> tuple[Rule, ...]:
        return self.by_kind.get("implication", ())

    @property
    def consequences(self) -> tuple[Rule, ...]:
        return self.by_kind.get("consequence", ())

    @property
    def tasks(self) -> tuple[Rule, ...]:
        return self.by_kind.get("task", ())

    @property
    def modes(self) -> tuple[Rule, ...]:
        return self.by_kind.get("mode", ())

    @property
    def readings(self) -> tuple[Rule, ...]:
        return self.by_kind.get("reading", ())

    @property
    def all(self) -> tuple[Rule, ...]:
        return tuple(r for kind in KINDS for r in self.by_kind.get(kind, ()))

    def get(self, rule_id: str) -> Rule | None:
        return next((r for r in self.all if r.id == rule_id), None)


def _terms(value) -> tuple[str, ...]:
    """`needs` and `skills` take one term or a list of them; either way the engine sees a tuple of lower-case words."""
    if value is None:
        return ()
    items = value if isinstance(value, (list, tuple)) else [value]
    return tuple(str(x).strip().lower() for x in items if str(x).strip())


def _rule_from(raw: dict, filename: str) -> Rule:
    kwargs: dict[str, Any] = {k: raw[k] for k in _FIELDS if k in raw}
    for key in ("open", "needs", "skills"):
        if isinstance(kwargs.get(key), list):
            kwargs[key] = tuple(kwargs[key])
    return Rule(id=raw["id"], kind=raw["kind"], when=dict(raw.get("when") or {}), source=raw["source"],
                why=str(raw.get("why", "")), file=filename, **kwargs)


def _sub_validator(schema: dict, name: str) -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator({"$ref": f"#/$defs/{name}", "$defs": schema["$defs"]})


def _validate(raw: dict, filename: str, schema: dict, errors: list[str]) -> None:
    for key in ("rules", "bulletins"):
        if key in raw and not isinstance(raw[key], list):
            errors.append(f"{filename}: {key}: must be a list")
            return
    if "rules" not in raw:
        errors.append(f"{filename}: file: 'rules' is a required property")
        return
    rule_validator = _sub_validator(schema, "rule")
    for index, item in enumerate(raw["rules"]):
        where = f"rule '{item['id']}'" if isinstance(item, dict) and isinstance(item.get("id"), str) else f"rule {index}"
        for err in sorted(rule_validator.iter_errors(item), key=lambda e: list(e.path)):
            path = "/".join(str(p) for p in err.path)
            errors.append(f"{filename}: {where}: {path + ': ' if path else ''}{err.message}")
        if isinstance(item, dict) and not str(item.get("why", "")).strip():
            errors.append(f"{filename}: {where}: every rule needs a 'why'")
    bulletin_validator = _sub_validator(schema, "bulletin")
    for index, item in enumerate(raw.get("bulletins") or []):
        for err in sorted(bulletin_validator.iter_errors(item), key=lambda e: list(e.path)):
            path = "/".join(str(p) for p in err.path)
            errors.append(f"{filename}: bulletin {index}: {path + ': ' if path else ''}{err.message}")


def load_file(path: Path, schema: dict) -> tuple[list[Rule], list[dict], list[str]]:
    path = Path(path)
    errors: list[str] = []
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return [], [], [f"{path.name}: cannot parse: {str(exc).splitlines()[0]}"]
    if not isinstance(raw, dict):
        return [], [], [f"{path.name}: file must be a mapping with a 'rules' list"]
    _validate(raw, path.name, schema, errors)
    if errors:
        return [], [], errors
    rules = [_rule_from(item, path.name) for item in raw.get("rules") or []]
    return rules, list(raw.get("bulletins") or []), errors


def load(directory: Path) -> Rules:
    """Every `*.yaml` in the rules directory, validated and cached by mtime."""
    directory = Path(directory)
    signature = tuple(sorted((p.name, p.stat().st_mtime, p.stat().st_size) for p in directory.glob("*.yaml")))
    cached = _CACHE.get(directory)
    if cached is not None and cached[0] == signature:
        return cached[1]
    schema_path = directory / "schema.json"
    if not schema_path.is_file():
        raise RulesError(f"{schema_path}: missing schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    by_kind: dict[str, list[Rule]] = {k: [] for k in KINDS}
    bulletins: list[dict] = []
    errors: list[str] = []
    seen: dict[str, str] = {}
    files: list[str] = []
    for path in sorted(directory.glob("*.yaml")):
        files.append(path.name)
        rules, file_bulletins, file_errors = load_file(path, schema)
        errors += file_errors
        bulletins += file_bulletins
        for rule in rules:
            if rule.id in seen:
                errors.append(f"{path.name}: rule '{rule.id}': duplicate id (also in {seen[rule.id]})")
                continue
            seen[rule.id] = path.name
            by_kind[rule.kind].append(rule)
    if errors:
        raise RulesError("\n".join(errors))
    loaded = Rules(by_kind={k: tuple(v) for k, v in by_kind.items()}, bulletins=tuple(bulletins), files=tuple(files))
    _CACHE[directory] = (signature, loaded)
    return loaded


def counts(rules: Rules) -> dict[str, int]:
    return {kind: len(rules.by_kind.get(kind, ())) for kind in KINDS} | {"bulletins": len(rules.bulletins)}


def link_targets(links: Iterable[str]) -> list[tuple[str, str]]:
    """(scheme, rest) for each content link, with the fragment stripped."""
    out = []
    for link in links:
        scheme, _, rest = link.partition(":")
        out.append((scheme, rest.partition("#")[0]))
    return out


_CACHE: dict[Path, tuple[tuple, Rules]] = {}
