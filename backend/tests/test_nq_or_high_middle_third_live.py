from __future__ import annotations

import datetime as dt

import pandas as pd

from app.research import nq_or_high_middle_third_live as live


def test_completed_session_end_exclusive_uses_new_york_date() -> None:
    now = dt.datetime(2026, 6, 17, 3, 0, tzinfo=dt.UTC)

    assert live.completed_session_end_exclusive(now) == dt.date(2026, 6, 16)


def test_live_monitor_skips_forward_when_no_or_events(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("BS_DATA_BACKEND", raising=False)
    monkeypatch.setattr(live, "run_opening_range_descriptive_study", _empty_descriptive)

    result = live.run_live_forward_monitor(
        events_dir=tmp_path / "events",
        monitor_dir=tmp_path / "monitor",
        now=dt.datetime(2026, 6, 17, 12, 0, tzinfo=dt.UTC),
    )

    summary = result["summary"]
    assert summary["opening_range_sessions_built"] == 0
    assert summary["monitor"]["monitor_status"] == "dormant_no_forward_or_high_events"
    assert (tmp_path / "monitor" / live.LIVE_SUMMARY_FILENAME).exists()
    assert (tmp_path / "monitor" / live.LIVE_RUN_HISTORY_FILENAME).exists()


def test_live_monitor_runs_forward_and_appends_monitor_outputs(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("BS_DATA_BACKEND", "local")
    monkeypatch.setattr(live, "run_opening_range_descriptive_study", _descriptive_with_events)
    monkeypatch.setattr(live, "run_forward_validation", _forward_result)

    result = live.run_live_forward_monitor(
        events_dir=tmp_path / "events",
        monitor_dir=tmp_path / "monitor",
        now=dt.datetime(2026, 6, 17, 12, 0, tzinfo=dt.UTC),
    )

    summary = result["summary"]
    assert summary["opening_range_sessions_built"] == 2
    assert summary["middle_third_sessions_built"] == 1
    assert summary["monitor"]["cumulative_or_high_events"] == 1
    assert summary["monitor"]["new_events_appended_this_run"] == 1
    assert (tmp_path / "monitor" / "or_high_forward_cumulative_events.csv").exists()


def _empty_descriptive(**_: object) -> dict[str, object]:
    empty = pd.DataFrame()
    return {
        "events": empty,
        "baseline_summary": empty,
        "context_summary": empty,
        "context_consistency": empty,
        "context_validation": empty,
        "walk_forward_validation": empty,
        "monthly_summary": empty,
        "config": empty,
        "summary": {},
    }


def _descriptive_with_events(**_: object) -> dict[str, object]:
    empty = pd.DataFrame()
    events = pd.DataFrame(
        [
            {
                "symbol": "NQ.c.0",
                "session_date": "2026-05-26",
                "opening_drive_close_bucket": "middle_third",
            },
            {
                "symbol": "NQ.c.0",
                "session_date": "2026-05-27",
                "opening_drive_close_bucket": "upper_third",
            },
        ]
    )
    return {
        "events": events,
        "baseline_summary": empty,
        "context_summary": empty,
        "context_consistency": empty,
        "context_validation": empty,
        "walk_forward_validation": empty,
        "monthly_summary": empty,
        "config": empty,
        "summary": {},
    }


def _forward_result(**_: object) -> dict[str, object]:
    events = pd.DataFrame(
        [
            {
                "event_id": "or_middle_third:2026-05-26",
                "symbol": "NQ.c.0",
                "session_date": "2026-05-26",
                "month": "2026-05",
                "is_holdout": True,
                "first_break_side": "high",
                "trade_side": "long",
                "outcome_label": "continuation_breakout",
                "first_break_ts": "2026-05-26 14:01:00+00:00",
            }
        ]
    )
    attempts = pd.DataFrame(
        [
            {
                "event_id": "or_middle_third:2026-05-26",
                "session_date": "2026-05-26",
                "month": "2026-05",
                "is_holdout": True,
                "entry_style": "immediate_break",
                "variant_id": "immediate_break",
                "status": "filled",
                "pnl": 100.0,
            }
        ]
    )
    return {
        "mbp_events": events,
        "attempts": attempts,
        "summary": {
            "status": "active",
            "current_or_high_events": 1,
            "current_labeled_events": 1,
        },
    }
