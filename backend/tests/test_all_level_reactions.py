"""Tests for the combined universal level-reaction table."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow as pa

from app.research.outcomes.level_reactions import level_reaction_column
from scripts.ml.build_all_level_reactions import (
    build_horizon_availability,
    build_stats,
    combine_level_frames,
)


def _gap_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "level.event_id": "gap-1",
                "level.kind": "opening_gap",
                "level.subtype": "ndog",
                "level.symbol": "ES.c.0",
                "level.side": "gap_up",
                "level.created_ts_utc": "2026-01-02T00:00:00+00:00",
                "level.price_low": 100.0,
                "level.price_high": 110.0,
                "level.price_mid": 105.0,
                "level.size_pts": 10.0,
                "level.direction": "gap_up",
                "level.first_meaningful_touch_age_bucket": "0-1h",
                "level.first_full_touch_age_bucket": "1-4h",
                level_reaction_column("next_60m", "touched"): True,
                level_reaction_column("next_60m", "meaningful_touch"): True,
                level_reaction_column("next_60m", "directional_rejection"): False,
                level_reaction_column("next_60m", "directional_break_acceptance"): True,
                level_reaction_column("next_60m", "reaction_away_x_size"): 1.5,
                level_reaction_column("full_horizon", "touched"): True,
                level_reaction_column("full_horizon", "meaningful_touch"): True,
                level_reaction_column("full_horizon", "directional_rejection"): False,
                level_reaction_column("full_horizon", "directional_break_acceptance"): True,
                level_reaction_column("full_horizon", "reaction_away_x_size"): 2.0,
            }
        ]
    )


def _fvg_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "level.event_id": "fvg-1",
                "level.kind": "fair_value_gap",
                "level.subtype": "1h_fvg",
                "level.symbol": "NQ.c.0",
                "level.side": "bullish",
                "level.created_ts_utc": "2026-01-02T01:00:00+00:00",
                "level.price_low": 200.0,
                "level.price_high": 220.0,
                "level.price_mid": 210.0,
                "level.size_pts": 20.0,
                "level.direction": "bullish",
                "level.first_meaningful_touch_age_bucket": "1-4h",
                "level.first_full_touch_age_bucket": "1-4h",
                "lr.next_3_bars.touched": True,
                "lr.next_3_bars.meaningful_touch": True,
                "lr.next_3_bars.directional_rejection": True,
                "lr.next_3_bars.directional_break_acceptance": False,
                "lr.next_3_bars.reaction_away_x_size": 1.2,
                "lr.full_horizon.touched": True,
                "lr.full_horizon.meaningful_touch": True,
                "lr.full_horizon.directional_rejection": True,
                "lr.full_horizon.directional_break_acceptance": False,
                "lr.full_horizon.reaction_away_x_size": 3.0,
                "lr.full_horizon.post_tap_mfe_pts": 15.0,
            }
        ]
    )


def test_combine_level_frames_preserves_sources_and_extras() -> None:
    combined = combine_level_frames(
        [
            ("opening_gap", Path("opening_gap_level_reactions.parquet"), "clock_time", _gap_frame()),
            ("fair_value_gap", Path("fvg_level_reactions.parquet"), "native_bars", _fvg_frame()),
        ]
    )

    assert len(combined) == 2
    assert list(combined["level.source_name"]) == ["opening_gap", "fair_value_gap"]
    assert combined["level.event_key"].tolist() == ["opening_gap:gap-1", "fair_value_gap:fvg-1"]
    assert "lr.full_horizon.post_tap_mfe_pts" in combined.columns
    assert pd.isna(combined.loc[0, "lr.full_horizon.post_tap_mfe_pts"])
    assert combined.loc[1, "lr.full_horizon.post_tap_mfe_pts"] == 15.0


def test_combine_level_frames_casts_mixed_event_ids_for_parquet() -> None:
    gap = _gap_frame()
    gap["level.event_id"] = [1]
    fvg = _fvg_frame()
    fvg["level.event_id"] = ["equal_levels-abc"]

    combined = combine_level_frames(
        [
            ("opening_gap", Path("opening_gap_level_reactions.parquet"), "clock_time", gap),
            ("fair_value_gap", Path("fvg_level_reactions.parquet"), "native_bars", fvg),
        ]
    )
    assert combined["level.event_id"].tolist() == ["1", "equal_levels-abc"]
    table = pa.Table.from_pandas(combined, preserve_index=False)
    assert table.schema.field("level.event_id").type == pa.string()


def test_combined_stats_skip_unsupported_horizons() -> None:
    combined = combine_level_frames(
        [
            ("opening_gap", Path("opening_gap_level_reactions.parquet"), "clock_time", _gap_frame()),
            ("fair_value_gap", Path("fvg_level_reactions.parquet"), "native_bars", _fvg_frame()),
        ]
    )
    stats = build_stats(combined)
    availability = build_horizon_availability(combined)

    gap_3 = stats[stats["group"].eq("kind=opening_gap") & stats["horizon"].eq("next_3_bars")].iloc[0]
    assert gap_3["rows_total"] == 1
    assert gap_3["rows_with_horizon"] == 0

    gap_60 = stats[stats["group"].eq("kind=opening_gap") & stats["horizon"].eq("next_60m")].iloc[0]
    assert gap_60["rows_with_horizon"] == 1
    assert gap_60["meaningful_touch_rate"] == 1.0
    assert gap_60["directional_break_acceptance_rate"] == 1.0

    fvg_3 = stats[stats["group"].eq("kind=fair_value_gap") & stats["horizon"].eq("next_3_bars")].iloc[0]
    assert fvg_3["rows_with_horizon"] == 1
    assert fvg_3["directional_rejection_rate"] == 1.0

    fvg_60 = availability[
        availability["level_kind"].eq("fair_value_gap")
        & availability["horizon"].eq("next_60m")
    ].iloc[0]
    assert fvg_60["rows_with_horizon"] == 0
