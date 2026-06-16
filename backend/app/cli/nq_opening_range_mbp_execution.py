"""Run the NQ middle-third opening-range MBP execution study."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app.research.nq_opening_range_mbp_execution import (
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
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--symbol", default="NQ.c.0")
    parser.add_argument("--holdout-start", default="2026-02-01")
    parser.add_argument("--start")
    parser.add_argument("--end")
    args = parser.parse_args(argv)

    lock_fd = acquire_lock(args.output_dir)
    config = OpeningRangeMbpExecutionConfig(
        symbol=args.symbol,
        holdout_start=args.holdout_start,
    )
    try:
        result = run_opening_range_mbp_execution_study(
            events_path=args.events_path,
            config=config,
            start=args.start,
            end=args.end,
        )
        write_opening_range_mbp_execution_outputs(result, args.output_dir)
        print(json.dumps(json_safe(result["summary"]), indent=2))
        return 0
    finally:
        release_lock(args.output_dir, lock_fd)


def acquire_lock(output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    lock_path = output_dir / ".run.lock"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise SystemExit(f"study already running or stale lock exists: {lock_path}") from exc
    os.write(fd, str(os.getpid()).encode("ascii"))
    return fd


def release_lock(output_dir: Path, lock_fd: int) -> None:
    os.close(lock_fd)
    lock_path = output_dir / ".run.lock"
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    raise SystemExit(main())
