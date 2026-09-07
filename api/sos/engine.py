"""The situation engine: one pure function from the model to the View that every screen reads.

`compute(model, rules)` takes the conditions, the scenario clock, the home and the time, and returns the View:
effective conditions, inferred proposals, a forecast with due times, the task list, what to read, the interface
modes and the next radio bulletin. No I/O, no clock of its own, no randomness: the same model and the same rules
always give the same View, which is what makes it testable.

It knows nothing about who lives in the house: there is no register to read, so every line it writes is written
for anybody (no-setup spec)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo

from sos import conditions as cond
from sos import sun
from sos.rules import Rule, Rules, parse_duration
from sos.system import THEMES

BUCKETS = ("now", "hour", "today", "week")
PHASE_TITLES = {"right-now": "Right now", "first-72-hours": "First 72 hours", "first-month": "First month",
                "long-term": "Long term"}
LINK_KINDS = {"playbook": "playbook", "module": "module", "page": "page", "card": "card", "doc": "doc", "map": "map",
              "kiwix": "kiwix"}
DEFAULT_MODES = {"theme": None, "dim": False, "calls": "shown", "map_first": False, "board": False}
DEFAULT_HOME: dict[str, Any] = {"lat": None, "lon": None, "label": "Home", "flood_zone": None}
FALLBACK_LATLON = (54.0, -2.0)               # the middle of the country until the house is set on the map
WINTER_MONTHS = {11, 12, 1, 2, 3}
SUMMER_MONTHS = {5, 6, 7, 8, 9}


@dataclass
class Model:
    """Everything the engine is allowed to know. Built from the database by the router, or by hand in a test."""
    now: datetime
    conditions: dict[str, cond.Condition] = field(default_factory=dict)
    scenario: Optional[dict] = None                       # {slug, title, started_at, elapsed_s, phase}
    home: dict = field(default_factory=lambda: dict(DEFAULT_HOME))
    drill: bool = False
    checklist: tuple[dict, ...] = ()                      # {id, text} for the active scenario
    checklist_state: dict[str, bool] = field(default_factory=dict)
    kits: tuple[dict, ...] = ()                           # {slug, title, relevant, basic_done, basic_total}
    task_state: dict[str, dict] = field(default_factory=dict)
    detected: dict[str, dict] = field(default_factory=dict)   # condition id -> {state, at, confidence, sensor}
    titles: dict[str, str] = field(default_factory=dict)      # content link -> title, for the briefing
    tz: str = "Europe/London"

    def __post_init__(self) -> None:
        if self.now.tzinfo is None:
            self.now = self.now.replace(tzinfo=timezone.utc)
        self.conditions = {cid: self.conditions.get(cid) or cond.Condition(cid) for cid in cond.IDS}
        self.home = {**DEFAULT_HOME, **(self.home or {})}

    @property
    def latlon(self) -> tuple[float, float]:
        lat, lon = self.home.get("lat"), self.home.get("lon")
        return (float(lat), float(lon)) if lat is not None and lon is not None else FALLBACK_LATLON


# --- matching -----------------------------------------------------------------------------------------------

def phones_state(states: dict[str, str]) -> str:
    """`working` while any phone route is up (a degraded mobile still reaches 999), `off` when neither is."""
    return "off" if states.get("mobile") == "off" and states.get("landline") == "off" else "working"


def _season(now: datetime) -> str:
    return "winter" if now.month in WINTER_MONTHS else ("summer" if now.month in SUMMER_MONTHS else "")


def matches(clause: dict, states: dict[str, str], model: Model, dark: bool) -> bool:
    """Every key in a `when` (or `until`) must hold. An empty clause always holds."""
    for key, value in (clause or {}).items():
        if key in cond.IDS:
            wanted = value if isinstance(value, list) else [value]
            if states.get(key) not in wanted:
                return False
        elif key == "phones":
            if phones_state(states) != value:
                return False
        elif key == "scenario":
            slug = (model.scenario or {}).get("slug")
            if value == "any":
                if slug is None:
                    return False
            elif slug != value:
                return False
        elif key == "dark":
            if bool(value) != dark:
                return False
        elif key == "drill":
            if bool(value) != bool(model.drill):
                return False
        elif key == "season":
            if _season(model.now) != value:
                return False
        else:
            return False
    return True


def trigger_since(clause: dict, model: Model, states: dict[str, str]) -> datetime:
    """When the situation the rule is about began: the most recent `since` among the conditions it names."""
    candidates: list[datetime] = []
    for key, value in (clause or {}).items():
        ids = [key] if key in cond.IDS else (["mobile", "landline"] if key == "phones" else [])
        for cid in ids:
            since = cond.parse_iso(model.conditions[cid].since)
            if since is not None and states.get(cid) != "working":
                candidates.append(since)
        if key == "scenario" and model.scenario:
            started = cond.parse_iso(model.scenario.get("started_at"))
            if started is not None:
                candidates.append(started)
    return max(candidates) if candidates else model.now


# --- the parts of the View ----------------------------------------------------------------------------------

def effective_states(model: Model) -> dict[str, str]:
    """Manual beats detected beats inferred. A detected reading never overrides a hand-set state."""
    states = {}
    for cid, condition in model.conditions.items():
        reading = model.detected.get(cid)
        if reading and condition.source != "manual":
            states[cid] = reading["state"]
        else:
            states[cid] = condition.state
    return states


def condition_view(model: Model, states: dict[str, str]) -> dict[str, dict]:
    out = {}
    for cid, condition in model.conditions.items():
        item = condition.as_dict()
        item["state"] = states[cid]
        item["stale"] = cond.is_stale(condition, model.now)
        if states[cid] == condition.state:
            item["for_s"] = cond.duration_s(condition, model.now)
        else:                                              # a sensor reading is standing in for the stored row
            at = cond.parse_iso((model.detected.get(cid) or {}).get("at")) or model.now
            item["for_s"] = 0 if states[cid] == "working" else max(0, int((model.now - at).total_seconds()))
            item["since"] = at.isoformat() if states[cid] != "working" else None
            item["source"] = "detected"
        out[cid] = item
    return out


def inferred(model: Model, rules: Rules, states: dict[str, str], dark: bool) -> list[dict]:
    """Proposals: what the implications say has probably happened, and what the sensors have noticed."""
    out: list[dict] = []
    for rule in rules.implications:
        if not matches(rule.when, states, model, dark):
            continue
        target = rule.expect["condition"]
        wanted = rule.expect["state"]
        current = states.get(target)
        if current == wanted or (wanted == "degraded" and current == "off") or current is None:
            continue
        due_at = trigger_since(rule.when, model, states) + parse_duration(rule.expect["after"])
        if due_at > model.now:
            continue
        why = rule.why + (f" Applies to {rule.where}." if rule.where else "")
        out.append({"condition": target, "state": wanted, "confidence": rule.confidence,
                    "due_at": due_at.isoformat(), "why": why, "rule": rule.id, "source": rule.source})
    out = _strongest_per_condition(out)
    for cid, reading in sorted(model.detected.items()):
        condition = model.conditions[cid]
        newer = cond.parse_iso(reading.get("at")) or model.now
        updated = cond.parse_iso(condition.updated_at)
        if condition.source == "manual" and reading["state"] != condition.state and (updated is None or newer > updated):
            out.append({"condition": cid, "state": reading["state"], "confidence": float(reading.get("confidence", 0.6)),
                        "due_at": newer.isoformat(), "why": f"The box has detected this itself ({reading.get('sensor', 'sensor')}).",
                        "rule": f"sensor:{reading.get('sensor', cid)}", "source": "page:what-still-works"})
    return out


def _strongest_per_condition(proposals: list[dict]) -> list[dict]:
    """One proposal per condition: `off` beats `degraded`, then the one that came due first."""
    best: dict[str, dict] = {}
    for item in proposals:
        rank = (cond.STATES.index(item["state"]), item["due_at"])
        current = best.get(item["condition"])
        if current is None or rank > (cond.STATES.index(current["state"]), current["due_at"]):
            best[item["condition"]] = item
    return [item for item in proposals if best.get(item["condition"]) is item]


def forecast(model: Model, rules: Rules, states: dict[str, str], dark: bool) -> list[dict]:
    items: list[dict] = []
    for rule in rules.consequences:
        if not matches(rule.when, states, model, dark):
            continue
        since = trigger_since(rule.when, model, states)
        due_at = since + rule.after_td
        items.append({"id": rule.id, "title": rule.title, "due_at": due_at.isoformat(), "severity": rule.severity,
                      "why": rule.why, "link": rule.link, "passed": due_at <= model.now, "rule": rule.id})
    items.sort(key=lambda i: (i["due_at"], i["title"]))
    return items


def _task(model: Model, task_id: str, title: str, bucket: str, why: str, link: Optional[str], source: str,
          done_from_checklist: Optional[bool] = None) -> dict:
    state = model.task_state.get(task_id) or {}
    done = bool(state.get("done")) if done_from_checklist is None else bool(done_from_checklist)
    return {"id": task_id, "title": title, "bucket": bucket, "why": why, "link": link,
            "person": state.get("person") or None, "done": done, "done_at": state.get("done_at"), "source": source}


def task_rule_applies(rule: Rule, model: Model, states: dict[str, str], dark: bool) -> bool:
    if not matches(rule.when, states, model, dark):
        return False
    if rule.until and matches(rule.until, states, model, dark):
        return False
    return not (rule.after and trigger_since(rule.when, model, states) + rule.after_td > model.now)


def tasks(model: Model, rules: Rules, states: dict[str, str], dark: bool) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()

    def add(task: dict) -> None:
        if task["id"] not in seen:
            seen.add(task["id"])
            out.append(task)

    for rule in rules.tasks:
        if not task_rule_applies(rule, model, states, dark):
            continue
        add(_task(model, rule.id, rule.title, rule.bucket, rule.why, rule.link, f"rule:{rule.id}"))
    if model.scenario:
        slug = model.scenario["slug"]
        title = model.scenario.get("title") or slug
        for item in model.checklist:
            add(_task(model, f"checklist:{slug}/{item['id']}", item["text"], "today",
                      f"On the {title} checklist.", f"playbook:{slug}#checklist", f"checklist:{slug}",
                      done_from_checklist=bool(model.checklist_state.get(item["id"]))))
    out.sort(key=lambda t: (BUCKETS.index(t["bucket"]) if t["bucket"] in BUCKETS else len(BUCKETS), t["title"]))
    return out


def _briefing_entry(model: Model, link: str) -> dict:
    scheme, _, rest = link.partition(":")
    slug, hash_, fragment = rest.partition("#")
    kind = LINK_KINDS.get(scheme, scheme)
    if scheme == "playbook" and fragment:
        kind = "playbook-section"
    title = model.titles.get(link) or model.titles.get(f"{scheme}:{slug}")
    if not title and scheme == "map":
        title = "The map"
    if not title:
        title = PHASE_TITLES.get(fragment) if fragment else None
    if not title:
        title = slug.replace("-", " ").capitalize() if slug else "The map"
    return {"title": title, "kind": kind, "ref": rest if scheme != "map" else rest.lstrip("?")}


def briefing(model: Model, rules: Rules, states: dict[str, str], dark: bool) -> list[dict]:
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add(entry: dict) -> None:
        key = (entry["kind"], entry["ref"])
        if key not in seen:
            seen.add(key)
            out.append(entry)

    if model.scenario:
        slug, phase = model.scenario["slug"], model.scenario.get("phase") or "right-now"
        add({"title": PHASE_TITLES.get(phase, phase), "kind": "playbook-section", "ref": f"{slug}#{phase}"})
    for rule in rules.readings:
        if matches(rule.when, states, model, dark):
            for link in rule.open:
                add(_briefing_entry(model, link))
    return out


def modes(model: Model, rules: Rules, states: dict[str, str], dark: bool) -> dict:
    out = dict(DEFAULT_MODES)
    for rule in rules.modes:
        if matches(rule.when, states, model, dark):
            out.update(rule.set or {})
    # A rules file written for the three-theme box still says `theme: vault`, and rules are content:
    # they travel on a stick and outlive the build that reads them. A theme the box has no palette
    # for, stamped on <html>, is a document with no colours at all — so it is no theme, and the
    # reader keeps whichever of the two they were on.
    if out.get("theme") not in THEMES:
        out["theme"] = None
    return out


def next_bulletin(model: Model, rules: Rules) -> dict:
    """The next scheduled bulletin today or tomorrow, in the box's local zone."""
    try:
        zone = ZoneInfo(model.tz)
    except Exception:                                     # an unknown zone on a fresh box: fall back to UTC
        zone = timezone.utc
    local_now = model.now.astimezone(zone)
    best: Optional[tuple[datetime, dict]] = None
    for bulletin in rules.bulletins:
        for text in bulletin.get("times") or []:
            hour, minute = (int(x) for x in text.split(":"))
            for day in (0, 1):
                naive = (local_now + timedelta(days=day)).replace(hour=hour, minute=minute, second=0, microsecond=0)
                at = naive.astimezone(timezone.utc)
                if at <= model.now:
                    continue
                if best is None or at < best[0] or (at == best[0] and bulletin["station"] < best[1]["station"]):
                    best = (at, bulletin)
    if best is None:
        return {"next": None}
    at, bulletin = best
    return {"next": {"station": bulletin["station"], "frequency": bulletin.get("frequency", ""),
                     "at": at.isoformat(), "note": bulletin.get("note", "")}}


