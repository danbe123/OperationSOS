"""The simulator, run as a normal test on a few fixed seeds. `make test` runs it again, longer and wider."""
import pytest

from tests import simulate
from tests.simulate import walk


@pytest.mark.parametrize("seed", [1234, 7, 2026])
def test_the_random_walk_holds_every_invariant(seed):
    summary = walk(seed=seed, steps=400)
    assert summary["steps"] == 400 and summary["states_seen"] >= 20
    assert summary["tasks_seen"] >= 10 and summary["forecast_seen"] >= 5 and summary["modes_seen"] >= 4


def test_the_walk_is_reproducible():
    assert walk(seed=1234, steps=50) == walk(seed=1234, steps=50)
    assert walk(seed=1234, steps=50) != walk(seed=99, steps=50)


def test_the_walk_renders_real_content_when_the_phones_are_down():
    """Seed 7 loses both phone routes, so the rendered cards and playbook are actually checked."""
    assert walk(seed=7, steps=400)["rendered_checked"] > 0
    assert walk(seed=7, steps=400, content=False)["rendered_checked"] == 0


@pytest.mark.parametrize("text,caught", [
    ("Say \"chest pain\" and call 999.", True),
    ("Ring 111 for advice.", True),
    ("dial 112 from any mobile", True),
    ("Report it on 105.", False),                                   # not an instruction to ring it
    ("999 will not connect while the phones are down", False),      # what the directive renders instead
    ("the 999 call handler will talk you through it", False),
])
def test_the_dead_number_pattern_only_catches_instructions(text, caught):
    assert bool(simulate.BARE_CALL.search(text)) is caught


def test_the_escalate_section_is_the_tail_of_a_card():
    html = "<h2>Steps</h2><p>one</p><h2>Stop or escalate</h2><p>go now</p><h2>Source</h2><p>nhs</p>"
    assert simulate._escalate_html(html) == "</h2><p>go now</p>"
    assert simulate._escalate_html("<p>no such heading</p>") == ""


def test_the_summary_line_says_what_was_covered():
    line = simulate.summary_line(simulate.run(steps=40, seeds=2))
    assert line.startswith("simulate: 2 seed(s) x 40 steps = 80 views")
    assert "rendered sections checked for dead numbers" in line
