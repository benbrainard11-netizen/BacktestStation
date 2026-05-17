"""Tests for universal equal-level reaction artifacts."""

from __future__ import annotations

import pandas as pd

from app.research.outcomes.level_reactions import level_reaction_column
from scripts.ml.build_equal_level_reactions import build_age_decay, build_level_reactions, build_stats


def _sample_equal_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "event_id": "eq-high",
                "event_type": "eq_pivot_3_1h_5pts",
                "primary_symbol": "ES.c.0",
                "side": "high",
                "bar_end_utc": "2026-01-02T10:00:00+00:00",
                "year": 2026,
                "month": 1,
                "ed.side": "high",
                "ed.tolerance_pts": 5.0,
                "ed.parent_pivot_mode": "pivot_3_1h",
                "ed.n_members": 2,
                "ed.level_price": 100.0,
                "ed.cluster_mid": 98.0,
                "ed.cluster_spread_pts": 4.0,
                "ed.cluster_min_price": 96.0,
                "ed.cluster_max_price": 100.0,
                "oc.level_price": 100.0,
                "oc.side": "high",
                "oc.thesis_direction": "down",
                "oc.take.wick_taken": True,
                "oc.take.close_past": False,
                "oc.take.bars_to_wick": 3,
                "oc.take.bars_to_close": None,
                "oc.take.deepest_pts_past": 2.0,
                "oc.take.first_take_was_reversal": True,
                "oc.post_take_reaction.forward_5_after_take.mfe_pts_in_thesis": 8.0,
                "oc.post_take_reaction.forward_5_after_take.mae_pts_against_thesis": 1.0,
                "oc.post_take_reaction.forward_25_after_take.mfe_pts_in_thesis": 10.0,
                "oc.post_take_reaction.forward_25_after_take.mae_pts_against_thesis": 2.0,
                "oc.post_take_reaction.forward_100_after_take.mfe_pts_in_thesis": 15.0,
                "oc.post_take_reaction.forward_100_after_take.mae_pts_against_thesis": 2.0,
                "oc.post_take_reaction.forward_250_after_take.mfe_pts_in_thesis": 20.0,
                "oc.post_take_reaction.forward_250_after_take.mae_pts_against_thesis": 3.0,
            },
            {
                "event_id": "eq-low",
                "event_type": "eq_pivot_5_1h_15pts",
                "primary_symbol": "NQ.c.0",
                "side": "low",
                "bar_end_utc": "2026-01-03T10:00:00+00:00",
                "year": 2026,
                "month": 1,
                "ed.side": "low",
                "ed.tolerance_pts": 15.0,
                "ed.parent_pivot_mode": "pivot_5_1h",
                "ed.n_members": 3,
                "ed.level_price": 200.0,
                "ed.cluster_mid": 204.0,
                "ed.cluster_spread_pts": 8.0,
                "ed.cluster_min_price": 200.0,
                "ed.cluster_max_price": 208.0,
                "oc.level_price": 200.0,
                "oc.side": "low",
                "oc.thesis_direction": "up",
                "oc.take.wick_taken": True,
                "oc.take.close_past": True,
                "oc.take.bars_to_wick": 4,
                "oc.take.bars_to_close": 4,
                "oc.take.deepest_pts_past": 16.0,
                "oc.take.first_take_was_reversal": False,
                "oc.post_take_reaction.forward_5_after_take.mfe_pts_in_thesis": 3.0,
                "oc.post_take_reaction.forward_5_after_take.mae_pts_against_thesis": 20.0,
                "oc.post_take_reaction.forward_25_after_take.mfe_pts_in_thesis": 5.0,
                "oc.post_take_reaction.forward_25_after_take.mae_pts_against_thesis": 22.0,
                "oc.post_take_reaction.forward_100_after_take.mfe_pts_in_thesis": 7.0,
                "oc.post_take_reaction.forward_100_after_take.mae_pts_against_thesis": 25.0,
                "oc.post_take_reaction.forward_250_after_take.mfe_pts_in_thesis": 8.0,
                "oc.post_take_reaction.forward_250_after_take.mae_pts_against_thesis": 30.0,
            },
        ]
    )


def test_build_equal_level_reactions() -> None:
    levels = build_level_reactions(_sample_equal_frame())

    assert len(levels) == 2
    high = levels[levels["level.event_id"].eq("eq-high")].iloc[0]
    assert high["level.kind"] == "equal_levels"
    assert high["level.created_ts_utc"].startswith("2026-01-02T14:00:00")
    assert high["level.direction"] == "bearish"
    assert high["level.price_low"] == 96.0
    assert high["level.price_high"] == 100.0
    assert high["level.size_pts"] == 5.0
    assert bool(high[level_reaction_column("next_5_bars", "meaningful_touch")]) is True
    assert bool(high[level_reaction_column("next_5_bars", "full_touch")]) is False
    assert bool(high[level_reaction_column("next_5_bars", "directional_rejection")]) is True
    assert high[level_reaction_column("next_5_bars", "reaction_away_x_size")] == 1.6

    low = levels[levels["level.event_id"].eq("eq-low")].iloc[0]
    assert low["level.created_ts_utc"].startswith("2026-01-03T16:00:00")
    assert bool(low[level_reaction_column("next_5_bars", "full_touch")]) is True
    assert bool(low[level_reaction_column("next_5_bars", "directional_break_acceptance")]) is True
    assert bool(low[level_reaction_column("next_5_bars", "clean_fill_through")]) is True


def test_equal_level_stats_and_age_decay() -> None:
    levels = build_level_reactions(_sample_equal_frame())
    stats = build_stats(levels)
    age = build_age_decay(levels)

    all_5 = stats[stats["group"].eq("all") & stats["horizon"].eq("next_5_bars")].iloc[0]
    assert all_5["rows"] == 2
    assert all_5["meaningful_touch_rate"] == 1.0
    assert all_5["directional_rejection_rate"] == 0.5
    assert all_5["directional_break_acceptance_rate"] == 0.5
    assert set(age["first_meaningful_touch_age_bucket"]) == {"1-4h", "4h-1d"}
