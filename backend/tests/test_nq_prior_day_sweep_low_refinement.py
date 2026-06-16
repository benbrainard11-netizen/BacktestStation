from __future__ import annotations

import pandas as pd

from app.research.nq_prior_day_sweep_low_refinement import (
    run_prior_day_sweep_low_refinement_study,
)


def test_low_refinement_filters_low_sweeps_and_builds_holdout_validation(tmp_path) -> None:
    attempts_path = tmp_path / "attempts.csv"
    events_path = tmp_path / "events.csv"
    _attempts().to_csv(attempts_path, index=False)
    _events().to_csv(events_path, index=False)

    result = run_prior_day_sweep_low_refinement_study(
        attempts_path=attempts_path,
        events_path=events_path,
        holdout_start="2026-02-01",
        holdout_end="2026-03-01",
    )

    strategy = result["strategy_summary"]
    validation = result["context_validation"]
    monthly = result["monthly_summary"]
    assert strategy.loc[strategy["scope"] == "full", "attempts"].iloc[0] == 4
    assert set(monthly["month"]) == {"2026-01", "2026-02"}
    assert "overnight_range_location_vs_sweep" in validation["factor"].unique()


def _attempts() -> pd.DataFrame:
    rows = []
    for event_id, date, level_type, pnl, exit_reason in [
        ("l1", "2026-01-10", "prior_day_low", 100.0, "target"),
        ("l2", "2026-01-11", "prior_day_low", -80.0, "stop"),
        ("l3", "2026-02-10", "prior_day_low", 120.0, "target"),
        ("l4", "2026-02-11", "prior_day_low", -60.0, "stop"),
        ("h1", "2026-02-12", "prior_day_high", -70.0, "stop"),
    ]:
        rows.append(
            {
                "event_id": event_id,
                "session_date": date,
                "month": date[:7],
                "level_type": level_type,
                "trade_side": "short" if level_type == "prior_day_low" else "long",
                "variant_id": "immediate_sweep__sweep_extreme__fixed_8",
                "status": "filled",
                "exit_reason": exit_reason,
                "pnl": pnl,
            }
        )
    return pd.DataFrame(rows)


def _events() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _event("l1", "2026-01-10", "prior_day_low", "continuation_breakout", 40.0),
            _event("l2", "2026-01-11", "prior_day_low", "failed_breakout_reversal", 20.0),
            _event("l3", "2026-02-10", "prior_day_low", "continuation_breakout", 42.0),
            _event("l4", "2026-02-11", "prior_day_low", "failed_breakout_reversal", 19.0),
            _event("h1", "2026-02-12", "prior_day_high", "failed_breakout_reversal", 18.0),
        ]
    )


def _event(
    event_id: str,
    session_date: str,
    level_type: str,
    label: str,
    activity: float,
) -> dict[str, object]:
    return {
        "event_id": event_id,
        "session_date": session_date,
        "level_type": level_type,
        "level_price": 100.0,
        "sweep_price": 98.0,
        "fixed_outcome_label": label,
        "overnight_range_location_vs_sweep": "near_sweep_side",
        "overnight_range_location": "lower_third",
        "overnight_trend_vs_sweep": "with_sweep",
        "time_of_day_bucket": "opening_drive",
        "opening_drive_aligned": True,
        "rth_gap_vs_sweep": "with_sweep",
        "rth_gap_bucket": "down",
        "pre60_dir_aggr_ratio_band": "mild_with_sweep",
        "time_to_reclaim_level_0_30s": None,
        "post_5_30s_trade_events_per_second": activity,
        "sweep_0_5s_trade_events_per_second": activity,
        "post_5_30s_mbp_events_per_second": activity * 10,
        "sweep_0_5s_mbp_events_per_second": activity * 10,
        "pre_60s_directional_aggressive_trade_ratio": 0.1,
        "directional_overnight_trend_pts": 20.0,
        "directional_rth_gap_pts": 10.0,
        "sweep_minutes_after_rth_open": 5.0,
    }
