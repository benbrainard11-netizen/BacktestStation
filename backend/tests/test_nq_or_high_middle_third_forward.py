from __future__ import annotations

import pandas as pd

from app.research.nq_opening_range_mbp_execution_types import OpeningRangeMbpExecutionConfig
from app.research.nq_or_high_middle_third_forward import (
    empty_forward_result,
    freeze_or_high_result,
)


def test_forward_result_filters_to_mbp_or_high_events() -> None:
    config = OpeningRangeMbpExecutionConfig(holdout_start="2026-05-24")
    raw = {
        "source_events": pd.DataFrame(
            [
                {"session_date": "2026-05-26", "month": "2026-05"},
                {"session_date": "2026-05-27", "month": "2026-05"},
            ]
        ),
        "mbp_events": pd.DataFrame(
            [
                _event("2026-05-26", "high", "continuation_breakout"),
                _event("2026-05-27", "low", "failed_breakout_reversal"),
            ]
        ),
        "attempts": pd.DataFrame(
            [
                _attempt("2026-05-26", "immediate_break", 100.0),
                _attempt("2026-05-27", "immediate_break", -100.0),
            ]
        ),
    }

    result = freeze_or_high_result(raw, config, "2026-05-23")

    assert len(result["mbp_events"]) == 1
    assert result["mbp_events"].iloc[0]["first_break_side"] == "high"
    assert len(result["attempts"]) == 1
    assert result["summary"]["current_or_high_events"] == 1
    assert result["summary"]["next_report_at_event"] == 25


def test_empty_forward_result_is_dormant() -> None:
    result = empty_forward_result(
        OpeningRangeMbpExecutionConfig(holdout_start="2026-05-24"),
        "2026-05-23",
    )

    assert result["summary"]["status"] == "dormant_no_forward_or_high_events"
    assert result["summary"]["current_or_high_events"] == 0
    assert result["summary"]["next_report_at_event"] == 25


def _event(session_date: str, side: str, outcome: str) -> dict[str, object]:
    return {
        "event_id": f"or_middle_third:{session_date}",
        "symbol": "NQ.c.0",
        "session_date": session_date,
        "month": session_date[:7],
        "is_holdout": True,
        "first_break_side": side,
        "trade_side": "long" if side == "high" else "short",
        "outcome_label": outcome,
        "first_break_ts": f"{session_date} 14:00:00+00:00",
    }


def _attempt(session_date: str, variant_id: str, pnl: float) -> dict[str, object]:
    return {
        "event_id": f"or_middle_third:{session_date}",
        "session_date": session_date,
        "month": session_date[:7],
        "is_holdout": True,
        "entry_style": variant_id,
        "variant_id": variant_id,
        "status": "filled",
        "pnl": pnl,
    }
