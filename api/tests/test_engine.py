"""The engine: three golden models at a fixed clock, plus the pieces they do not reach."""
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from sos import engine, rules
from sos.conditions import Condition

REPO = Path(__file__).resolve().parents[2]
RULES_DIR = REPO / "playbooks" / "rules"
HOME = {"lat": 50.93, "lon": -1.43, "label": "Home", "flood_zone": "3"}


@pytest.fixture(scope="module")
def ruleset() -> rules.Rules:
    return rules.load(RULES_DIR)


def at(text: str) -> datetime:
    return datetime.fromisoformat(text)


def off(cid: str, since: str, *, state: str = "off", source: str = "manual", set_by: str = "kiosk") -> Condition:
    return Condition(cid, state=state, since=since, source=source, set_by=set_by, updated_at=since, confirmed_at=since)


def household(**kwargs) -> dict:
    return {"name": "?", "age": None, "needs": "", "medications": "", "contacts": "", **kwargs}


def stock(name: str, category: str, days_left: float | None, notes: str = "") -> dict:
    return {"name": name, "category": category, "days_left": days_left, "notes": notes}


# --- (a) peacetime: nothing off ------------------------------------------------------------------------------

@pytest.fixture
def peacetime() -> engine.Model:
    return engine.Model(
        now=at("2026-09-06T14:00:00+00:00"),
        household=(household(name="Dan", contacts="Gran 01703 555 123"), household(name="Sam", age=7),
                   household(name="Ali")),
        stock=(stock("Bottled water", "water", 4.0), stock("Tins and pasta", "food", 9.0),
               stock("Repeat prescriptions", "medicine", 21.0)),
        home=dict(HOME), meeting_point=True, last_drill_at="2026-07-01T10:00:00+00:00",
    )


def test_golden_peacetime(peacetime, ruleset):
    view = engine.compute(peacetime, ruleset)
    assert view["scenario"] is None and view["meta"]["drill"] is False and view["meta"]["dark"] is False
    assert view["meta"]["sunrise"] == "2026-09-06T05:26:54+00:00" and view["meta"]["sunset"] == "2026-09-06T18:40:14+00:00"
    assert all(c["state"] == "working" and c["for_s"] == 0 and c["stale"] is False for c in view["conditions"].values())
    assert set(view["conditions"]) == set(engine.cond.IDS)
    assert view["inferred"] == [] and view["forecast"] == [] and view["tasks"] == [] and view["briefing"] == []
    assert view["modes"] == {"theme": None, "dim": False, "calls": "shown", "map_first": False, "board": False}
    assert view["readiness"]["score"] == 100 and view["readiness"]["gaps"] == []
    assert view["bulletins"]["next"] == {
        "station": "BBC local radio", "frequency": "FM, see the comms module for your station",
        "at": "2026-09-06T16:00:00+00:00",
        "note": "Local radio is where the council, the police and the water company say what is happening in your town."}


def test_peacetime_gaps_name_what_is_missing(peacetime, ruleset):
    thin = engine.Model(now=peacetime.now, household=(household(name="Dan"),), stock=(stock("Bottled water", "water", 1.5),))
    view = engine.compute(thin, ruleset)
    assert view["readiness"]["score"] < 40
    assert view["readiness"]["gaps"][0]["points"] >= view["readiness"]["gaps"][-1]["points"]
    assert {"title": "Water: 1.5 days for 1 person", "link": "/plan#stock", "points": 7} in view["readiness"]["gaps"]
    assert any(g["title"] == "Home is not set on the map" for g in view["readiness"]["gaps"])
    assert [t["id"] for t in view["tasks"]] == ["medicine-stock-missing", "water-stock-low"]


# --- (b) power off five hours, with insulin and oxygen in the house ------------------------------------------

@pytest.fixture
def blackout() -> engine.Model:
    now = at("2026-09-06T14:00:00+00:00")
    since = (now - timedelta(hours=5)).isoformat()
    return engine.Model(
        now=now,
        conditions={"power": off("power", since)},
        household=(household(name="Dan", contacts="Gran 01703 555 123"),
                   household(name="Nan", age=81, needs="oxygen concentrator", medications="insulin, salbutamol")),
        stock=(stock("Bottled water", "water", 4.0), stock("Tins and pasta", "food", 9.0),
               stock("Insulin and oxygen spares", "medicine", 21.0, notes="insulin in the fridge, spare oxygen cylinder")),
        home=dict(HOME), meeting_point=True, last_drill_at="2026-07-01T10:00:00+00:00",
        titles={"page:what-still-works": "What still works in an outage", "module:power": "Power"},
    )


