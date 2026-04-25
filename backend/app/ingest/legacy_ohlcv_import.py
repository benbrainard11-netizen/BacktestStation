"""One-off importer for legacy ohlcv-1m DBN files.

The user has years of NQ/ES/YM 1m bars in pre-aggregated DBN format
from prior backtest workflows (e.g.
`C:/Users/benbr/Documents/New nq bot/data/NQ.c.0_ohlcv-1m.dbn.zst`).
This script reads such a file and writes Hive-partitioned per-day
parquet at:

    {BS_DATA_ROOT}/processed/bars/timeframe=1m/symbol={X}/date={Y}/part-000.parquet

Schema matches `app.data.schema.BARS_1M_SCHEMA` exactly so the
warehouse reader can consume it identically to bars derived from
parquet_mirror. Lineage metadata embedded in the parquet footer.

Idempotent: skips dates that already have a parquet on disk. Pass
`--rebuild` to overwrite.

CLI:
    python -m app.ingest.legacy_ohlcv_import \\
        --src "C:/Users/benbr/Documents/New nq bot/data/NQ.c.0_ohlcv-1m.dbn.zst" \\
        [--symbol NQ.c.0]   # auto-detected from filename if omitted
        [--rebuild]
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import logging
import os
import re
import sys
from pathlib import Path

try:
    import databento as db
except ImportError:  # pragma: no cover
    db = None  # type: ignore

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from app.data.schema import BARS_1M_SCHEMA, GENERATOR_VERSION, SCHEMA_VERSION


GENERATOR_NAME = "legacy_ohlcv_import"


def _data_root() -> Path:
    default = "C:/data" if os.name == "nt" else "./data"
    return Path(os.environ.get("BS_DATA_ROOT", default))


def _setup_logger() -> logging.Logger:
    log = logging.getLogger("legacy_ohlcv_import")
    log.setLevel(logging.INFO)
    if not log.handlers:
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        log.addHandler(sh)
    return log


def _detect_symbol(src: Path) -> str:
    """Pull the canonical continuous symbol from filenames like
    `NQ.c.0_ohlcv-1m.dbn.zst`."""
    name = src.name
    m = re.match(r"([A-Z]+\.c\.\d+)_ohlcv-1m", name)
    if m:
        return m.group(1)
    # Fallback: try first underscore-separated token
    return name.split("_")[0]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_metadata(src: Path, src_sha: str, row_count: int, ts_min, ts_max) -> dict[bytes, bytes]:
    md: dict[bytes, bytes] = {}
    md[b"bs.source.kind"] = b"dbn-legacy"
    md[b"bs.source.path"] = str(src).encode("utf-8")
    md[b"bs.source.sha256"] = src_sha.encode("utf-8")
    md[b"bs.generator.name"] = GENERATOR_NAME.encode("utf-8")
    md[b"bs.generator.version"] = GENERATOR_VERSION.encode("utf-8")
    md[b"bs.generator.timestamp"] = (
        dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").encode("utf-8")
    )
    md[b"bs.row_count"] = str(row_count).encode("utf-8")
    md[b"bs.schema.name"] = b"ohlcv-1m"
    md[b"bs.schema.version"] = SCHEMA_VERSION.encode("utf-8")
    if ts_min is not None:
        md[b"bs.ts_event.min"] = str(ts_min.isoformat()).encode("utf-8")
    if ts_max is not None:
        md[b"bs.ts_event.max"] = str(ts_max.isoformat()).encode("utf-8")
    return md


def _bars_partition_path(data_root: Path, symbol: str, date: dt.date) -> Path:
    return (
        data_root
        / "processed"
        / "bars"
        / "timeframe=1m"
        / f"symbol={symbol}"
        / f"date={date.isoformat()}"
        / "part-000.parquet"
    )


def import_dbn(
    src: Path,
    *,
    symbol: str | None = None,
    rebuild: bool = False,
    data_root: Path | None = None,
    logger: logging.Logger | None = None,
) -> dict[str, int]:
    """Read one DBN-zst ohlcv-1m file, write per-day parquets.

    Returns a dict with counts: scanned_days, written, skipped_existing.
    """
    log = logger or _setup_logger()
    if db is None:
        raise RuntimeError(
            "databento package not installed; pip install databento"
        )
    data_root = data_root or _data_root()
    sym = symbol or _detect_symbol(src)
    log.info(f"importing {src.name} -> symbol={sym}")

    store = db.DBNStore.from_file(str(src))
    df = store.to_df()
    if df.empty:
        log.warning(f"{src.name} has no rows; skipping")
        return {"scanned_days": 0, "written": 0, "skipped_existing": 0}

    # Prep DataFrame: ts_event as a column, only the columns we need.
    df = df.reset_index().rename(columns={"index": "ts_event"})
    if "ts_event" not in df.columns:
        df["ts_event"] = df.index
    df["symbol"] = sym
    keep = ["ts_event", "symbol", "open", "high", "low", "close", "volume"]
    df = df[keep]
    # Fill the optional cols with neutral defaults so the schema
    # consumes cleanly. trade_count = 0 (unknown), vwap = NaN.
    df["trade_count"] = 0
    df["vwap"] = float("nan")

    # Compute integrity stuff once.
    src_sha = _sha256(src)

    days_scanned = 0
    written = 0
    skipped = 0
    df["_date"] = df["ts_event"].dt.date

    for date_obj, group in df.groupby("_date"):
        days_scanned += 1
        out = _bars_partition_path(data_root, sym, date_obj)
        if out.exists() and not rebuild:
            skipped += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)

        # Build pyarrow Table matching BARS_1M_SCHEMA.
        sub = group.drop(columns=["_date"]).copy()
        sub["symbol"] = sub["symbol"].astype("object")
        # Coerce volume to uint64 explicitly.
        sub["volume"] = sub["volume"].astype("uint64")
        sub["trade_count"] = sub["trade_count"].astype("uint32")
        table = pa.Table.from_pandas(
            sub, schema=BARS_1M_SCHEMA.pa_schema, preserve_index=False
        )
        ts_min = group["ts_event"].min()
        ts_max = group["ts_event"].max()
        meta = _build_metadata(src, src_sha, len(group), ts_min, ts_max)
        table = table.replace_schema_metadata(
            {**(table.schema.metadata or {}), **meta}
        )
        pq.write_table(table, out, compression="zstd")
        written += 1

    log.info(
        f"{sym}: scanned={days_scanned} written={written} skipped_existing={skipped}"
    )
    return {
        "scanned_days": days_scanned,
        "written": written,
        "skipped_existing": skipped,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="One-off importer for legacy ohlcv-1m DBN files into the warehouse.",
    )
    p.add_argument("--src", required=True, type=Path, help="Path to DBN-zst file.")
    p.add_argument(
        "--symbol",
        default=None,
        help="Canonical symbol (e.g. NQ.c.0). Auto-detected from filename if omitted.",
    )
    p.add_argument(
        "--rebuild",
        action="store_true",
        help="Overwrite existing per-day parquet files instead of skipping.",
    )
    args = p.parse_args(argv)

    log = _setup_logger()
    if not args.src.exists():
        log.error(f"source not found: {args.src}")
        return 1
    counts = import_dbn(args.src, symbol=args.symbol, rebuild=args.rebuild, logger=log)
    print(f"OK scanned={counts['scanned_days']} written={counts['written']} skipped={counts['skipped_existing']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
