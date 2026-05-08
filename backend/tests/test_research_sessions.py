"""Tests for the Globex session math.

Verifies Globex day/week boundaries match CME's published futures
trading schedule:
  - Globex day:  18:00 ET prev day  →  17:00 ET current day
  - Globex week: Sunday 18:00 ET    →  Friday 17:00 ET
  - Maintenance window 17:00-18:00 ET belongs to the NEXT session.
  - Saturday + early Sunday roll forward to next Sun 18:00 (no
    open session yet).
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from app.research.sessions import (
    GlobexPeriod,
    globex_day_for,
    globex_week_for,
    previous_globex_day,
    previous_globex_week,
)

ET = ZoneInfo("America/New_York")
UTC = timezone.utc


def _et(year: int, month: int, day: int, hour: int = 12, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=ET)


# ---------- globex_day_for ----------


def test_day_midweek_afternoon():
    """Tuesday 14:00 ET → Mon 18:00 → Tue 17:00."""
    p = globex_day_for(_et(2026, 5, 5, 14, 0))  # Tue
    assert p.start_utc == _et(2026, 5, 4, 18, 0).astimezone(UTC)
    assert p.end_utc == _et(2026, 5, 5, 17, 0).astimezone(UTC)
    assert p.label == "globex_day"


def test_day_during_maintenance_window():
    """Tuesday 17:30 ET (maintenance) → next session Tue 18:00 → Wed 17:00."""
    p = globex_day_for(_et(2026, 5, 5, 17, 30))
    assert p.start_utc == _et(2026, 5, 5, 18, 0).astimezone(UTC)
    assert p.end_utc == _et(2026, 5, 6, 17, 0).astimezone(UTC)


def test_day_just_before_close():
    """Tuesday 16:59 ET → still in current day's session → Mon 18 → Tue 17."""
    p = globex_day_for(_et(2026, 5, 5, 16, 59))
    assert p.start_utc == _et(2026, 5, 4, 18, 0).astimezone(UTC)
    assert p.end_utc == _et(2026, 5, 5, 17, 0).astimezone(UTC)


def test_day_at_session_open():
    """Tuesday 18:00 ET → next session opens → Tue 18:00 → Wed 17:00."""
    p = globex_day_for(_et(2026, 5, 5, 18, 0))
    assert p.start_utc == _et(2026, 5, 5, 18, 0).astimezone(UTC)
    assert p.end_utc == _et(2026, 5, 6, 17, 0).astimezone(UTC)


def test_day_sunday_evening_start():
    """Sunday 19:00 ET → Sun 18:00 → Mon 17:00 (week's first session)."""
    p = globex_day_for(_et(2026, 5, 3, 19, 0))  # Sun
    assert p.start_utc == _et(2026, 5, 3, 18, 0).astimezone(UTC)
    assert p.end_utc == _et(2026, 5, 4, 17, 0).astimezone(UTC)


def test_day_saturday_rolls_forward():
    """Saturday — no session — roll to upcoming Sun 18:00 → Mon 17:00."""
    p = globex_day_for(_et(2026, 5, 2, 12, 0))  # Sat
    assert p.start_utc == _et(2026, 5, 3, 18, 0).astimezone(UTC)
    assert p.end_utc == _et(2026, 5, 4, 17, 0).astimezone(UTC)


def test_day_early_sunday_rolls_forward():
    """Sunday before 18:00 → today's Sun 18:00 → Mon 17:00."""
    p = globex_day_for(_et(2026, 5, 3, 10, 0))  # Sun morning
    assert p.start_utc == _et(2026, 5, 3, 18, 0).astimezone(UTC)
    assert p.end_utc == _et(2026, 5, 4, 17, 0).astimezone(UTC)


def test_day_friday_afternoon():
    """Friday 14:00 → Thu 18:00 → Fri 17:00."""
    p = globex_day_for(_et(2026, 5, 1, 14, 0))  # Fri
    assert p.start_utc == _et(2026, 4, 30, 18, 0).astimezone(UTC)
    assert p.end_utc == _et(2026, 5, 1, 17, 0).astimezone(UTC)


def test_day_friday_post_close_rolls_to_sunday():
    """Friday 17:00 ET onward → no Friday-evening session → next Sun 18:00."""
    p = globex_day_for(_et(2026, 5, 1, 18, 0))  # Fri 18:00
    assert p.start_utc == _et(2026, 5, 3, 18, 0).astimezone(UTC)
    assert p.end_utc == _et(2026, 5, 4, 17, 0).astimezone(UTC)


