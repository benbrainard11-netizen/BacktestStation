"""Daily report generation for the OR-high shadow paper monitor."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd

from app.research.nq_opening_range_mbp_execution_stats import json_safe, profit_factor
from app.research.nq_or_high_middle_third_paper_types import (
    CLOSED_TRADES_JSONL,
    SIGNALS_JSONL,
    PaperMonitorConfig,
)


def write_daily_report(
    snapshot: dict[str, object],
    cfg: PaperMonitorConfig,
) -> dict[str, object]:
    report = build_daily_report(snapshot, cfg)
    report_dir = cfg.output_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    session_date = str(report["session_date"])
    json_path = report_dir / f"paper_daily_{session_date}.json"
    md_path = report_dir / f"paper_daily_{session_date}.md"
    json_path.write_text(json.dumps(json_safe(report), indent=2), encoding="utf-8")
    md_path.write_text(markdown_report(report), encoding="utf-8")
    return report | {"json_path": str(json_path), "markdown_path": str(md_path)}


def build_daily_report(
    snapshot: dict[str, object],
    cfg: PaperMonitorConfig,
) -> dict[str, object]:
    session_date = str(snapshot["session_date"])
    signals = read_jsonl(cfg.output_dir / SIGNALS_JSONL)
    trades = read_jsonl(cfg.output_dir / CLOSED_TRADES_JSONL)
    session_signals = rows_for_session(signals, session_date)
    session_trades = rows_for_session(trades, session_date)
    primary_trades = [
        row for row in session_trades if row.get("entry_style") == cfg.primary_entry_style
    ]
    all_primary = [
        row for row in trades if row.get("entry_style") == cfg.primary_entry_style
    ]
    pnl = pd.Series([float(row.get("pnl") or 0.0) for row in all_primary], dtype=float)
    losses = pnl.loc[pnl < 0]
    wins = pnl.loc[pnl > 0]
    latest_position = latest_primary_position(snapshot, cfg)
    data_status = dict(snapshot.get("data_status") or {})
    errors = data_status.get("errors") or []
    if snapshot.get("last_error"):
        errors = [*errors, snapshot["last_error"]]
    return {
        "prototype_id": snapshot.get("prototype_id"),
        "frozen_rules_commit": snapshot.get("frozen_rules_commit"),
        "mode": snapshot.get("mode"),
        "session_date": session_date,
        "generated_at": dt.datetime.now(dt.UTC),
        "state": snapshot.get("state"),
        "primary_entry_style": cfg.primary_entry_style,
        "signal_occurred": bool(session_signals),
        "paper_trade_taken": bool(latest_position and latest_position.get("entry_ts")),
        "latest_position": latest_position,
        "session_signal_count": len(session_signals),
        "session_closed_primary_trades": len(primary_trades),
        "session_primary_pnl": sum(float(row.get("pnl") or 0.0) for row in primary_trades),
        "cumulative_primary_trades": len(all_primary),
        "cumulative_equity": float(pnl.sum()) if len(pnl) else 0.0,
        "cumulative_win_rate": float((pnl > 0).mean()) if len(pnl) else 0.0,
        "cumulative_profit_factor": profit_factor(wins, losses),
        "data_status": data_status,
        "errors": errors,
        "missing_data": missing_data(snapshot),
    }


def markdown_report(report: dict[str, object]) -> str:
    pos = report.get("latest_position") or {}
    lines = [
        f"# OR-High Paper Daily Report {report['session_date']}",
        "",
        f"State: `{report['state']}`",
        f"Signal occurred: `{report['signal_occurred']}`",
        f"Paper trade taken: `{report['paper_trade_taken']}`",
        f"Primary entry style: `{report['primary_entry_style']}`",
        "",
        "## Result",
        "",
        f"- Position status: `{pos.get('status', 'none') if isinstance(pos, dict) else 'none'}`",
        f"- Exit reason: `{pos.get('exit_reason') if isinstance(pos, dict) else None}`",
        f"- Session primary PnL: `{report['session_primary_pnl']}`",
        f"- Cumulative equity: `{report['cumulative_equity']}`",
        f"- Cumulative win rate: `{report['cumulative_win_rate']}`",
        f"- Cumulative profit factor: `{report['cumulative_profit_factor']}`",
        "",
        "## Data",
        "",
        f"- Event schema used: `{dict(report['data_status']).get('event_schema_used')}`",
        f"- Event rows: `{dict(report['data_status']).get('event_rows')}`",
        f"- Bars rows: `{dict(report['data_status']).get('bars_rows')}`",
        f"- Missing data: `{', '.join(report['missing_data']) if report['missing_data'] else 'none'}`",
        f"- Errors: `{'; '.join(map(str, report['errors'])) if report['errors'] else 'none'}`",
        "",
    ]
    return "\n".join(lines)


def latest_primary_position(
    snapshot: dict[str, object],
    cfg: PaperMonitorConfig,
) -> dict[str, object] | None:
    positions = snapshot.get("positions") or []
    if not isinstance(positions, list):
        return None
    for row in positions:
        if isinstance(row, dict) and row.get("entry_style") == cfg.primary_entry_style:
            return row
    return None


def missing_data(snapshot: dict[str, object]) -> list[str]:
    data = dict(snapshot.get("data_status") or {})
    missing: list[str] = []
    if not data.get("bars_available"):
        missing.append("1m_bars")
    if not data.get("event_data_available"):
        missing.append("event_data_mbp1_or_tbbo")
    return missing


def rows_for_session(rows: list[dict[str, object]], session_date: str) -> list[dict[str, object]]:
    return [row for row in rows if str(row.get("session_date")) == session_date]


def read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            loaded = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, dict):
            rows.append(loaded)
    return rows
