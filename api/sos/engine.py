"""The situation engine: one pure function from the model to the View that every screen reads.

`compute(model, rules)` takes the conditions, the scenario clock, the household, the stock, the home and the time,
and returns the View: effective conditions, inferred proposals, a forecast with due times, the task list, what to
read, the interface modes, the readiness score and the next radio bulletin. No I/O, no clock of its own, no
randomness: the same model and the same rules always give the same View, which is what makes it testable."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo

from sos import conditions as cond
from sos import sun
from sos.rules import Rule, Rules, parse_duration

BUCKETS = ("now", "hour", "today", "week")
PHASE_TITLES = {"right-now": "Right now", "first-72-hours": "First 72 hours", "first-month": "First month",
                "long-term": "Long term"}
LINK_KINDS = {"playbook": "playbook", "module": "module", "page": "page", "card": "card", "doc": "doc", "map": "map",
              "kiwix": "kiwix"}
DEFAULT_MODES = {"theme": None, "dim": False, "calls": "shown", "map_first": False, "board": False}
DEFAULT_HOME: dict[str, Any] = {"lat": None, "lon": None, "label": "Home", "flood_zone": None}
FALLBACK_LATLON = (54.0, -2.0)               # the middle of the country until the house is set on the map
STOCK_TARGETS = (("water", "Water", 3.0, 15), ("food", "Food", 7.0, 15), ("medicine", "Medicine", 14.0, 10))
DRILL_FRESH = timedelta(days=183)            # a drill counts as practice for six months
WINTER_MONTHS = {11, 12, 1, 2, 3}
SUMMER_MONTHS = {5, 6, 7, 8, 9}
_SLUG = re.compile(r"[^a-z0-9]+")
_SPLIT_NEEDS = re.compile(r"[,;/]| and ")


def _slug(text: str) -> str:
    return _SLUG.sub("-", (text or "").lower()).strip("-") or "x"


@dataclass
class Model:
    """Everything the engine is allowed to know. Built from the database by the router, or by hand in a test."""
    now: datetime
    conditions: dict[str, cond.Condition] = field(default_factory=dict)
    scenario: Optional[dict] = None                       # {slug, title, started_at, elapsed_s, phase}
    household: tuple[dict, ...] = ()
    neighbours: tuple[dict, ...] = ()                     # the street list: name, address, needs, skills, contacts
    stock: tuple[dict, ...] = ()                          # rows with category and days_left
    home: dict = field(default_factory=lambda: dict(DEFAULT_HOME))
    drill: bool = False
    checklist: tuple[dict, ...] = ()                      # {id, text} for the active scenario
    checklist_state: dict[str, bool] = field(default_factory=dict)
    task_state: dict[str, dict] = field(default_factory=dict)
    detected: dict[str, dict] = field(default_factory=dict)   # condition id -> {state, at, confidence, sensor}
    titles: dict[str, str] = field(default_factory=dict)      # content link -> title, for the briefing
    meeting_point: bool = False
    last_drill_at: Optional[str] = None
    tz: str = "Europe/London"

    def __post_init__(self) -> None:
        if self.now.tzinfo is None:
            self.now = self.now.replace(tzinfo=timezone.utc)
        self.conditions = {cid: self.conditions.get(cid) or cond.Condition(cid) for cid in cond.IDS}
        self.home = {**DEFAULT_HOME, **(self.home or {})}

    @property
    def people(self) -> int:
        return max(1, len(self.household))

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


# --- household and stock ------------------------------------------------------------------------------------

def need_words(person: dict) -> list[str]:
    text = f"{person.get('needs') or ''}, {person.get('medications') or ''}"
    return [w.strip().lower() for w in _SPLIT_NEEDS.split(text) if w.strip()]


def matches_needs(terms: tuple[str, ...], words: list[str]) -> bool:
    """`any` is everyone on the list, `*` is anyone with something recorded, otherwise a substring of a need."""
    if not terms:
        return False
    if "any" in terms:
        return True
    if "*" in terms and words:
        return True
    return any(term in word for term in terms if term not in ("*", "any") for word in words)


def register(rule: Rule, model: Model) -> tuple[dict, ...]:
    return model.neighbours if rule.who == "neighbours" else model.household


def people_for(rule: Rule, model: Model) -> list[dict]:
    """The people a `needs:` rule is about, from the household register or the street list (`who: neighbours`)."""
    return [person for person in register(rule, model) if matches_needs(rule.need_terms, need_words(person))]


class _Fields(dict):
    """Whatever a rule's title asks for; anything the register has not got is simply left out."""

    def __missing__(self, key: str) -> str:
        return ""


