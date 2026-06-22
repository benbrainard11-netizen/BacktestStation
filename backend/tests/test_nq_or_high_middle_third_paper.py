from __future__ import annotations

import datetime as dt
import json

import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_sessions import normalize_mbp1
from app.research import nq_or_high_middle_third_paper_data as paper_data
from app.research.nq_or_high_middle_third_paper_report import write_daily_report
from app.research.nq_or_high_middle_third_paper import (
    PaperMonitorConfig,
    evaluate_snapshot,
    write_outputs,
)


def test_paper_monitor_opens_primary_immediate_entry(tmp_path) -> None:
    cfg = PaperMonitorConfig(output_dir=tmp_path, live_status_path=tmp_path / "live_status.json")
    context = _context()
    mbp1 = normalize_mbp1(pd.DataFrame(_mbp_rows(target=False)))

    snapshot = evaluate_snapshot(
        cfg,
        dt.date(2026, 5, 26),
        dt.datetime(2026, 5, 26, 14, 1, tzinfo=dt.UTC),
        context,
        mbp1,
    )

    primary = [p for p in snapshot["positions"] if p["entry_style"] == "immediate_break"][0]
    assert snapshot["state"] == "paper_open"
    assert primary["status"] == "open"
    assert primary["entry_price"] > context["or_high"]
    assert snapshot["last_signal"]["executed"] is True


def test_paper_monitor_closes_target_and_writes_status(tmp_path) -> None:
    cfg = PaperMonitorConfig(output_dir=tmp_path, live_status_path=tmp_path / "live_status.json")
    snapshot = evaluate_snapshot(
        cfg,
        dt.date(2026, 5, 26),
        dt.datetime(2026, 5, 26, 14, 15, tzinfo=dt.UTC),
        _context(),
        normalize_mbp1(pd.DataFrame(_mbp_rows(target=True))),
    )

    write_outputs(snapshot, cfg)

    primary = [p for p in snapshot["positions"] if p["entry_style"] == "immediate_break"][0]
    assert primary["status"] == "closed"
    assert primary["exit_reason"] == "target"
    assert primary["pnl"] > 0
    status = json.loads((tmp_path / "live_status.json").read_text(encoding="utf-8"))
    assert status["strategy_status"] == "running"
    assert status["today_pnl"] > 0
    assert (tmp_path / "paper_positions.csv").exists()
    assert (tmp_path / "paper_signals.jsonl").exists()


def test_paper_monitor_stands_down_if_context_not_middle_third() -> None:
    cfg = PaperMonitorConfig()
    context = _context() | {"opening_drive_close_bucket": "upper_third"}

    snapshot = evaluate_snapshot(
        cfg,
        dt.date(2026, 5, 26),
        dt.datetime(2026, 5, 26, 14, 1, tzinfo=dt.UTC),
        context,
        normalize_mbp1(pd.DataFrame(_mbp_rows(target=False))),
    )

    assert snapshot["state"] == "stand_down_not_middle_third"
    assert snapshot["positions"] == []


def test_live_event_loader_falls_back_to_tbbo(monkeypatch) -> None:
    monkeypatch.setattr(paper_data, "read_mbp1", lambda **_: pd.DataFrame())
    monkeypatch.setattr(
        paper_data,
        "read_tbbo",
        lambda **_: pd.DataFrame(_mbp_rows(target=False)),
    )

    frame, status = paper_data.load_live_event_window(
        symbol="NQ.c.0",
        session_date=dt.date(2026, 5, 26),
        start=dt.datetime(2026, 5, 26, 14, 0, tzinfo=dt.UTC),
        end=dt.datetime(2026, 5, 26, 14, 1, tzinfo=dt.UTC),
    )

    assert not frame.empty
    assert status["event_schema_used"] == "tbbo"
    assert status["event_data_available"] is True


def test_daily_report_summarizes_primary_trade(tmp_path) -> None:
    cfg = PaperMonitorConfig(output_dir=tmp_path, live_status_path=tmp_path / "live_status.json")
    snapshot = evaluate_snapshot(
        cfg,
        dt.date(2026, 5, 26),
        dt.datetime(2026, 5, 26, 14, 15, tzinfo=dt.UTC),
        _context(),
        normalize_mbp1(pd.DataFrame(_mbp_rows(target=True))),
    )
    snapshot["data_status"] = {
        "bars_available": True,
        "bars_rows": 30,
        "event_data_available": True,
        "event_schema_used": "tbbo",
        "event_rows": 4,
        "errors": [],
    }
    write_outputs(snapshot, cfg)

    report = write_daily_report(snapshot, cfg)

    assert report["signal_occurred"] is True
    assert report["paper_trade_taken"] is True
    assert report["session_primary_pnl"] > 0
    assert report["cumulative_equity"] > 0
    assert report["missing_data"] == []
    assert (tmp_path / "reports" / "paper_daily_2026-05-26.md").exists()


def _context() -> dict[str, object]:
    return {
        "event_id": "paper_or_high_middle_third:2026-05-26",
        "symbol": "NQ.c.0",
        "session_date": "2026-05-26",
        "or_open": 105.0,
        "or_high": 110.0,
        "or_low": 100.0,
        "or_close": 105.0,
        "or_range_pts": 10.0,
        "opening_drive_close_bucket": "middle_third",
    }


def _mbp_rows(*, target: bool) -> list[dict[str, object]]:
    base = dt.datetime(2026, 5, 26, 14, 0, tzinfo=dt.UTC)
    rows = [
        _row(base + dt.timedelta(seconds=5), "T", 110.25, 110.25, 110.50, 1),
        _row(base + dt.timedelta(seconds=6), "M", None, 110.50, 110.75, 2),
        _row(base + dt.timedelta(seconds=40), "M", None, 111.00, 111.25, 3),
    ]
    if target:
        rows.append(_row(base + dt.timedelta(minutes=10), "T", 120.00, 119.75, 120.00, 4))
    return rows


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
