from __future__ import annotations

import pandas as pd

from app.research.nq_prior_day_sweep_direction_split import (
    run_prior_day_sweep_direction_split_analysis,
)


def test_direction_split_compares_high_and_low_sweeps(tmp_path) -> None:
    attempts_path = tmp_path / "attempts.csv"
    events_path = tmp_path / "events.csv"
    _attempts().to_csv(attempts_path, index=False)
    _events().to_csv(events_path, index=False)

    result = run_prior_day_sweep_direction_split_analysis(
        attempts_path=attempts_path,
        events_path=events_path,
        holdout_start="2026-02-01",
        holdout_end="2026-03-01",
    )

    event_summary = result["event_continuation"]
    strategy_summary = result["strategy_direction"]
    comparison = result["direction_comparison"]
    assert set(event_summary["level_type"]) == {"prior_day_high", "prior_day_low"}
    assert set(strategy_summary["level_type"]) == {"prior_day_high", "prior_day_low"}
    full = comparison.loc[comparison["scope"] == "full"].iloc[0]
    assert full["event_low_minus_high_continuation_rate"] > 0
    assert full["strategy_low_minus_high_win_rate"] > 0


def _attempts() -> pd.DataFrame:
    rows = []
    for event_id, date, level_type, side, pnl in [
        ("h1", "2026-01-10", "prior_day_high", "long", -80.0),
        ("h2", "2026-02-10", "prior_day_high", "long", -70.0),
        ("l1", "2026-01-11", "prior_day_low", "short", 100.0),
        ("l2", "2026-02-11", "prior_day_low", "short", -40.0),
    ]:
        rows.append(
            {
                "event_id": event_id,
                "session_date": date,
                "level_type": level_type,
                "trade_side": side,
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
            _event("h1", "2026-01-10", "prior_day_high", "failed_breakout_reversal"),
            _event("h2", "2026-02-10", "prior_day_high", "failed_breakout_reversal"),
            _event("l1", "2026-01-11", "prior_day_low", "continuation_breakout"),
            _event("l2", "2026-02-11", "prior_day_low", "failed_breakout_reversal"),
        ]
    )


def _event(
    event_id: str,
    session_date: str,
    level_type: str,
    label: str,
) -> dict[str, object]:
    return {
        "event_id": event_id,
        "session_date": session_date,
        "level_price": 100.0,
        "sweep_price": 102.0,
        "fixed_outcome_label": label,
        "overnight_range_location_vs_sweep": "near_sweep_side",
        "time_of_day_bucket": "opening_drive",
        "post_5_30s_trade_events_per_second": 30.0,
        "sweep_0_5s_trade_events_per_second": 40.0,
        "post_5_30s_mbp_events_per_second": 500.0,
        "level_type": level_type,
    }