def test_golden_blackout_conditions_and_inferred(blackout, ruleset):
    view = engine.compute(blackout, ruleset)
    assert view["conditions"]["power"]["state"] == "off" and view["conditions"]["power"]["for_s"] == 5 * 3600
    assert view["conditions"]["power"]["source"] == "manual" and view["conditions"]["power"]["stale"] is False
    assert view["conditions"]["water"]["state"] == "working"
    # one proposal per condition, the strongest that has come due
    assert [(i["condition"], i["state"], i["rule"]) for i in view["inferred"]] == [
        ("internet", "off", "power-off-internet-off"),
        ("landline", "off", "power-off-landline-off"),
        ("shops", "off", "power-off-shops-off"),
        ("heating", "off", "power-off-heating-off"),
        ("mobile", "degraded", "power-off-mobile-degraded"),
    ]
    mobile = next(i for i in view["inferred"] if i["condition"] == "mobile")
    assert mobile["confidence"] == 0.7 and mobile["due_at"] == "2026-09-06T13:00:00+00:00"
    assert mobile["source"] == "page:what-still-works" and mobile["why"]
    # water needs 24 hours of power cut before it is even suspected
    assert not any(i["condition"] == "water" for i in view["inferred"])


def test_golden_blackout_forecast_is_ordered_by_due_time(blackout, ruleset):
    view = engine.compute(blackout, ruleset)
    ids = [f["id"] for f in view["forecast"]]
    assert ids == ["fridge", "oxygen-concentrator:nan", "phone-batteries", "hot-water",
                   "cold-medicines-insulin:nan", "freezer"]
    fridge = view["forecast"][0]
    assert fridge["due_at"] == "2026-09-06T13:00:00+00:00" and fridge["passed"] is True and fridge["severity"] == "warn"
    oxygen = view["forecast"][1]
    assert oxygen["title"] == "Nan's oxygen: back-up cylinders running low" and oxygen["severity"] == "danger"
    assert oxygen["due_at"] == "2026-09-06T15:00:00+00:00" and oxygen["passed"] is False and oxygen["link"] == "module:medical"
    assert view["forecast"][-1]["id"] == "freezer" and view["forecast"][-1]["due_at"] == "2026-09-08T09:00:00+00:00"


def test_golden_blackout_tasks_buckets_modes_and_briefing(blackout, ruleset):
    view = engine.compute(blackout, ruleset)
    now_tasks = [t["id"] for t in view["tasks"] if t["bucket"] == "now"]
    assert set(now_tasks) == {"fill-bath", "fridge-doors-shut", "cooker-off", "co-alarm-power", "check-dependent:nan"}
    assert now_tasks == sorted(now_tasks, key=lambda i: next(t["title"] for t in view["tasks"] if t["id"] == i))
    assert [t["id"] for t in view["tasks"] if t["bucket"] == "hour"] == ["medicines-cold-box:nan"]
    assert not any(t["bucket"] == "week" for t in view["tasks"])       # the store cupboard is stocked
    fill = next(t for t in view["tasks"] if t["id"] == "fill-bath")
    assert fill["done"] is False and fill["person"] is None and fill["source"] == "rule:fill-bath" and fill["link"] == "module:water"
    check = next(t for t in view["tasks"] if t["id"] == "check-dependent:nan")
    assert check["title"] == "Check on Nan and everything of theirs that needed a plug"
    assert view["modes"] == {"theme": None, "dim": False, "calls": "shown", "map_first": False, "board": False}
    assert view["briefing"] == [{"title": "What still works in an outage", "kind": "page", "ref": "what-still-works"},
                                {"title": "Power", "kind": "module", "ref": "power"}]
    assert view["readiness"]["score"] == 100


def test_done_and_assigned_tasks_come_from_task_state(blackout, ruleset):
    blackout.task_state = {"fill-bath": {"done": True, "done_at": "2026-09-06T13:30:00+00:00", "person": "Sam"}}
    view = engine.compute(blackout, ruleset)
    fill = next(t for t in view["tasks"] if t["id"] == "fill-bath")
    assert fill["done"] is True and fill["person"] == "Sam" and fill["done_at"] == "2026-09-06T13:30:00+00:00"


def test_fill_the_bath_retires_when_the_water_goes(blackout, ruleset):
    blackout.conditions["water"] = off("water", "2026-09-06T13:00:00+00:00", state="degraded")
    view = engine.compute(blackout, ruleset)
    ids = [t["id"] for t in view["tasks"]]
    assert "fill-bath" not in ids and "fill-containers" in ids and "boil-water" in ids


