"""One-off: backfill continuous-symbol TBBO partitions from live DBN files.

The live ingester subscribes to NQ.c.0 / ES.c.0 / YM.c.0 / RTY.c.0 but the
DBN file records carry the resolved contract symbol (NQM6 etc.) — the
continuous symbol is not preserved in the records themselves. parquet_mirror
groups by record symbol so partitions land under symbol=NQM6/.

This script reads each DBN file, maps the resolved contract back to the
continuous symbol by ticker prefix, and writes partitions under the
continuous name.

Run:
    python -m scripts.backfill_continuous_tbbo --start 2026-04-22 --end 2026-05-05
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import databento as db
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from app.data.schema import TBBO_SCHEMA, get_schema
from app.ingest.parquet_mirror import (
    _attach_metadata,
    _ensure_utc,
    _normalize_for_schema,
    _raw_partition_path,
)


PREFIX_TO_CONTINUOUS = [
    ("RTY", "RTY.c.0"),  # 3-char prefix first to avoid greedy match by 2-char
    ("NQ", "NQ.c.0"),
    ("ES", "ES.c.0"),
    ("YM", "YM.c.0"),
]


def map_to_continuous(symbol: str) -> str | None:
    s = str(symbol)
    for prefix, cont in PREFIX_TO_CONTINUOUS:
        if s.startswith(prefix):
            return cont
    return None


def daterange(start: dt.date, end: dt.date):
    d = start
    while d <= end:
        yield d
        d += dt.timedelta(days=1)


def process_file(dbn_path: Path, data_root: Path) -> dict:
    """Read one DBN, map symbols, write per-continuous-symbol partitions.

    Returns a per-continuous-symbol summary: {sym: rows_written}.
    """
    schema_name = "tbbo"
    schema = get_schema(schema_name)

    store = db.DBNStore.from_file(str(dbn_path))
    df = store.to_df(schema=schema_name)
    if df.empty:
        return {}

    # Filename carries the trade date (UTC).
    # GLBX.MDP3-tbbo-YYYY-MM-DD.dbn
    date_str = dbn_path.stem.split("-", 2)[-1]  # "tbbo-2026-05-05" → strip prefix
    # Robust extraction: last 10 chars of stem if stem ends with date.
    # Filename is GLBX.MDP3-tbbo-YYYY-MM-DD so split by - from end.
    parts = dbn_path.stem.split("-")
    # Last 3 parts are YYYY MM DD
    date_str = "-".join(parts[-3:])
    date_obj = dt.date.fromisoformat(date_str)

    df["__continuous"] = df["symbol"].map(map_to_continuous)
    unmapped = df["__continuous"].isna().sum()
    if unmapped:
        unique_unmapped = df.loc[df["__continuous"].isna(), "symbol"].unique()
        print(f"  WARN {dbn_path.name}: {unmapped} rows with unmappable symbols: {list(unique_unmapped)[:5]}")
    df = df[df["__continuous"].notna()]
    if df.empty:
        return {}

    summary: dict[str, int] = {}
    for cont_sym, group in df.groupby("__continuous"):
        group = group.drop(columns=["__continuous"]).copy()
        # Overwrite symbol column with continuous symbol so partition path
        # is consistent with row contents. instrument_id stays as-is and
        # preserves the actual contract identity for any consumer that
        # cares.
        group["symbol"] = cont_sym

        raw_path = _raw_partition_path(data_root, schema_name, str(cont_sym), date_obj)
        if raw_path.exists():
            print(f"  skip {raw_path.relative_to(data_root)} (exists)")
            continue

        raw_df = _normalize_for_schema(group, schema)
        raw_df = _ensure_utc(raw_df, ["ts_event", "ts_recv"])
        raw_df = raw_df.sort_values("ts_event").reset_index(drop=True)

        ts_min = raw_df["ts_event"].min() if not raw_df.empty else None
        ts_max = raw_df["ts_event"].max() if not raw_df.empty else None

        raw_path.parent.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pandas(raw_df, schema=schema.pa_schema, preserve_index=False)
        table = _attach_metadata(
            table,
            source_dbn=dbn_path,
            schema_name=schema_name,
            row_count=len(raw_df),
            ts_min=ts_min,
            ts_max=ts_max,
        )
        pq.write_table(table, raw_path, compression="zstd")
        summary[str(cont_sym)] = len(raw_df)
        print(f"  wrote {raw_path.relative_to(data_root)} ({len(raw_df)} rows)")
    return summary


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--start", required=True, help="YYYY-MM-DD inclusive")
    p.add_argument("--end", required=True, help="YYYY-MM-DD inclusive")
    p.add_argument("--data-root", default=r"D:\data")
    args = p.parse_args(argv)

    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end)
    data_root = Path(args.data_root)
    live_dir = data_root / "raw" / "live"

    print(f"backfill window: {start} -> {end}")
    print(f"live dir: {live_dir}")

    grand_total: dict[str, int] = {}
    for d in daterange(start, end):
        # Files are named by UTC date the session was OPENED, which is the
        # day before for a session that runs through the night. The live
        # ingester opens a new file each UTC midnight named with that
        # date. So GLBX.MDP3-tbbo-2026-05-05.dbn covers UTC 05-05.
        fname = f"GLBX.MDP3-tbbo-{d.isoformat()}.dbn"
        fpath = live_dir / fname
        if not fpath.exists():
            print(f"{d}: missing ({fname}) — skip")
            continue
        # Skip files modified in last 60s (still being written).
        import time
        if time.time() - fpath.stat().st_mtime < 60:
            print(f"{d}: {fname} still being written — skip")
            continue
        print(f"{d}: processing {fname} ({fpath.stat().st_size:,} bytes)")
        try:
            summary = process_file(fpath, data_root)
            for k, v in summary.items():
                grand_total[k] = grand_total.get(k, 0) + v
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")

    print()
    print("=== SUMMARY ===")
    for k, v in sorted(grand_total.items()):
        print(f"  {k}: {v:,} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
