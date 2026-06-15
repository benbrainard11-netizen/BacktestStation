from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_types import LiquiditySweepStudyConfig
from app.research.nq_prior_day_sweep_decision_tree import categorical_decision_table
from app.research.nq_prior_day_sweep_decision_tree_context import (
    direction_bucket,
    pre60_directional_aggressive_ratio_band,
    range_location_bucket,
    range_location_vs_sweep,
    time_of_day_bucket,
)
from app.research.nq_prior_day_sweep_decision_tree_labels import (
    fixed_target_label_for_event,
    fixed_target_label_for_event_from_bars,
)
from app.research.nq_prior_day_sweep_decision_tree_types import (
    AMB,
    CONT,
    REV,
    DecisionTreeStudyConfig,
)

UTC = dt.UTC


def test_fixed_high_target_label_starts_after_feature_window() -> None:
    sweep_ts = dt.datetime(2026, 5, 6, 13, 36, tzinfo=UTC)
    mbp1 = _mbp(
        [
            _trade(sweep_ts + dt.timedelta(seconds=10), 108.25),
            _trade(sweep_ts + dt.timedelta(seconds=40), 108.25),
        ]
    )
    event = SimpleNamespace(
        session_date="2026-05-06",
        sweep_ts=sweep_ts,
        level_price=100.0,
        sweep_side="high",
    )

    label, hit_ts, error = fixed_target_label_for_event(
        mbp1,
        event,
        config=DecisionTreeStudyConfig(fixed_target_pts=8.0),
        sweep_config=LiquiditySweepStudyConfig(),
    )

    assert label == CONT
    assert hit_ts == sweep_ts + dt.timedelta(seconds=40)
    assert error is None


def test_fixed_low_target_reversal_label() -> None:
    sweep_ts = dt.datetime(2026, 5, 6, 13, 36, tzinfo=UTC)
    mbp1 = _mbp([_trade(sweep_ts + dt.timedelta(seconds=45), 108.25)])
    event = SimpleNamespace(
        session_date="2026-05-06",
        sweep_ts=sweep_ts,
        level_price=100.0,
        sweep_side="low",
    )

    label, _, _ = fixed_target_label_for_event(
        mbp1,
        event,
        config=DecisionTreeStudyConfig(fixed_target_pts=8.0),
        sweep_config=LiquiditySweepStudyConfig(),
    )

    assert label == REV


def test_bar_label_starts_on_next_complete_minute_and_marks_conflicts_ambiguous() -> None:
    sweep_ts = pd.Timestamp("2026-05-06T13:36:20Z")
    bars = pd.DataFrame(
        [
            {"open": 100, "high": 108.25, "low": 99, "close": 108},
            {"open": 108, "high": 109, "low": 91.75, "close": 100},
        ],
        index=pd.DatetimeIndex(
            [
                pd.Timestamp("2026-05-06T13:36:00Z"),
                pd.Timestamp("2026-05-06T13:37:00Z"),
            ]
        ),
    )
    event = SimpleNamespace(
        session_date="2026-05-06",
        sweep_ts=sweep_ts,
        level_price=100.0,
        sweep_side="high",
    )

    label, hit_ts, error = fixed_target_label_for_event_from_bars(
        bars,
        event,
        config=DecisionTreeStudyConfig(fixed_target_pts=8.0),
        sweep_config=LiquiditySweepStudyConfig(),
    )

    assert label == AMB
    assert hit_ts == dt.datetime(2026, 5, 6, 13, 37, tzinfo=UTC)
    assert error == "same_bar_both_targets"


def test_fixed_context_bins_are_predeclared() -> None:
    assert direction_bucket(9.0, 8.0) == "with_sweep"
    assert direction_bucket(-9.0, 8.0) == "against_sweep"
    assert direction_bucket(2.0, 8.0) == "neutral"
    assert range_location_bucket(0.20) == "lower_third"
    assert range_location_bucket(0.50) == "middle_third"
    assert range_location_bucket(0.90) == "upper_third"
    assert range_location_vs_sweep("upper_third", "high") == "near_sweep_side"
    assert range_location_vs_sweep("upper_third", "low") == "away_from_sweep_side"
    assert pre60_directional_aggressive_ratio_band(-0.30) == "strong_against_sweep"
    assert pre60_directional_aggressive_ratio_band(0.00) == "neutral"
    assert pre60_directional_aggressive_ratio_band(0.30) == "strong_with_sweep"
    assert time_of_day_bucket(pd.Timestamp("2026-05-06T13:36:00Z")) == "opening_drive"


def test_walk_forward_decision_table_scores_stable_contexts() -> None:
    rows = []
    for month in pd.period_range("2026-01", "2026-06", freq="M").astype(str):
        for idx in range(5):
            rows.append(_row(month, "good", CONT if idx < 4 else REV))
            rows.append(_row(month, "bad", CONT if idx == 0 else REV))
    df = pd.DataFrame(rows)

    table = categorical_decision_table(
        df,
        ["ctx"],
        DecisionTreeStudyConfig(min_train_months=2, min_category_train_sample=4),
    )
    good = table.loc[table["category"] == "good"].iloc[0]
    bad = table.loc[table["category"] == "bad"].iloc[0]

    assert good["oos_delta"] > 0
    assert good["verdict"] == "historically_improved"
    assert bad["oos_delta"] < 0
    assert bad["verdict"] == "historically_worsened"


def _trade(ts: dt.datetime, price: float) -> dict[str, object]:
    return {
        "ts_event": ts,
        "action": "T",
        "price": price,
    }


def _mbp(rows: list[dict[str, object]]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df.index = pd.DatetimeIndex(df["ts_event"])
    return df


def _row(month: str, ctx: str, label: str) -> dict[str, object]:
    return {
        "month": month,
        "session_date": f"{month}-01",
        "ctx": ctx,
        "fixed_outcome_label": label,
    }
