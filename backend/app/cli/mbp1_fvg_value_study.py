"""Run an MBP-1 assisted FVG support/resistance study.

The study builds one row per touched FVG:

1. Detect FVGs from OHLC bars.
2. Find the first later bar that retests the gap.
3. Label whether the gap held or failed over a forward bar horizon.
4. Compute MBP-1 top-of-book features around the first retest.

Usage:

    python -m app.cli.mbp1_fvg_value_study \\
        --symbol NQ.c.0 \\
        --start 2026-04-24 \\
        --end 2026-04-25 \\
        --timeframe 15m \\
        --max-zones 25 \\
        --output data/research/fvg_mbp1_nq_2026-04-24.csv
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

from app.data.reader import read_bars, read_mbp1
from app.research.mbp1_fvg_value import (
    build_fvg_value_study,
    rank_mbp1_feature_edges,
    summarize_outcomes,
)

logger = logging.getLogger("mbp1_fvg_value_study")

_MBP1_COLUMNS = [
    "ts_event",
    "symbol",
    "action",
    "side",
    "price",
    "size",
    "bid_px",
    "ask_px",
    "bid_sz",
    "ask_sz",
    "sequence",
]


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="NQ.c.0", help="Symbol to study.")
    parser.add_argument("--start", type=_parse_date, required=True, help="Inclusive date.")
    parser.add_argument("--end", type=_parse_date, required=True, help="Exclusive date.")
    parser.add_argument("--timeframe", default="15m", help="FVG bar timeframe.")
    parser.add_argument("--min-width-pts", type=float, default=0.0)
    parser.add_argument("--max-zones", type=int, default=50)
    parser.add_argument("--max-bars-after-formation", type=int, default=None)
    parser.add_argument("--horizon-bars", type=int, default=20)
    parser.add_argument("--reaction-multiple", type=float, default=1.0)
    parser.add_argument("--min-reaction-pts", type=float, default=0.0)
    parser.add_argument("--failure-buffer-pts", type=float, default=0.0)
    parser.add_argument("--pre-seconds", type=int, default=30)
    parser.add_argument("--post-seconds", type=int, default=30)
    parser.add_argument("--tick-size", type=float, default=0.25)
    parser.add_argument(
        "--exclude-neutral",
        action="store_true",
        help="Keep only decisive hold/fail/ambiguous labels.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional CSV path for the full study rows.",
    )
    args = parser.parse_args(argv)
    _setup_logging()

    if args.start >= args.end:
        parser.error("--start must be before --end")

    logger.info(
        "loading %s bars and MBP-1 for %s [%s, %s)",
        args.timeframe,
        args.symbol,
        args.start,
        args.end,
    )
    bars = read_bars(
        symbol=args.symbol,
        timeframe=args.timeframe,
        start=args.start,
        end=args.end,
    )
    mbp1 = read_mbp1(
        symbol=args.symbol,
        start=args.start,
        end=args.end,
        columns=_MBP1_COLUMNS,
    )
    logger.info("loaded %d bars and %d MBP-1 rows", len(bars), len(mbp1))

    study = build_fvg_value_study(
        bars=bars,
        mbp1=mbp1,
        symbol=args.symbol,
        timeframe=args.timeframe,
        min_width_pts=args.min_width_pts,
        max_zones=args.max_zones,
        max_bars_after_formation=args.max_bars_after_formation,
        horizon_bars=args.horizon_bars,
        reaction_multiple=args.reaction_multiple,
        min_reaction_pts=args.min_reaction_pts,
        failure_buffer_pts=args.failure_buffer_pts,
        pre_seconds=args.pre_seconds,
        post_seconds=args.post_seconds,
        tick_size=args.tick_size,
        include_neutral=not args.exclude_neutral,
    )

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        study.to_csv(args.output, index=False)
        logger.info("wrote %s", args.output)

    edges = rank_mbp1_feature_edges(study, min_count_per_side=3)
    payload = {
        "summary": summarize_outcomes(study),
        "rows_preview": (
            study.head(10).to_dict(orient="records") if not study.empty else []
        ),
        "top_feature_edges": (
            edges.head(15).to_dict(orient="records") if not edges.empty else []
        ),
        "output": str(args.output) if args.output is not None else None,
    }
    print(json.dumps(payload, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
