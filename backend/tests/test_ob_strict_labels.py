"""Tests for strict order-block label helpers."""

from __future__ import annotations

import numpy as np

from scripts.ml.build_ob_strict_labels import _window_flags


def _flags(side: str, highs, lows, closes):
    return _window_flags(
        side=side,
        body_top=100.0,
        body_bottom=96.0,
        body_width=4.0,
        range_top=101.0,
        range_bottom=95.0,
        range_width=6.0,
        highs=np.asarray(highs, dtype="float64"),
        lows=np.asarray(lows, dtype="float64"),
        closes=np.asarray(closes, dtype="float64"),
        immediate_minutes=3,
        deep_frac=0.70,
        reaction_frac=0.18,
        continuation_frac=0.55,
        sweep_buffer_frac=0.05,
        min_reaction_pts=1.0,
        min_continuation_pts=1.0,
        min_sweep_buffer_pts=0.25,
    )


def test_bullish_ob_partial_test_rejected() -> None:
    flags = _flags(
        "bullish",
        highs=[101.0, 101.5, 103.0, 102.0],
        lows=[99.5, 98.5, 99.0, 100.5],
        closes=[100.5, 100.0, 101.5, 101.0],
    )

    assert flags["ob_respected_partial_test"] is True
    assert flags["ob_broken_through_continuation"] is False


def test_bearish_ob_break_continuation() -> None:
    flags = _flags(
        "bearish",
        highs=[98.0, 100.5, 101.5, 103.0],
        lows=[95.0, 96.0, 98.0, 99.5],
        closes=[97.0, 100.5, 101.0, 102.0],
    )

    assert flags["ob_broken_through_continuation"] is True
    assert flags["ob_respected_partial_test"] is False


def test_bullish_ob_swept_and_recovered() -> None:
    flags = _flags(
        "bullish",
        highs=[100.0, 99.0, 101.5, 103.0],
        lows=[97.0, 94.0, 96.0, 99.0],
        closes=[97.0, 95.0, 99.0, 101.0],
    )

    assert flags["ob_swept_and_recovered"] is True
    assert flags["ob_failed_immediately"] is True


def test_bearish_ob_immediate_fail() -> None:
    flags = _flags(
        "bearish",
        highs=[98.0, 102.0, 104.0, 103.0],
        lows=[96.0, 97.0, 99.0, 100.0],
        closes=[97.0, 101.0, 102.5, 102.0],
    )

    assert flags["ob_failed_immediately"] is True
    assert flags["ob_broken_through_continuation"] is True


def test_invalid_side_returns_false_flags() -> None:
    flags = _flags(
        "low",
        highs=[101.0],
        lows=[99.0],
        closes=[100.0],
    )

    assert all(value is False for value in flags.values())
