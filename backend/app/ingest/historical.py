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

    # Pull CFE VIX futures 1-minute bars:
    python -m app.ingest.historical --dataset XCBF.PITCH \
        --schema ohlcv-1m --symbols VX.n.0 --month 2026-03

Environment variables:
    DATABENTO_API_KEY   required. Same key the live ingester uses.
    BS_DATA_ROOT        optional. Same warehouse root.

Output layout:
    {DATA_ROOT}/raw/historical/{DATASET}-{SCHEMA}-{YYYY-MM-DD}-{SYMBOL}.dbn

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
import time
from dataclasses import dataclass, field
from pathlib import Path

try:
    import databento as db
except ImportError:  # pragma: no cover
    sys.stderr.write("databento package not installed. Run: pip install databento\n")
    sys.exit(1)


# --- Configuration -------------------------------------------------------

DATASET = "GLBX.MDP3"
DEFAULT_SCHEMA = "mbp-1"
ALLOWED_SCHEMAS = ("mbp-1", "tbbo", "ohlcv-1m", "ohlcv-1s", "ohlcv-1h", "ohlcv-1d")
SYMBOLS = ["NQ.c.0", "ES.c.0", "YM.c.0", "RTY.c.0"]
STYPE_IN = "continuous"

# Retry config for transient Databento failures. Empirically (2026-04-27)
# their MBP-1 endpoint returned "503 <empty message>" or "Response ended
# prematurely" cascades on consecutive full-day requests; backing off
# lets the rate-limit window clear. Keys: errors that should retry.
_TRANSIENT_ERROR_PATTERNS = (
    "503",
    "ended prematurely",
    "Service Unavailable",
    "timeout",
    "Connection",
)
_RETRY_BACKOFFS_SEC = (5, 30, 120, 600)
_THROTTLE_BETWEEN_CALLS_SEC = 1.0


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
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(fh)
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(fh.formatter)
        logger.addHandler(sh)
    return logger


def _data_root() -> Path:
    """Backwards-compat alias for `app.core.paths.warehouse_root`."""
    from app.core.paths import warehouse_root

    return warehouse_root()


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
    data_root: Path,
    day: dt.date,
    schema: str = DEFAULT_SCHEMA,
    dataset: str = DATASET,
) -> Path:
    """Legacy per-day path (multi-symbol). Kept for skip-existing checks
    on files written before the per-symbol refactor."""
    return data_root / "raw" / "historical" / f"{dataset}-{schema}-{day.isoformat()}.dbn"


def file_for_date_symbol(
    data_root: Path,
    day: dt.date,
    symbol: str,
    schema: str = DEFAULT_SCHEMA,
    dataset: str = DATASET,
) -> Path:
    """Per-symbol-per-day path. This is the path produced by the current
    puller; mirror's _DBN_RE accepts both legacy and new layouts."""
    return data_root / "raw" / "historical" / f"{dataset}-{schema}-{day.isoformat()}-{symbol}.dbn"


# --- Core pull -----------------------------------------------------------


def _is_transient(exc: BaseException) -> bool:
    msg = str(exc)
    return any(pat in msg for pat in _TRANSIENT_ERROR_PATTERNS)


def _get_range_with_retry(
    client: "db.Historical",
    schema: str,
    symbol: str,
    start: dt.datetime,
    end: dt.datetime,
    logger: logging.Logger,
    dataset: str = DATASET,
    stype_in: str = STYPE_IN,
) -> "db.DBNStore":
    """Call client.timeseries.get_range for ONE symbol with backoff retry
    on transient Databento errors. Non-transient errors propagate."""
    last_exc: BaseException | None = None
    for attempt in range(len(_RETRY_BACKOFFS_SEC) + 1):
        if attempt > 0:
            wait = _RETRY_BACKOFFS_SEC[attempt - 1]
            logger.warning(
                f"retry {attempt}/{len(_RETRY_BACKOFFS_SEC)} for {symbol} "
                f"on {start.date().isoformat()} after {wait}s "
                f"(last error: {type(last_exc).__name__}: {last_exc})"
            )
            time.sleep(wait)
        try:
            return client.timeseries.get_range(
                dataset=dataset,
                schema=schema,
                symbols=[symbol],
                stype_in=stype_in,
                start=start.isoformat(),
                end=end.isoformat(),
            )
        except Exception as e:
            last_exc = e
            if not _is_transient(e):
                # Permanent failure (auth, schema, etc.) -- don't retry.
                raise RuntimeError(f"databento get_range failed: {e}") from e
    raise RuntimeError(
        f"databento get_range failed after {len(_RETRY_BACKOFFS_SEC)} "
        f"retries for {symbol} on {start.date().isoformat()}: {last_exc}"
    ) from last_exc


