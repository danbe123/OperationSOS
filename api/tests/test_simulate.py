"""The simulator, run as a normal test on a few fixed seeds."""
import pytest

from tests.simulate import walk


@pytest.mark.parametrize("seed", [1234, 7, 2026])
def test_the_random_walk_holds_every_invariant(seed):
    summary = walk(seed=seed, steps=400)
    assert summary["steps"] == 400 and summary["states_seen"] >= 20
    assert summary["tasks_seen"] >= 10 and summary["forecast_seen"] >= 10 and summary["modes_seen"] >= 4


def test_the_walk_is_reproducible():
    assert walk(seed=1234, steps=50) == walk(seed=1234, steps=50)
    assert walk(seed=1234, steps=50) != walk(seed=99, steps=50)