def fill(text: str, person: dict) -> str:
    """`{name}`, `{address}` and `{at_address}` (which disappears when nobody wrote the address down)."""
    address = str(person.get("address") or "").strip()
    return str(text).format_map(_Fields({**person, "name": person.get("name", ""), "address": address,
                                         "at_address": f" at {address}" if address else ""}))


def stock_matches(rule: Rule, model: Model) -> bool:
    predicate = rule.stock or {}
    if not predicate:
        return True
    items = [i for i in model.stock if i.get("category") == predicate.get("category")]
    if predicate.get("missing"):
        return not items
    if "days_lt" in predicate:
        if not items:
            return True                       # nothing at all is certainly less than the target
        days = sum(float(i.get("days_left") or 0.0) for i in items)
        return days < float(predicate["days_lt"])
    return bool(items)


def stock_days(model: Model, category: str) -> float:
    return sum(float(i.get("days_left") or 0.0) for i in model.stock if i.get("category") == category)


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
        if not matches(rule.when, states, model, dark) or not stock_matches(rule, model):
            continue
        since = trigger_since(rule.when, model, states)
        due_at = since + rule.after_td
        base = {"due_at": due_at.isoformat(), "severity": rule.severity, "why": rule.why, "link": rule.link,
                "passed": due_at <= model.now, "rule": rule.id}
        if rule.need_terms:
            for person in people_for(rule, model):
                items.append({"id": f"{rule.id}:{_slug(person['name'])}",
                              "title": fill(rule.title, person), **base})
        else:
            items.append({"id": rule.id, "title": rule.title, **base})
    items.sort(key=lambda i: (i["due_at"], i["title"]))
    return items


def _task(model: Model, task_id: str, title: str, bucket: str, why: str, link: Optional[str], source: str,
          done_from_checklist: Optional[bool] = None) -> dict:
    state = model.task_state.get(task_id) or {}
    done = bool(state.get("done")) if done_from_checklist is None else bool(done_from_checklist)
    return {"id": task_id, "title": title, "bucket": bucket, "why": why, "link": link,
            "person": state.get("person") or None, "done": done, "done_at": state.get("done_at"), "source": source}


def task_rule_applies(rule: Rule, model: Model, states: dict[str, str], dark: bool) -> bool:
    if not matches(rule.when, states, model, dark) or not stock_matches(rule, model):
        return False
    if rule.until and matches(rule.until, states, model, dark):
        return False
    return not (rule.after and trigger_since(rule.when, model, states) + rule.after_td > model.now)


def check_on(model: Model, rules: Rules, states: dict[str, str], dark: bool) -> list[dict]:
    """Who on the street to knock on, once each however many rules point at them, most urgent first."""
    out: list[dict] = []
    seen: set[str] = set()
    for rule in rules.tasks:
        if rule.who != "neighbours" or not task_rule_applies(rule, model, states, dark):
            continue
        for person in people_for(rule, model):
            task_id = f"neighbour:{_slug(person.get('name', ''))}"
            if task_id in seen:
                continue
            seen.add(task_id)
            state = model.task_state.get(task_id) or {}
            out.append({"id": task_id, "name": person.get("name", ""), "address": person.get("address") or "",
                        "needs": person.get("needs") or "", "contacts": person.get("contacts") or "",
                        "title": fill(rule.title, person), "why": rule.why, "rule": rule.id, "link": rule.link,
                        "bucket": rule.bucket, "done": bool(state.get("done"))})
    out.sort(key=lambda c: (BUCKETS.index(c["bucket"]) if c["bucket"] in BUCKETS else len(BUCKETS), c["name"]))
    return out


def neighbour_skills(model: Model, rules: Rules, states: dict[str, str], dark: bool) -> list[dict]:
    """"Mrs Khan is a nurse": what the street can do, from the reading rules that ask for a skill."""
    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for rule in rules.readings:
        if not rule.skill_terms or not matches(rule.when, states, model, dark):
            continue
        for person in model.neighbours:
            words = [w.strip().lower() for w in _SPLIT_NEEDS.split(person.get("skills") or "") if w.strip()]
            for term in rule.skill_terms:
                key = (person.get("name", ""), term)
                if key in seen or not any(term in word for word in words):
                    continue
                seen.add(key)
                article = "an" if term[:1] in "aeiou" else "a"
                template = rule.title or "{name} is {article} {skill}"
                out.append({"name": person.get("name", ""), "address": person.get("address") or "", "skill": term,
                            "text": fill(template, {**person, "skill": term, "article": article}),
                            "contacts": person.get("contacts") or "", "why": rule.why, "rule": rule.id,
                            "link": rule.link})
    return out


