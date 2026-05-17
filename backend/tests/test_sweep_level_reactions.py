"""Tests for universal liquidity-sweep level reaction artifacts."""

from __future__ import annotations

import pandas as pd

from app.research.outcomes.level_reactions import level_reaction_column
from scripts.ml.build_sweep_level_reactions import build_age_decay, build_level_reactions, build_stats


def _sample_sweep_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "event_id": "low-sweep",
                "event_type": "pdl_1h",
                "primary_symbol": "ES.c.0",
                "side": "low",
                "bar_end_utc": "2026-01-02T10:00:00+00:00",
                "year": 2026,
                "month": 1,
                "ed.ref_type": "pdl",
                "ed.ref_side": "low",
                "ed.thesis": "bullish",
                "ed.tracking_timeframe": "1h",
                "ed.swept_reference.level_price": 100.0,
                "ed.manipulation_candle.low": 98.0,
                "ed.manipulation_candle.high": 104.0,
                "ed.manipulation_candle.close": 99.0,
                "ed.sweep_depth_pts": 2.0,
                "oc.swept_level_recovery.bars_to_recovery": 2,
                "oc.forward_continuation.bars_to_first_extension": None,
                "oc.ob_confirmation.bars_to_first_ob": 3,
                "oc.forward_3_candles.mfe_pts_in_thesis": 3.0,
                "oc.forward_3_candles.mae_pts_against_thesis": 0.5,
                "oc.forward_10_candles.mfe_pts_in_thesis": 4.0,
                "oc.forward_10_candles.mae_pts_against_thesis": 1.0,
                "oc.forward_50_candles.mfe_pts_in_thesis": 6.0,
                "oc.forward_50_candles.mae_pts_against_thesis": 1.0,
            },
            {
                "event_id": "high-sweep",
                "event_type": "pdh_1h",
                "primary_symbol": "NQ.c.0",
                "side": "high",
                "bar_end_utc": "2026-01-02T10:00:00+00:00",
                "year": 2026,
                "month": 1,
                "ed.ref_type": "pdh",
                "ed.ref_side": "high",
                "ed.thesis": "bearish",
                "ed.tracking_timeframe": "1h",
                "ed.swept_reference.level_price": 200.0,
                "ed.manipulation_candle.low": 197.0,
                "ed.manipulation_candle.high": 203.0,
                "ed.manipulation_candle.close": 201.0,
                "ed.sweep_depth_pts": 3.0,
                "oc.swept_level_recovery.bars_to_recovery": 4,
                "oc.forward_continuation.bars_to_first_extension": 2,
                "oc.ob_confirmation.bars_to_first_ob": 3,
                "oc.forward_3_candles.mfe_pts_in_thesis": 2.0,
                "oc.forward_3_candles.mae_pts_against_thesis": 4.0,
                "oc.forward_10_candles.mfe_pts_in_thesis": 4.0,
                "oc.forward_10_candles.mae_pts_against_thesis": 6.0,
                "oc.forward_50_candles.mfe_pts_in_thesis": 5.0,
                "oc.forward_50_candles.mae_pts_against_thesis": 7.0,
            },
        ]
    )


def test_build_sweep_level_reactions() -> None:
    levels = build_level_reactions(_sample_sweep_frame())

    assert len(levels) == 2
    low = levels[levels["level.event_id"].eq("low-sweep")].iloc[0]
    assert low["level.kind"] == "liquidity_sweep"
    assert low["level.created_ts_utc"].startswith("2026-01-02T11:00:00")
    assert bool(low[level_reaction_column("next_3_bars", "touched")]) is True
    assert bool(low[level_reaction_column("next_3_bars", "meaningful_touch")]) is True
    assert bool(low[level_reaction_column("next_3_bars", "directional_rejection")]) is True
    assert bool(low[level_reaction_column("next_3_bars", "directional_break_acceptance")]) is False
    assert bool(low["lr.next_3_bars.ob_confirmed"]) is True
    assert low[level_reaction_column("next_3_bars", "reaction_away_x_size")] == 1.5
    assert low["level.first_meaningful_touch_age_bucket"] == "1-4h"

    high = levels[levels["level.event_id"].eq("high-sweep")].iloc[0]
    assert bool(high[level_reaction_column("next_3_bars", "meaningful_touch")]) is False
    assert bool(high[level_reaction_column("next_3_bars", "directional_break_acceptance")]) is True
    assert bool(high["lr.next_3_bars.continued_beyond_manipulation"]) is True
    assert bool(high["lr.next_10_bars.sweep_failed_recovered"]) is True
    assert bool(high[level_reaction_column("next_10_bars", "directional_rejection")]) is True


def test_sweep_level_stats_and_age_decay() -> None:
    levels = build_level_reactions(_sample_sweep_frame())
    stats = build_stats(levels)
    age = build_age_decay(levels)

    all_3 = stats[stats["group"].eq("all") & stats["horizon"].eq("next_3_bars")].iloc[0]
    assert all_3["rows"] == 2
    assert all_3["touched_rate"] == 1.0
    assert all_3["meaningful_touch_rate"] == 0.5
    assert all_3["directional_rejection_rate"] == 0.5
    assert all_3["directional_break_acceptance_rate"] == 0.5
    assert set(age["first_meaningful_touch_age_bucket"]) == {"1-4h", "4h-1d"}
