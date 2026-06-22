"""Continuous session runner for the OR-high shadow paper monitor."""

from __future__ import annotations

import datetime as dt
import time
from pathlib import Path

from app.research.nq_liquidity_sweep_outcomes_sessions import ET, et_datetime
from app.research.nq_opening_range_mbp_execution_types import OpeningRangeMbpExecutionConfig
from app.research.nq_or_high_middle_third_paper import run_paper_monitor_once
from app.research.nq_or_high_middle_third_paper_data import run_parquet_mirror_once
from app.research.nq_or_high_middle_third_paper_report import write_daily_report
from app.research.nq_or_high_middle_third_paper_types import PaperMonitorConfig


def run_paper_monitor_session(
    *,
    config: PaperMonitorConfig,
    session_date: str | dt.date | None,
    poll_seconds: int,
    backend_dir: Path,
    auto_mirror: bool,
    mirror_interval_seconds: int,
    mirror_timeout_seconds: int,
    stop_after_report: bool,
) -> dict[str, object]:
    session = resolve_session_date(session_date)
    last_mirror_at: dt.datetime | None = None
    report_written = False
    last_snapshot: dict[str, object] | None = None
    while True:
        now = dt.datetime.now(dt.UTC)
        mirror_result = None
        if auto_mirror and mirror_due(now, last_mirror_at, mirror_interval_seconds):
            mirror_result = run_parquet_mirror_once(
                backend_dir=backend_dir,
                timeout_seconds=mirror_timeout_seconds,
            )
            last_mirror_at = now
        last_snapshot = run_paper_monitor_once(
            config=config,
            session_date=session,
            now=now,
        )
        if mirror_result is not None:
            last_snapshot["last_mirror_result"] = mirror_result
        if is_after_report_time(session, config.execution) and not report_written:
            report = write_daily_report(last_snapshot, config)
            report_written = True
            if stop_after_report:
                return {"snapshot": last_snapshot, "report": report}
        time.sleep(max(1, poll_seconds))


def run_paper_monitor_cycle(
    *,
    config: PaperMonitorConfig,
    session_date: str | dt.date | None,
    backend_dir: Path,
    auto_mirror: bool,
    mirror_timeout_seconds: int,
    write_report: bool,
) -> dict[str, object]:
    session = resolve_session_date(session_date)
    mirror_result = (
        run_parquet_mirror_once(
            backend_dir=backend_dir,
            timeout_seconds=mirror_timeout_seconds,
        )
        if auto_mirror
        else None
    )
    snapshot = run_paper_monitor_once(config=config, session_date=session)
    if mirror_result is not None:
        snapshot["last_mirror_result"] = mirror_result
    report = write_daily_report(snapshot, config) if write_report else None
    return {"snapshot": snapshot, "report": report}


def is_after_report_time(
    session_date: dt.date,
    execution: OpeningRangeMbpExecutionConfig,
) -> bool:
    report_time = et_datetime(session_date, execution.rth_close_et) + dt.timedelta(minutes=5)
    return dt.datetime.now(dt.UTC) >= report_time


def mirror_due(
    now: dt.datetime,
    last_mirror_at: dt.datetime | None,
    interval_seconds: int,
) -> bool:
    if last_mirror_at is None:
        return True
    return (now - last_mirror_at).total_seconds() >= interval_seconds


def resolve_session_date(value: str | dt.date | None) -> dt.date:
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        return dt.date.fromisoformat(value)
    return dt.datetime.now(dt.UTC).astimezone(ET).date()
