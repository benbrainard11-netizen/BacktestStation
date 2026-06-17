"""Run the live frozen OR-high middle-third forward monitor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.research.nq_opening_range_mbp_execution_stats import json_safe
from app.research.nq_or_high_middle_third_forward import FORWARD_START_EXCLUSIVE
from app.research.nq_or_high_middle_third_live import (
    DEFAULT_EVENTS_DIR,
    DEFAULT_MONITOR_DIR,
    run_live_forward_monitor,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="NQ.c.0")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--holdout-start")
    parser.add_argument("--events-dir", type=Path, default=DEFAULT_EVENTS_DIR)
    parser.add_argument("--monitor-dir", type=Path, default=DEFAULT_MONITOR_DIR)
    parser.add_argument("--context-deadzone-pts", type=float, default=8.0)
    parser.add_argument("--forward-start-exclusive", default=FORWARD_START_EXCLUSIVE)
    args = parser.parse_args(argv)

    result = run_live_forward_monitor(
        symbol=args.symbol,
        start=args.start,
        end=args.end,
        holdout_start=args.holdout_start,
        events_dir=args.events_dir,
        monitor_dir=args.monitor_dir,
        context_deadzone_pts=args.context_deadzone_pts,
        forward_start_exclusive=args.forward_start_exclusive,
    )
    print(json.dumps(json_safe(result["summary"]), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
