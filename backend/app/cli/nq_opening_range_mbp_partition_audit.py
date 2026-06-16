"""Audit MBP partition availability for frozen middle-third OR events."""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from app.research.nq_opening_range_mbp_execution import (
    MbpWindowLoader,
    load_middle_third_events,
)
from app.research.nq_opening_range_mbp_execution_types import (
    OpeningRangeMbpExecutionConfig,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events-path", type=Path, required=True)
    parser.add_argument("--symbol", default="NQ.c.0")
    parser.add_argument("--holdout-start", default="2026-02-01")
    parser.add_argument("--start")
    parser.add_argument("--end")
    args = parser.parse_args(argv)

    config = OpeningRangeMbpExecutionConfig(
        symbol=args.symbol,
        holdout_start=args.holdout_start,
    )
    events = load_middle_third_events(
        args.events_path,
        config,
        start=args.start,
        end=args.end,
    )
    loader = MbpWindowLoader(config.symbol)
    available: list[str] = []
    missing: list[str] = []
    for session_date in events["session_date"].astype(str):
        date_value = dt.date.fromisoformat(session_date)
        if loader._partition_path(date_value) is None:
            missing.append(session_date)
        else:
            available.append(session_date)

    print(f"middle_third_sessions={len(events)}")
    print(f"available_mbp_partitions={len(available)}")
    print(f"missing_mbp_partitions={len(missing)}")
    if available:
        print(f"first_available={available[0]}")
        print(f"last_available={available[-1]}")
    if missing:
        print("missing=" + ",".join(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
