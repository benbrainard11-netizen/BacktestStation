"""Run the frozen OR middle-third MBP study in resumable monthly chunks."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd

from app.cli.combine_nq_opening_range_mbp_execution import combine_chunks
from app.research.nq_opening_range_mbp_execution import (
    load_middle_third_events,
    run_opening_range_mbp_execution_study,
    write_opening_range_mbp_execution_outputs,
)
from app.research.nq_opening_range_mbp_execution_stats import json_safe
from app.research.nq_opening_range_mbp_execution_types import (
    OpeningRangeMbpExecutionConfig,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-path", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--symbol", default="NQ.c.0")
    parser.add_argument("--holdout-start", default="2026-02-01")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    config = OpeningRangeMbpExecutionConfig(
        symbol=args.symbol,
        holdout_start=args.holdout_start,
    )
    args.output_root.mkdir(parents=True, exist_ok=True)
    lock_fd = acquire_lock(args.output_root)
    try:
        chunk_dirs = run_chunks(
            args.events_path,
            args.output_root,
            config,
            args.start,
            args.end,
            args.force,
        )
        result = combine_chunks(chunk_dirs, config)
        combined_dir = args.output_root / "combined"
        write_opening_range_mbp_execution_outputs(result, combined_dir)
        print(json.dumps(json_safe(result["summary"]), indent=2))
        return 0
    finally:
        release_lock(args.output_root, lock_fd)


def run_chunks(
    events_path: Path,
    output_root: Path,
    config: OpeningRangeMbpExecutionConfig,
    start: str | None,
    end: str | None,
    force: bool,
) -> list[Path]:
    events = load_middle_third_events(events_path, config, start=start, end=end)
    chunk_dirs: list[Path] = []
    for month_start, month_end in month_windows(events["session_date"]):
        chunk_dir = output_root / "chunks" / month_start.strftime("%Y-%m")
        chunk_dirs.append(chunk_dir)
        summary_path = chunk_dir / "or_middle_third_mbp_summary.json"
        if summary_path.exists() and not force:
            print(f"SKIP {month_start:%Y-%m}: existing output", flush=True)
            continue
        print(f"RUN {month_start:%Y-%m}: {month_start} to {month_end}", flush=True)
        result = run_opening_range_mbp_execution_study(
            events_path=events_path,
            config=config,
            start=month_start.isoformat(),
            end=month_end.isoformat(),
        )
        write_opening_range_mbp_execution_outputs(result, chunk_dir)
        print(f"DONE {month_start:%Y-%m}", flush=True)
    return chunk_dirs


def month_windows(session_dates: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    months = sorted(pd.to_datetime(session_dates).dt.to_period("M").unique())
    return [
        (month.to_timestamp(), (month + 1).to_timestamp())
        for month in months
    ]


def acquire_lock(output_root: Path) -> int:
    lock_path = output_root / ".history.lock"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise SystemExit(f"history run already active or stale lock exists: {lock_path}") from exc
    os.write(fd, str(os.getpid()).encode("ascii"))
    return fd


def release_lock(output_root: Path, lock_fd: int) -> None:
    os.close(lock_fd)
    try:
        (output_root / ".history.lock").unlink()
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    raise SystemExit(main())
