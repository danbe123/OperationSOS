"""The engine: three golden models at a fixed clock, plus the pieces they do not reach.

Nothing is typed into the box before it is useful, so no model here has a household, a street list or a
store cupboard in it: every line the engine writes is written for anybody (no-setup spec)."""
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


# --- (a) peacetime: nothing off ------------------------------------------------------------------------------

@pytest.fixture
def peacetime() -> engine.Model:
    return engine.Model(now=at("2026-09-06T14:00:00+00:00"), home=dict(HOME))


def test_golden_peacetime(peacetime, ruleset):
    view = engine.compute(peacetime, ruleset)
    assert view["scenario"] is None and view["meta"]["drill"] is False and view["meta"]["dark"] is False
    assert view["meta"]["sunrise"] == "2026-09-06T05:26:54+00:00" and view["meta"]["sunset"] == "2026-09-06T18:40:14+00:00"
    assert all(c["state"] == "working" and c["for_s"] == 0 and c["stale"] is False for c in view["conditions"].values())
    assert set(view["conditions"]) == set(engine.cond.IDS)
    assert view["inferred"] == [] and view["forecast"] == [] and view["tasks"] == [] and view["briefing"] == []
    assert view["modes"] == {"theme": None, "dim": False, "calls": "shown", "map_first": False, "board": False}
    assert view["bulletins"]["next"] == {
        "station": "BBC local radio", "frequency": "FM, see the comms module for your station",
        "at": "2026-09-06T16:00:00+00:00",
        "note": "Local radio is where the council, the police and the water company say what is happening in your town."}


# --- (b) power off five hours -------------------------------------------------------------------------------

