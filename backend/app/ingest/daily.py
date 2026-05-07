"""Daily Databento pull — runs during the CME daily break.

Pulls one calendar day (default: yesterday UTC) of:
    - MBP-1 for equity-index futures: NQ.c.0, ES.c.0, YM.c.0
    - TBBO for the rest of the warehouse universe (energy, metals,
      bonds, FX futures)

Idempotent: per-symbol-per-day files already on disk are skipped.

Cost safety:
    Pre-flight check via `databento.Historical.metadata.get_cost`.
    If the quote exceeds COST_ABORT_THRESHOLD_USD ($0.01), the script
    refuses to run. This is the safety against silent billing once
    the user's free trial of MBP-1 ends.

CLI:
    # default: pull yesterday UTC
    python -m app.ingest.daily

    # explicit single day
    python -m app.ingest.daily --date 2026-04-30

    # backfill a range [start, end) (end exclusive, ISO dates)
    python -m app.ingest.daily --start 2026-04-16 --end 2026-05-04

    # dry-run: print the cost quote and exit
    python -m app.ingest.daily --dry-run
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import databento as db
except ImportError:  # pragma: no cover
    sys.stderr.write("databento package not installed. pip install databento\n")
    sys.exit(1)

from app.ingest import historical


# --- Universe ------------------------------------------------------------

DATASET = "GLBX.MDP3"
STYPE_IN = "continuous"

# Equity-index futures get MBP-1 (deeper than TBBO; included in current
# Databento trial). Add RTY here later if Ben starts trading it.
INDEX_SYMBOLS = ["NQ.c.0", "ES.c.0", "YM.c.0"]
INDEX_SCHEMA = "mbp-1"

# Everything else gets TBBO (top-of-book + trades, lighter, included
# on the $180/mo plan).
OTHER_SYMBOLS = [
    # Energy
    "CL.c.0", "NG.c.0",
    # Metals
    "GC.c.0", "SI.c.0",
    # Rates
    "ZN.c.0", "ZB.c.0", "ZF.c.0",
    # FX futures
    "6E.c.0", "6B.c.0", "6J.c.0",
]
OTHER_SCHEMA = "tbbo"

# Hard guard against silent billing. The trial returns $0; if the API
# ever quotes more, this aborts the whole run before any pull happens.
COST_ABORT_THRESHOLD_USD = 0.01


@dataclass
class DailyResult:
    days_attempted: int = 0
    days_written: int = 0
    days_skipped_existing: int = 0
    days_skipped_empty: int = 0
    bytes_written: int = 0
    cost_quote_usd: float = 0.0
    errors: list[str] = field(default_factory=list)


# --- Helpers -------------------------------------------------------------


def _data_root() -> Path:
    default = "C:/data" if os.name == "nt" else "./data"
    return Path(os.environ.get("BS_DATA_ROOT", default))


def _setup_logging(data_root: Path) -> logging.Logger:
    log_dir = data_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("daily_puller")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(log_dir / "daily.log", encoding="utf-8")
        fh.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(fh)
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(fh.formatter)
        logger.addHandler(sh)
    return logger


def yesterday_utc(today: dt.date | None = None) -> dt.date:
    """T-1 UTC date. Default reference point is now UTC."""
    today = today or dt.datetime.now(dt.timezone.utc).date()
    return today - dt.timedelta(days=1)


def date_range(start: dt.date, end: dt.date) -> list[dt.date]:
    """Half-open [start, end). Returns [] if end <= start."""
    if end <= start:
        return []
    days = []
    cur = start
    while cur < end:
        days.append(cur)
        cur += dt.timedelta(days=1)
    return days


# --- Cost pre-flight ----------------------------------------------------


def quote_total_cost(
    client: "db.Historical",
    days: list[dt.date],
    logger: logging.Logger,
) -> float:
    """Sum of cost quotes across (INDEX_SYMS + OTHER_SYMS) for the date
    range. Returns USD as float. Only `metadata` calls — no data is
    transferred."""
    if not days:
        return 0.0
    start = days[0].isoformat()
    end = (days[-1] + dt.timedelta(days=1)).isoformat()  # half-open
    total = 0.0
    quotes = [
        ("mbp-1", INDEX_SYMBOLS),
        ("tbbo", OTHER_SYMBOLS),
    ]
    for schema, syms in quotes:
        c = float(
            client.metadata.get_cost(
                dataset=DATASET,
                schema=schema,
                symbols=syms,
                stype_in=STYPE_IN,
                start=start,
                end=end,
            )
        )
        logger.info(
            f"cost quote: schema={schema} symbols={len(syms)} "
            f"window={start}..{end} = ${c:.4f}"
        )
        total += c
    return total


# --- Core ----------------------------------------------------------------


def pull_days(
    days: list[dt.date],
    *,
    data_root: Path | None = None,
    api_key: str | None = None,
    client: "db.Historical | None" = None,
    logger: logging.Logger | None = None,
    dry_run: bool = False,
    cost_threshold_usd: float = COST_ABORT_THRESHOLD_USD,
) -> DailyResult:
    """Pull each day in `days` for both schema/symbol groups.

    Idempotent: pre-existing per-symbol DBN files are skipped (handled
    by `historical.pull_day`).

    Cost safety: aborts before any pull if the metadata cost quote
    exceeds `cost_threshold_usd`. Returns a result with the quote
    populated so callers can surface what happened.
    """
    data_root = data_root or _data_root()
    api_key = api_key or os.environ.get("DATABENTO_API_KEY")
    logger = logger or _setup_logging(data_root)

    result = DailyResult()
    if not days:
        logger.info("no days to pull")
        return result

    if client is None:
        if not api_key:
            raise RuntimeError("DATABENTO_API_KEY not set")
        client = db.Historical(key=api_key)

    # 1. Cost pre-flight
    cost = quote_total_cost(client, days, logger)
    result.cost_quote_usd = cost
    logger.info(f"total cost quote for window: ${cost:.4f}")

    if cost > cost_threshold_usd:
        msg = (
            f"ABORT: cost quote ${cost:.4f} exceeds threshold "
            f"${cost_threshold_usd:.4f}. Refusing to pull. Check trial "
            f"status on databento.com or raise threshold explicitly."
        )
        logger.error(msg)
        result.errors.append(msg)
        return result

    if dry_run:
        logger.info("dry-run: cost ok, not pulling")
        return result

    # 2. Pull each day for both groups
    for day in days:
        result.days_attempted += 1
        for schema, syms in (
            (INDEX_SCHEMA, INDEX_SYMBOLS),
            (OTHER_SCHEMA, OTHER_SYMBOLS),
        ):
            out_path = historical.file_for_date(data_root, day, schema)
            try:
                wrote, size = historical.pull_day(
                    client, out_path, day, syms, logger, schema
                )
                if wrote:
                    result.days_written += 1
                    result.bytes_written += size
                else:
                    result.days_skipped_empty += 1
            except Exception as e:
                msg = f"{day.isoformat()} {schema}: {type(e).__name__}: {e}"
                logger.error(msg)
                result.errors.append(msg)

    logger.info(
        f"daily pull done: days={len(days)} "
        f"written_bundles={result.days_written} "
        f"empty_bundles={result.days_skipped_empty} "
        f"errors={len(result.errors)} "
        f"bytes={result.bytes_written:,}"
    )
    return result


# --- CLI -----------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument(
        "--date",
        type=str,
        default=None,
        help="Single ISO date (YYYY-MM-DD). Defaults to yesterday UTC.",
    )
    p.add_argument(
        "--start",
        type=str,
        default=None,
        help="Backfill range start (ISO date, inclusive). Use with --end.",
    )
    p.add_argument(
        "--end",
        type=str,
        default=None,
        help="Backfill range end (ISO date, EXCLUSIVE). Use with --start.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the cost quote and exit without pulling.",
    )
    p.add_argument(
        "--cost-threshold-usd",
        type=float,
        default=COST_ABORT_THRESHOLD_USD,
        help=(
            f"Abort if metadata cost quote exceeds this (default "
            f"${COST_ABORT_THRESHOLD_USD}). Set higher to allow paid pulls."
        ),
    )
    return p.parse_args(argv)


def _resolve_days(args: argparse.Namespace) -> list[dt.date]:
    if args.start and args.end:
        start = dt.date.fromisoformat(args.start)
        end = dt.date.fromisoformat(args.end)
        return date_range(start, end)
    if args.date:
        return [dt.date.fromisoformat(args.date)]
    return [yesterday_utc()]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    days = _resolve_days(args)
    if not days:
        sys.stderr.write("no days resolved (empty range?)\n")
        return 1

    result = pull_days(
        days,
        dry_run=args.dry_run,
        cost_threshold_usd=args.cost_threshold_usd,
    )
    return 0 if not result.errors else 1


if __name__ == "__main__":
    sys.exit(main())
