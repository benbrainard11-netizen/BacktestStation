"""Live orchestration for the frozen OR-high middle-third monitor."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from app.research.nq_liquidity_sweep_outcomes_sessions import ET
from app.research.nq_opening_range_descriptive import (
    run_opening_range_descriptive_study,
    write_opening_range_descriptive_outputs,
)
from app.research.nq_opening_range_mbp_execution_stats import json_safe
from app.research.nq_or_high_middle_third_forward import (
    FORWARD_START_EXCLUSIVE,
    FROZEN_COMMIT,
    PROTOTYPE_ID,
    empty_forward_result,
    forward_config,
    next_session_start,
    run_forward_validation,
    write_forward_outputs,
)
from app.research.nq_or_high_middle_third_monitor import update_monitoring_outputs

DEFAULT_EVENTS_DIR = Path("../data/backtests/nq_opening_range_descriptive_forward_live")
DEFAULT_MONITOR_DIR = Path("../data/backtests/nq_or_high_middle_third_forward_validation")
EVENTS_FILENAME = "opening_range_descriptive_events.csv"
LIVE_SUMMARY_FILENAME = "or_high_live_monitor_summary.json"
LIVE_RUN_HISTORY_FILENAME = "or_high_live_monitor_runs.csv"


def run_live_forward_monitor(
    *,
    symbol: str = "NQ.c.0",
    start: str | None = None,
    end: str | None = None,
    holdout_start: str | None = None,
    events_dir: Path = DEFAULT_EVENTS_DIR,
    monitor_dir: Path = DEFAULT_MONITOR_DIR,
    context_deadzone_pts: float = 8.0,
    forward_start_exclusive: str = FORWARD_START_EXCLUSIVE,
    now: dt.datetime | None = None,
) -> dict[str, object]:
    """Refresh live OR events, then append frozen OR-high forward results.

    This is workflow glue only. It intentionally calls the existing
    descriptive event builder and frozen forward validator without changing
    their strategy definitions or execution assumptions.
    """

    run_started = now or dt.datetime.now(dt.UTC)
    validate_storage_environment()
    start_value = start or next_session_start(forward_start_exclusive)
    end_value = end or completed_session_end_exclusive(run_started).isoformat()
    holdout_value = holdout_start or start_value

    descriptive = run_opening_range_descriptive_study(
        symbol=symbol,
        start=start_value,
        end=end_value,
        holdout_start=holdout_value,
        context_deadzone_pts=context_deadzone_pts,
    )
    write_opening_range_descriptive_outputs(descriptive, events_dir)
    events_path = events_dir / EVENTS_FILENAME
    events = as_frame(descriptive["events"])

    if live_events_are_usable(events):
        forward = run_forward_validation(
            events_path=events_path,
            output_dir=monitor_dir,
            forward_start_exclusive=forward_start_exclusive,
            end=end_value,
        )
    else:
        cfg = forward_config(forward_start_exclusive)
        forward = empty_forward_result(cfg, forward_start_exclusive)
        write_forward_outputs(forward, monitor_dir)

    monitor = update_monitoring_outputs(forward, monitor_dir)
    summary = live_summary(
        run_started=run_started,
        symbol=symbol,
        start=start_value,
        end=end_value,
        holdout_start=holdout_value,
        context_deadzone_pts=context_deadzone_pts,
        events_dir=events_dir,
        events_path=events_path,
        monitor_dir=monitor_dir,
        events=events,
        forward=forward,
        monitor=monitor,
        forward_start_exclusive=forward_start_exclusive,
    )
    write_live_outputs(summary, monitor_dir)
    return {
        "descriptive": descriptive,
        "forward": forward,
        "monitor": monitor,
        "summary": summary,
    }


def completed_session_end_exclusive(now: dt.datetime | None = None) -> dt.date:
    """Return the default exclusive end date for completed sessions.

    If it is June 17 in New York, the live monitor defaults to
    ``end=2026-06-17``, which includes sessions up through June 16.
    Today can be included manually by passing ``--end`` after data is final.
    """

    now_value = now or dt.datetime.now(dt.UTC)
    if now_value.tzinfo is None:
        now_value = now_value.replace(tzinfo=dt.UTC)
    return now_value.astimezone(ET).date()


def validate_storage_environment() -> None:
    backend = os.environ.get("BS_DATA_BACKEND", "local").lower()
    if backend != "r2":
        return
    missing = [
        name
        for name in ("BS_R2_ACCESS_KEY", "BS_R2_SECRET", "BS_R2_ENDPOINT")
        if not os.environ.get(name)
    ]
    if missing:
        raise RuntimeError(
            "BS_DATA_BACKEND=r2 is set, but these required env vars are missing: "
            + ", ".join(missing)
        )


def live_events_are_usable(events: pd.DataFrame) -> bool:
    required = {"session_date", "opening_drive_close_bucket"}
    return not events.empty and required.issubset(events.columns)


def live_summary(
    *,
    run_started: dt.datetime,
    symbol: str,
    start: str,
    end: str,
    holdout_start: str,
    context_deadzone_pts: float,
    events_dir: Path,
    events_path: Path,
    monitor_dir: Path,
    events: pd.DataFrame,
    forward: dict[str, object],
    monitor: dict[str, object],
    forward_start_exclusive: str,
) -> dict[str, object]:
    forward_summary = dict(forward.get("summary", {}))
    monitor_summary = dict(monitor.get("summary", {}))
    middle_third = middle_third_count(events)
    summary = {
        "prototype_id": PROTOTYPE_ID,
        "frozen_rules_commit": FROZEN_COMMIT,
        "run_started_utc": run_started.astimezone(dt.UTC).isoformat(),
        "data_backend": os.environ.get("BS_DATA_BACKEND", "local").lower(),
        "symbol": symbol,
        "forward_start_exclusive": forward_start_exclusive,
        "date_window": {
            "start_inclusive": start,
            "end_exclusive": end,
            "completed_sessions_only_by_default": True,
        },
        "descriptive_events_path": str(events_path),
        "descriptive_events_dir": str(events_dir),
        "monitor_output_dir": str(monitor_dir),
        "opening_range_sessions_built": int(len(events)),
        "middle_third_sessions_built": middle_third,
        "latest_opening_range_session": latest_date(events, "session_date"),
        "latest_middle_third_session": latest_middle_third_date(events),
        "context_deadzone_pts": context_deadzone_pts,
        "holdout_start": holdout_start,
        "forward": forward_summary,
        "monitor": monitor_summary,
        "warnings": live_warnings(events, middle_third, monitor_summary),
    }
    return json_safe(summary)


def write_live_outputs(summary: dict[str, object], monitor_dir: Path) -> None:
    monitor_dir.mkdir(parents=True, exist_ok=True)
    (monitor_dir / LIVE_SUMMARY_FILENAME).write_text(
        json.dumps(json_safe(summary), indent=2),
        encoding="utf-8",
    )
    append_run_history(summary, monitor_dir / LIVE_RUN_HISTORY_FILENAME)


def append_run_history(summary: dict[str, object], path: Path) -> None:
    row = flatten_run_summary(summary)
    current = pd.DataFrame([row])
    if path.exists() and path.stat().st_size > 2:
        existing = pd.read_csv(path)
        current = pd.concat([existing, current], ignore_index=True)
    current.to_csv(path, index=False)


def flatten_run_summary(summary: dict[str, object]) -> dict[str, object]:
    date_window = dict(summary.get("date_window", {}))
    forward = dict(summary.get("forward", {}))
    monitor = dict(summary.get("monitor", {}))
    return {
        "run_started_utc": summary.get("run_started_utc"),
        "data_backend": summary.get("data_backend"),
        "symbol": summary.get("symbol"),
        "start_inclusive": date_window.get("start_inclusive"),
        "end_exclusive": date_window.get("end_exclusive"),
        "opening_range_sessions_built": summary.get("opening_range_sessions_built"),
        "middle_third_sessions_built": summary.get("middle_third_sessions_built"),
        "latest_opening_range_session": summary.get("latest_opening_range_session"),
        "latest_middle_third_session": summary.get("latest_middle_third_session"),
        "forward_status": forward.get("status"),
        "current_or_high_events": forward.get("current_or_high_events"),
        "monitor_status": monitor.get("monitor_status"),
        "cumulative_or_high_events": monitor.get("cumulative_or_high_events"),
        "new_events_appended_this_run": monitor.get("new_events_appended_this_run"),
        "completed_milestones": ",".join(map(str, monitor.get("completed_milestones", []))),
        "next_milestone": monitor.get("next_milestone"),
    }


def middle_third_count(events: pd.DataFrame) -> int:
    if events.empty or "opening_drive_close_bucket" not in events.columns:
        return 0
    return int(events["opening_drive_close_bucket"].astype(str).eq("middle_third").sum())


def latest_date(events: pd.DataFrame, column: str) -> str | None:
    if events.empty or column not in events.columns:
        return None
    values = pd.to_datetime(events[column], errors="coerce").dropna()
    return None if values.empty else values.max().date().isoformat()


def latest_middle_third_date(events: pd.DataFrame) -> str | None:
    if events.empty or "opening_drive_close_bucket" not in events.columns:
        return None
    middle = events.loc[events["opening_drive_close_bucket"].astype(str).eq("middle_third")]
    return latest_date(middle, "session_date")


def live_warnings(
    events: pd.DataFrame,
    middle_third: int,
    monitor_summary: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if events.empty:
        warnings.append(
            "No opening-range sessions were built from the available 1m bars."
        )
    elif middle_third == 0:
        warnings.append(
            "Opening-range sessions were built, but none closed in the middle third."
        )
    if int(monitor_summary.get("cumulative_or_high_events") or 0) == 0:
        warnings.append(
            "No post-2026-05-23 MBP-confirmed OR-high events have accumulated yet."
        )
    if os.environ.get("BS_DATA_BACKEND", "local").lower() != "r2":
        warnings.append(
            "The monitor is using the local warehouse. Set BS_DATA_BACKEND=r2 to consume R2."
        )
    return warnings


def as_frame(value: object) -> pd.DataFrame:
    assert isinstance(value, pd.DataFrame)
    return value.copy()
