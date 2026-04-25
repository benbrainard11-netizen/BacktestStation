"""Monthly historical MBP-1 puller from Databento.

Live TBBO is the going-forward feed. This script pulls the higher-fidelity
MBP-1 data for a complete past month, one day at a time, and writes
per-day DBN files into the warehouse archive. Run on the 1st of each
month via Windows Task Scheduler to accumulate a multi-year MBP-1
archive automatically.

Usage:

    # Default: pull last full month for the configured symbols.
    python -m app.ingest.historical

    # Backfill a specific month:
    python -m app.ingest.historical --month 2026-03

    # Back-cap how many days to pull (useful for testing):
    python -m app.ingest.historical --month 2026-03 --max-days 5

Environment variables:
    DATABENTO_API_KEY   required. Same key the live ingester uses.
    BS_DATA_ROOT        optional. Same warehouse root.

Output layout:
    {DATA_ROOT}/raw/historical/{DATASET}-{SCHEMA}-{YYYY-MM-DD}.dbn

Idempotent: days that already have a non-empty .dbn file are skipped.
Days where Databento returns no data (weekends, holidays, mid-day gaps)
do not write a file — the absence of a file is the signal.

This is BLOCKING — runs day-by-day in a single thread. A full month of
MBP-1 for 4 CME futures symbols is ~10-30 minutes of API + write time
depending on tick volume. Keep the Task Scheduler entry's timeout
generous (1+ hour).
"""

from __future__ import annotations

import argparse
import calendar
import datetime as dt
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import databento as db
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "databento package not installed. Run: pip install databento\n"
    )
    sys.exit(1)


# --- Configuration -------------------------------------------------------

DATASET = "GLBX.MDP3"
DEFAULT_SCHEMA = "mbp-1"
ALLOWED_SCHEMAS = ("mbp-1", "tbbo", "ohlcv-1m", "ohlcv-1s", "ohlcv-1h", "ohlcv-1d")
SYMBOLS = ["NQ.c.0", "ES.c.0", "YM.c.0", "RTY.c.0"]
STYPE_IN = "continuous"


# --- Result --------------------------------------------------------------


@dataclass
class PullResult:
    days_attempted: int = 0
    days_written: int = 0
    days_skipped_existing: int = 0
    days_skipped_empty: int = 0
    bytes_written: int = 0
    errors: list[str] = field(default_factory=list)


# --- Setup ---------------------------------------------------------------


def _setup_logging(data_root: Path) -> logging.Logger:
    log_dir = data_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("historical_puller")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(log_dir / "historical.log", encoding="utf-8")
        fh.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(fh)
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(fh.formatter)
        logger.addHandler(sh)
    return logger


def _data_root() -> Path:
    default = "C:/data" if os.name == "nt" else "./data"
    return Path(os.environ.get("BS_DATA_ROOT", default))


# --- Date helpers --------------------------------------------------------


def previous_month(today: dt.date | None = None) -> tuple[int, int]:
    """Return (year, month) for the calendar month before `today`.

    `today` defaults to UTC now. Picking from the 1st of any month
    targets the prior month uniformly.
    """
    today = today or dt.datetime.now(dt.timezone.utc).date()
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


def days_in_month(year: int, month: int) -> list[dt.date]:
    last = calendar.monthrange(year, month)[1]
    return [dt.date(year, month, d) for d in range(1, last + 1)]


# --- File path -----------------------------------------------------------


def file_for_date(
    data_root: Path, day: dt.date, schema: str = DEFAULT_SCHEMA
) -> Path:
    return (
        data_root
        / "raw"
        / "historical"
        / f"{DATASET}-{schema}-{day.isoformat()}.dbn"
    )


# --- Core pull -----------------------------------------------------------


