"""Tests for stricter volume-profile reaction labels."""

from __future__ import annotations

import pandas as pd

from app.research.outcomes.volume_profile_reactions import level_reaction


def _bars(rows: list[tuple[float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"high": high, "low": low, "close": close} for high, low, close in rows]
    )


def test_level_reaction_support_rejection_after_touch() -> None:
    reaction = level_reaction(
        _bars([
            (101.0, 99.5, 100.5),
            (101.5, 100.1, 100.8),
            (102.0, 100.2, 101.2),
        ]),
        100.0,
        reference_close=101.0,
    )

    assert reaction["first_touch_bars"] == 1
    assert reaction["first_touch_from_above"] is True
    assert reaction["held_above_3bar_after_touch"] is True
    assert reaction["support_rejection_3bar"] is True
    assert reaction["support_break_acceptance_3bar"] is False


def test_level_reaction_resistance_break_acceptance() -> None:
    reaction = level_reaction(
        _bars([
            (100.5, 99.0, 100.25),
            (101.2, 100.1, 100.75),
            (101.5, 100.2, 101.0),
        ]),
        100.0,
        reference_close=99.0,
    )

    assert reaction["first_touch_bars"] == 1
    assert reaction["first_touch_from_below"] is True
    assert reaction["held_above_3bar_after_touch"] is True
    assert reaction["resistance_break_acceptance_3bar"] is True
    assert reaction["resistance_rejection_3bar"] is False


def test_level_reaction_no_touch_has_no_strict_reaction() -> None:
    reaction = level_reaction(
        _bars([
            (99.0, 98.0, 98.5),
            (99.5, 98.5, 99.25),
            (99.75, 98.75, 99.5),
        ]),
        100.0,
        reference_close=98.0,
    )

    assert reaction["first_touch_bars"] is None
    assert reaction["wicked_above"] is False
    assert reaction["accepted_above_3bar"] is False
    assert reaction["support_rejection_3bar"] is False
    assert reaction["resistance_break_acceptance_3bar"] is False
