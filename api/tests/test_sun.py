"""Sunrise and sunset against published times for London and the polar cases."""
from datetime import date, datetime, timezone

import pytest

from sos import sun

LONDON = (51.5074, -0.1278)
TROMSO = (69.6496, 18.9560)


def _hhmm(moment: datetime) -> tuple[int, int]:
    return moment.hour, moment.minute


def _minutes(moment: datetime) -> int:
    return moment.hour * 60 + moment.minute + moment.second / 60


@pytest.mark.parametrize("day,rise,set_", [
    # UTC times; London is on BST in June (published local times 04:43 and 21:21)
    (date(2026, 6, 21), (3, 43), (20, 21)),
    (date(2026, 12, 21), (8, 3), (15, 53)),
])
def test_london_solstices(day, rise, set_):
    sunrise, sunset = sun.sun_times(*LONDON, day)
    assert sunrise.tzinfo == timezone.utc and sunset.tzinfo == timezone.utc
    assert abs(_minutes(sunrise) - (rise[0] * 60 + rise[1])) <= 2, sunrise
    assert abs(_minutes(sunset) - (set_[0] * 60 + set_[1])) <= 2, sunset
    assert sunrise < sunset


def test_accepts_a_datetime_and_uses_its_utc_day():
    from_date = sun.sun_times(*LONDON, date(2026, 6, 21))
    from_dt = sun.sun_times(*LONDON, datetime(2026, 6, 21, 23, 30, tzinfo=timezone.utc))
    assert from_date == from_dt


def test_is_dark_around_the_london_midsummer_day():
    assert sun.is_dark(*LONDON, datetime(2026, 6, 21, 2, 0, tzinfo=timezone.utc)) is True
    assert sun.is_dark(*LONDON, datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)) is False
    assert sun.is_dark(*LONDON, datetime(2026, 6, 21, 21, 0, tzinfo=timezone.utc)) is True
    # a winter afternoon is already dark in London
    assert sun.is_dark(*LONDON, datetime(2026, 12, 21, 16, 30, tzinfo=timezone.utc)) is True
    assert sun.is_dark(*LONDON, datetime(2026, 12, 21, 12, 0, tzinfo=timezone.utc)) is False


def test_polar_day_and_night():
    assert sun.sun_times(*TROMSO, date(2026, 6, 21)) == (None, None)
    assert sun.sun_times(*TROMSO, date(2026, 12, 21)) == (None, None)
    assert sun.is_dark(*TROMSO, datetime(2026, 6, 21, 1, 0, tzinfo=timezone.utc)) is False
    assert sun.is_dark(*TROMSO, datetime(2026, 12, 21, 12, 0, tzinfo=timezone.utc)) is True


def test_naive_times_are_read_as_utc():
    assert sun.is_dark(*LONDON, datetime(2026, 12, 21, 22, 0)) is True
