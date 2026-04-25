"""Bulk pull of all data covered by the user's $180/mo Standard plan.

The plan covers (verified 2026-04-25 by Databento metadata.get_cost
returning $0):
- OHLCV-1s/1m/1h/1d at any history (15+ years available)
- TBBO / MBP-1 / BBO / Trades for the rolling LAST 12 MONTHS

This script walks the asset universe defined in cost_estimator.UNIVERSE
and pulls each schema in monthly chunks, calling the existing
historical.pull_month() for each (year, month, schema) combination.
Idempotent: skips dates that already have non-empty DBN on disk.

**IMPORTANT**: historical.py's filename convention is one DBN per
(schema, date), regardless of which symbols were pulled. So
splitting your symbol list across multiple batches produces
DATA LOSS -- the second batch's call sees "file exists, skipping"
and the symbols-in-batch-2 are never written. Default batch size
here is 999 so all symbols go in a single call. Don't lower it
unless you have a specific reason and you're OK with the
overwrites/skips behavior.

CLI:
    python -m app.ingest.bulk_free_pull
       [--schemas ohlcv-1m,ohlcv-1s,tbbo]   # comma-separated; default = all free
       [--years 8]                          # for OHLCV; TBBO is always 12mo
       [--max-symbols-per-call 999]         # one batch by default; see warning above

Run in the background; logs to D:/data/logs/bulk_free_pull.log.
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import sys
from pathlib import Path

from app.ingest.cost_estimator import UNIVERSE
from app.ingest.historical import (
    ALLOWED_SCHEMAS,
    pull_month,
)


def _setup_logger(data_root: Path) -> logging.Logger:
    log_dir = data_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log = logging.getLogger("bulk_free_pull")
    log.setLevel(logging.INFO)
    if not log.handlers:
        fh = logging.FileHandler(log_dir / "bulk_free_pull.log", encoding="utf-8")
        fh.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        log.addHandler(fh)
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(fh.formatter)
        log.addHandler(sh)
    return log


def _data_root() -> Path:
    default = "C:/data" if os.name == "nt" else "./data"
    return Path(os.environ.get("BS_DATA_ROOT", default))


def _all_symbols() -> list[str]:
    flat: list[str] = []
    for syms in UNIVERSE.values():
        flat.extend(syms)
    # Stable order, dedup.
    seen: set[str] = set()
    out: list[str] = []
    for s in flat:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _months_back(months: int, today: dt.date | None = None) -> list[tuple[int, int]]:
    """Return (year, month) tuples for the last N months ending at today's
    month, in chronological order."""
    today = today or dt.date.today()
    out: list[tuple[int, int]] = []
    y, m = today.year, today.month
    for _ in range(months):
        out.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(out))


def pull_schema(
    schema: str,
    *,
    symbols: list[str],
    months: list[tuple[int, int]],
    batch_size: int,
    logger: logging.Logger,
) -> None:
    """Pull all (year, month) batches for a schema. Symbols are batched
    so we don't hit Databento's symbol-per-request cap."""
    batches: list[list[str]] = []
    for i in range(0, len(symbols), batch_size):
        batches.append(symbols[i : i + batch_size])
    for year, month in months:
        for batch in batches:
            logger.info(
                f"pull {schema} {year}-{month:02d} symbols={','.join(batch)}"
            )
            try:
                result = pull_month(
                    year, month, symbols=batch, schema=schema, logger=logger
                )
                logger.info(
                    f"  -> attempted={result.days_attempted} "
                    f"written={result.days_written} "
                    f"skipped_existing={result.days_skipped_existing} "
                    f"skipped_empty={result.days_skipped_empty} "
                    f"errors={len(result.errors)}"
                )
            except Exception as e:
                logger.error(f"  -> CRASH: {type(e).__name__}: {e}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Bulk free pull from Databento.")
    p.add_argument(
        "--schemas",
        type=str,
        default="ohlcv-1m,ohlcv-1s,tbbo",
        help="Comma-separated schemas. Default: ohlcv-1m,ohlcv-1s,tbbo.",
    )
    p.add_argument(
        "--years",
        type=int,
        default=8,
        help="For OHLCV: how many years back. Default: 8. TBBO/MBP-1 always 12mo.",
    )
    p.add_argument(
        "--max-symbols-per-call",
        type=int,
        default=999,
        help=(
            "Symbols per Databento request. Default 999 = one batch "
            "(required for correctness; see module docstring)."
        ),
    )
    args = p.parse_args(argv)

    schemas = [s.strip() for s in args.schemas.split(",") if s.strip()]
    for s in schemas:
        if s not in ALLOWED_SCHEMAS:
            sys.stderr.write(f"unknown schema: {s} (allowed: {ALLOWED_SCHEMAS})\n")
            return 1

    data_root = _data_root()
    logger = _setup_logger(data_root)
    symbols = _all_symbols()

    logger.info(f"bulk pull starting; data_root={data_root} symbols={len(symbols)}")
    logger.info(f"  symbols: {','.join(symbols)}")
    logger.info(f"  schemas: {schemas}")

    for schema in schemas:
        if schema.startswith("ohlcv"):
            months = _months_back(args.years * 12)
        else:
            # L1 schemas (tbbo, mbp-1, etc.) are free for last 12 months only.
            months = _months_back(12)
        logger.info(
            f"--- {schema}: {len(months)} months "
            f"({months[0][0]}-{months[0][1]:02d} -> {months[-1][0]}-{months[-1][1]:02d}) ---"
        )
        pull_schema(
            schema,
            symbols=symbols,
            months=months,
            batch_size=args.max_symbols_per_call,
            logger=logger,
        )

    logger.info("bulk pull done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
