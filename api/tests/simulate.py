"""A random walk over the situation, to catch what fixed examples never will.

Hundreds of steps of conditions changing, scenarios starting and ending, drills, ticks and the clock moving on. After every step the View is computed twice and checked against the invariants the
whole app relies on, including the one that matters most: no rendered instruction ever tells someone to ring a
number that will not connect. Seeded, so a failure is reproducible:

    python -m tests.simulate --steps 2000 --seeds 5
    python -m tests.simulate --seed 1234 --steps 400
"""
from __future__ import annotations

import argparse
import random
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sos import conditions as cond
from sos import engine, rules as rules_mod

REPO = Path(__file__).resolve().parents[2]
RULES_DIR = REPO / "playbooks" / "rules"
PLAYBOOKS = REPO / "playbooks"
START = datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc)
SCENARIOS = ("grid-collapse", "storms-flooding", "severe-winter", "pandemic", "heat-drought")
PHASE_TITLES = ("National grid collapse", "Storms and flooding", "Severe winter", "Pandemic", "Heat and drought")
SEEDS = (1234, 7, 2026, 99, 31415, 8, 555, 271828, 42, 17)

# A number that will not connect, given as an instruction. The directives turn `[[call 999]]` into "999 will not
# connect while the phones are down", which names the number but tells nobody to ring it: that is the difference.
DEAD_NUMBERS = ("999", "112", "111", "105", "101")
BARE_CALL = re.compile(r"\b(?:call|calling|dial|dialling|ring|ringing|phone|telephone)\s+(?:the\s+|for\s+)?"
                       r"(" + "|".join(DEAD_NUMBERS) + r")\b", re.IGNORECASE)
ESCALATE = "Stop or escalate"


def _scenario(slug: str, started: datetime, now: datetime) -> dict:
    from sos.situation import phase_for

    elapsed = max(0.0, (now - started).total_seconds())
    return {"slug": slug, "title": PHASE_TITLES[SCENARIOS.index(slug)], "started_at": started.isoformat(),
            "elapsed_s": int(elapsed), "phase": phase_for(elapsed)}


# --- the content invariant ------------------------------------------------------------------------------------

def _content_cache():
    from sos.content import ContentCache

    return ContentCache(PLAYBOOKS)


def _card_slugs() -> tuple[str, ...]:
    return tuple(sorted(p.stem for p in (PLAYBOOKS / "cards").glob("*.md")))


def _escalate_html(html: str) -> str:
    """The part of a quick card after its "Stop or escalate" heading: the last thing anyone reads."""
    start = html.find(ESCALATE)
    if start < 0:
        return ""
    rest = html[start + len(ESCALATE):]
    end = rest.find("<h2")
    return rest if end < 0 else rest[:end]


def check_content(view: dict, cache, cards: tuple[str, ...], seen: set, where: str) -> int:
    """With both phone routes down, nothing rendered may tell anyone to ring a number that will not connect."""
    states = {cid: item["state"] for cid, item in view["conditions"].items()}
    if engine.phones_state(states) != "off":
        return 0
    flags = engine.flags(view)
    slug = (view.get("scenario") or {}).get("slug")
    key = (slug, tuple(sorted(flags.items())))
    if key in seen:
        return 0
    seen.add(key)
    checked = 0
    pieces: list[tuple[str, str]] = []
    if slug:
        rendered = cache.rendered("scenario", slug, flags)
        if rendered is not None:
            section = next((s for s in rendered.sections if s["id"] == "right-now"), None)
            if section:
                pieces.append((f"scenario {slug} right-now", section["html"]))
    for card in cards:
        rendered = cache.rendered("card", card, flags)
        if rendered is not None:
            pieces.append((f"card {card} stop-or-escalate", _escalate_html(rendered.html)))
    for name, html in pieces:
        checked += 1
        found = BARE_CALL.search(html)
        assert found is None, f"{where}: {name} still says {found.group(0)!r} with both phone routes down"
    return checked


# --- the invariants -------------------------------------------------------------------------------------------

def _check(view: dict, model: engine.Model, ruleset: rules_mod.Rules, step: int) -> None:
    where = f"step {step}"
    assert set(view["conditions"]) == set(cond.IDS), where
    states = {cid: item["state"] for cid, item in view["conditions"].items()}
    dark = view["meta"]["dark"]

    for item in view["forecast"]:
        assert item["due_at"] and datetime.fromisoformat(item["due_at"]).tzinfo is not None, f"{where}: {item}"
        assert item["severity"] in ("info", "warn", "danger") and item["title"], f"{where}: {item}"

    ids = [t["id"] for t in view["tasks"]]
    assert len(ids) == len(set(ids)), f"{where}: duplicate task ids"
    for task in view["tasks"]:
        assert task["bucket"] in engine.BUCKETS, f"{where}: {task}"
        if task["source"].startswith("rule:"):
            rule = ruleset.get(task["source"][len("rule:"):])
            assert rule is not None, f"{where}: {task['source']} is not a rule"
            assert engine.matches(rule.when, states, model, dark), f"{where}: {task['id']} does not apply"
            if rule.until:
                assert not engine.matches(rule.until, states, model, dark), f"{where}: {task['id']} should have retired"

    proposed = [i["condition"] for i in view["inferred"]]
    assert len(proposed) == len(set(proposed)), f"{where}: two proposals for one condition"
    for item in view["inferred"]:
        assert 0 < item["confidence"] <= 1 and item["why"] and item["due_at"], f"{where}: {item}"

    for item in view["tasks"] + view["forecast"]:
        assert "{" not in item["title"], f"{where}: {item['title']!r} still has a name-shaped hole in it"

    if states["mobile"] == "off" and states["landline"] == "off":
        assert view["modes"]["calls"] == "hidden", f"{where}: numbers still on show with no phones"
    assert view["meta"]["now"] == model.now.isoformat(), where


