"""Tests for level reaction leaderboard scoring."""

from __future__ import annotations

import pandas as pd

from app.research.outcomes.level_reactions import level_reaction_column
from scripts.ml.build_level_reaction_leaderboard import build_leaderboard


def _rows(
    *,
    n: int,
    kind: str,
    subtype: str,
    side: str,
    horizon: str,
    reject: bool,
    brk: bool,
) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for i in range(n):
        out.append(
            {
                "level.kind": kind,
                "level.subtype": subtype,
                "level.side": side,
                "level.horizon_style": "native_bars",
                f"lr.{horizon}.touched": True,
                level_reaction_column(horizon, "meaningful_touch"): True,
                level_reaction_column(horizon, "directional_rejection"): reject,
                level_reaction_column(horizon, "directional_break_acceptance"): brk,
                level_reaction_column(horizon, "clean_fill_through"): brk,
                level_reaction_column(horizon, "reaction_away_x_size"): 2.0,
            }
        )
    return out


def test_leaderboard_scores_dominant_rejection_and_break() -> None:
    df = pd.DataFrame(
        [
            *_rows(n=300, kind="fair_value_gap", subtype="1h_fvg", side="bullish", horizon="next_3_bars", reject=True, brk=False),
            *_rows(n=300, kind="order_block", subtype="swept_pdh_1h", side="bearish", horizon="next_3_bars", reject=False, brk=True),
            *_rows(n=300, kind="liquidity_sweep", subtype="pdl_1h", side="low", horizon="next_3_bars", reject=True, brk=True),
        ]
    )

    leaderboard = build_leaderboard(df, min_rows=50, full_weight_rows=300)
    kind_rows = leaderboard[
        leaderboard["segment_level"].eq("kind")
        & leaderboard["horizon"].eq("next_3_bars")
    ]

    fvg = kind_rows[kind_rows["level_kind"].eq("fair_value_gap")].iloc[0]
    assert fvg["dominant_behavior"] == "rejection"
    assert fvg["action_hint"] == "rejection_bias"
    assert fvg["reject_score"] > 0

    ob = kind_rows[kind_rows["level_kind"].eq("order_block")].iloc[0]
    assert ob["dominant_behavior"] == "break"
    assert ob["action_hint"] == "break_continuation_bias"
    assert ob["break_score"] > 0

    mixed = kind_rows[kind_rows["level_kind"].eq("liquidity_sweep")].iloc[0]
    assert mixed["clean_signal_score"] == 0
    assert mixed["action_hint"] == "mixed_or_weak"


def test_leaderboard_downweights_small_samples() -> None:
    df = pd.DataFrame(
        [
            *_rows(n=10, kind="tiny", subtype="tiny_a", side="x", horizon="next_3_bars", reject=True, brk=False),
            *_rows(n=500, kind="large", subtype="large_a", side="x", horizon="next_3_bars", reject=True, brk=False),
        ]
    )

    leaderboard = build_leaderboard(df, min_rows=50, full_weight_rows=500)
    kind_rows = leaderboard[
        leaderboard["segment_level"].eq("kind")
        & leaderboard["horizon"].eq("next_3_bars")
    ]

    tiny = kind_rows[kind_rows["level_kind"].eq("tiny")].iloc[0]
    large = kind_rows[kind_rows["level_kind"].eq("large")].iloc[0]
    assert tiny["sample_weight"] < large["sample_weight"]
    assert tiny["clean_signal_score"] < large["clean_signal_score"]
    assert tiny["tier"] == "small_sample"