def compute(model: Model, rules: Rules) -> dict:
    """The View: everything a screen needs, from one model and one set of rules."""
    lat, lon = model.latlon
    sunrise, sunset = sun.sun_times(lat, lon, model.now)
    sunrise = sunrise.replace(microsecond=0) if sunrise else None
    sunset = sunset.replace(microsecond=0) if sunset else None
    dark = sun.is_dark(lat, lon, model.now)
    states = effective_states(model)
    return {
        "meta": {"now": model.now.isoformat(), "dark": dark,
                 "sunrise": sunrise.isoformat() if sunrise else None,
                 "sunset": sunset.isoformat() if sunset else None,
                 "home": dict(model.home), "drill": bool(model.drill)},
        "scenario": dict(model.scenario) if model.scenario else None,
        "conditions": condition_view(model, states),
        "inferred": inferred(model, rules, states, dark),
        "forecast": forecast(model, rules, states, dark),
        "tasks": tasks(model, rules, states, dark),
        "briefing": briefing(model, rules, states, dark),
        "modes": modes(model, rules, states, dark),
        "bulletins": next_bulletin(model, rules),
    }


def flags_for(states: dict[str, str], scenario: Optional[str], dark: bool) -> dict[str, bool]:
    """The content directives' flag set: a service counts as working while it is not off."""
    out = {cid: states.get(cid, "working") != "off" for cid in cond.IDS}
    out["phones"] = out["mobile"] or out["landline"]
    out["dark"] = bool(dark)
    if scenario:
        out[f"scenario:{scenario}"] = True
    return out


