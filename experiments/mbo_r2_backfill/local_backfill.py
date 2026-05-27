"""Convert local Databento MBO DBN files into local parquet partitions.

This is the local-only companion to ``backfill.py``. It does not touch R2.

Example:
    backend/.venv/Scripts/python.exe experiments/mbo_r2_backfill/local_backfill.py \
        --start 2026-01-01 --end 2026-03-31
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

import databento as db  # noqa: E402

SYMBOLS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]
RAW_HISTORICAL = Path(r"D:\data\raw\historical")
PARQUET_ROOT = Path(r"D:\data\raw\databento\mbo")


def daterange(start: dt.date, end: dt.date):
    cur = start
    while cur <= end:
        yield cur
        cur += dt.timedelta(days=1)


def dbn_path(day: dt.date, symbol: str) -> Path:
    return RAW_HISTORICAL / f"GLBX.MDP3-mbo-{day.isoformat()}-{symbol}.dbn"


def parquet_path(day: dt.date, symbol: str) -> Path:
    return PARQUET_ROOT / f"symbol={symbol}" / f"date={day.isoformat()}" / "part-000.parquet"


def convert_dbn_to_parquet(source: Path, destination: Path, symbol: str) -> int:
    store = db.DBNStore.from_file(source)
    df = store.to_df(price_type="float")
    if "ts_event" not in df.columns:
        df = df.reset_index()

    df["symbol"] = symbol
    if "raw_symbol" in df.columns:
        df = df.drop(columns=["raw_symbol"])

    columns = [
        "ts_event",
        "ts_recv",
        "rtype",
        "publisher_id",
        "instrument_id",
        "action",
        "side",
        "price",
        "size",
        "channel_id",
        "order_id",
        "flags",
        "ts_in_delta",
        "sequence",
        "symbol",
    ]
    df = df[[c for c in columns if c in df.columns]]

    destination.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(destination, index=False, compression="snappy")
    return len(df)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--symbols", nargs="+", default=SYMBOLS)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)

    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)

    converted = 0
    skipped_existing = 0
    skipped_no_dbn = 0
    failed = 0
    total_rows = 0
    total_bytes = 0

    print(f"local MBO parquet backfill {start} -> {end}, symbols={args.symbols}")
    for day in daterange(start, end):
        for symbol in args.symbols:
            source = dbn_path(day, symbol)
            destination = parquet_path(day, symbol)

            if not source.exists():
                skipped_no_dbn += 1
                continue
            if destination.exists() and destination.stat().st_size > 0 and not args.overwrite:
                skipped_existing += 1
                continue

            print(f"  converting {symbol} {day} ... ", end="", flush=True)
            try:
                rows = convert_dbn_to_parquet(source, destination, symbol)
            except Exception as exc:
                failed += 1
                print(f"FAILED: {type(exc).__name__}: {exc}")
                continue

            size = destination.stat().st_size
            converted += 1
            total_rows += rows
            total_bytes += size
            print(f"{rows:,} rows, {size / 1e6:.1f} MB")

    print(
        "\nDONE: "
        f"converted={converted} skipped_existing={skipped_existing} "
        f"skipped_no_dbn={skipped_no_dbn} failed={failed} "
        f"rows={total_rows:,} size={total_bytes / 1e6:.1f} MB"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
