from __future__ import annotations

import datetime as dt

import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_sessions import et_datetime
from app.research.nq_opening_range_descriptive import (
    build_opening_range_descriptive_study,
)


def test_opening_range_study_labels_first_breaks_and_contexts() -> None:
    bars = _bars(
        _session_rows(dt.date(2026, 1, 5), break_side="high", continuation=True)
        + _session_rows(dt.date(2026, 2, 3), break_side="low", continuation=False)
    )

    result = build_opening_range_descriptive_study(
        bars,
        symbol="NQ.c.0",
        start=dt.date(2026, 1, 5),
        end=dt.date(2026, 2, 4),
        holdout_start="2026-02-01",
    )

    events = result["events"]
    baseline = result["baseline_summary"]
    contexts = result["context_summary"]
    validation = result["context_validation"]
    walk_forward = result["walk_forward_validation"]
    assert list(events["first_break_side"]) == ["high", "low"]
    assert list(events["outcome_label"]) == [
        "continuation_breakout",
        "failed_breakout_reversal",
    ]
    assert list(events["time_of_break_bucket"]) == ["first_15m", "first_15m"]
    assert "opening_drive_alignment" in events.columns
    assert "overnight_inventory_bucket" in events.columns
    assert "overnight_trend_bucket" in set(contexts["factor"])
    assert "time_of_break_bucket" in set(contexts["factor"])
    assert "opening_drive_alignment" in set(validation["factor"])
    assert "first_15m" in set(walk_forward["category"])
    assert int(baseline.loc[baseline["scope"] == "full", "labeled_count"].iloc[0]) == 2


def _session_rows(
    session_date: dt.date,
    *,
    break_side: str,
    continuation: bool,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    # Overnight context.
    rows.extend(_minute_rows(et_datetime(session_date, dt.time(8, 0)), 90, 100.0, 100.5))
    # Opening range: high 110, low 100, close 106.
    rows.extend(_minute_rows(et_datetime(session_date, dt.time(9, 30)), 30, 105.0, 105.0))
    rows[-1]["close"] = 106.0
    for row in rows[-30:]:
        row["high"] = 110.0
        row["low"] = 100.0
    # After 10:00, force one first break and one target result.
    start = et_datetime(session_date, dt.time(10, 0))
    if break_side == "high":
        rows.append(_bar(start, 110.5, 111.0, 109.0, 110.5))
        target_bar = _bar(start + dt.timedelta(minutes=1), 111.0, 121.0, 110.0, 120.0)
        reversal_bar = _bar(start + dt.timedelta(minutes=1), 109.0, 110.0, 99.0, 100.0)
    else:
        rows.append(_bar(start, 99.5, 101.0, 99.0, 99.5))
        target_bar = _bar(start + dt.timedelta(minutes=1), 99.0, 100.0, 89.0, 90.0)
        reversal_bar = _bar(start + dt.timedelta(minutes=1), 100.0, 111.0, 99.0, 110.0)
    rows.append(target_bar if continuation else reversal_bar)
    return rows


def _minute_rows(
    start: dt.datetime,
    count: int,
    open_price: float,
    close_price: float,
) -> list[dict[str, object]]:
    return [
        _bar(
            start + dt.timedelta(minutes=i),
            open_price,
            max(open_price, close_price) + 0.25,
            min(open_price, close_price) - 0.25,
            close_price,
        )
        for i in range(count)
    ]


def _bar(
    ts: dt.datetime,
    open_price: float,
    high: float,
    low: float,
    close: float,
) -> dict[str, object]:
    return {
        "ts_event": ts,
        "symbol": "NQ.c.0",
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": 1,
        "trade_count": 1,
        "vwap": close,
    }


def _bars(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)