def flags(view: dict) -> dict[str, bool]:
    """The flag set for a computed View."""
    return flags_for({cid: item["state"] for cid, item in view["conditions"].items()},
                     (view.get("scenario") or {}).get("slug"), view["meta"]["dark"])


def summary_line(view: dict) -> str:
    """One line for the log and the report: what is not working."""
    broken = [item["title"] for item in view["conditions"].values() if item["state"] != "working"]
    return ", ".join(broken) if broken else "Everything working"


def report(view: dict, events: Iterable[dict] = ()) -> str:
    """The printable hand-over: the situation, the forecast, the tasks and the log, as Markdown."""
    lines: list[str] = ["# Situation report", ""]
    meta, scenario = view["meta"], view.get("scenario")
    lines.append(f"Written {meta['now']}." + (" **This is a drill.**" if meta.get("drill") else ""))
    lines.append("")
    if scenario:
        hours = scenario.get("elapsed_s", 0) / 3600
        lines += [f"**{scenario.get('title') or scenario['slug']}**, started {scenario['started_at']} "
                  f"({hours:.1f} hours ago, phase: {scenario.get('phase')}).", ""]
    lines += ["## Conditions", ""]
    for item in view["conditions"].values():
        note = f" — {item['note']}" if item.get("note") else ""
        since = f" since {item['since']}" if item.get("since") else ""
        lines.append(f"- **{item['title']}**: {item['state']}{since} ({item['source']}){note}")
    if view["inferred"]:
        lines += ["", "## Probably also", ""]
        for item in view["inferred"]:
            lines.append(f"- {item['condition']} may be {item['state']} ({int(item['confidence'] * 100)}%): {item['why']}")
    if view["forecast"]:
        lines += ["", "## What is coming", ""]
        for item in view["forecast"]:
            lines.append(f"- {'PASSED' if item['passed'] else 'due'} {item['due_at']}: **{item['title']}** ({item['severity']}) — {item['why']}")
    lines += ["", "## Tasks", ""]
    for bucket in BUCKETS:
        rows = [t for t in view["tasks"] if t["bucket"] == bucket]
        if not rows:
            continue
        lines.append(f"### {bucket.capitalize()}")
        for task in rows:
            who = f" — {task['person']}" if task.get("person") else ""
            lines.append(f"- [{'x' if task['done'] else ' '}] {task['title']}{who}")
        lines.append("")
    if view["briefing"]:
        lines += ["## Read", ""] + [f"- {b['title']} ({b['kind']} {b['ref']})" for b in view["briefing"]] + [""]
    events = list(events)
    if events:
        lines += ["## Log", ""] + [f"- {e.get('updated_at')}: {e.get('title')}" for e in events] + [""]
    return "\n".join(lines).rstrip() + "\n"
