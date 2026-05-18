"""Overnight queue — sequential task runner for benpc.

Runs a list of long-running database additions + analyses + cleanups
in sequence while the operator sleeps. Each task is a subprocess call
with a timeout. Logs go to experiments/overnight_runs/<run_id>/.

DESIGN GOALS:
  - Idempotent: each task is safe to re-run (record_event, run_outcomes,
    and our build scripts all skip already-current rows).
  - Resumable: kill -INT, fix the bug, re-run; finished tasks are
    skipped via the marker files.
  - Logged: per-task stdout/stderr + master MD log with start/end/exit.
  - Survivable: one failure doesn't kill the queue. Critical tasks
    can flag the queue to abort if needed.

USAGE:
    python backend/scripts/overnight_queue.py           # full queue
    python backend/scripts/overnight_queue.py --list    # dry-run; show tasks
    python backend/scripts/overnight_queue.py --skip 1 3 5   # skip tasks

MORNING REVIEW:
    cat experiments/overnight_runs/<run_id>/MASTER_LOG.md
    ls experiments/overnight_runs/<run_id>/
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time as time_mod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VENV_PY = REPO_ROOT / "backend" / ".venv" / "Scripts" / "python.exe"
OVERNIGHT_BASE = REPO_ROOT / "experiments" / "overnight_runs"


@dataclass
class Task:
    """One queue entry."""

    id: str  # short slug for filenames, e.g. "01_v28_23sym_2018_2019"
    description: str  # human-readable
    cmd: list[str]  # subprocess command (each token a list element)
    timeout_sec: int = 3600
    cwd: Path = REPO_ROOT
    critical: bool = False  # if True, queue aborts on failure
    skip_if_exists: Path | None = None  # if this path exists, skip
    env: dict[str, str] = field(default_factory=dict)


# ===========================================================================
# Task definitions — in execution order
# ===========================================================================


def build_tasks() -> list[Task]:
    py = str(VENV_PY)
    tasks: list[Task] = []

    # -----------------------------------------------------------------------
    # PHASE 1 — finish today's research line
    # -----------------------------------------------------------------------

    tasks.append(Task(
        id="01_v28_23sym_2018_2019",
        description=(
            "Run v28 walk-forward against the 23-symbol slim anchors "
            "(2018-2019). Outputs per-family per-symbol trades."
        ),
        cmd=[
            py,
            "backend/scripts/ml/v28_slim_anchor_walkforward.py",
            "--anchor-base", "D:/BacktestStationData/slim_anchors_2018_2019_universe/data/ml/anchors",
            "--window-start", "2018-01-01",
            "--window-end", "2019-12-31",
            "--symbols",
            "6A.c.0,6B.c.0,6C.c.0,6E.c.0,6J.c.0,6N.c.0,6S.c.0,BZ.c.0,CL.c.0,"
            "ES.c.0,HO.c.0,NG.c.0,NQ.c.0,RB.c.0,RTY.c.0,YM.c.0,ZB.c.0,ZC.c.0,"
            "ZF.c.0,ZN.c.0,ZS.c.0,ZT.c.0,ZW.c.0",
        ],
        timeout_sec=2700,
        skip_if_exists=Path(
            "D:/BacktestStationData/slim_anchors_2018_2019_universe/"
            "v28_simulation_results/rollup.csv"
        ),
    ))

    tasks.append(Task(
        id="02_v29_per_symbol_2018_2019",
        description=(
            "Per-symbol cum_R + liquidity profile + 4-universe single-account "
            "retention against the 23-symbol 2018-2019 trades."
        ),
        cmd=[
            py,
            "backend/scripts/ml/v29_per_symbol_analysis.py",
            "--trades-dir", "D:/BacktestStationData/slim_anchors_2018_2019_universe/v28_simulation_results",
            "--bars-window-start", "2018-01-01",
            "--bars-window-end", "2020-01-01",
        ],
        timeout_sec=1800,
        skip_if_exists=Path(
            "D:/BacktestStationData/slim_anchors_2018_2019_universe/"
            "v28_simulation_results/v29_summary.json"
        ),
    ))

    # -----------------------------------------------------------------------
    # PHASE 2 — extend other detectors to 2015-2017 (NQ/ES/YM only —
    # other 20 symbols don't have pre-2018 bars)
    # -----------------------------------------------------------------------

    other_detectors = [
        ("fvg_formation", "daily_fvg/4h_fvg/1h_fvg/15m_fvg"),
        ("swing_pivot", "pivot_3_1h/pivot_5_1h/pivot_3_4h/pivot_5_4h/pivot_5_daily"),
        ("displacement_candle", "1h_disp/4h_disp/daily_disp"),
        ("opening_gap_levels", "ndog/nwog"),
        ("opening_range_breakout", "ny_5m/ny_15m/ny_30m/asia_60m"),
        ("first_third_range", "first_third_daily/first_third_weekly"),
        ("interval_true_range", "daily_itr/weekly_itr/asia_itr/london_itr/ny_itr"),
        ("volume_profile", "daily_volume_profile/weekly_volume_profile/asia_volume_profile/london_volume_profile/ny_volume_profile"),
        ("forming_volume_profile", "daily_vp_asof_1h/daily_vp_asof_4h"),
        ("time_profile", "daily_3session/daily_4session/weekly/monthly"),
        ("psp_candle_divergence", "daily_psp/4h_psp/1h_psp"),
        ("smt_htf_reference_divergence", "weekly_smt/previous_day_smt"),
        ("equal_levels", "eq_pivot_5_1h_5pts/eq_pivot_5_1h_15pts/eq_pivot_5_4h_15pts/eq_pivot_5_daily_30pts/eq_pivot_3_1h_5pts/eq_pivot_3_1h_15pts/eq_pivot_3_4h_15pts"),
    ]

    for i, (detector, modes_slash) in enumerate(other_detectors, start=3):
        modes = modes_slash.split("/")
        for j, mode in enumerate(modes):
            tasks.append(Task(
                id=f"{i:02d}_{j:02d}_{detector}_{mode}_2015_2017",
                description=(
                    f"Run detector {detector} mode={mode} for NQ/ES/YM × 2015-2017"
                ),
                cmd=[
                    py, "-m", "app.cli.scan_research_events",
                    "--detector", detector,
                    "--mode", mode,
                    "--symbols", "NQ.c.0", "ES.c.0", "YM.c.0",
                    "--start", "2015-01-01",
                    "--end", "2018-01-01",
                ],
                timeout_sec=600,
                cwd=REPO_ROOT / "backend",
            ))

    # -----------------------------------------------------------------------
    # PHASE 3 — full-universe (23-symbol) slim anchors 2018-2026 + sim
    # -----------------------------------------------------------------------

    tasks.append(Task(
        id="91_slim_anchors_23sym_2018_2026",
        description=(
            "Build slim anchor matrices for 23-symbol universe × full available "
            "window (2018-2026). Largest single dataset we can build."
        ),
        cmd=[
            py,
            "backend/scripts/build_slim_anchors_2015_2017.py",
            "--start", "2018-01-01",
            "--end", "2026-05-15",
            "--out-dir",
            "D:/BacktestStationData/slim_anchors_2018_2026_universe/data/ml/anchors",
            "--symbols",
            "6A.c.0,6B.c.0,6C.c.0,6E.c.0,6J.c.0,6N.c.0,6S.c.0,BZ.c.0,CL.c.0,"
            "ES.c.0,HO.c.0,NG.c.0,NQ.c.0,RB.c.0,RTY.c.0,YM.c.0,ZB.c.0,ZC.c.0,"
            "ZF.c.0,ZN.c.0,ZS.c.0,ZT.c.0,ZW.c.0",
        ],
        timeout_sec=5400,  # 90 min
        skip_if_exists=Path(
            "D:/BacktestStationData/slim_anchors_2018_2026_universe/data/ml/anchors/"
            "ob_snapshots_xctx_strict_slim.parquet"
        ),
    ))

    tasks.append(Task(
        id="92_v28_23sym_2018_2026",
        description=(
            "Walk-forward against full-window 23-symbol slim anchors. The "
            "headline multi-year multi-symbol result."
        ),
        cmd=[
            py,
            "backend/scripts/ml/v28_slim_anchor_walkforward.py",
            "--anchor-base", "D:/BacktestStationData/slim_anchors_2018_2026_universe/data/ml/anchors",
            "--window-start", "2018-01-01",
            "--window-end", "2026-05-15",
            "--symbols",
            "6A.c.0,6B.c.0,6C.c.0,6E.c.0,6J.c.0,6N.c.0,6S.c.0,BZ.c.0,CL.c.0,"
            "ES.c.0,HO.c.0,NG.c.0,NQ.c.0,RB.c.0,RTY.c.0,YM.c.0,ZB.c.0,ZC.c.0,"
            "ZF.c.0,ZN.c.0,ZS.c.0,ZT.c.0,ZW.c.0",
        ],
        timeout_sec=3600,
        skip_if_exists=Path(
            "D:/BacktestStationData/slim_anchors_2018_2026_universe/"
            "v28_simulation_results/rollup.csv"
        ),
    ))

    tasks.append(Task(
        id="93_v29_per_symbol_2018_2026",
        description="Per-symbol analysis on the full-window 23-symbol trades.",
        cmd=[
            py,
            "backend/scripts/ml/v29_per_symbol_analysis.py",
            "--trades-dir", "D:/BacktestStationData/slim_anchors_2018_2026_universe/v28_simulation_results",
            "--bars-window-start", "2018-01-01",
            "--bars-window-end", "2026-05-15",
        ],
        timeout_sec=1800,
        skip_if_exists=Path(
            "D:/BacktestStationData/slim_anchors_2018_2026_universe/"
            "v28_simulation_results/v29_summary.json"
        ),
    ))

    # -----------------------------------------------------------------------
    # PHASE 4 — database hygiene
    # -----------------------------------------------------------------------

    backup_dir = REPO_ROOT / "experiments" / "db_backups"
    backup_stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    backup_path = backup_dir / f"meta_{backup_stamp}.sqlite"
    tasks.append(Task(
        id="94_backup_meta_sqlite",
        description=(
            f"Snapshot meta.sqlite to {backup_path.relative_to(REPO_ROOT)} "
            f"(uncompressed copy, ~37GB)."
        ),
        cmd=[
            py, "-c",
            f"import shutil, pathlib; p=pathlib.Path('{backup_path.as_posix()}'); "
            f"p.parent.mkdir(parents=True, exist_ok=True); "
            f"shutil.copyfile('{(REPO_ROOT / 'data' / 'meta.sqlite').as_posix()}', p); "
            f"print(f'wrote {{p}} ({{p.stat().st_size/1e9:.1f}} GB)')",
        ],
        timeout_sec=1800,
        skip_if_exists=backup_path,
    ))

    tasks.append(Task(
        id="95_data_inventory_report",
        description="Re-run the factual partition inventory report.",
        cmd=[
            py, "scripts/data_inventory_report.py",
        ],
        timeout_sec=1200,
    ))

    return tasks


# ===========================================================================
# Runner
# ===========================================================================


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f}m"
    return f"{minutes/60:.2f}h"


def run_task(task: Task, log_dir: Path) -> dict:
    """Run a single task. Returns a dict with status + timing + log path."""
    log_path = log_dir / f"{task.id}.log"
    started_at = datetime.now(timezone.utc)
    t0 = time_mod.time()

    if task.skip_if_exists is not None and task.skip_if_exists.exists():
        return {
            "id": task.id,
            "description": task.description,
            "started_at": started_at.isoformat(),
            "ended_at": started_at.isoformat(),
            "duration_sec": 0,
            "exit_code": -10,
            "status": "SKIPPED_EXISTS",
            "log_path": None,
            "skip_reason": f"exists: {task.skip_if_exists}",
        }

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"  # so logs flush as we go
    env.update(task.env)

    try:
        with log_path.open("w", encoding="utf-8") as logf:
            logf.write(f"# {task.id}\n")
            logf.write(f"# Started: {started_at.isoformat()}\n")
            logf.write(f"# Command: {' '.join(task.cmd)}\n")
            logf.write(f"# CWD: {task.cwd}\n")
            logf.write(f"# Timeout: {task.timeout_sec}s\n\n")
            logf.flush()

            proc = subprocess.run(
                task.cmd,
                stdout=logf,
                stderr=subprocess.STDOUT,
                cwd=task.cwd,
                timeout=task.timeout_sec,
                env=env,
            )
        exit_code = proc.returncode
        status = "OK" if exit_code == 0 else "FAIL"
    except subprocess.TimeoutExpired:
        exit_code = -1
        status = "TIMEOUT"
    except FileNotFoundError as exc:
        with log_path.open("a", encoding="utf-8") as logf:
            logf.write(f"\n!! FileNotFoundError: {exc}\n")
        exit_code = -2
        status = "NOT_FOUND"
    except Exception as exc:  # pragma: no cover — runtime safety
        with log_path.open("a", encoding="utf-8") as logf:
            logf.write(f"\n!! {type(exc).__name__}: {exc}\n")
        exit_code = -3
        status = f"EXCEPTION_{type(exc).__name__}"

    duration = time_mod.time() - t0
    ended_at = datetime.now(timezone.utc)
    return {
        "id": task.id,
        "description": task.description,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "duration_sec": round(duration, 1),
        "exit_code": exit_code,
        "status": status,
        "log_path": str(log_path.relative_to(REPO_ROOT)),
    }


def write_master_log(
    run_id: str, log_dir: Path, results: list[dict], header_extra: dict,
) -> None:
    md = log_dir / "MASTER_LOG.md"
    lines: list[str] = []
    lines.append(f"# Overnight queue run — {run_id}")
    lines.append("")
    lines.append(f"_Generated by `backend/scripts/overnight_queue.py`_")
    lines.append("")
    lines.append("## Header")
    lines.append("")
    for k, v in header_extra.items():
        lines.append(f"- **{k}**: {v}")
    lines.append("")
    lines.append("## Tasks")
    lines.append("")
    lines.append("| # | Task | Status | Duration | Exit |")
    lines.append("|---|---|---|---:|---:|")
    for i, r in enumerate(results, start=1):
        emoji = {
            "OK": "✓",
            "SKIPPED_EXISTS": "•",
            "FAIL": "✗",
            "TIMEOUT": "⏱",
            "NOT_FOUND": "?",
        }.get(r["status"], "!")
        dur = _format_duration(r["duration_sec"])
        lines.append(
            f"| {i:>2} | `{r['id']}` | {emoji} {r['status']} | {dur} | {r['exit_code']} |"
        )
    lines.append("")
    n_ok = sum(1 for r in results if r["status"] == "OK")
    n_skip = sum(1 for r in results if r["status"] == "SKIPPED_EXISTS")
    n_fail = len(results) - n_ok - n_skip
    lines.append(f"**Summary**: {n_ok} OK, {n_skip} skipped, {n_fail} failed/timed-out.")
    lines.append("")
    lines.append("## Per-task detail")
    lines.append("")
    for i, r in enumerate(results, start=1):
        lines.append(f"### {i}. `{r['id']}`")
        lines.append("")
        lines.append(f"{r['description']}")
        lines.append("")
        lines.append(f"- Started: `{r['started_at']}`")
        lines.append(f"- Ended:   `{r['ended_at']}`")
        lines.append(f"- Duration: {_format_duration(r['duration_sec'])}")
        lines.append(f"- Status: **{r['status']}** (exit {r['exit_code']})")
        if r.get("log_path"):
            lines.append(f"- Log: `{r['log_path']}`")
        if r.get("skip_reason"):
            lines.append(f"- Skip reason: {r['skip_reason']}")
        lines.append("")
    md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--list", action="store_true",
        help="Show the queue without running anything.",
    )
    parser.add_argument(
        "--skip", nargs="*", type=int, default=[],
        help="1-indexed task numbers to skip.",
    )
    parser.add_argument(
        "--only", nargs="*", type=int, default=None,
        help="1-indexed task numbers to run (everything else skipped).",
    )
    args = parser.parse_args()

    tasks = build_tasks()
    if args.list:
        print(f"=== Overnight queue ({len(tasks)} tasks) ===")
        for i, t in enumerate(tasks, start=1):
            print(f"  {i:>2}. {t.id}")
            print(f"      {t.description}")
            print(f"      timeout: {t.timeout_sec}s")
        return 0

    skip_set = set(args.skip)
    only_set = set(args.only) if args.only is not None else None

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir = OVERNIGHT_BASE / run_id
    log_dir.mkdir(parents=True, exist_ok=True)

    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:
        git_sha = "<unknown>"

    header = {
        "Run ID": run_id,
        "Started": datetime.now(timezone.utc).isoformat(),
        "Git SHA": git_sha,
        "Tasks queued": len(tasks),
        "Tasks skipped via --skip": sorted(skip_set) or "(none)",
        "Tasks limited via --only": sorted(only_set) if only_set else "(all)",
        "Repo root": str(REPO_ROOT),
    }

    print(f"=== Overnight queue run {run_id} ===")
    print(f"Log dir: {log_dir}")
    print(f"Tasks: {len(tasks)}")
    print()

    results = []
    for i, t in enumerate(tasks, start=1):
        # Pre-skip per CLI flags
        if i in skip_set:
            results.append({
                "id": t.id, "description": t.description,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "duration_sec": 0, "exit_code": -20,
                "status": "SKIPPED_CLI", "log_path": None,
            })
            print(f"[{i:>2}/{len(tasks)}] {t.id} -- SKIPPED via --skip")
            write_master_log(run_id, log_dir, results, header)
            continue
        if only_set is not None and i not in only_set:
            results.append({
                "id": t.id, "description": t.description,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "duration_sec": 0, "exit_code": -21,
                "status": "SKIPPED_ONLY", "log_path": None,
            })
            print(f"[{i:>2}/{len(tasks)}] {t.id} -- SKIPPED (not in --only)")
            write_master_log(run_id, log_dir, results, header)
            continue

        print(f"[{i:>2}/{len(tasks)}] {t.id} starting...", flush=True)
        result = run_task(t, log_dir)
        results.append(result)
        print(
            f"[{i:>2}/{len(tasks)}] {t.id} -> {result['status']} "
            f"({_format_duration(result['duration_sec'])})",
            flush=True,
        )
        # Write master log incrementally so user can check progress
        write_master_log(run_id, log_dir, results, header)

    # Final summary
    write_master_log(run_id, log_dir, results, header)
    n_ok = sum(1 for r in results if r["status"] == "OK")
    n_skip = sum(1 for r in results if r["status"].startswith("SKIPPED"))
    n_fail = len(results) - n_ok - n_skip
    print()
    print(f"=== Done. {n_ok} OK, {n_skip} skipped, {n_fail} failed/timed-out ===")
    print(f"Master log: {log_dir / 'MASTER_LOG.md'}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
