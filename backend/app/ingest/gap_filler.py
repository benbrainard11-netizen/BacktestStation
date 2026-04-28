"""Weekly gap-filler for the historical MBP-1 archive.

Scans `D:\\data\\raw\\historical\\` for the last N months of NQ/ES/YM/RTY
MBP-1 partitions, identifies missing (date, symbol) pairs, cost-checks
each gap, pulls if free, skip-warns if paid.

Designed for a Sunday 03:00 local scheduled task — the historical
puller fires monthly on day 1, so by Sunday the previous week's data
should be on disk; this catches anything the monthly fire missed.

Insurance, not an emergency tool. The default `--last-n-months 3` keeps
the scan cheap (a few hundred (date, symbol) checks) and bounded by
what's still in the Databento $0 free tier.

Usage:

    # Default: scan last 3 months, fill any $0-cost gaps.
    python -m app.ingest.gap_filler

    # Wider window:
    python -m app.ingest.gap_filler --last-n-months 6

    # See what would happen without pulling:
    python -m app.ingest.gap_filler --dry-run

Environment variables:
    DATABENTO_API_KEY   required (for cost estimation + pulls).
    BS_DATA_ROOT        optional. Same warehouse root as historical.py.

Discipline rules honored:
- Raw data is append-only — only writes new files, never modifies existing.
- $0-cost guardrail: any gap with cost > $0 is logged with a "skip-warn"
  and never pulled. The CLI will not silently rack up Databento charges.
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

from app.ingest import cost_estimator, historical


# --- Result --------------------------------------------------------------


@dataclass
class GapFillResult:
    scanned_partitions: int = 0
    existing: int = 0
    gaps_found: int = 0
    pulled: int = 0
    skipped_paid: int = 0
    failed: int = 0
    bytes_written: int = 0
    skip_warn_log: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# --- Date helpers --------------------------------------------------------


def _data_root() -> Path:
    default = "C:/data" if os.name == "nt" else "./data"
    return Path(os.environ.get("BS_DATA_ROOT", default))


def _is_weekday(day: dt.date) -> bool:
    return day.weekday() < 5  # Mon-Fri


def _months_back(today: dt.date, n: int) -> list[tuple[int, int]]:
    """Return [(year, month)] for the last `n` months ending in
    today's month, oldest first."""
    out: list[tuple[int, int]] = []
    y, m = today.year, today.month
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(out))


def _days_in_month(year: int, month: int) -> list[dt.date]:
    last = calendar.monthrange(year, month)[1]
    return [dt.date(year, month, d) for d in range(1, last + 1)]


def iter_target_partitions(
    last_n_months: int,
    symbols: list[str],
    today: dt.date | None = None,
) -> list[tuple[dt.date, str]]:
    """Enumerate every (weekday, symbol) pair in the last N months.

    Excludes weekends (no market data). Holidays are not filtered —
    they'll surface as empty-data days and produce no file (the
    pull_one_day_one_symbol caller handles this gracefully).
    """
    today = today or dt.date.today()
    out: list[tuple[dt.date, str]] = []
    for year, month in _months_back(today, last_n_months):
        for day in _days_in_month(year, month):
            if not _is_weekday(day):
                continue
            # Don't try to pull data for days that haven't happened yet.
            if day > today:
                continue
            for symbol in symbols:
                out.append((day, symbol))
    return out


def existing_partitions(
    data_root: Path,
    schema: str = historical.DEFAULT_SCHEMA,
) -> set[tuple[dt.date, str]]:
    """Set of (date, symbol) pairs already on disk for `schema`.

    Recognizes both the per-symbol filename layout (current) AND the
    legacy multi-symbol layout (pre-2026-04-27). For legacy files
    we cannot tell which symbols were inside without reading the DBN,
    so we treat a legacy file as "all configured symbols present" for
    that date — over-counting is safer than re-pulling.
    """
    out: set[tuple[dt.date, str]] = set()
    historical_dir = data_root / "raw" / "historical"
    if not historical_dir.is_dir():
        return out

    prefix = f"{historical.DATASET}-{schema}-"
    for path in historical_dir.iterdir():
        if not path.is_file() or not path.name.endswith(".dbn"):
            continue
        if path.stat().st_size == 0:
            continue
        if not path.name.startswith(prefix):
            continue
        # Strip prefix and extension. Pattern after that is either:
        #   YYYY-MM-DD                   (legacy multi-symbol)
        #   YYYY-MM-DD-{symbol}          (per-symbol)
        rest = path.name[len(prefix) : -len(".dbn")]
        # ISO date is exactly 10 chars
        date_str = rest[:10]
        try:
            day = dt.date.fromisoformat(date_str)
        except ValueError:
            continue
        sym_part = rest[10:]
        if sym_part == "":
            # Legacy multi-symbol file — mark all configured symbols.
            for sym in historical.SYMBOLS:
                out.add((day, sym))
        elif sym_part.startswith("-"):
            sym = sym_part[1:]
            out.add((day, sym))
    return out


def compute_gaps(
    targets: list[tuple[dt.date, str]],
    existing: set[tuple[dt.date, str]],
) -> list[tuple[dt.date, str]]:
    return [pair for pair in targets if pair not in existing]