def walk(seed: int = 1234, steps: int = 400, content: bool = True) -> dict:
    """Take the walk and return a small summary. Raises on the first broken invariant."""
    rng = random.Random(seed)
    ruleset = rules_mod.load(RULES_DIR)
    cache = _content_cache() if content else None
    cards = _card_slugs() if content else ()
    now = START
    conditions: dict[str, cond.Condition] = {cid: cond.Condition(cid) for cid in cond.IDS}
    scenario_slug: str | None = None
    scenario_started = now
    drill = False
    task_state: dict[str, dict] = {}
    seen_states: set[str] = set()
    tasks_seen: set[str] = set()
    forecast_seen: set[str] = set()
    modes_seen: set[str] = set()
    content_seen: set = set()
    rendered_checked = 0

    for step in range(steps):
        action = rng.choice(["condition", "condition", "condition", "clock", "clock", "scenario", "drill",
                             "task", "task"])
        if action == "condition":
            cid = rng.choice(cond.IDS)
            state = rng.choice(cond.STATES)
            since = None if state == "working" else (now - timedelta(minutes=rng.randint(0, 3000))).isoformat()
            conditions[cid] = cond.Condition(cid, state=state, since=since, source=rng.choice(["manual", "inferred"]),
                                             set_by=rng.choice(["kiosk", "phone"]), updated_at=now.isoformat(),
                                             confirmed_at=now.isoformat())
            seen_states.add(f"{cid}:{state}")
        elif action == "clock":
            now = now + timedelta(minutes=rng.choice([5, 30, 120, 480, 1440]))
        elif action == "scenario":
            if scenario_slug and rng.random() < 0.4:
                scenario_slug = None
            else:
                scenario_slug = rng.choice(SCENARIOS)
                scenario_started = now - timedelta(hours=rng.choice([0, 1, 20, 100, 800]))
        elif action == "drill":
            drill = not drill
        else:
            if task_ids := [t for t in task_state] or ["fill-bath", "boil-water", "meeting-point"]:
                task_state[rng.choice(task_ids)] = {"done": rng.random() < 0.5, "done_at": now.isoformat(),
                                                    "person": rng.choice([None, "Sam", "Ali"])}

        model = engine.Model(
            now=now, conditions=dict(conditions),
            scenario=_scenario(scenario_slug, scenario_started, now) if scenario_slug else None,
            home={"lat": 50.93, "lon": -1.43, "label": "Home", "flood_zone": "3"}, drill=drill,
            checklist=({"id": "one", "text": "The first thing"}, {"id": "two", "text": "The second thing"})
            if scenario_slug else (),
            checklist_state={"one": rng.random() < 0.5}, task_state=dict(task_state),
        )
        view = engine.compute(model, ruleset)
        assert engine.compute(model, ruleset) == view, f"step {step}: the same model gave two different Views"
        _check(view, model, ruleset, step)
        if cache is not None:
            rendered_checked += check_content(view, cache, cards, content_seen, f"step {step}")
        tasks_seen.update(t["id"] for t in view["tasks"])
        forecast_seen.update(f["id"] for f in view["forecast"])
        modes_seen.add(repr(sorted(view["modes"].items())))
        engine.report(view)                                    # the report must survive every situation too

    return {"seed": seed, "steps": steps, "states_seen": len(seen_states), "now": now.isoformat(),
            "tasks_seen": len(tasks_seen), "forecast_seen": len(forecast_seen), "modes_seen": len(modes_seen),
            "rendered_checked": rendered_checked}


def run(steps: int = 400, seeds: int = 1, first: int | None = None, content: bool = True) -> dict:
    """Several walks, and one line saying what they covered."""
    chosen = [first] if first is not None else [SEEDS[i % len(SEEDS)] for i in range(max(1, seeds))]
    started = time.monotonic()
    totals = {"tasks_seen": 0, "forecast_seen": 0, "modes_seen": 0, "rendered_checked": 0}
    for seed in chosen:
        summary = walk(seed=seed, steps=steps, content=content)
        for key in totals:
            totals[key] = max(totals[key], summary[key]) if key != "rendered_checked" else \
                totals[key] + summary[key]
    return {"seeds": chosen, "steps": steps, "views": len(chosen) * steps,
            "seconds": round(time.monotonic() - started, 1), **totals}


def summary_line(result: dict) -> str:
    return (f"simulate: {len(result['seeds'])} seed(s) x {result['steps']} steps = {result['views']} views, "
            f"{result['tasks_seen']} task ids, {result['forecast_seen']} forecast ids, {result['modes_seen']} mode sets, "
            f"{result['rendered_checked']} rendered sections checked for dead numbers, no invariant broken in "
            f"{result['seconds']}s")


def main(argv: list[str] | None = None) -> int:                # pragma: no cover - a hand-run and make-run tool
    parser = argparse.ArgumentParser(description="Random walk over the situation engine")
    parser.add_argument("--steps", type=int, default=400, help="steps in each walk")
    parser.add_argument("--seeds", type=int, default=1, help="how many seeded walks to take")
    parser.add_argument("--seed", type=int, default=None, help="one particular seed, to reproduce a failure")
    parser.add_argument("--no-content", action="store_true", help="skip the rendered-content invariant")
    args = parser.parse_args(argv)
    try:
        result = run(steps=args.steps, seeds=args.seeds, first=args.seed, content=not args.no_content)
    except AssertionError as exc:
        print(f"simulate: FAILED: {exc}", file=sys.stderr)
        return 1
    print(summary_line(result))
    return 0


if __name__ == "__main__":                                     # pragma: no cover - a hand-run tool
    raise SystemExit(main())