def test_blackout_at_night_dims_the_screen(blackout, ruleset):
    blackout.now = at("2026-12-21T20:00:00+00:00")
    blackout.conditions["power"] = off("power", "2026-12-21T15:00:00+00:00")
    view = engine.compute(blackout, ruleset)
    assert view["meta"]["dark"] is True
    assert view["modes"]["theme"] == "blackout" and view["modes"]["dim"] is True


# --- (c) storms and flooding, phones down, at night ----------------------------------------------------------

@pytest.fixture
def flood() -> engine.Model:
    now = at("2026-12-21T22:00:00+00:00")
    return engine.Model(
        now=now,
        conditions={"mobile": off("mobile", "2026-12-21T20:00:00+00:00"),
                    "landline": off("landline", "2026-12-21T20:00:00+00:00")},
        scenario={"slug": "storms-flooding", "title": "Storms and flooding",
                  "started_at": "2026-12-21T19:00:00+00:00", "elapsed_s": 3 * 3600, "phase": "right-now"},
        household=(household(name="Dan", contacts="Gran 01703 555 123"),),
        stock=(stock("Bottled water", "water", 4.0), stock("Tins and pasta", "food", 9.0),
               stock("Repeat prescriptions", "medicine", 21.0)),
        home=dict(HOME), meeting_point=True, last_drill_at="2026-11-01T10:00:00+00:00",
        checklist=({"id": "move-upstairs", "text": "Move what matters upstairs"},
                   {"id": "sandbags", "text": "Sandbag the doors"}),
        checklist_state={"sandbags": True},
        titles={"page:no-phones": "Getting help without phones", "module:comms": "Communications",
                "playbook:storms-flooding": "Storms and flooding", "module:evacuation": "Leaving"},
    )


def test_golden_flood_view(flood, ruleset):
    view = engine.compute(flood, ruleset)
    assert view["meta"]["dark"] is True and view["scenario"]["phase"] == "right-now"
    assert view["conditions"]["mobile"]["for_s"] == 2 * 3600 and view["conditions"]["landline"]["state"] == "off"
    assert view["inferred"] == [] and view["forecast"] == []
    assert view["modes"] == {"theme": None, "dim": False, "calls": "hidden", "map_first": True, "board": True}
    assert [t["id"] for t in view["tasks"]] == [
        "meeting-point", "checklist:storms-flooding/move-upstairs", "checklist:storms-flooding/sandbags"]
    checklist_task = view["tasks"][2]
    assert checklist_task["done"] is True and checklist_task["source"] == "checklist:storms-flooding"
    assert checklist_task["link"] == "playbook:storms-flooding#checklist" and checklist_task["bucket"] == "today"
    assert view["tasks"][1]["done"] is False
    assert view["briefing"] == [
        {"title": "Right now", "kind": "playbook-section", "ref": "storms-flooding#right-now"},
        {"title": "Getting help without phones", "kind": "page", "ref": "no-phones"},
        {"title": "Communications", "kind": "module", "ref": "comms"},
        {"title": "Storms and flooding", "kind": "playbook", "ref": "storms-flooding"},
        {"title": "Leaving", "kind": "module", "ref": "evacuation"},
        {"title": "The map", "kind": "map", "ref": "overlay=flood-zones"},
    ]
    assert view["bulletins"]["next"]["at"] == "2026-12-22T06:00:00+00:00"


def test_flags_from_the_view(flood, ruleset):
    view = engine.compute(flood, ruleset)
    flags = engine.flags(view)
    assert flags["mobile"] is False and flags["landline"] is False and flags["phones"] is False
    assert flags["power"] is True and flags["dark"] is True and flags["scenario:storms-flooding"] is True
    assert "scenario:grid-collapse" not in flags


def test_flags_count_degraded_as_working(ruleset):
    model = engine.Model(now=at("2026-09-06T14:00:00+00:00"),
                         conditions={"water": off("water", "2026-09-06T10:00:00+00:00", state="degraded")})
    flags = engine.flags(engine.compute(model, ruleset))
    assert flags["water"] is True and flags["phones"] is True


# --- the rest ------------------------------------------------------------------------------------------------

def test_compute_is_deterministic(blackout, ruleset):
    assert engine.compute(blackout, ruleset) == engine.compute(blackout, ruleset)