# ---------- previous_globex_day ----------


def test_previous_day_midweek():
    """Tue → Monday's session."""
    prev = previous_globex_day(_et(2026, 5, 5, 14, 0))
    assert prev.start_utc == _et(2026, 5, 3, 18, 0).astimezone(UTC)
    assert prev.end_utc == _et(2026, 5, 4, 17, 0).astimezone(UTC)


def test_previous_day_for_monday_skips_weekend():
    """Monday's previous-day → Friday's session, not Saturday/Sunday."""
    prev = previous_globex_day(_et(2026, 5, 4, 14, 0))  # Mon
    assert prev.start_utc == _et(2026, 4, 30, 18, 0).astimezone(UTC)
    assert prev.end_utc == _et(2026, 5, 1, 17, 0).astimezone(UTC)


def test_previous_day_for_sunday_evening():
    """Sun evening session → previous-day is Friday's."""
    prev = previous_globex_day(_et(2026, 5, 3, 19, 0))  # Sun 19:00
    assert prev.start_utc == _et(2026, 4, 30, 18, 0).astimezone(UTC)
    assert prev.end_utc == _et(2026, 5, 1, 17, 0).astimezone(UTC)


# ---------- globex_week_for ----------


def test_week_midweek():
    """Wed → most recent Sunday open → upcoming Fri close."""
    w = globex_week_for(_et(2026, 5, 6, 12, 0))  # Wed
    assert w.start_utc == _et(2026, 5, 3, 18, 0).astimezone(UTC)
    assert w.end_utc == _et(2026, 5, 8, 17, 0).astimezone(UTC)


def test_week_sunday_evening():
    """Sun 19:00 → THIS Sunday opens the week."""
    w = globex_week_for(_et(2026, 5, 3, 19, 0))
    assert w.start_utc == _et(2026, 5, 3, 18, 0).astimezone(UTC)
    assert w.end_utc == _et(2026, 5, 8, 17, 0).astimezone(UTC)


def test_week_saturday_rolls_forward():
    """Saturday → next week (Sun 18 → Fri 17)."""
    w = globex_week_for(_et(2026, 5, 2, 12, 0))  # Sat
    assert w.start_utc == _et(2026, 5, 3, 18, 0).astimezone(UTC)
    assert w.end_utc == _et(2026, 5, 8, 17, 0).astimezone(UTC)


def test_week_friday_post_close_rolls_forward():
    """Friday 17:00+ → next Sunday's week."""
    w = globex_week_for(_et(2026, 5, 1, 18, 0))
    assert w.start_utc == _et(2026, 5, 3, 18, 0).astimezone(UTC)
    assert w.end_utc == _et(2026, 5, 8, 17, 0).astimezone(UTC)


def test_week_friday_pre_close_is_current_week():
    """Friday 14:00 → current week (Sun 18 → Fri 17)."""
    w = globex_week_for(_et(2026, 5, 1, 14, 0))
    assert w.start_utc == _et(2026, 4, 26, 18, 0).astimezone(UTC)
    assert w.end_utc == _et(2026, 5, 1, 17, 0).astimezone(UTC)


# ---------- previous_globex_week ----------


def test_previous_week_midweek():
    """This week's previous → Sun-Fri before."""
    prev = previous_globex_week(_et(2026, 5, 6, 12, 0))  # Wed
    assert prev.start_utc == _et(2026, 4, 26, 18, 0).astimezone(UTC)
    assert prev.end_utc == _et(2026, 5, 1, 17, 0).astimezone(UTC)


def test_previous_week_at_sunday_open():
    prev = previous_globex_week(_et(2026, 5, 3, 19, 0))  # Sun open
    assert prev.start_utc == _et(2026, 4, 26, 18, 0).astimezone(UTC)
    assert prev.end_utc == _et(2026, 5, 1, 17, 0).astimezone(UTC)


# ---------- contains() ----------


def test_period_contains_inclusive_start_exclusive_end():
    p: GlobexPeriod = globex_day_for(_et(2026, 5, 5, 14, 0))
    assert p.contains(p.start_utc)
    assert p.contains(p.end_utc - __import__("datetime").timedelta(seconds=1))
    assert not p.contains(p.end_utc)
    assert not p.contains(
        p.start_utc - __import__("datetime").timedelta(seconds=1)
    )
