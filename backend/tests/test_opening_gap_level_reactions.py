"""Tests for universal opening-gap level reaction artifacts."""

from __future__ import annotations

import pandas as pd

from app.research.outcomes.level_reactions import age_bucket_minutes, level_reaction_column
from scripts.ml.build_opening_gap_level_reactions import (
    build_age_decay,
    build_level_reactions,
    build_stats,
)


def _sample_ogap_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "event_id": "gap-up",
                "event_type": "ndog",
                "primary_symbol": "ES.c.0",
                "side": "gap_up",
                "bar_end_utc": "2026-01-02T23:00:00+00:00",
                "year": 2026,
                "month": 1,
                "ed.gap_open_ts_utc": "2026-01-02T23:00:00+00:00",
                "ed.gap_low": 100.0,
                "ed.gap_high": 110.0,
                "ed.gap_mid": 105.0,
                "ed.gap_size_pts": 10.0,
                "ed.gap_direction": "gap_up",
                "oc.next_60m.touched_gap": True,
                "oc.next_60m.fully_filled": False,
                "oc.next_60m.touched_midpoint": True,
                "oc.next_60m.support_rejection_3bar": True,
                "oc.next_60m.resistance_rejection_3bar": False,
                "oc.next_60m.support_break_acceptance_3bar": False,
                "oc.next_60m.resistance_break_acceptance_3bar": False,
                "oc.next_60m.accepted_above_3bar": True,
                "oc.next_60m.accepted_below_3bar": False,
                "oc.next_60m.closed_above_gap_high": True,
                "oc.next_60m.closed_below_gap_low": False,
                "oc.next_60m.took_gap_low_rejected_inside": False,
                "oc.next_60m.took_gap_high_rejected_inside": False,
                "oc.next_60m.unfilled_at_window_end": True,
                "oc.next_60m.mfe_up_pts": 12.0,
                "oc.next_60m.mfe_down_pts": 3.0,
                "oc.next_60m.forward_low": 104.0,
                "oc.next_60m.forward_high": 122.0,
                "oc.next_60m.first_touch_minutes": 15.0,
                "oc.next_60m.first_midpoint_minutes": 30.0,
                "oc.next_60m.first_full_fill_minutes": None,
                "oc.full_horizon.touched_gap": True,
                "oc.full_horizon.fully_filled": False,
                "oc.full_horizon.touched_midpoint": True,
                "oc.full_horizon.support_rejection_3bar": True,
                "oc.full_horizon.resistance_rejection_3bar": False,
                "oc.full_horizon.support_break_acceptance_3bar": False,
                "oc.full_horizon.resistance_break_acceptance_3bar": False,
                "oc.full_horizon.accepted_above_3bar": True,
                "oc.full_horizon.accepted_below_3bar": False,
                "oc.full_horizon.closed_above_gap_high": True,
                "oc.full_horizon.closed_below_gap_low": False,
                "oc.full_horizon.took_gap_low_rejected_inside": False,
                "oc.full_horizon.took_gap_high_rejected_inside": False,
                "oc.full_horizon.unfilled_at_window_end": True,
                "oc.full_horizon.mfe_up_pts": 20.0,
                "oc.full_horizon.mfe_down_pts": 3.0,
                "oc.full_horizon.forward_low": 104.0,
                "oc.full_horizon.forward_high": 130.0,
                "oc.full_horizon.first_touch_minutes": 15.0,
                "oc.full_horizon.first_midpoint_minutes": 30.0,
                "oc.full_horizon.first_full_fill_minutes": None,
            },
            {
                "event_id": "gap-down",
                "event_type": "nwog",
                "primary_symbol": "NQ.c.0",
                "side": "gap_down",
                "bar_end_utc": "2026-01-05T23:00:00+00:00",
                "year": 2026,
                "month": 1,
                "ed.gap_open_ts_utc": "2026-01-05T23:00:00+00:00",
                "ed.gap_low": 200.0,
                "ed.gap_high": 220.0,
                "ed.gap_mid": 210.0,
                "ed.gap_size_pts": 20.0,
                "ed.gap_direction": "gap_down",
                "oc.next_60m.touched_gap": True,
                "oc.next_60m.fully_filled": True,
                "oc.next_60m.touched_midpoint": True,
                "oc.next_60m.support_rejection_3bar": False,
                "oc.next_60m.resistance_rejection_3bar": False,
                "oc.next_60m.support_break_acceptance_3bar": False,
                "oc.next_60m.resistance_break_acceptance_3bar": True,
                "oc.next_60m.accepted_above_3bar": True,
                "oc.next_60m.accepted_below_3bar": False,
                "oc.next_60m.closed_above_gap_high": True,
                "oc.next_60m.closed_below_gap_low": False,
                "oc.next_60m.took_gap_low_rejected_inside": False,
                "oc.next_60m.took_gap_high_rejected_inside": False,
                "oc.next_60m.unfilled_at_window_end": False,
                "oc.next_60m.mfe_up_pts": 25.0,
                "oc.next_60m.mfe_down_pts": 9.0,
                "oc.next_60m.forward_low": 191.0,
                "oc.next_60m.forward_high": 245.0,
                "oc.next_60m.first_touch_minutes": 75.0,
                "oc.next_60m.first_midpoint_minutes": 80.0,
                "oc.next_60m.first_full_fill_minutes": 90.0,
                "oc.full_horizon.touched_gap": True,
                "oc.full_horizon.fully_filled": True,
                "oc.full_horizon.touched_midpoint": True,
                "oc.full_horizon.support_rejection_3bar": False,
                "oc.full_horizon.resistance_rejection_3bar": False,
                "oc.full_horizon.support_break_acceptance_3bar": False,
                "oc.full_horizon.resistance_break_acceptance_3bar": True,
                "oc.full_horizon.accepted_above_3bar": True,
                "oc.full_horizon.accepted_below_3bar": False,
                "oc.full_horizon.closed_above_gap_high": True,
                "oc.full_horizon.closed_below_gap_low": False,
                "oc.full_horizon.took_gap_low_rejected_inside": False,
                "oc.full_horizon.took_gap_high_rejected_inside": False,
                "oc.full_horizon.unfilled_at_window_end": False,
                "oc.full_horizon.mfe_up_pts": 30.0,
                "oc.full_horizon.mfe_down_pts": 9.0,
                "oc.full_horizon.forward_low": 191.0,
                "oc.full_horizon.forward_high": 250.0,
                "oc.full_horizon.first_touch_minutes": 75.0,
                "oc.full_horizon.first_midpoint_minutes": 80.0,
                "oc.full_horizon.first_full_fill_minutes": 90.0,
            },
        ]
    )


