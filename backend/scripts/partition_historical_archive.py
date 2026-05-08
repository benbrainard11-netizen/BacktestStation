"""One-time partition job: split archive .dbn.zst files into the
BacktestStation warehouse layout.

Source: a single Databento OHLCV-1m DBN.zst file per symbol (covering
years of bars). Recovered from the recycle bin of the deleted
InSyncTradeBot project on 2026-05-08.

Destination: per-day partitioned parquets in the existing warehouse:

    D:\\data\\processed\\bars\\timeframe=1m\\symbol={SYM}\\date={YYYY-MM-DD}\\part-000.parquet

Schema matches existing partitions written by ingest/parquet_mirror.py:
ts_event, symbol, open, high, low, close, volume, trade_count, vwap.
The DBN OHLCV-1m records don't carry trade_count or vwap, so trade_count
is filled with 0 and vwap with NaN. The reader's resampler tolerates
NaN vwap (see app/data/reader.py:_resample_bars docstring).

Idempotent: if a target partition file already exists, it's left
untouched. The existing 2026-03+ warehouse partitions (written by the
daily Databento ingester) won't be overwritten.

Run:
    cd C:\\Users\\benbr\\BacktestStation\\backend
    python -m scripts.partition_historical_archive
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import databento as db
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("partition_archive")


SOURCE_DIR = Path(r"C:\Users\benbr\BacktestStation\staging\historical_archive")
WAREHOUSE_ROOT = Path(r"D:\data\processed\bars\timeframe=1m")
SYMBOLS = ["NQ.c.0", "ES.c.0", "YM.c.0"]


def _source_path(symbol: str) -> Path:
    bare = symbol.split(".")[0]  # NQ.c.0 -> NQ
    return SOURCE_DIR / f"{bare}.c.0_ohlcv-1m.dbn.zst"


def _target_partition(symbol: str, date_str: str) -> Path:
    return (
        WAREHOUSE_ROOT
        / f"symbol={symbol}"
        / f"date={date_str}"
        / "part-000.parquet"
    )


def _normalize_for_warehouse(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Match the existing warehouse parquet schema (see reader.py /
    parquet_mirror.py)."""
    out = df.reset_index()  # ts_event becomes a column
    if "ts_event" not in out.columns:
        # databento DBNStore.to_df() indexes by ts_event by default, but
        # be defensive in case that changes.
        out = out.rename(columns={out.columns[0]: "ts_event"})
    keep = ["ts_event", "open", "high", "low", "close", "volume"]
    missing = [c for c in keep if c not in out.columns]
    if missing:
        raise ValueError(f"DBN frame missing columns: {missing}")
    out = out[keep].copy()
    out["symbol"] = symbol
    # Schema requires trade_count + vwap; OHLCV records don't carry them.
    out["trade_count"] = 0
    out["vwap"] = float("nan")
    # Ensure correct dtypes
    out["ts_event"] = pd.to_datetime(out["ts_event"], utc=True)
    out["volume"] = out["volume"].astype("uint64")
    out["trade_count"] = out["trade_count"].astype("uint32")
    return out[
        [
            "ts_event", "symbol", "open", "high", "low", "close",
            "volume", "trade_count", "vwap",
        ]
    ]


def partition_one_symbol(symbol: str) -> dict[str, int]:
    src = _source_path(symbol)
    if not src.exists():
        log.warning("source missing: %s", src)
        return {"src_rows": 0, "partitions_written": 0, "partitions_skipped": 0}

    log.info("loading %s ...", src)
    store = db.DBNStore.from_file(str(src))
    df = store.to_df()  # indexed by ts_event UTC
    log.info(
        "  %s rows: %s, range %s → %s",
        symbol, f"{len(df):,}", df.index.min(), df.index.max(),
    )

    df = _normalize_for_warehouse(df, symbol)
    df["date_str"] = df["ts_event"].dt.strftime("%Y-%m-%d")

    written = 0
    skipped = 0
    for date_str, day_df in df.groupby("date_str", sort=True):
        target = _target_partition(symbol, date_str)
        if target.exists():
            skipped += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        day_df.drop(columns=["date_str"]).reset_index(drop=True).to_parquet(
            target, index=False
        )
        written += 1

    log.info(
        "  %s done. written=%d, skipped=%d (target dir=%s)",
        symbol, written, skipped, WAREHOUSE_ROOT / f"symbol={symbol}",
    )
    return {
        "src_rows": int(len(df)),
        "partitions_written": written,
        "partitions_skipped": skipped,
    }


def main() -> int:
    if not WAREHOUSE_ROOT.exists():
        log.error("warehouse root missing: %s", WAREHOUSE_ROOT)
        return 1
    totals = {"src_rows": 0, "partitions_written": 0, "partitions_skipped": 0}
    for symbol in SYMBOLS:
        result = partition_one_symbol(symbol)
        for k, v in result.items():
            totals[k] += v
    log.info("totals: %s", totals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