@pytest.fixture
def blackout() -> engine.Model:
    now = at("2026-09-06T14:00:00+00:00")
    since = (now - timedelta(hours=5)).isoformat()
    return engine.Model(
        now=now,
        conditions={"power": off("power", since)},
        home=dict(HOME),
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
    assert ids == ["powered-medical-kit", "fridge", "phone-batteries", "hot-water", "freezer"]
    fridge = view["forecast"][0]
    assert fridge["due_at"] == "2026-09-06T13:00:00+00:00" and fridge["passed"] is True and fridge["severity"] == "warn"
    assert view["forecast"][-1]["id"] == "freezer" and view["forecast"][-1]["due_at"] == "2026-09-08T09:00:00+00:00"


def test_golden_blackout_tasks_buckets_modes_and_briefing(blackout, ruleset):
    view = engine.compute(blackout, ruleset)
    now_tasks = [t["id"] for t in view["tasks"] if t["bucket"] == "now"]
    # the file order of tasks.yaml, not the alphabet: the author decides what a household does first
    assert now_tasks == ["fill-bath", "fridge-doors-shut", "cooker-off", "co-alarm-power", "check-on-people-nearby"]
    assert not any(t["bucket"] == "week" for t in view["tasks"])
    fill = next(t for t in view["tasks"] if t["id"] == "fill-bath")
    assert fill["done"] is False and fill["person"] is None and fill["source"] == "rule:fill-bath" and fill["link"] == "module:water"
    assert view["modes"] == {"theme": None, "dim": False, "calls": "shown", "map_first": False, "board": False}
    assert view["briefing"] == [{"title": "What still works in an outage", "kind": "page", "ref": "what-still-works"},
                                {"title": "Power", "kind": "module", "ref": "power"}]


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
    assert view["modes"]["theme"] == "mono" and view["modes"]["dim"] is True


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
        home=dict(HOME),
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
    assert "Freezer food unsafe" in text and "PASSED" in text
    assert "Readiness" not in text and "## Neighbours" not in text


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


def test_an_unknown_timezone_falls_back_to_utc(blackout, ruleset):
    blackout.tz = "Mars/Olympus"
    assert engine.compute(blackout, ruleset)["bulletins"]["next"]["at"].endswith("+00:00")


def test_no_bulletins_configured(blackout):
    empty = rules.Rules(by_kind={}, bulletins=())
    assert engine.compute(blackout, empty)["bulletins"] == {"next": None}


def mode_rule(rule_id: str, **set_values) -> rules.Rules:
    rule = rules.Rule(id=rule_id, kind="mode", when={}, source="test", set=set_values)
    return rules.Rules(by_kind={"mode": (rule,)}, bulletins=())


def test_a_mode_theme_the_box_has_no_palette_for_is_no_theme(blackout):
    """Rules travel on a stick and outlive the build that reads them: a modes file written for the
    three-theme box still says `theme: vault`. Serving that would stamp <html> with a theme that has
    no palette and no map style, so it is dropped and the reader keeps whichever of the two they chose."""
    assert engine.compute(blackout, mode_rule("old", theme="vault", dim=True))["modes"]["theme"] is None
    assert engine.compute(blackout, mode_rule("older", theme="blackout"))["modes"]["theme"] is None
    # The rest of the rule still applies: only the theme it cannot honour is dropped.
    assert engine.compute(blackout, mode_rule("old", theme="vault", dim=True))["modes"]["dim"] is True
    # And the two the box does have palettes for come through untouched.
    assert engine.compute(blackout, mode_rule("dark", theme="mono"))["modes"]["theme"] == "mono"
    assert engine.compute(blackout, mode_rule("light", theme="field"))["modes"]["theme"] == "field"


# --- no setup: the View names nobody (no-setup spec) -----------------------------------------------------------

def test_the_view_has_no_readiness_and_no_neighbours(blackout, ruleset):
    view = engine.compute(blackout, ruleset)
    assert set(view) == {"meta", "scenario", "conditions", "inferred", "forecast", "tasks", "briefing", "modes",
                         "bulletins"}


def test_the_two_generic_rules_fire_on_a_power_cut(blackout, ruleset):
    """No register, so the warning and the knock on the door are written for anybody."""
    view = engine.compute(blackout, ruleset)
    powered = next(f for f in view["forecast"] if f["id"] == "powered-medical-kit")
    assert powered["title"] == "Anyone on powered medical kit or fridge-kept medicine needs a plan now"
    assert powered["severity"] == "warn" and powered["link"] == "page:chronic-conditions"
    assert powered["due_at"] == "2026-09-06T13:00:00+00:00"       # the power went at 09:00, and this is four hours on
    check = next(t for t in view["tasks"] if t["id"] == "check-on-people-nearby")
    assert check["title"] == "Check on anyone nearby who would struggle on their own"
    assert check["bucket"] == "now" and check["link"] == "module:community"
    assert not any("{" in f["title"] for f in view["forecast"]) and not any("{" in t["title"] for t in view["tasks"])


def test_a_dry_tap_asks_the_street_to_carry_water(ruleset):
    """The water knock stands in for the power one when only the tap has gone: no register, so the two
    generic rules cover the two ways a neighbour is stuck."""
    now = at("2026-09-06T14:00:00+00:00")
    model = engine.Model(now=now, conditions={"water": off("water", "2026-09-06T09:00:00+00:00")}, home=dict(HOME))
    view = engine.compute(model, ruleset)
    check = next(t for t in view["tasks"] if t["id"] == "check-on-people-nearby-water")
    assert check["title"] == "Take water to anyone nearby who would struggle to fetch it"
    assert check["bucket"] == "hour" and check["link"] == "module:community" and check["why"]
    assert not any(t["id"] == "check-on-people-nearby" for t in view["tasks"])


def test_the_power_knock_is_not_doubled_when_the_water_has_gone_too(ruleset):
    now = at("2026-09-06T14:00:00+00:00")
    model = engine.Model(
        now=now,
        conditions={"power": off("power", "2026-09-06T09:00:00+00:00"),
                    "water": off("water", "2026-09-06T09:00:00+00:00")},
        home=dict(HOME),
    )
    view = engine.compute(model, ruleset)
    ids = [t["id"] for t in view["tasks"]]
    assert "check-on-people-nearby" in ids and "check-on-people-nearby-water" not in ids


def test_a_winter_heating_failure_asks_after_the_old_and_the_young(ruleset):
    model = engine.Model(now=at("2026-12-21T14:00:00+00:00"),
                         conditions={"heating": off("heating", "2026-12-21T09:00:00+00:00")}, home=dict(HOME))
    view = engine.compute(model, ruleset)
    check = next(t for t in view["tasks"] if t["id"] == "check-on-people-nearby-cold")
    assert check["title"] == "Check anyone nearby who is old or very young is warm"
    assert check["bucket"] == "hour" and check["link"] == "module:shelter-heat" and check["why"]
    # The same failure in September, which the engine counts as summer, does not fire it.
    model.now = at("2026-09-06T14:00:00+00:00")
    assert not any(t["id"] == "check-on-people-nearby-cold" for t in engine.compute(model, ruleset)["tasks"])


# --- prioritised tasks: buckets, the author's order and scenario-aware rules ---------------------------------

DRILL_RULES = """
rules:
  - id: fridge-doors-shut
    kind: task
    when: {power: "off"}
    title: Keep the fridge and freezer doors shut
    bucket: now
    rank: 200
    why: Housekeeping, and it waits while a scenario's own first actions are done.
    source: module:water

  - id: cooker-off
    kind: task
    when: {power: "off"}
    unless: {scenario: [nuclear-drill, chemical]}
    title: Turn the cooker off at the knobs
    bucket: now
    why: A ring left on starts a fire when the power comes back.
    source: module:water

  - id: co-alarm-power
    kind: task
    when: {power: "off"}
    title: Test the carbon monoxide alarm
    bucket: now
    why: Carbon monoxide gives no warning.
    source: module:water

  - id: get-everyone-in
    kind: task
    when: {scenario: nuclear-drill}
    title: Get everyone into the house
    bucket: now
    rank: 10
    why: The first minutes are the ones that count.
    source: module:water

  - id: shut-the-windows
    kind: task
    when: {scenario: nuclear-drill}
    title: Shut every window and door
    bucket: now
    rank: 10
    why: The first minutes are the ones that count.
    source: module:water

  - id: turn-the-radio-on
    kind: task
    when: {scenario: nuclear-drill}
    title: Turn the radio on
    bucket: now
    rank: 10
    why: The first minutes are the ones that count.
    source: module:water

  - id: plan-the-week
    kind: task
    when: {scenario: any}
    title: Plan the week
    bucket: week
    why: Something for later, whatever the scenario is.
    source: module:water

  - id: peacetime-only
    kind: task
    when: {power: "off"}
    unless: {scenario: any}
    title: Only when no scenario is running
    bucket: now
    why: A scenario's own list supersedes it.
    source: module:water
"""


@pytest.fixture
def drill_rules(tmp_path) -> rules.Rules:
    """A small rule set of its own, so the ordering test does not move whenever the real tasks.yaml does."""
    (tmp_path / "schema.json").write_text((RULES_DIR / "schema.json").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "tasks.yaml").write_text(DRILL_RULES, encoding="utf-8")
    return rules.load(tmp_path)


@pytest.fixture
def drill() -> engine.Model:
    """A nuclear-war drill with the power off: the scenario's own checklist, three items of it urgent."""
    now = at("2026-09-06T14:00:00+00:00")
    return engine.Model(
        now=now,
        conditions={"power": off("power", "2026-09-06T13:00:00+00:00")},
        scenario={"slug": "nuclear-drill", "title": "Nuclear drill", "started_at": "2026-09-06T13:00:00+00:00",
                  "elapsed_s": 3600, "phase": "right-now"},
        home=dict(HOME), drill=True,
        checklist=({"id": "count-people", "text": "Count everyone in the house", "bucket": "now"},
                   {"id": "fill-the-bath", "text": "Fill the bath", "bucket": "now"},
                   {"id": "tape-the-room", "text": "Tape up the inner room", "bucket": "now"},
                   {"id": "ration-food", "text": "Work out the food", "bucket": "hour"},
                   {"id": "write-it-down", "text": "Write down what you have used", "bucket": "today"},
                   {"id": "the-long-haul", "text": "Think about the month", "bucket": "week"}),
    )


def test_a_drill_leads_with_the_scenarios_own_first_actions(drill, drill_rules):
    """The complaint that started this: generic power-cut housekeeping led the list and the scenario's
    own first actions were ninth, alphabetically. Now the scenario leads and the fridge waits."""
    view = engine.compute(drill, drill_rules)
    ids = [t["id"] for t in view["tasks"]]
    assert ids[:3] == ["get-everyone-in", "shut-the-windows", "turn-the-radio-on"]
    assert "fridge-doors-shut" not in ids[:5]
    assert ids == ["get-everyone-in", "shut-the-windows", "turn-the-radio-on",       # the scenario's rules, rank 10
                   "co-alarm-power",                                                 # generic, rank 100
                   "checklist:nuclear-drill/count-people",                            # the checklist's own now items
                   "checklist:nuclear-drill/fill-the-bath",
                   "checklist:nuclear-drill/tape-the-room",
                   "fridge-doors-shut",                                               # demoted to rank 200
                   "checklist:nuclear-drill/ration-food",                             # hour
                   "checklist:nuclear-drill/write-it-down",                           # today
                   "plan-the-week", "checklist:nuclear-drill/the-long-haul"]          # week, rules before checklist
    assert [t["bucket"] for t in view["tasks"][:8]] == ["now"] * 8


def test_checklist_items_take_their_own_bucket_and_say_why(drill, drill_rules):
    view = engine.compute(drill, drill_rules)
    by_id = {t["id"]: t for t in view["tasks"]}
    assert [(by_id[f"checklist:nuclear-drill/{i}"]["bucket"], by_id[f"checklist:nuclear-drill/{i}"]["why"])
            for i in ("count-people", "ration-food", "write-it-down", "the-long-haul")] == [
        ("now", "Nuclear drill: right now"), ("hour", "Nuclear drill: in the first hour"),
        ("today", "Nuclear drill: today"), ("week", "Nuclear drill: this week")]
    assert by_id["checklist:nuclear-drill/count-people"]["link"] == "playbook:nuclear-drill#checklist"


def test_a_rule_may_name_the_scenario_it_belongs_to(drill, drill_rules):
    """`when: {scenario: …}` fires only in that scenario; `unless: {scenario: […]}` stands the rule down."""
    view = engine.compute(drill, drill_rules)
    ids = [t["id"] for t in view["tasks"]]
    assert "cooker-off" not in ids                      # unless: [nuclear-drill, chemical]
    assert "peacetime-only" not in ids                  # unless: {scenario: any}
    assert "plan-the-week" in ids                       # when: {scenario: any}
    drill.scenario = {"slug": "storms-flooding", "title": "Storms and flooding",
                      "started_at": "2026-09-06T13:00:00+00:00", "elapsed_s": 3600, "phase": "right-now"}
    drill.checklist = ()
    other = [t["id"] for t in engine.compute(drill, drill_rules)["tasks"]]
    assert other == ["cooker-off", "co-alarm-power", "fridge-doors-shut", "plan-the-week"]
    assert not any(i in other for i in ("get-everyone-in", "shut-the-windows", "turn-the-radio-on"))
    drill.scenario = None
    none = [t["id"] for t in engine.compute(drill, drill_rules)["tasks"]]
    assert none == ["cooker-off", "co-alarm-power", "peacetime-only", "fridge-doors-shut"]


def test_the_order_is_the_files_order_when_nothing_is_ranked(drill_rules, tmp_path):
    """No sort by title anywhere: equal bucket and equal rank means the order they were written in."""
    text = DRILL_RULES.replace("    rank: 200\n", "").replace("    rank: 10\n", "")
    (tmp_path / "schema.json").write_text((RULES_DIR / "schema.json").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "tasks.yaml").write_text(text, encoding="utf-8")
    plain = rules.load(tmp_path)
    assert all(rule.rank == 100 for rule in plain.tasks)
    model = engine.Model(now=at("2026-09-06T14:00:00+00:00"),
                         conditions={"power": off("power", "2026-09-06T13:00:00+00:00")},
                         scenario={"slug": "nuclear-drill", "title": "Nuclear drill",
                                   "started_at": "2026-09-06T13:00:00+00:00", "elapsed_s": 3600, "phase": "right-now"},
                         home=dict(HOME),
                         checklist=({"id": "count-people", "text": "Count everyone in the house", "bucket": "now"},))
    ids = [t["id"] for t in engine.compute(model, plain)["tasks"]]
    assert ids == ["fridge-doors-shut", "co-alarm-power", "get-everyone-in", "shut-the-windows",
                   "turn-the-radio-on", "checklist:nuclear-drill/count-people", "plan-the-week"]