def pull_day(
    client: "db.Historical",
    out_path: Path,
    day: dt.date,
    symbols: list[str],
    logger: logging.Logger,
    schema: str = DEFAULT_SCHEMA,
    dataset: str = DATASET,
    stype_in: str = STYPE_IN,
) -> tuple[bool, int]:
    """Fetch one day of `schema` data, ONE SYMBOL AT A TIME.

    Writes per-symbol DBN files at file_for_date_symbol(...). Each
    symbol's response is small enough (~30 MB / 1.5M rows for an
    active CME equity-index future on a busy weekday) that Databento's
    MBP-1 endpoint serves it cleanly, where a 4-symbol full-day request
    would 503 on payload size.

    Args:
        out_path: legacy per-day path (kept in signature for backward
            compatibility with callers; not actually written to anymore).

    Returns:
        (any_wrote_file, total_bytes_across_symbols). Empty days for
        every symbol return (False, 0) -- absence of all per-symbol
        files is the "no data" signal.
    """
    start = dt.datetime.combine(day, dt.time(0, 0, tzinfo=dt.timezone.utc))
    end = start + dt.timedelta(days=1)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        f"pulling {day.isoformat()}: "
        f"dataset={dataset} schema={schema} symbols={symbols} "
        f"(per-symbol mode)"
    )

    # Resolve data_root from out_path. Legacy caller passes
    # file_for_date(data_root, day, schema) which is
    # data_root/raw/historical/{filename}.dbn -- so data_root is two
    # parents up from the directory.
    data_root = out_path.parent.parent.parent

    any_wrote = False
    total_bytes = 0
    for i, symbol in enumerate(symbols):
        sym_path = file_for_date_symbol(data_root, day, symbol, schema, dataset)

        # Idempotent skip: if this symbol-day file already exists and is
        # non-empty, leave it alone.
        if sym_path.exists() and sym_path.stat().st_size > 0:
            logger.info(f"  skip existing: {sym_path.name}")
            any_wrote = True  # treat existing files as "we have this day"
            total_bytes += sym_path.stat().st_size
            continue

        try:
            response = _get_range_with_retry(
                client, schema, symbol, start, end, logger, dataset, stype_in
            )
        except RuntimeError as e:
            # Already-formatted error from _get_range_with_retry. Log per-
            # symbol failure and keep going to the next symbol -- partial
            # day is better than no day.
            logger.error(f"  {symbol}: {e}")
            continue

        df = response.to_df()
        if df.empty:
            logger.info(f"  {symbol}: no data, skipping write")
        else:
            response.to_file(str(sym_path))
            sz = sym_path.stat().st_size
            logger.info(f"  wrote {sym_path.name} ({sz:,} bytes, {len(df)} rows)")
            any_wrote = True
            total_bytes += sz

        # Throttle so successive calls don't trip Databento's rate limit.
        if i < len(symbols) - 1:
            time.sleep(_THROTTLE_BETWEEN_CALLS_SEC)

    return any_wrote, total_bytes


def pull_one_day_one_symbol(
    client: "db.Historical",
    day: dt.date,
    symbol: str,
    *,
    data_root: Path | None = None,
    schema: str = DEFAULT_SCHEMA,
    dataset: str = DATASET,
    stype_in: str = STYPE_IN,
    logger: logging.Logger | None = None,
) -> tuple[bool, int]:
    """Pull a single (date, symbol) DBN partition. Idempotent.

    Returns (wrote_or_existed, bytes). If the file exists non-empty,
    skip and return (True, current_size). Otherwise hit Databento with
    the same retry-with-backoff logic as `pull_day`. Empty data days
    return (False, 0). Permanent errors are caught and logged; caller
    sees (False, 0) without an exception.

    Used by `app.ingest.gap_filler` to fill missing partitions one at
    a time after a cost check has confirmed the call is free.
    """
    data_root = data_root or _data_root()
    logger = logger or _setup_logging(data_root)

    out_path = file_for_date_symbol(data_root, day, symbol, schema, dataset)
    if out_path.exists() and out_path.stat().st_size > 0:
        logger.info(f"  skip existing: {out_path.name}")
        return True, out_path.stat().st_size

    out_path.parent.mkdir(parents=True, exist_ok=True)
    start = dt.datetime.combine(day, dt.time(0, 0, tzinfo=dt.timezone.utc))
    end = start + dt.timedelta(days=1)

    try:
        response = _get_range_with_retry(
            client, schema, symbol, start, end, logger, dataset, stype_in
        )
    except RuntimeError as e:
        logger.error(f"  {symbol} {day.isoformat()}: {e}")
        return False, 0

    df = response.to_df()
    if df.empty:
        logger.info(f"  {symbol} {day.isoformat()}: no data, skipping write")
        return False, 0

    response.to_file(str(out_path))
    sz = out_path.stat().st_size
    logger.info(f"  wrote {out_path.name} ({sz:,} bytes, {len(df)} rows)")
    return True, sz


def pull_month(
    year: int,
    month: int,
    symbols: list[str] | None = None,
    data_root: Path | None = None,
    api_key: str | None = None,
    max_days: int | None = None,
    schema: str = DEFAULT_SCHEMA,
    dataset: str = DATASET,
    stype_in: str = STYPE_IN,
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
        raise ValueError(f"schema {schema!r} not in {ALLOWED_SCHEMAS}")

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
        out_path = file_for_date(data_root, day, schema, dataset)
        if out_path.exists() and out_path.stat().st_size > 0:
            result.days_skipped_existing += 1
            logger.info(f"skipping {day.isoformat()}: file exists")
            continue
        try:
            wrote, size = pull_day(
                client,
                out_path,
                day,
                symbols,
                logger,
                schema,
                dataset,
                stype_in,
            )
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
    p = argparse.ArgumentParser(description="Pull a month of historical data from Databento")
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
            "Comma-separated symbols, e.g. ES.c.0,YM.c.0 or VX.n.0. "
            f"Defaults to {','.join(SYMBOLS)}."
        ),
    )
    p.add_argument(
        "--dataset",
        type=str,
        default=DATASET,
        help=f"Databento dataset ID (default: {DATASET}; VX uses XCBF.PITCH).",
    )
    p.add_argument(
        "--stype-in",
        type=str,
        default=STYPE_IN,
        help=f"Databento input symbology type (default: {STYPE_IN}).",
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

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()] if args.symbols else None

    result = pull_month(
        year,
        month,
        symbols=symbols,
        max_days=args.max_days,
        schema=args.schema,
        dataset=args.dataset,
        stype_in=args.stype_in,
    )
    return 0 if not result.errors else 1


if __name__ == "__main__":
    sys.exit(main())