def pull_day(
    client: "db.Historical",
    out_path: Path,
    day: dt.date,
    symbols: list[str],
    logger: logging.Logger,
    schema: str = DEFAULT_SCHEMA,
) -> tuple[bool, int]:
    """Fetch one day's worth of `schema` data and write to `out_path`.

    Returns (wrote_file, bytes_written). Empty responses produce no
    file (returns (False, 0)) — the absence of the file is the signal
    for "no data on that day".
    """
    start = dt.datetime.combine(
        day, dt.time(0, 0, tzinfo=dt.timezone.utc)
    )
    end = start + dt.timedelta(days=1)

    logger.info(
        f"pulling {day.isoformat()}: "
        f"dataset={DATASET} schema={schema} symbols={symbols}"
    )

    try:
        response = client.timeseries.get_range(
            dataset=DATASET,
            schema=schema,
            symbols=symbols,
            stype_in=STYPE_IN,
            start=start.isoformat(),
            end=end.isoformat(),
        )
    except Exception as e:
        # Databento raises a variety of exception types; log and bubble
        # up so the caller can decide whether to keep going.
        raise RuntimeError(f"databento get_range failed: {e}") from e

    # The response is a DBNStore. .to_file() writes the DBN bytes to
    # disk. If the response is empty, write nothing and return.
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Quick empty-check: if the dataframe form has zero rows, skip.
    df = response.to_df()
    if df.empty:
        logger.info(f"no data for {day.isoformat()}, skipping write")
        return False, 0

    response.to_file(str(out_path))
    size = out_path.stat().st_size
    logger.info(f"wrote {out_path.name} ({size:,} bytes, {len(df)} rows)")
    return True, size


def pull_month(
    year: int,
    month: int,
    symbols: list[str] | None = None,
    data_root: Path | None = None,
    api_key: str | None = None,
    max_days: int | None = None,
    schema: str = DEFAULT_SCHEMA,
    *,
    client: "db.Historical | None" = None,
    logger: logging.Logger | None = None,
) -> PullResult:
    """Pull every day in (year, month). Idempotent on existing files.

    `client` and `logger` parameters are for tests — production callers
    leave them None and get the real ones constructed from env.
    """
    if not (1 <= month <= 12):
        raise ValueError(f"month must be 1..12, got {month}")
    if schema not in ALLOWED_SCHEMAS:
        raise ValueError(
            f"schema {schema!r} not in {ALLOWED_SCHEMAS}"
        )

    symbols = symbols or SYMBOLS
    data_root = data_root or _data_root()
    api_key = api_key or os.environ.get("DATABENTO_API_KEY")
    logger = logger or _setup_logging(data_root)

    if client is None:
        if not api_key:
            raise RuntimeError("DATABENTO_API_KEY not set")
        client = db.Historical(key=api_key)

    result = PullResult()
    days = days_in_month(year, month)
    if max_days is not None:
        days = days[:max_days]

    for day in days:
        result.days_attempted += 1
        out_path = file_for_date(data_root, day, schema)
        if out_path.exists() and out_path.stat().st_size > 0:
            result.days_skipped_existing += 1
            logger.info(f"skipping {day.isoformat()}: file exists")
            continue
        try:
            wrote, size = pull_day(client, out_path, day, symbols, logger, schema)
            if wrote:
                result.days_written += 1
                result.bytes_written += size
            else:
                result.days_skipped_empty += 1
        except Exception as e:
            msg = f"{day.isoformat()}: {type(e).__name__}: {e}"
            logger.error(msg)
            result.errors.append(msg)

    logger.info(
        f"pull complete: attempted={result.days_attempted} "
        f"written={result.days_written} "
        f"skipped_existing={result.days_skipped_existing} "
        f"skipped_empty={result.days_skipped_empty} "
        f"errors={len(result.errors)} "
        f"bytes={result.bytes_written:,}"
    )
    return result


# --- Entry point ---------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Pull a month of historical data from Databento"
    )
    p.add_argument(
        "--month",
        type=str,
        default=None,
        help="YYYY-MM (defaults to last full month UTC)",
    )
    p.add_argument(
        "--schema",
        type=str,
        default=DEFAULT_SCHEMA,
        choices=ALLOWED_SCHEMAS,
        help=f"Databento schema (default: {DEFAULT_SCHEMA})",
    )
    p.add_argument(
        "--symbols",
        type=str,
        default=None,
        help=(
            "Comma-separated continuous symbols, e.g. ES.c.0,YM.c.0. "
            f"Defaults to {','.join(SYMBOLS)}."
        ),
    )
    p.add_argument(
        "--max-days",
        type=int,
        default=None,
        help="Cap the number of days pulled (testing/backfill control)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.month is None:
        year, month = previous_month()
    else:
        try:
            year_str, month_str = args.month.split("-")
            year = int(year_str)
            month = int(month_str)
        except ValueError:
            sys.stderr.write(f"--month must be YYYY-MM, got {args.month!r}\n")
            return 1

    symbols = (
        [s.strip() for s in args.symbols.split(",") if s.strip()]
        if args.symbols
        else None
    )

    result = pull_month(
        year,
        month,
        symbols=symbols,
        max_days=args.max_days,
        schema=args.schema,
    )
    return 0 if not result.errors else 1


if __name__ == "__main__":
    sys.exit(main())