# --- Cost gating ---------------------------------------------------------


def _is_free(
    client: "db.Historical",
    symbol: str,
    day: dt.date,
    schema: str,
) -> tuple[bool, float]:
    """Returns (is_free, cost_usd). Cost-check failures fall closed
    (returns (False, NaN)) — we'd rather skip-warn than accidentally
    bill on a flaky cost call."""
    start = day.isoformat()
    end = (day + dt.timedelta(days=1)).isoformat()
    try:
        cost = cost_estimator.estimate(
            client, [symbol], schema, start, end
        )
    except Exception:  # pragma: no cover — defensive against API blips
        return False, float("nan")
    return cost == 0.0, cost


# --- Driver --------------------------------------------------------------


def fill_gaps(
    *,
    last_n_months: int,
    symbols: list[str] | None = None,
    schema: str = historical.DEFAULT_SCHEMA,
    data_root: Path | None = None,
    dry_run: bool = False,
    api_key: str | None = None,
    today: dt.date | None = None,
    client: "db.Historical | None" = None,
    logger: logging.Logger | None = None,
) -> GapFillResult:
    """Pure(ish): scan, classify, optionally pull. `today` is injected
    so tests can pin the clock."""
    symbols = symbols or historical.SYMBOLS
    data_root = data_root or _data_root()
    api_key = api_key or os.environ.get("DATABENTO_API_KEY")
    logger = logger or _setup_logging(data_root)

    if client is None and not dry_run:
        if not api_key:
            raise RuntimeError("DATABENTO_API_KEY not set")
        client = db.Historical(key=api_key)

    targets = iter_target_partitions(last_n_months, symbols, today=today)
    existing = existing_partitions(data_root, schema=schema)
    gaps = compute_gaps(targets, existing)

    result = GapFillResult(
        scanned_partitions=len(targets),
        existing=len(targets) - len(gaps),
        gaps_found=len(gaps),
    )

    logger.info(
        f"gap-filler scan: targets={result.scanned_partitions} "
        f"existing={result.existing} gaps={result.gaps_found} "
        f"dry_run={dry_run}"
    )

    for day, symbol in gaps:
        if dry_run or client is None:
            # Dry-run: we can still cost-check IF we have a client,
            # otherwise just log "would attempt".
            if client is not None:
                free, cost = _is_free(client, symbol, day, schema)
                msg = (
                    f"DRY: {symbol} {day.isoformat()} "
                    f"({'free' if free else f'${cost:.2f}'}) "
                    f"-> would {'pull' if free else 'skip-warn'}"
                )
            else:
                msg = f"DRY: {symbol} {day.isoformat()} -> would cost-check + decide"
            logger.info(msg)
            continue

        free, cost = _is_free(client, symbol, day, schema)
        if not free:
            warn = (
                f"skip-warn: {symbol} {day.isoformat()} would cost "
                f"${cost:.2f} (above $0 guardrail)"
            )
            logger.warning(warn)
            result.skip_warn_log.append(warn)
            result.skipped_paid += 1
            continue

        wrote, sz = historical.pull_one_day_one_symbol(
            client, day, symbol, data_root=data_root, schema=schema, logger=logger
        )
        if wrote:
            result.pulled += 1
            result.bytes_written += sz
        else:
            # Empty-data day OR a permanent failure (already logged inside).
            # Either way it's not a "we tried but couldn't recover" — just no data.
            result.failed += 1

    logger.info(
        f"gap-filler done: pulled={result.pulled} "
        f"skipped_paid={result.skipped_paid} failed={result.failed} "
        f"bytes={result.bytes_written:,}"
    )
    return result


# --- Logging -------------------------------------------------------------


def _setup_logging(data_root: Path) -> logging.Logger:
    """Same convention as historical.py: file + stderr, append mode."""
    logs_dir = data_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "gap_filler.log"

    logger = logging.getLogger("app.ingest.gap_filler")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


# --- CLI -----------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fill gaps in the historical MBP-1 archive."
    )
    p.add_argument(
        "--last-n-months", type=int, default=3,
        help="Scan window in months (default: 3).",
    )
    p.add_argument(
        "--schema", type=str, default=historical.DEFAULT_SCHEMA,
        choices=historical.ALLOWED_SCHEMAS,
        help=f"Databento schema (default: {historical.DEFAULT_SCHEMA}).",
    )
    p.add_argument(
        "--symbols", type=str, default=None,
        help=(
            "Comma-separated continuous symbols. "
            f"Defaults to {','.join(historical.SYMBOLS)}."
        ),
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be pulled without hitting the paid API.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    symbols = (
        [s.strip() for s in args.symbols.split(",") if s.strip()]
        if args.symbols
        else None
    )
    result = fill_gaps(
        last_n_months=args.last_n_months,
        symbols=symbols,
        schema=args.schema,
        dry_run=args.dry_run,
    )
    # Exit non-zero if there were unexpected failures (paid skips are not
    # failures — they're the guardrail working as intended).
    return 0 if not result.errors else 1


if __name__ == "__main__":
    sys.exit(main())
