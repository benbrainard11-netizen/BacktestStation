from __future__ import annotations

import pandas as pd

from app.research.nq_prior_day_sweep_failure_modes import (
    run_prior_day_sweep_failure_mode_analysis,
)


def test_failure_mode_analysis_joins_attempts_and_summarizes_holdout(tmp_path) -> None:
    attempts_path = tmp_path / "attempts.csv"
    events_path = tmp_path / "events.csv"
    _attempts().to_csv(attempts_path, index=False)
    _events().to_csv(events_path, index=False)

    result = run_prior_day_sweep_failure_mode_analysis(
        attempts_path=attempts_path,
        events_path=events_path,
        holdout_start="2026-02-01",
        holdout_end="2026-03-01",
    )

    summary = result["summary"]
    categorical = result["categorical_summary"]
    numeric = result["numeric_summary"]
    assert summary["filled_win_loss_trades"] == 4
    assert summary["holdout_trades"] == 2
    assert "level_type" in categorical["factor"].unique()
    assert "sweep_distance_pts" in numeric["feature"].unique()


def _attempts() -> pd.DataFrame:
    rows = []
    for event_id, session_date, pnl in [
        ("e1", "2026-01-10", 100.0),
        ("e2", "2026-01-11", -50.0),
        ("e3", "2026-02-10", 80.0),
        ("e4", "2026-02-11", -70.0),
    ]:
        rows.append(
            {
                "event_id": event_id,
                "session_date": session_date,
                "level_type": "prior_day_high",
                "sweep_side": "high",
                "trade_side": "long",
                "entry_method": "immediate_sweep",
                "target_method": "fixed_8",
                "variant_id": "immediate_sweep__sweep_extreme__fixed_8",
                "status": "filled",
                "pnl": pnl,
            }
        )
    return pd.DataFrame(rows)


def _events() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _event("e1", "2026-01-10", 100.0, 108.0, "near_sweep_side", 0.20, 800.0),
            _event("e2", "2026-01-11", 100.0, 102.0, "far_sweep_side", -0.10, 400.0),
            _event("e3", "2026-02-10", 100.0, 107.0, "near_sweep_side", 0.15, 700.0),
            _event("e4", "2026-02-11", 100.0, 101.0, "far_sweep_side", -0.20, 300.0),
        ]
    )


def _event(
    event_id: str,
    session_date: str,
    level_price: float,
    sweep_price: float,
    location: str,
    aggr_ratio: float,
    intensity: float,
) -> dict[str, object]:
    return {
        "event_id": event_id,
        "session_date": session_date,
        "level_price": level_price,
        "sweep_price": sweep_price,
        "time_of_day_bucket": "opening_drive",
        "overnight_range_location_vs_sweep": location,
        "overnight_range_location": "upper_third",
        "overnight_trend_vs_sweep": "with_sweep",
        "rth_gap_vs_sweep": "with_sweep",
        "rth_gap_bucket": "up",
        "opening_drive_aligned": True,
        "pre60_dir_aggr_ratio_band": "positive",
        "time_to_reclaim_level_0_30s": None,
        "sweep_minutes_after_rth_open": 5.0,
        "pre_60s_directional_aggressive_trade_ratio": aggr_ratio,
        "sweep_0_5s_mbp_events_per_second": intensity,
        "sweep_0_5s_trade_events_per_second": intensity / 20.0,
        "post_5_30s_mbp_events_per_second": intensity / 2.0,
        "post_5_30s_trade_events_per_second": intensity / 50.0,
    }
