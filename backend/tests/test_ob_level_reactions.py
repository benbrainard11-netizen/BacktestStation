"""Tests for universal order-block level reaction artifacts."""

from __future__ import annotations

import pandas as pd

from app.research.outcomes.level_reactions import level_reaction_column
from scripts.ml.build_ob_level_reactions import build_age_decay, build_level_reactions, build_stats


def _sample_ob_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "event_id": "bull-ob",
                "event_type": "swept_pdl_1h",
                "primary_symbol": "ES.c.0",
                "side": "bullish",
                "bar_end_utc": "2026-01-02T10:00:00+00:00",
                "year": 2026,
                "month": 1,
                "ed.tracking_timeframe": "1h",
                "ed.direction": "bullish",
                "ed.ob_body_bottom": 100.0,
                "ed.ob_body_top": 110.0,
                "ed.ob_body_mid": 105.0,
                "ed.ob_body_width_pts": 10.0,
                "ed.ob_range_bottom": 95.0,
                "ed.ob_range_top": 112.0,
                "ed.ob_range_width_pts": 17.0,
                "oc.level_tags.open.bars_to_wick_tap": 1,
                "oc.level_tags.open.bars_to_close_past": 2,
                "oc.level_tags.q25.bars_to_wick_tap": 2,
                "oc.level_tags.q50.bars_to_wick_tap": None,
                "oc.level_tags.q75.bars_to_wick_tap": None,
                "oc.level_tags.close.bars_to_wick_tap": None,
                "oc.level_tags.range_far.bars_to_wick_tap": None,
                "oc.invalidation.bars_to_invalidation": None,
                "oc.forward_3_candles.mfe_pts_in_thesis": 12.0,
                "oc.forward_3_candles.mae_pts_against_thesis": 3.0,
                "oc.forward_10_candles.mfe_pts_in_thesis": 20.0,
                "oc.forward_10_candles.mae_pts_against_thesis": 4.0,
                "oc.forward_50_candles.mfe_pts_in_thesis": 30.0,
                "oc.forward_50_candles.mae_pts_against_thesis": 4.0,
                "oc.post_tap_reactions.open_tap.forward_3_after_tap.mfe_pts_in_thesis": 9.0,
                "oc.post_tap_reactions.open_tap.forward_3_after_tap.mae_pts_against_thesis": 2.0,
                "oc.post_tap_reactions.close_tap.forward_3_after_tap.mfe_pts_in_thesis": None,
                "oc.post_tap_reactions.close_tap.forward_3_after_tap.mae_pts_against_thesis": None,
            },
            {
                "event_id": "bear-ob",
                "event_type": "swept_pdh_1h",
                "primary_symbol": "NQ.c.0",
                "side": "bearish",
                "bar_end_utc": "2026-01-02T10:00:00+00:00",
                "year": 2026,
                "month": 1,
                "ed.tracking_timeframe": "1h",
                "ed.direction": "bearish",
                "ed.ob_body_bottom": 200.0,
                "ed.ob_body_top": 220.0,
                "ed.ob_body_mid": 210.0,
                "ed.ob_body_width_pts": 20.0,
                "ed.ob_range_bottom": 198.0,
                "ed.ob_range_top": 225.0,
                "ed.ob_range_width_pts": 27.0,
                "oc.level_tags.open.bars_to_wick_tap": 1,
                "oc.level_tags.open.bars_to_close_past": 1,
                "oc.level_tags.q25.bars_to_wick_tap": 2,
                "oc.level_tags.q50.bars_to_wick_tap": 2,
                "oc.level_tags.q75.bars_to_wick_tap": 3,
                "oc.level_tags.close.bars_to_wick_tap": 3,
                "oc.level_tags.range_far.bars_to_wick_tap": 4,
                "oc.invalidation.bars_to_invalidation": 4,
                "oc.forward_3_candles.mfe_pts_in_thesis": 10.0,
                "oc.forward_3_candles.mae_pts_against_thesis": 25.0,
                "oc.forward_10_candles.mfe_pts_in_thesis": 25.0,
                "oc.forward_10_candles.mae_pts_against_thesis": 30.0,
                "oc.forward_50_candles.mfe_pts_in_thesis": 60.0,
                "oc.forward_50_candles.mae_pts_against_thesis": 30.0,
                "oc.post_tap_reactions.open_tap.forward_3_after_tap.mfe_pts_in_thesis": 5.0,
                "oc.post_tap_reactions.open_tap.forward_3_after_tap.mae_pts_against_thesis": 25.0,
                "oc.post_tap_reactions.close_tap.forward_3_after_tap.mfe_pts_in_thesis": 4.0,
                "oc.post_tap_reactions.close_tap.forward_3_after_tap.mae_pts_against_thesis": 20.0,
            },
        ]
    )


def test_build_ob_level_reactions() -> None:
    levels = build_level_reactions(_sample_ob_frame())

    assert len(levels) == 2
    bull = levels[levels["level.event_id"].eq("bull-ob")].iloc[0]
    assert bull["level.kind"] == "order_block"
    assert bull["level.created_ts_utc"].startswith("2026-01-02T11:00:00")
    assert bool(bull[level_reaction_column("next_3_bars", "meaningful_touch")]) is True
    assert bool(bull[level_reaction_column("next_3_bars", "partial_touch")]) is True
    assert bool(bull[level_reaction_column("next_3_bars", "directional_rejection")]) is True
    assert bool(bull[level_reaction_column("next_3_bars", "full_touch")]) is False
    assert bull[level_reaction_column("next_3_bars", "reaction_away_x_size")] == 1.2
    assert bull["level.first_meaningful_touch_age_bucket"] == "1-4h"

    bear = levels[levels["level.event_id"].eq("bear-ob")].iloc[0]
    assert bool(bear[level_reaction_column("next_3_bars", "full_touch")]) is True
    assert bool(bear[level_reaction_column("next_3_bars", "clean_fill_through")]) is False
    assert bool(bear[level_reaction_column("next_10_bars", "clean_fill_through")]) is True
    assert bool(bear["lr.next_10_bars.range_far_touched"]) is True
    assert bear["level.first_full_touch_age_bucket"] == "1-4h"


def test_ob_level_stats_and_age_decay() -> None:
    levels = build_level_reactions(_sample_ob_frame())
    stats = build_stats(levels)
    age = build_age_decay(levels)

    all_3 = stats[stats["group"].eq("all") & stats["horizon"].eq("next_3_bars")].iloc[0]
    assert all_3["rows"] == 2
    assert all_3["meaningful_touch_rate"] == 1.0
    assert all_3["full_touch_rate"] == 0.5
    assert all_3["clean_fill_through_rate"] == 0.0
    assert set(age["first_meaningful_touch_age_bucket"]) == {"1-4h"}