def tasks(model: Model, rules: Rules, states: dict[str, str], dark: bool) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()

    def add(task: dict) -> None:
        if task["id"] not in seen:
            seen.add(task["id"])
            out.append(task)

    for rule in rules.tasks:
        if rule.who == "neighbours" or not task_rule_applies(rule, model, states, dark):
            continue
        if rule.need_terms:
            for person in people_for(rule, model):
                add(_task(model, f"{rule.id}:{_slug(person['name'])}", fill(rule.title, person),
                          rule.bucket, rule.why, rule.link, f"rule:{rule.id}"))
        else:
            add(_task(model, rule.id, rule.title, rule.bucket, rule.why, rule.link, f"rule:{rule.id}"))
    for entry in check_on(model, rules, states, dark):
        add(_task(model, entry["id"], entry["title"], entry["bucket"], entry["why"], entry["link"],
                  f"rule:{entry['rule']}"))
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
    return out


def readiness(model: Model, rules: Rules) -> dict:
    """Spec section 7: 40 points stock, 30 household coverage, 20 plan, 10 practice."""
    score = 0
    gaps: list[dict] = []
    for category, label, target, points in STOCK_TARGETS:
        days = stock_days(model, category)
        got = int(round(points * min(1.0, days / target)))
        score += got
        if got < points:
            people = "1 person" if model.people == 1 else f"{model.people} people"
            gaps.append({"title": f"{label}: {days:g} days for {people}", "link": "/plan#stock", "points": points - got})
    watched = [t for r in rules.all if r.who == "household" for t in r.need_terms if t not in ("*", "any")]
    with_needs = [p for p in model.household if need_words(p)]
    if not with_needs:
        score += 30
    else:
        rule_points = stock_points = 0.0
        for person in with_needs:
            words = need_words(person)
            covered_by_rule = any(term in word for term in watched for word in words)
            covered_by_stock = any(any(word in f"{i.get('name', '')} {i.get('notes', '')}".lower() for word in words)
                                   for i in model.stock)
            rule_points += 15 / len(with_needs) if covered_by_rule else 0
            stock_points += 15 / len(with_needs) if covered_by_stock else 0
            if not covered_by_stock:
                gaps.append({"title": f"Nothing in the stock list covers {person['name']}'s {words[0]}",
                             "link": "/plan#stock", "points": int(round(15 / len(with_needs)))})
            if not covered_by_rule:
                gaps.append({"title": f"No rule watches {person['name']}'s {words[0]}", "link": "/plan#household",
                             "points": int(round(15 / len(with_needs)))})
        score += int(round(rule_points + stock_points))
    if model.home.get("lat") is not None and model.home.get("lon") is not None:
        score += 8
    else:
        gaps.append({"title": "Home is not set on the map", "link": "/map", "points": 8})
    if any((p.get("contacts") or "").strip() for p in model.household):
        score += 6
    else:
        gaps.append({"title": "No contact numbers in the household register", "link": "/plan#household", "points": 6})
    if model.meeting_point:
        score += 6
    else:
        gaps.append({"title": "No meeting point written down", "link": "/plan", "points": 6})
    last = cond.parse_iso(model.last_drill_at)
    if last is not None and model.now - last <= DRILL_FRESH:
        score += 10
    else:
        gaps.append({"title": "No drill in the last six months", "link": "/situation", "points": 10})
    gaps.sort(key=lambda g: (-g["points"], g["title"]))
    return {"score": max(0, min(100, score)), "gaps": gaps}


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
        "neighbours": {"check_on": check_on(model, rules, states, dark),
                       "skills": neighbour_skills(model, rules, states, dark)},
        "briefing": briefing(model, rules, states, dark),
        "modes": modes(model, rules, states, dark),
        "readiness": readiness(model, rules),
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
    neighbours = view.get("neighbours") or {}
    if neighbours.get("check_on") or neighbours.get("skills"):
        lines += ["## Neighbours", ""]
        for item in neighbours.get("check_on") or []:
            contacts = f" — {item['contacts']}" if item.get("contacts") else ""
            lines.append(f"- [{'x' if item['done'] else ' '}] {item['title']}"
                         + (f" ({item['needs']})" if item.get("needs") else "") + contacts)
        for item in neighbours.get("skills") or []:
            where = f" at {item['address']}" if item.get("address") else ""
            contacts = f" — {item['contacts']}" if item.get("contacts") else ""
            lines.append(f"- {item['text']}{where}{contacts}")
        lines.append("")
    if view["briefing"]:
        lines += ["## Read", ""] + [f"- {b['title']} ({b['kind']} {b['ref']})" for b in view["briefing"]] + [""]
    lines += [f"Readiness {view['readiness']['score']} of 100.", ""]
    events = list(events)
    if events:
        lines += ["## Log", ""] + [f"- {e.get('updated_at')}: {e.get('title')}" for e in events] + [""]
    return "\n".join(lines).rstrip() + "\n"