def test_a_stale_condition_is_flagged(ruleset):
    model = engine.Model(now=at("2026-09-06T14:00:00+00:00"),
                         conditions={"power": off("power", "2026-09-04T09:00:00+00:00")})
    view = engine.compute(model, ruleset)
    assert view["conditions"]["power"]["stale"] is True and view["conditions"]["water"]["stale"] is False


def test_a_detected_reading_proposes_but_never_overrides_a_manual_state(ruleset):
    model = engine.Model(
        now=at("2026-09-06T14:00:00+00:00"),
        conditions={"internet": Condition("internet", state="working", source="manual",
                                          updated_at="2026-09-06T12:00:00+00:00")},
        detected={"internet": {"state": "off", "at": "2026-09-06T13:00:00+00:00", "confidence": 0.9, "sensor": "probe"}},
    )
    view = engine.compute(model, ruleset)
    assert view["conditions"]["internet"]["state"] == "working"
    assert [(i["condition"], i["state"], i["rule"]) for i in view["inferred"]] == [("internet", "off", "sensor:probe")]


def test_a_detected_reading_wins_when_nobody_has_said_otherwise(ruleset):
    model = engine.Model(
        now=at("2026-09-06T14:00:00+00:00"),
        conditions={"internet": Condition("internet", state="working", source="inferred",
                                          updated_at="2026-09-06T12:00:00+00:00")},
        detected={"internet": {"state": "off", "at": "2026-09-06T13:00:00+00:00", "sensor": "probe"}},
    )
    view = engine.compute(model, ruleset)
    assert view["conditions"]["internet"]["state"] == "off" and view["conditions"]["internet"]["source"] == "detected"
    assert view["conditions"]["internet"]["for_s"] == 3600 and view["inferred"] == []


def test_drill_shows_in_the_meta_and_the_report(flood, ruleset):
    flood.drill = True
    view = engine.compute(flood, ruleset)
    assert view["meta"]["drill"] is True
    text = engine.report(view, [{"updated_at": "2026-12-21T20:00:00+00:00", "title": "Mobile network off since 20:00 (kiosk)"}])
    assert text.startswith("# Situation report") and "**This is a drill.**" in text
    assert "## Conditions" in text and "Mobile network**: off" in text
    assert "- [x] Sandbag the doors" in text and "- [ ] Move what matters upstairs" in text
    assert "## Log" in text and "Mobile network off since 20:00 (kiosk)" in text


def test_report_of_a_blackout_lists_the_forecast(blackout, ruleset):
    text = engine.report(engine.compute(blackout, ruleset))
    assert "Freezer food unsafe" in text and "PASSED" in text and "Readiness 100 of 100." in text


def test_summary_line(blackout, ruleset):
    assert engine.summary_line(engine.compute(blackout, ruleset)) == "Mains power"
    assert engine.summary_line(engine.compute(engine.Model(now=at("2026-09-06T14:00:00+00:00")), ruleset)) == "Everything working"


@pytest.mark.parametrize("clause,expected", [
    ({}, True),
    ({"power": "off"}, True),
    ({"power": "working"}, False),
    ({"power": ["degraded", "off"]}, True),
    ({"phones": "off"}, False),
    ({"phones": "working"}, True),
    ({"scenario": "any"}, False),
    ({"dark": False}, True),
    ({"drill": True}, False),
    ({"power": "off", "water": "working"}, True),
    ({"nonsense": "x"}, False),
])
def test_matches(clause, expected, blackout):
    states = engine.effective_states(blackout)
    assert engine.matches(clause, states, blackout, dark=False) is expected


def test_season_matching(ruleset):
    model = engine.Model(now=at("2026-01-15T12:00:00+00:00"))
    assert engine.matches({"season": "winter"}, {}, model, False) is True
    assert engine.matches({"season": "summer"}, {}, model, False) is False


def test_stock_predicates(blackout):
    water_low = rules.Rule(id="x", kind="task", when={}, source="module:water", stock={"category": "water", "days_lt": 3})
    assert engine.stock_matches(water_low, blackout) is False
    fuel_missing = rules.Rule(id="y", kind="task", when={}, source="module:power", stock={"category": "fuel", "missing": True})
    assert engine.stock_matches(fuel_missing, blackout) is True


def test_an_unknown_timezone_falls_back_to_utc(blackout, ruleset):
    blackout.tz = "Mars/Olympus"
    assert engine.compute(blackout, ruleset)["bulletins"]["next"]["at"].endswith("+00:00")


def test_no_bulletins_configured(blackout):
    empty = rules.Rules(by_kind={}, bulletins=())
    assert engine.compute(blackout, empty)["bulletins"] == {"next": None}
