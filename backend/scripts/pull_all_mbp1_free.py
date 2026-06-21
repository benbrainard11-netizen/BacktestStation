"""Pull all-universe MBP-1 while Databento quotes the window at $0.

This is intentionally conservative:
- one upfront metadata.get_cost quote for the exact symbol/date window
- aborts before any download if the quote exceeds --cost-threshold-usd
- skips symbol-days that already exist as DBN or raw parquet
- writes only new raw DBN files, then optionally runs parquet_mirror

Example:
    python backend/scripts/pull_all_mbp1_free.py \
        --start 2025-05-28 --end 2026-05-27 --mirror
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import sys
import time
from pathlib import Path

try:
    import databento as db
except ImportError:  # pragma: no cover
    sys.stderr.write("databento package not installed. Run: pip install databento\n")
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.paths import warehouse_root  # noqa: E402
from app.ingest import cost_estimator, historical, parquet_mirror  # noqa: E402

SCHEMA = "mbp-1"
DATASET = "GLBX.MDP3"
STYPE_IN = "continuous"


def all_symbols() -> list[str]:
    out: list[str] = []
    for symbols in cost_estimator.UNIVERSE.values():
        for symbol in symbols:
            if symbol not in out:
                out.append(symbol)
    return out


def parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def iter_days(start: dt.date, end: dt.date) -> list[dt.date]:
    if end < start:
        raise ValueError(f"end {end} is before start {start}")
    days: list[dt.date] = []
    cur = start
    while cur <= end:
        days.append(cur)
        cur += dt.timedelta(days=1)
    return days


def dbn_path(data_root: Path, day: dt.date, symbol: str) -> Path:
    return historical.file_for_date_symbol(data_root, day, symbol, SCHEMA)


def parquet_path(data_root: Path, day: dt.date, symbol: str) -> Path:
    return (
        data_root
        / "raw"
        / "databento"
        / SCHEMA
        / f"symbol={symbol}"
        / f"date={day.isoformat()}"
        / "part-000.parquet"
    )


def have_symbol_day(data_root: Path, day: dt.date, symbol: str) -> bool:
    dbn = dbn_path(data_root, day, symbol)
    pq = parquet_path(data_root, day, symbol)
    return (dbn.exists() and dbn.stat().st_size > 0) or (pq.exists() and pq.stat().st_size > 0)


def setup_logger(data_root: Path) -> logging.Logger:
    log_dir = data_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("pull_all_mbp1_free")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh = logging.FileHandler(log_dir / "mbp1_all_assets_pull.log", encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def write_progress(data_root: Path, payload: dict) -> None:
    path = data_root / "logs" / "mbp1_all_assets_pull_progress.json"
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def quote_window(
    client: "db.Historical",
    symbols: list[str],
    start: dt.date,
    end: dt.date,
) -> float:
    return cost_estimator.estimate(
        client,
        symbols,
        SCHEMA,
        start.isoformat(),
        (end + dt.timedelta(days=1)).isoformat(),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pull all free MBP-1 symbol-days.")
    parser.add_argument("--start", required=True, type=parse_date, help="YYYY-MM-DD inclusive")
    parser.add_argument("--end", required=True, type=parse_date, help="YYYY-MM-DD inclusive")
    parser.add_argument("--symbols", default=None, help="Comma-separated symbols; defaults to full universe")
    parser.add_argument("--cost-threshold-usd", type=float, default=0.0)
    parser.add_argument("--sleep-sec", type=float, default=0.25, help="Throttle between pulls")
    parser.add_argument("--max-pulls", type=int, default=None, help="Cap pulls for testing")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mirror", action="store_true", help="Run parquet_mirror after pulling")
    args = parser.parse_args(argv)

    data_root = warehouse_root()
    logger = setup_logger(data_root)

    api_key = os.environ.get("DATABENTO_API_KEY")
    if not api_key:
        logger.error("DATABENTO_API_KEY not set")
        return 1

    symbols = (
        [s.strip() for s in args.symbols.split(",") if s.strip()]
        if args.symbols
        else all_symbols()
    )
    days = iter_days(args.start, args.end)
    client = db.Historical(key=api_key)

    logger.info(
        "starting all-assets MBP-1 pull: symbols=%d days=%d window=%s..%s dry_run=%s",
        len(symbols),
        len(days),
        args.start,
        args.end,
        args.dry_run,
    )
    logger.info("symbols: %s", ",".join(symbols))

    cost = quote_window(client, symbols, args.start, args.end)
    logger.info("upfront cost quote: $%.4f", cost)
    if cost > args.cost_threshold_usd:
        logger.error(
            "ABORT: cost quote $%.4f exceeds threshold $%.4f",
            cost,
            args.cost_threshold_usd,
        )
        return 2

    targets = [(day, symbol) for day in days for symbol in symbols]
    missing = [(day, symbol) for day, symbol in targets if not have_symbol_day(data_root, day, symbol)]
    logger.info("target symbol-days=%d existing=%d missing=%d", len(targets), len(targets) - len(missing), len(missing))

    if args.dry_run:
        write_progress(
            data_root,
            {
                "status": "dry_run",
                "cost_quote_usd": cost,
                "symbols": symbols,
                "start": args.start,
                "end": args.end,
                "targets": len(targets),
                "existing": len(targets) - len(missing),
                "missing": len(missing),
                "first_missing": missing[:20],
            },
        )
        return 0

    pulled = 0
    skipped_empty = 0
    bytes_written = 0
    errors: list[str] = []
    started = dt.datetime.now(dt.timezone.utc)

    for idx, (day, symbol) in enumerate(missing, start=1):
        if args.max_pulls is not None and pulled >= args.max_pulls:
            logger.info("max-pulls reached: %d", args.max_pulls)
            break

        try:
            wrote, size = historical.pull_one_day_one_symbol(
                client,
                day,
                symbol,
                data_root=data_root,
                schema=SCHEMA,
                logger=logger,
            )
            if wrote:
                pulled += 1
                bytes_written += size
            else:
                skipped_empty += 1
        except Exception as exc:  # pragma: no cover - defensive long-run guard
            msg = f"{day.isoformat()} {symbol}: {type(exc).__name__}: {exc}"
            logger.error(msg)
            errors.append(msg)

        if idx == 1 or idx % 25 == 0:
            write_progress(
                data_root,
                {
                    "status": "running",
                    "started_at_utc": started.isoformat(),
                    "last_update_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "cost_quote_usd": cost,
                    "symbols": symbols,
                    "start": args.start,
                    "end": args.end,
                    "missing_at_start": len(missing),
                    "processed_missing": idx,
                    "pulled": pulled,
                    "skipped_empty": skipped_empty,
                    "bytes_written": bytes_written,
                    "errors": errors[-10:],
                },
            )

        if args.sleep_sec > 0:
            time.sleep(args.sleep_sec)

    mirror_summary: dict | None = None
    if args.mirror:
        logger.info("running parquet_mirror for %s %s..%s", SCHEMA, args.start, args.end)
        result = parquet_mirror.mirror_warehouse(
            data_root,
            schemas={SCHEMA},
            start=args.start,
            end=args.end,
            symbols=set(symbols),
        )
        mirror_summary = {
            "scanned": result.scanned,
            "converted_dbn": result.converted_dbn,
            "converted_partitions": result.converted_partitions,
            "skipped_recent": result.skipped_recent,
            "skipped_unchanged": result.skipped_unchanged,
            "skipped_filtered": result.skipped_filtered,
            "skipped_unrecognized": result.skipped_unrecognized,
            "errors": result.errors,
        }
        logger.info("parquet_mirror summary: %s", mirror_summary)

    final = {
        "status": "done" if not errors else "done_with_errors",
        "started_at_utc": started.isoformat(),
        "completed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cost_quote_usd": cost,
        "symbols": symbols,
        "start": args.start,
        "end": args.end,
        "missing_at_start": len(missing),
        "pulled": pulled,
        "skipped_empty": skipped_empty,
        "bytes_written": bytes_written,
        "errors": errors,
        "mirror": mirror_summary,
    }
    write_progress(data_root, final)
    logger.info("done: %s", final)
    return 0 if not errors else 3


if __name__ == "__main__":
    raise SystemExit(main())
