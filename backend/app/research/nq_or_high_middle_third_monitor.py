"""Append-only monitoring outputs for frozen OR-high forward validation."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from app.research.nq_opening_range_mbp_execution_stats import (
    CONTINUATION,
    REVERSAL,
    json_safe,
    outcome_row,
    profit_factor,
)
from app.research.nq_or_high_middle_third_forward import FROZEN_COMMIT, PROTOTYPE_ID

MILESTONE_EVENT_COUNTS = (25, 50, 75, 100)
ROLLING_WINDOW = 25


def update_monitoring_outputs(
    result: dict[str, object],
    output_dir: Path,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    new_events = as_frame(result["mbp_events"])
    new_attempts = as_frame(result["attempts"])
    existing_events = read_csv(output_dir / "or_high_forward_cumulative_events.csv")
    existing_attempts = read_csv(output_dir / "or_high_forward_cumulative_attempts.csv")
    existing_ids = set(existing_events.get("event_id", pd.Series(dtype=str)).astype(str))
    events = assign_event_numbers(append_only(existing_events, new_events, ["event_id"]))
    attempts = append_only(existing_attempts, new_attempts, ["event_id", "variant_id"])
    attempts = attach_event_numbers(attempts, events)
    trade_mask = (
        attempts["status"].astype(str).eq("filled")
        if "status" in attempts.columns
        else pd.Series(False, index=attempts.index)
    )
    trades = attempts.loc[trade_mask].copy()
    equity = cumulative_equity(events, attempts)
    milestones = milestone_report_rows(events, attempts, equity)
    write_monitor_files(output_dir, events, attempts, trades, equity, milestones)
    summary = monitor_summary(events, milestones, set(new_events.get("event_id", [])), existing_ids)
    (output_dir / "or_high_forward_monitor_summary.json").write_text(
        json.dumps(json_safe(summary), indent=2),
        encoding="utf-8",
    )
    return {
        "events": events,
        "attempts": attempts,
        "trades": trades,
        "equity": equity,
        "milestones": milestones,
        "summary": summary,
    }


def cumulative_equity(events: pd.DataFrame, attempts: pd.DataFrame) -> pd.DataFrame:
    if attempts.empty:
        return pd.DataFrame(columns=equity_columns())
    rows = attempts.copy()
    rows["pnl_signal"] = pd.to_numeric(rows.get("pnl"), errors="coerce").fillna(0.0)
    rows["is_trade"] = rows["status"].astype(str).eq("filled")
    rows["is_win"] = rows["is_trade"] & (rows["pnl_signal"] > 0)
    rows = rows.sort_values(["variant_id", "forward_event_number"]).reset_index(drop=True)
    out = []
    for variant_id, group in rows.groupby("variant_id", sort=True):
        cur = group.copy()
        cur["cumulative_pnl"] = cur["pnl_signal"].cumsum()
        cur["cumulative_peak"] = cur["cumulative_pnl"].cummax()
        cur["drawdown"] = cur["cumulative_pnl"] - cur["cumulative_peak"]
        trades = cur["is_trade"].rolling(ROLLING_WINDOW, min_periods=1).sum()
        wins = cur["is_win"].rolling(ROLLING_WINDOW, min_periods=1).sum()
        cur["rolling_win_rate_25"] = (wins / trades.where(trades > 0)).fillna(0.0)
        cur["variant_id"] = variant_id
        out.append(cur)
    return pd.concat(out, ignore_index=True)[equity_columns()]


def milestone_report_rows(
    events: pd.DataFrame,
    attempts: pd.DataFrame,
    equity: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for event_count in MILESTONE_EVENT_COUNTS:
        if len(events) < event_count:
            continue
        event_subset = events.iloc[:event_count].copy()
        ids = set(event_subset["event_id"].astype(str))
        attempt_subset = attempts.loc[attempts["event_id"].astype(str).isin(ids)].copy()
        outcome = outcome_row("forward", "or_high_event_count", str(event_count), event_subset)
        for variant_id, group in attempt_subset.groupby("variant_id", sort=True):
            trades = group.loc[group["status"] == "filled"]
            pnl = pd.to_numeric(trades.get("pnl"), errors="coerce").fillna(0.0)
            signal_pnl = pd.to_numeric(group.get("pnl"), errors="coerce").fillna(0.0)
            wins = pnl.loc[pnl > 0]
            losses = pnl.loc[pnl < 0]
            equity_row = last_equity_row(equity, variant_id, event_count)
            rows.append(
                outcome
                | {
                    "milestone_event_count": event_count,
                    "variant_id": variant_id,
                    "signals": int(len(group)),
                    "trades": int(len(trades)),
                    "skips": int((group["status"] == "skipped").sum()),
                    "holdout_style_net_pnl": float(signal_pnl.sum()),
                    "avg_pnl_per_trade": float(pnl.mean()) if len(trades) else 0.0,
                    "win_rate": float((pnl > 0).mean()) if len(trades) else 0.0,
                    "rolling_win_rate_25": float(equity_row.get("rolling_win_rate_25", 0.0)),
                    "profit_factor": profit_factor(wins, losses),
                    "cumulative_equity": float(equity_row.get("cumulative_pnl", 0.0)),
                    "max_drawdown": float(
                        equity.loc[equity["variant_id"] == variant_id, "drawdown"].min()
                    ),
                }
            )
    return pd.DataFrame(rows)


def write_monitor_files(
    output_dir: Path,
    events: pd.DataFrame,
    attempts: pd.DataFrame,
    trades: pd.DataFrame,
    equity: pd.DataFrame,
    milestones: pd.DataFrame,
) -> None:
    events.to_csv(output_dir / "or_high_forward_cumulative_events.csv", index=False)
    attempts.to_csv(output_dir / "or_high_forward_cumulative_attempts.csv", index=False)
    trades.to_csv(output_dir / "or_high_forward_cumulative_trades.csv", index=False)
    equity.to_csv(output_dir / "or_high_forward_cumulative_equity.csv", index=False)
    milestones.to_csv(output_dir / "or_high_forward_monitor_milestones.csv", index=False)
    write_monitor_reports(output_dir / "reports", milestones, equity)


def write_monitor_reports(report_dir: Path, milestones: pd.DataFrame, equity: pd.DataFrame) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    if milestones.empty:
        return
    for event_count, group in milestones.groupby("milestone_event_count", sort=True):
        curve = equity.loc[equity["forward_event_number"] <= event_count].copy()
        curve_path = report_dir / f"or_high_forward_monitor_{int(event_count):04d}_equity.csv"
        curve.to_csv(curve_path, index=False)
        lines = [
            f"# OR-High Forward Monitor {int(event_count)} Events",
            "",
            f"Frozen rules commit: `{FROZEN_COMMIT}`",
            "",
            "## Summary",
            "",
            markdown_table(group),
            "",
            "## Cumulative Equity Curve",
            "",
            f"CSV: `{curve_path.name}`",
            "",
            markdown_table(curve.tail(12)),
            "",
        ]
        (report_dir / f"or_high_forward_monitor_{int(event_count):04d}.md").write_text(
            "\n".join(lines),
            encoding="utf-8",
        )


def monitor_summary(
    events: pd.DataFrame,
    milestones: pd.DataFrame,
    new_ids: set[object],
    existing_ids: set[str],
) -> dict[str, object]:
    event_count = int(len(events))
    completed = [count for count in MILESTONE_EVENT_COUNTS if event_count >= count]
    pending = [count for count in MILESTONE_EVENT_COUNTS if event_count < count]
    appended = len({str(event_id) for event_id in new_ids} - existing_ids)
    labeled = events["outcome_label"].isin([CONTINUATION, REVERSAL]) if not events.empty else []
    return {
        "prototype_id": PROTOTYPE_ID,
        "frozen_rules_commit": FROZEN_COMMIT,
        "monitor_status": "dormant_no_forward_or_high_events" if event_count == 0 else "active",
        "cumulative_or_high_events": event_count,
        "cumulative_labeled_events": int(pd.Series(labeled).sum()) if len(events) else 0,
        "new_events_appended_this_run": appended,
        "milestones": list(MILESTONE_EVENT_COUNTS),
        "completed_milestones": completed,
        "next_milestone": pending[0] if pending else None,
        "milestone_rows": int(len(milestones)),
        "rolling_window_events": ROLLING_WINDOW,
    }


def append_only(existing: pd.DataFrame, new: pd.DataFrame, subset: list[str]) -> pd.DataFrame:
    frames = [frame for frame in [existing, new] if not frame.empty]
    if not frames:
        return pd.DataFrame()
    all_columns = sorted(set().union(*(frame.columns for frame in frames)))
    aligned = [frame.reindex(columns=all_columns) for frame in frames]
    out = pd.concat(aligned, ignore_index=True)
    out = out.drop_duplicates(subset=[col for col in subset if col in out.columns], keep="first")
    return out.reset_index(drop=True)


def assign_event_numbers(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events
    out = events.sort_values(["session_date", "first_break_ts"], na_position="last").reset_index(
        drop=True
    )
    out["forward_event_number"] = range(1, len(out) + 1)
    return out


def attach_event_numbers(attempts: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    if attempts.empty:
        return attempts
    event_cols = ["event_id", "forward_event_number", "session_date", "first_break_ts"]
    event_order = events[[col for col in event_cols if col in events.columns]]
    out = attempts.drop(columns=["forward_event_number"], errors="ignore").merge(
        event_order,
        on="event_id",
        how="left",
        suffixes=("", "_event"),
    )
    if "session_date_event" in out.columns:
        out["session_date"] = out["session_date_event"].combine_first(out.get("session_date"))
        out = out.drop(columns=["session_date_event"])
    return out.sort_values(["variant_id", "forward_event_number"]).reset_index(drop=True)


def last_equity_row(equity: pd.DataFrame, variant_id: str, event_count: int) -> pd.Series:
    rows = equity.loc[
        (equity["variant_id"] == variant_id) & (equity["forward_event_number"] <= event_count)
    ]
    return pd.Series(dtype=object) if rows.empty else rows.iloc[-1]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() and path.stat().st_size > 2 else pd.DataFrame()


def as_frame(value: object) -> pd.DataFrame:
    assert isinstance(value, pd.DataFrame)
    return value.copy()


def equity_columns() -> list[str]:
    return [
        "forward_event_number",
        "event_id",
        "session_date",
        "first_break_ts",
        "variant_id",
        "status",
        "pnl_signal",
        "cumulative_pnl",
        "drawdown",
        "rolling_win_rate_25",
    ]


def markdown_table(frame: pd.DataFrame) -> str:
    columns = [str(column) for column in frame.columns]
    rows = ["| " + " | ".join(columns) + " |"]
    rows.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for _, row in frame.iterrows():
        rows.append("| " + " | ".join(str(row[column]) for column in frame.columns) + " |")
    return "\n".join(rows)
