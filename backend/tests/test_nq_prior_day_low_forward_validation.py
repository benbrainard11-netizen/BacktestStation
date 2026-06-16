from __future__ import annotations

import pandas as pd

from app.research.nq_prior_day_low_forward_validation import (
    run_prior_day_low_forward_validation,
)


def test_forward_validation_collects_only_unseen_prior_day_low_events(tmp_path) -> None:
    events_path = tmp_path / "events.csv"
    attempts_path = tmp_path / "attempts.csv"
    _events().to_csv(events_path, index=False)
    _attempts().to_csv(attempts_path, index=False)

    result = run_prior_day_low_forward_validation(
        events_path=events_path,
        attempts_path=attempts_path,
        cutoff="2026-05-23",
        max_events=2,
    )

    events = result["events"]
    execution = result["execution"]
    consistency = result["effect_consistency"]
    assert list(events["event_id"]) == ["l_future_1", "l_future_2"]
    assert set(events["level_type"]) == {"prior_day_low"}
    assert set(execution["variant_id"]) == {"immediate_sweep__sweep_extreme__fixed_8"}
    assert "post_5_30s_trade_events_per_second" in set(consistency["effect_name"])


def _events() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _event("l_old", "2026-05-22", "prior_day_low", "continuation_breakout", 30.0),
            _event("h_future", "2026-05-24", "prior_day_high", "continuation_breakout", 30.0),
            _event("l_future_1", "2026-05-24", "prior_day_low", "continuation_breakout", 40.0),
            _event("l_future_2", "2026-05-25", "prior_day_low", "failed_breakout_reversal", 20.0),
            _event("l_future_3", "2026-05-26", "prior_day_low", "continuation_breakout", 50.0),
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
        "sweep_side": "low" if level_type == "prior_day_low" else "high",
        "sweep_ts": f"{session_date} 13:35:00+00:00",
        "level_price": 100.0,
        "sweep_price": 99.0,
        "fixed_outcome_label": label,
        "fixed_outcome_hit_ts": f"{session_date} 13:45:00+00:00",
        "post_5_30s_trade_events_per_second": activity,
        "time_of_day_bucket": "opening_drive",
        "overnight_range_location_vs_sweep": "near_sweep_side",
        "overnight_range_location": "lower_third",
    }


def _attempts() -> pd.DataFrame:
    rows = []
    for event_id, date, level_type, pnl in [
        ("l_future_1", "2026-05-24", "prior_day_low", 100.0),
        ("l_future_2", "2026-05-25", "prior_day_low", -80.0),
        ("l_future_3", "2026-05-26", "prior_day_low", 120.0),
        ("h_future", "2026-05-24", "prior_day_high", 90.0),
    ]:
        rows.append(
            {
                "event_id": event_id,
                "session_date": date,
                "level_type": level_type,
                "sweep_side": "low" if level_type == "prior_day_low" else "high",
                "trade_side": "short" if level_type == "prior_day_low" else "long",
                "sweep_ts": f"{date} 13:35:00+00:00",
                "level_price": 100.0,
                "sweep_price": 99.0,
                "context_score": 3,
                "overnight_location_aligned": True,
                "rth_gap_aligned": True,
                "opening_drive_aligned": True,
                "variant_id": "immediate_sweep__sweep_extreme__fixed_8",
                "status": "filled",
                "exit_reason": "target" if pnl > 0 else "stop",
                "pnl": pnl,
            }
        )
    return pd.DataFrame(rows)
