"""Tests for universal FVG level reaction artifacts."""

from __future__ import annotations

import pandas as pd

from app.research.outcomes.level_reactions import level_reaction_column
from scripts.ml.build_fvg_level_reactions import build_age_decay, build_level_reactions, build_stats


def _sample_fvg_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "event_id": "bull-fvg",
                "event_type": "1h_fvg",
                "primary_symbol": "ES.c.0",
                "side": "bullish",
                "bar_end_utc": "2026-01-02T10:00:00+00:00",
                "year": 2026,
                "month": 1,
                "ed.tracking_timeframe": "1h",
                "ed.direction": "bullish",
                "ed.fvg_low": 100.0,
                "ed.fvg_high": 110.0,
                "ed.fvg_mid": 105.0,
                "ed.fvg_width_pts": 10.0,
                "oc.mitigation.bars_to_tap": 2,
                "oc.mitigation.bars_to_mid": None,
                "oc.mitigation.bars_to_full": None,
                "oc.mitigation.bars_to_close_inside": None,
                "oc.mitigation.bars_to_close_through": None,
                "oc.mitigation.tap_bar_classification": "wick_reject",
                "oc.zone_reaction.took_fvg_low_rejected_inside": True,
                "oc.zone_reaction.took_fvg_high_rejected_inside": False,
                "oc.forward_3_candles.mfe_pts_in_thesis": 12.0,
                "oc.forward_3_candles.mae_pts_against_thesis": 3.0,
                "oc.forward_10_candles.mfe_pts_in_thesis": 20.0,
                "oc.forward_10_candles.mae_pts_against_thesis": 4.0,
                "oc.forward_50_candles.mfe_pts_in_thesis": 30.0,
                "oc.forward_50_candles.mae_pts_against_thesis": 4.0,
                "oc.post_tap_reaction.forward_3_after_tap.mfe_pts_in_thesis": 9.0,
                "oc.post_tap_reaction.forward_3_after_tap.mae_pts_against_thesis": 2.0,
                "oc.post_tap_reaction.forward_10_after_tap.mfe_pts_in_thesis": 14.0,
                "oc.post_tap_reaction.forward_10_after_tap.mae_pts_against_thesis": 2.0,
                "oc.post_tap_reaction.forward_50_after_tap.mfe_pts_in_thesis": 22.0,
                "oc.post_tap_reaction.forward_50_after_tap.mae_pts_against_thesis": 2.0,
            },
            {
                "event_id": "bear-fvg",
                "event_type": "15m_fvg",
                "primary_symbol": "NQ.c.0",
                "side": "bearish",
                "bar_end_utc": "2026-01-02T10:15:00+00:00",
                "year": 2026,
                "month": 1,
                "ed.tracking_timeframe": "15m",
                "ed.direction": "bearish",
                "ed.fvg_low": 200.0,
                "ed.fvg_high": 220.0,
                "ed.fvg_mid": 210.0,
                "ed.fvg_width_pts": 20.0,
                "oc.mitigation.bars_to_tap": 1,
                "oc.mitigation.bars_to_mid": 2,
                "oc.mitigation.bars_to_full": 3,
                "oc.mitigation.bars_to_close_inside": 2,
                "oc.mitigation.bars_to_close_through": 4,
                "oc.mitigation.tap_bar_classification": "close_inside",
                "oc.zone_reaction.took_fvg_low_rejected_inside": False,
                "oc.zone_reaction.took_fvg_high_rejected_inside": False,
                "oc.forward_3_candles.mfe_pts_in_thesis": 10.0,
                "oc.forward_3_candles.mae_pts_against_thesis": 25.0,
                "oc.forward_10_candles.mfe_pts_in_thesis": 25.0,
                "oc.forward_10_candles.mae_pts_against_thesis": 30.0,
                "oc.forward_50_candles.mfe_pts_in_thesis": 60.0,
                "oc.forward_50_candles.mae_pts_against_thesis": 30.0,
                "oc.post_tap_reaction.forward_3_after_tap.mfe_pts_in_thesis": 5.0,
                "oc.post_tap_reaction.forward_3_after_tap.mae_pts_against_thesis": 25.0,
                "oc.post_tap_reaction.forward_10_after_tap.mfe_pts_in_thesis": 24.0,
                "oc.post_tap_reaction.forward_10_after_tap.mae_pts_against_thesis": 20.0,
                "oc.post_tap_reaction.forward_50_after_tap.mfe_pts_in_thesis": 50.0,
                "oc.post_tap_reaction.forward_50_after_tap.mae_pts_against_thesis": 20.0,
            },
        ]
    )


def test_build_fvg_level_reactions() -> None:
    levels = build_level_reactions(_sample_fvg_frame())

    assert len(levels) == 2
    bull = levels[levels["level.event_id"].eq("bull-fvg")].iloc[0]
    assert bull["level.kind"] == "fair_value_gap"
    assert bull["level.created_ts_utc"].startswith("2026-01-02T11:00:00")
    assert bool(bull[level_reaction_column("next_3_bars", "meaningful_touch")]) is True
    assert bool(bull[level_reaction_column("next_3_bars", "partial_touch")]) is True
    assert bool(bull[level_reaction_column("next_3_bars", "directional_rejection")]) is True
    assert bool(bull[level_reaction_column("next_3_bars", "unfilled_expanded_away")]) is True
    assert bull[level_reaction_column("next_3_bars", "reaction_away_x_size")] == 1.2
    assert bull["level.first_meaningful_touch_age_bucket"] == "1-4h"

    bear = levels[levels["level.event_id"].eq("bear-fvg")].iloc[0]
    assert bear["level.created_ts_utc"].startswith("2026-01-02T10:30:00")
    assert bool(bear[level_reaction_column("next_3_bars", "full_touch")]) is True
    assert bool(bear[level_reaction_column("next_3_bars", "clean_fill_through")]) is False
    assert bool(bear[level_reaction_column("next_10_bars", "clean_fill_through")]) is True
    assert bear["level.first_full_touch_age_bucket"] == "0-1h"


def test_fvg_level_stats_and_age_decay() -> None:
    levels = build_level_reactions(_sample_fvg_frame())
    stats = build_stats(levels)
    age = build_age_decay(levels)

    all_3 = stats[stats["group"].eq("all") & stats["horizon"].eq("next_3_bars")].iloc[0]
    assert all_3["rows"] == 2
    assert all_3["meaningful_touch_rate"] == 1.0
    assert all_3["full_touch_rate"] == 0.5
    assert all_3["clean_fill_through_rate"] == 0.0
    assert set(age["first_meaningful_touch_age_bucket"]) == {"0-1h", "1-4h"}
