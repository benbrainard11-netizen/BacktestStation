from __future__ import annotations

import pandas as pd

from app.research.nq_prior_day_low_sweep_descriptive import (
    run_prior_day_low_sweep_descriptive_study,
)


def test_low_sweep_descriptive_outputs_requested_effect_tables(tmp_path) -> None:
    attempts_path = tmp_path / "attempts.csv"
    events_path = tmp_path / "events.csv"
    _attempts().to_csv(attempts_path, index=False)
    _events().to_csv(events_path, index=False)

    result = run_prior_day_low_sweep_descriptive_study(
        attempts_path=attempts_path,
        events_path=events_path,
        holdout_start="2026-02-01",
        holdout_end="2026-03-01",
    )

    trades = result["trade_rows"]
    categorical = result["categorical_distributions"]
    numeric = result["numeric_effects"]
    consistency = result["effect_consistency"]

    assert len(trades) == 4
    assert set(trades["level_type"]) == {"prior_day_low"}
    assert "time_of_day_bucket" in set(categorical["factor"])
    assert "post_5_30s_trade_events_per_second" in set(numeric["feature"])
    assert "sweep_distance_pts" in set(numeric["feature"])
    assert "post_5_30s_trade_events_per_second" in set(consistency["effect_name"])


def _attempts() -> pd.DataFrame:
    rows = []
    for event_id, date, level_type, pnl in [
        ("l1", "2026-01-10", "prior_day_low", 100.0),
        ("l2", "2026-01-11", "prior_day_low", -80.0),
        ("l3", "2026-02-10", "prior_day_low", 120.0),
        ("l4", "2026-02-11", "prior_day_low", -60.0),
        ("h1", "2026-02-12", "prior_day_high", 90.0),
    ]:
        rows.append(
            {
                "event_id": event_id,
                "session_date": date,
                "level_type": level_type,
                "trade_side": "short" if level_type == "prior_day_low" else "long",
                "variant_id": "immediate_sweep__sweep_extreme__fixed_8",
                "status": "filled",
                "exit_reason": "target" if pnl > 0 else "stop",
                "pnl": pnl,
            }
        )
    return pd.DataFrame(rows)


def _events() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _event("l1", "2026-01-10", "prior_day_low", 40.0, 100.0, 98.0, None),
            _event("l2", "2026-01-11", "prior_day_low", 20.0, 100.0, 99.5, 0.5),
            _event("l3", "2026-02-10", "prior_day_low", 42.0, 100.0, 97.0, None),
            _event("l4", "2026-02-11", "prior_day_low", 19.0, 100.0, 99.0, 0.25),
            _event("h1", "2026-02-12", "prior_day_high", 80.0, 100.0, 101.0, None),
        ]
    )


def _event(
    event_id: str,
    session_date: str,
    level_type: str,
    activity: float,
    level_price: float,
    sweep_price: float,
    reclaim_seconds: float | None,
) -> dict[str, object]:
    return {
        "event_id": event_id,
        "session_date": session_date,
        "level_type": level_type,
        "level_price": level_price,
        "sweep_price": sweep_price,
        "time_of_day_bucket": "opening_drive",
        "overnight_range_location_vs_sweep": "near_sweep_side",
        "overnight_range_location": "lower_third",
        "opening_drive_aligned": True,
        "time_to_reclaim_level_0_30s": reclaim_seconds,
        "post_5_30s_trade_events_per_second": activity,
        "sweep_minutes_after_rth_open": 5.0,
    }
