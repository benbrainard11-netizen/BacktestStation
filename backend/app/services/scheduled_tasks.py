"""Windows Scheduled Task introspection.

Shells out to PowerShell `Get-ScheduledTaskInfo` for each known task,
parses the output, returns structured status. On non-Windows (Linux,
macOS) `enabled=False` short-circuits and returns an empty list +
`platform_supported=False` so callers can render a graceful empty
state.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Tasks BacktestStation registers via scripts/install_scheduled_tasks.ps1
# and scripts/install_reconcile_taildrop_tasks.ps1. Names must match
# exactly what the install scripts use.
KNOWN_TASKS: list[str] = [
    "BacktestStationParquetMirror",
    "BacktestStationHistorical",
    "BacktestStationGapFiller",
    "BacktestStation - Import Live Trades",
]


@dataclass
class TaskInfo:
    name: str
    last_run_ts: dt.datetime | None
    last_result: int | None
    last_result_label: str
    next_run_ts: dt.datetime | None
    state: str | None


def is_supported() -> bool:
    """True only on Windows. PowerShell + Get-ScheduledTaskInfo don't
    exist on Linux/macOS."""
    return os.name == "nt"


def get_task_info(name: str, *, timeout_sec: float = 8.0) -> TaskInfo | None:
    """Query one task by name. Returns None if PowerShell errors or
    the task doesn't exist (caller should treat as 'unknown', not as
    'failed' — missing != broken).
    """
    if not is_supported():
        return None

    # PowerShell 5.1 parser quirk: `if` inside a hashtable literal needs
    # to be wrapped in `$(...)` (subexpression), not `(...)`. With plain
    # parens, `if` is treated as a command name and lookup fails. The
    # `$(...)` form lets the statement run and yields a value.
    ps = (
        "$ErrorActionPreference='Stop'; "
        f"$info = Get-ScheduledTaskInfo -TaskName '{name}'; "
        f"$task = Get-ScheduledTask -TaskName '{name}'; "
        "@{ "
        "  LastRunTime = $(if ($info.LastRunTime) { $info.LastRunTime.ToString('o') } else { $null }); "
        "  LastTaskResult = $info.LastTaskResult; "
        "  NextRunTime = $(if ($info.NextRunTime) { $info.NextRunTime.ToString('o') } else { $null }); "
        "  State = $task.State.ToString(); "
        "} | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logger.warning("powershell unavailable / timed out for task %s", name)
        return None

    if result.returncode != 0:
        # Most likely cause: task doesn't exist. Don't log as ERROR —
        # this is normal for hosts that haven't installed all tasks.
        logger.info(
            "task %s lookup returned non-zero (probably not installed): %s",
            name,
            result.stderr.strip()[:200],
        )
        return None

    try:
        payload = json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        logger.warning(
            "could not parse PowerShell output for task %s: %s",
            name,
            result.stdout[:200],
        )
        return None

    return TaskInfo(
        name=name,
        last_run_ts=_parse_dt(payload.get("LastRunTime")),
        last_result=_parse_int(payload.get("LastTaskResult")),
        last_result_label=_label_for_result(
            _parse_int(payload.get("LastTaskResult")),
            _parse_dt(payload.get("LastRunTime")),
        ),
        next_run_ts=_parse_dt(payload.get("NextRunTime")),
        state=payload.get("State"),
    )


def get_all_known_tasks() -> list[TaskInfo]:
    """Query every task in KNOWN_TASKS. Skips ones not installed
    (returns None from get_task_info)."""
    if not is_supported():
        return []
    out: list[TaskInfo] = []
    for name in KNOWN_TASKS:
        info = get_task_info(name)
        if info is not None:
            out.append(info)
    return out


# --- helpers -------------------------------------------------------------


def _parse_dt(value: str | None) -> dt.datetime | None:
    if value is None or value == "":
        return None
    # PowerShell's ToString('o') produces ISO-8601 round-trip, e.g.
    # "2026-04-27T15:00:00.0000000-07:00". Python's fromisoformat
    # handles this directly in 3.11+.
    try:
        return dt.datetime.fromisoformat(value)
    except ValueError:
        return None


def _parse_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _label_for_result(
    result: int | None, last_run_ts: dt.datetime | None
) -> str:
    """Map LastTaskResult into a human-readable label.

    Windows special case: 267011 = "task has not yet run" (gets returned
    by Get-ScheduledTaskInfo when LastRunTime is the epoch sentinel).
    """
    if last_run_ts is None or result == 267011:
        return "never_run"
    if result is None:
        return "unknown"
    if result == 0:
        return "ok"
    return "failed"
