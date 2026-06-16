from __future__ import annotations

import datetime as dt

import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_sessions import normalize_mbp1
from app.research.nq_opening_range_mbp_execution_fills import simulate_entry_style
from app.research.nq_opening_range_mbp_execution_sequence import build_mbp_event
from app.research.nq_opening_range_mbp_execution_types import (
    ENTRY_STYLES,
    OpeningRangeMbpExecutionConfig,
)


def test_middle_third_or_mbp_sequence_and_entries() -> None:
    event = pd.Series(
        {
            "symbol": "NQ.c.0",
            "session_date": "2026-04-24",
            "month": "2026-04",
            "is_holdout": True,
            "opening_drive_close_bucket": "middle_third",
            "or_open": 105.0,
            "or_high": 110.0,
            "or_low": 100.0,
            "or_close": 105.0,
            "or_range_pts": 10.0,
            "first_break_side": "high",
            "outcome_label": "continuation_breakout",
        }
    )
    mbp1 = normalize_mbp1(pd.DataFrame(_mbp_rows()))

    mbp_event = pd.Series(build_mbp_event(event, mbp1))
    assert mbp_event["first_break_side"] == "high"
    assert mbp_event["trade_side"] == "long"
    assert mbp_event["outcome_label"] == "continuation_breakout"

    attempts = [
        simulate_entry_style(
            mbp_event,
            mbp1,
            entry_style,
            OpeningRangeMbpExecutionConfig(),
        )
        for entry_style in ENTRY_STYLES
    ]
    assert [row["status"] for row in attempts] == ["filled", "filled", "filled"]
    assert {row["entry_note"] for row in attempts} == {
        "first_quote_after_break",
        "first_level_retest",
        "30s_confirmation",
    }
    assert all(row["exit_reason"] == "target" for row in attempts)
    assert all(row["pnl"] > 0 for row in attempts)


def _mbp_rows() -> list[dict[str, object]]:
    base = dt.datetime(2026, 4, 24, 14, 0, tzinfo=dt.UTC)
    return [
        _row(base + dt.timedelta(seconds=5), "T", 110.25, 110.25, 110.50, 1),
        _row(base + dt.timedelta(seconds=40), "M", None, 111.00, 111.25, 2),
        _row(base + dt.timedelta(minutes=5), "T", 110.00, 110.00, 110.25, 3),
        _row(base + dt.timedelta(minutes=10), "T", 120.00, 119.75, 120.00, 4),
    ]


def _row(
    ts: dt.datetime,
    action: str,
    price: float | None,
    bid: float,
    ask: float,
    sequence: int,
) -> dict[str, object]:
    return {
        "ts_event": ts,
        "action": action,
        "price": price,
        "bid_px": bid,
        "ask_px": ask,
        "sequence": sequence,
    }
