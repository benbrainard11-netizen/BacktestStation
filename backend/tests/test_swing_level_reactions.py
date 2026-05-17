"""Tests for universal swing-pivot level reaction artifacts."""

from __future__ import annotations

import pandas as pd

from app.research.outcomes.level_reactions import level_reaction_column
from scripts.ml.build_swing_level_reactions import build_age_decay, build_level_reactions, build_stats


def _sample_swing_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "event_id": "swing-high",
                "event_type": "pivot_3_1h",
                "primary_symbol": "ES.c.0",
                "side": "high",
                "bar_end_utc": "2026-01-02T10:00:00+00:00",
                "year": 2026,
                "month": 1,
                "ed.n": 3,
                "ed.tracking_timeframe": "1h",
                "ed.pivot_price": 100.0,
                "ed.pivot_bar.high": 100.0,
                "ed.pivot_bar.low": 96.0,
                "ed.pivot_bar.close": 98.0,
                "ed.knowable_ts_utc": "2026-01-02T14:00:00+00:00",
                "oc.thesis_direction": "down",
                "oc.pivot_price": 100.0,
                "oc.reference_close": 98.0,
                "oc.breakout.wick_taken": True,
                "oc.breakout.close_taken": False,
                "oc.breakout.bars_to_wick": 2,
                "oc.breakout.bars_to_close": None,
                "oc.breakout.deepest_breakout_pts": 1.0,
                "oc.extreme.bars_to_extreme": 3,
                "oc.forward_3_candles.mfe_pts_in_thesis": 3.0,
                "oc.forward_3_candles.mae_pts_against_thesis": 1.0,
                "oc.forward_10_candles.mfe_pts_in_thesis": 5.0,
                "oc.forward_10_candles.mae_pts_against_thesis": 1.0,
                "oc.forward_50_candles.mfe_pts_in_thesis": 8.0,
                "oc.forward_50_candles.mae_pts_against_thesis": 1.0,
            },
            {
                "event_id": "swing-low",
                "event_type": "pivot_5_4h",
                "primary_symbol": "NQ.c.0",
                "side": "low",
                "bar_end_utc": "2026-01-03T00:00:00+00:00",
                "year": 2026,
                "month": 1,
                "ed.n": 5,
                "ed.tracking_timeframe": "4h",
                "ed.pivot_price": 200.0,
                "ed.pivot_bar.high": 206.0,
                "ed.pivot_bar.low": 200.0,
                "ed.pivot_bar.close": 205.0,
                "ed.knowable_ts_utc": None,
                "oc.thesis_direction": "up",
                "oc.pivot_price": 200.0,
                "oc.reference_close": 205.0,
                "oc.breakout.wick_taken": True,
                "oc.breakout.close_taken": True,
                "oc.breakout.bars_to_wick": 8,
                "oc.breakout.bars_to_close": 8,
                "oc.breakout.deepest_breakout_pts": 10.0,
                "oc.extreme.bars_to_extreme": 7,
                "oc.forward_3_candles.mfe_pts_in_thesis": 2.0,
                "oc.forward_3_candles.mae_pts_against_thesis": 1.0,
                "oc.forward_10_candles.mfe_pts_in_thesis": 15.0,
                "oc.forward_10_candles.mae_pts_against_thesis": 8.0,
                "oc.forward_50_candles.mfe_pts_in_thesis": 20.0,
                "oc.forward_50_candles.mae_pts_against_thesis": 12.0,
            },
        ]
    )


def test_build_swing_level_reactions() -> None:
    levels = build_level_reactions(_sample_swing_frame())

    assert len(levels) == 2
    high = levels[levels["level.event_id"].eq("swing-high")].iloc[0]
    assert high["level.kind"] == "swing_pivot"
    assert high["level.created_ts_utc"].startswith("2026-01-02T14:00:00")
    assert high["level.direction"] == "bearish"
    assert high["level.size_pts"] == 2.0
    assert bool(high[level_reaction_column("next_3_bars", "meaningful_touch")]) is True
    assert bool(high[level_reaction_column("next_3_bars", "full_touch")]) is False
    assert bool(high[level_reaction_column("next_3_bars", "directional_rejection")]) is True
    assert high[level_reaction_column("next_3_bars", "reaction_away_x_size")] == 1.5
    assert high["level.first_meaningful_touch_age_bucket"] == "1-4h"

    low = levels[levels["level.event_id"].eq("swing-low")].iloc[0]
    assert low["level.created_ts_utc"].startswith("2026-01-04T00:00:00")
    assert bool(low[level_reaction_column("next_3_bars", "meaningful_touch")]) is False
    assert bool(low[level_reaction_column("next_10_bars", "full_touch")]) is True
    assert bool(low[level_reaction_column("next_10_bars", "directional_break_acceptance")]) is True


def test_swing_level_stats_and_age_decay() -> None:
    levels = build_level_reactions(_sample_swing_frame())
    stats = build_stats(levels)
    age = build_age_decay(levels)

    all_3 = stats[stats["group"].eq("all") & stats["horizon"].eq("next_3_bars")].iloc[0]
    assert all_3["rows"] == 2
    assert all_3["meaningful_touch_rate"] == 0.5
    assert all_3["directional_rejection_rate"] == 0.5
    assert set(age["first_meaningful_touch_age_bucket"]) == {"1-4h", "1-3d"}
