"""Tests for strict swing-pivot label helpers."""

from __future__ import annotations

import numpy as np

from scripts.ml.build_swing_strict_labels import _window_flags


def _flags(side: str, highs, lows, closes):
    return _window_flags(
        side=side,
        pivot_price=100.0,
        pivot_high=102.0,
        pivot_low=98.0,
        highs=np.asarray(highs, dtype="float64"),
        lows=np.asarray(lows, dtype="float64"),
        closes=np.asarray(closes, dtype="float64"),
        immediate_minutes=3,
        zone_frac=0.50,
        reaction_frac=0.25,
        continuation_frac=0.20,
        min_zone_pts=1.0,
        min_reaction_pts=1.0,
        min_continuation_pts=1.0,
    )


def test_swing_high_held_rejection() -> None:
    flags = _flags(
        "high",
        highs=[99.5, 100.25, 99.75, 98.5],
        lows=[97.5, 96.0, 95.0, 94.0],
        closes=[99.0, 99.5, 98.0, 96.5],
    )

    assert flags["pivot_held_rejection"] is True
    assert flags["pivot_broken_through_continuation"] is False


def test_swing_low_break_continuation() -> None:
    flags = _flags(
        "low",
        highs=[101.0, 100.5, 99.0, 98.0],
        lows=[99.5, 97.5, 96.5, 95.0],
        closes=[99.0, 98.0, 97.0, 96.0],
    )

    assert flags["pivot_broken_through_continuation"] is True
    assert flags["pivot_held_rejection"] is False


def test_partial_test_requires_no_full_touch() -> None:
    flags = _flags(
        "high",
        highs=[98.5, 99.5, 99.0, 98.0],
        lows=[97.0, 96.5, 95.0, 94.0],
        closes=[98.0, 97.5, 96.0, 95.0],
    )

    assert flags["pivot_partial_test_rejected"] is True
    assert flags["pivot_broken_through_continuation"] is False


def test_double_test_held_needs_two_touch_clusters() -> None:
    flags = _flags(
        "high",
        highs=[100.25, 97.5, 100.5, 97.5, 97.0],
        lows=[98.0, 97.0, 96.5, 95.0, 94.0],
        closes=[99.5, 98.0, 99.0, 97.0, 95.0],
    )

    assert flags["pivot_double_test_held"] is True
