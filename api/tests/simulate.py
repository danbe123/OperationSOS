"""A random walk over the situation, to catch what fixed examples never will.

Four hundred steps of conditions changing, scenarios starting and ending, drills, ticks and the clock moving on.
After every step the View is computed twice and checked against the invariants the whole app relies on. Seeded,
so a failure is reproducible: `python -m tests.simulate 1234`."""
from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sos import conditions as cond
from sos import engine, rules as rules_mod

REPO = Path(__file__).resolve().parents[2]
RULES_DIR = REPO / "playbooks" / "rules"
START = datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc)
SCENARIOS = ("grid-collapse", "storms-flooding", "severe-winter", "pandemic", "heat-drought")
NEEDS = ("insulin", "oxygen", "cpap", "stairlift", "asthma", "")
PHASE_TITLES = ("National grid collapse", "Storms and flooding", "Severe winter", "Pandemic", "Heat and drought")


def _scenario(slug: str, started: datetime, now: datetime) -> dict:
    from sos.situation import phase_for

    elapsed = max(0.0, (now - started).total_seconds())
    return {"slug": slug, "title": PHASE_TITLES[SCENARIOS.index(slug)], "started_at": started.isoformat(),
            "elapsed_s": int(elapsed), "phase": phase_for(elapsed)}


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

    if states["mobile"] == "off" and states["landline"] == "off":
        assert view["modes"]["calls"] == "hidden", f"{where}: numbers still on show with no phones"
    assert 0 <= view["readiness"]["score"] <= 100, where
    assert view["meta"]["now"] == model.now.isoformat(), where


def walk(seed: int = 1234, steps: int = 400) -> dict:
    """Take the walk and return a small summary. Raises on the first broken invariant."""
    rng = random.Random(seed)
    ruleset = rules_mod.load(RULES_DIR)
    now = START
    conditions: dict[str, cond.Condition] = {cid: cond.Condition(cid) for cid in cond.IDS}
    household: list[dict] = []
    stock: list[dict] = [{"name": "Bottled water", "category": "water", "days_left": 4.0, "notes": ""}]
    scenario_slug: str | None = None
    scenario_started = now
    drill = False
    task_state: dict[str, dict] = {}
    seen_states: set[str] = set()
    tasks_seen: set[str] = set()
    forecast_seen: set[str] = set()
    modes_seen: set[str] = set()

    for step in range(steps):
        action = rng.choice(["condition", "condition", "condition", "clock", "clock", "scenario", "drill",
                             "task", "household", "stock"])
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
        elif action == "task":
            if task_ids := [t for t in task_state] or ["fill-bath", "boil-water", "meeting-point"]:
                task_state[rng.choice(task_ids)] = {"done": rng.random() < 0.5, "done_at": now.isoformat(),
                                                    "person": rng.choice([None, "Sam", "Ali"])}
        elif action == "household":
            if household and rng.random() < 0.3:
                household.pop()
            else:
                household.append({"name": f"Person {len(household) + 1}", "needs": rng.choice(NEEDS),
                                  "medications": rng.choice(NEEDS), "contacts": rng.choice(["", "Gran 01703 555 123"])})
        else:
            if stock and rng.random() < 0.3:
                stock.pop()
            else:
                stock.append({"name": rng.choice(["Tins", "Insulin", "Nappies", "Diesel"]),
                              "category": rng.choice(["water", "food", "medicine", "fuel", "other"]),
                              "days_left": rng.choice([None, 0.5, 2.0, 9.0, 30.0]), "notes": ""})

        model = engine.Model(
            now=now, conditions=dict(conditions), household=tuple(household), stock=tuple(stock),
            scenario=_scenario(scenario_slug, scenario_started, now) if scenario_slug else None,
            home={"lat": 50.93, "lon": -1.43, "label": "Home", "flood_zone": "3"}, drill=drill,
            checklist=({"id": "one", "text": "The first thing"}, {"id": "two", "text": "The second thing"})
            if scenario_slug else (),
            checklist_state={"one": rng.random() < 0.5}, task_state=dict(task_state),
        )
        view = engine.compute(model, ruleset)
        assert engine.compute(model, ruleset) == view, f"step {step}: the same model gave two different Views"
        _check(view, model, ruleset, step)
        tasks_seen.update(t["id"] for t in view["tasks"])
        forecast_seen.update(f["id"] for f in view["forecast"])
        modes_seen.add(repr(sorted(view["modes"].items())))
        engine.report(view)                                    # the report must survive every situation too

    return {"seed": seed, "steps": steps, "states_seen": len(seen_states), "people": len(household),
            "stock": len(stock), "now": now.isoformat(), "tasks_seen": len(tasks_seen),
            "forecast_seen": len(forecast_seen), "modes_seen": len(modes_seen)}


if __name__ == "__main__":                                     # pragma: no cover - a hand-run tool
    print(walk(int(sys.argv[1]) if len(sys.argv) > 1 else 1234))