def test_age_bucket_minutes() -> None:
    assert age_bucket_minutes(0) == "0-1h"
    assert age_bucket_minutes(60) == "1-4h"
    assert age_bucket_minutes(24 * 60) == "1-3d"
    assert age_bucket_minutes(None) == "unreached_20d"


def test_build_opening_gap_level_reactions() -> None:
    levels = build_level_reactions(_sample_ogap_frame())

    assert len(levels) == 2
    up = levels[levels["level.event_id"].eq("gap-up")].iloc[0]
    assert up["level.kind"] == "opening_gap"
    assert bool(up[level_reaction_column("next_60m", "partial_touch")]) is True
    assert bool(up[level_reaction_column("next_60m", "directional_rejection")]) is True
    assert bool(up[level_reaction_column("next_60m", "unfilled_expanded_away")]) is True
    assert up[level_reaction_column("next_60m", "reaction_away_x_size")] == 1.2
    assert up["level.first_meaningful_touch_age_bucket"] == "0-1h"

    down = levels[levels["level.event_id"].eq("gap-down")].iloc[0]
    assert bool(down[level_reaction_column("next_60m", "full_touch")]) is True
    assert bool(down[level_reaction_column("next_60m", "directional_break_acceptance")]) is True
    assert bool(down[level_reaction_column("next_60m", "clean_fill_through")]) is True
    assert down["level.first_meaningful_touch_age_bucket"] == "1-4h"


def test_opening_gap_level_stats_and_age_decay() -> None:
    levels = build_level_reactions(_sample_ogap_frame())
    stats = build_stats(levels)
    age = build_age_decay(levels)

    all_60m = stats[stats["group"].eq("all") & stats["horizon"].eq("next_60m")].iloc[0]
    assert all_60m["rows"] == 2
    assert all_60m["touched_rate"] == 1.0
    assert all_60m["partial_touch_rate"] == 0.5
    assert all_60m["clean_fill_through_rate"] == 0.5
    assert set(age["first_meaningful_touch_age_bucket"]) == {"0-1h", "1-4h"}
