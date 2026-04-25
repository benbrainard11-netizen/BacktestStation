"""One-off importer for legacy TBBO parquet files into the warehouse.

The user has TBBO data for individual futures contracts saved as
parquet at e.g.
`C:/Users/benbr/Documents/trading-bot-main/data/l2/NQM6_tbbo_<start>_<end>.parquet`.
Each file is one contract month (NQM5, NQU5, etc.). For backtesting
we want continuous-symbol partitions (`NQ.c.0`), which means stitching
the contract files into a single continuous stream, choosing the
front-month contract on each date.

This script:
1. Walks a directory of `<CONTRACT>_tbbo_<start>_<end>.parquet` files
2. Sorts them by file-name start date (chronological order)
3. For each file: reads, renames bid/ask columns to match TBBO_SCHEMA,
   replaces the per-row `symbol` field with the continuous mapping
4. Groups by date, writes per-day parquet to
   `processed/tbbo/symbol={CONTINUOUS}/date={Y}/part-000.parquet`
5. Idempotent: skip partitions already on disk (use --rebuild to
   overwrite).

Roll-week handling: the FIRST contract written for a given date wins.
If you have NQM5_tbbo_..._2025-06-13 and NQU5_tbbo_2025-06-13_...
both containing 2025-06-13 rows, NQM5's go in and NQU5's get
deduped at the partition level. This matches the simple
"front-month-by-default" continuous mapping; users who need the
specific roll-week handoff can read the raw contract files directly.

CLI:
    python -m app.ingest.legacy_tbbo_import \\
        --src "C:/Users/benbr/Documents/trading-bot-main/data/l2" \\
        [--continuous NQ.c.0]   # default; for ES use ES.c.0
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

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from app.data.schema import GENERATOR_VERSION, SCHEMA_VERSION, TBBO_SCHEMA


GENERATOR_NAME = "legacy_tbbo_import"

# Maps the live bot's contract roots to canonical continuous symbols.
# Add more here as new asset families come online.
ROOT_TO_CONTINUOUS = {
    "NQ": "NQ.c.0",
    "ES": "ES.c.0",
    "YM": "YM.c.0",
    "RTY": "RTY.c.0",
    "GC": "GC.c.0",
    "CL": "CL.c.0",
    "6E": "6E.c.0",
    "6B": "6B.c.0",
}

# Regex for filenames like `NQM5_tbbo_2025-04-01_2025-04-07.parquet`.
FILENAME_RE = re.compile(
    r"^(?P<contract>[A-Z0-9]+)_tbbo_(?P<start>\d{4}-\d{2}-\d{2})_(?P<end>\d{4}-\d{2}-\d{2})\.parquet$"
)


def _data_root() -> Path:
    default = "C:/data" if os.name == "nt" else "./data"
    return Path(os.environ.get("BS_DATA_ROOT", default))


def _setup_logger() -> logging.Logger:
    log = logging.getLogger("legacy_tbbo_import")
    log.setLevel(logging.INFO)
    if not log.handlers:
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        log.addHandler(sh)
    return log


def _root_from_contract(contract: str) -> str | None:
    """e.g. NQM5 -> NQ, 6EH6 -> 6E, RTYZ5 -> RTY."""
    m = re.match(r"^([A-Z0-9]+?)([FGHJKMNQUVXZ]\d{1,2})$", contract)
    if m:
        return m.group(1)
    return None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_metadata(
    src: Path,
    src_sha: str,
    row_count: int,
    ts_min,
    ts_max,
    contract: str,
    continuous: str,
) -> dict[bytes, bytes]:
    md: dict[bytes, bytes] = {
        b"bs.source.kind": b"tbbo-legacy",
        b"bs.source.path": str(src).encode("utf-8"),
        b"bs.source.sha256": src_sha.encode("utf-8"),
        b"bs.source.contract": contract.encode("utf-8"),
        b"bs.source.continuous": continuous.encode("utf-8"),
        b"bs.generator.name": GENERATOR_NAME.encode("utf-8"),
        b"bs.generator.version": GENERATOR_VERSION.encode("utf-8"),
        b"bs.generator.timestamp": dt.datetime.now(dt.timezone.utc)
        .isoformat(timespec="seconds")
        .encode("utf-8"),
        b"bs.row_count": str(row_count).encode("utf-8"),
        b"bs.schema.name": b"tbbo",
        b"bs.schema.version": SCHEMA_VERSION.encode("utf-8"),
    }
    if ts_min is not None:
        md[b"bs.ts_event.min"] = str(ts_min.isoformat()).encode("utf-8")
    if ts_max is not None:
        md[b"bs.ts_event.max"] = str(ts_max.isoformat()).encode("utf-8")
    return md


def _tbbo_partition_path(
    data_root: Path, continuous: str, date: dt.date
) -> Path:
    """Match the convention used by parquet_mirror: raw market-data
    parquets live under raw/databento/{schema}/, processed/bars are
    derived. The reader (`app.data.read_tbbo`) reads from this path."""
    return (
        data_root
        / "raw"
        / "databento"
        / "tbbo"
        / f"symbol={continuous}"
        / f"date={date.isoformat()}"
        / "part-000.parquet"
    )


def import_one_file(
    src: Path,
    continuous: str,
    *,
    rebuild: bool,
    data_root: Path,
    logger: logging.Logger,
) -> dict[str, int]:
    """Import a single contract TBBO parquet -> per-day continuous partitions."""
    m = FILENAME_RE.match(src.name)
    contract = m.group("contract") if m else src.stem.split("_")[0]

    pf = pq.ParquetFile(src)
    table = pf.read()
    df = table.to_pandas()

    # Normalize column names to TBBO_SCHEMA.
    rename = {
        "bid_px_00": "bid_px",
        "ask_px_00": "ask_px",
        "bid_sz_00": "bid_sz",
        "ask_sz_00": "ask_sz",
    }
    df = df.rename(columns=rename)

    # Drop fields not in our TBBO schema.
    expected_cols = set(TBBO_SCHEMA.column_names)
    drop_cols = [c for c in df.columns if c not in expected_cols]
    df = df.drop(columns=drop_cols)

    # Replace per-row symbol with the canonical continuous symbol.
    df["symbol"] = continuous

    # Make sure the schema's required columns all exist; fill defaults
    # for any missing ones.
    for col, typ in zip(TBBO_SCHEMA.pa_schema.names, TBBO_SCHEMA.pa_schema.types):
        if col not in df.columns:
            if pa.types.is_string(typ):
                df[col] = ""
            elif pa.types.is_integer(typ):
                df[col] = 0
            elif pa.types.is_floating(typ):
                df[col] = float("nan")
            else:
                df[col] = None

    # Pick column order to match the schema (pyarrow strict-from-pandas
    # is happier this way).
    df = df[list(TBBO_SCHEMA.pa_schema.names)]

    # Ensure dtypes for columns where pandas might have widened.
    df["sequence"] = df["sequence"].astype("uint32")
    df["size"] = df["size"].astype("uint32")
    df["bid_sz"] = df["bid_sz"].astype("uint32")
    df["ask_sz"] = df["ask_sz"].astype("uint32")
    df["publisher_id"] = df["publisher_id"].astype("int16")
    df["instrument_id"] = df["instrument_id"].astype("uint32")

    # Date column (UTC).
    df["_date"] = df["ts_event"].dt.date

    src_sha = _sha256(src)
    days_scanned = 0
    written = 0
    skipped_existing = 0

    for date_obj, group in df.groupby("_date"):
        days_scanned += 1
        out = _tbbo_partition_path(data_root, continuous, date_obj)
        if out.exists() and not rebuild:
            skipped_existing += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        sub = group.drop(columns=["_date"]).copy()
        sub["symbol"] = sub["symbol"].astype("object")
        table_out = pa.Table.from_pandas(
            sub, schema=TBBO_SCHEMA.pa_schema, preserve_index=False
        )
        meta = _build_metadata(
            src,
            src_sha,
            len(group),
            group["ts_event"].min(),
            group["ts_event"].max(),
            contract,
            continuous,
        )
        table_out = table_out.replace_schema_metadata(
            {**(table_out.schema.metadata or {}), **meta}
        )
        pq.write_table(table_out, out, compression="zstd")
        written += 1

    logger.info(
        f"{src.name} ({contract}->{continuous}): scanned={days_scanned} "
        f"written={written} skipped_existing={skipped_existing}"
    )
    return {
        "scanned_days": days_scanned,
        "written": written,
        "skipped_existing": skipped_existing,
    }


def import_directory(
    src_dir: Path,
    *,
    continuous_override: str | None = None,
    rebuild: bool = False,
    data_root: Path | None = None,
    logger: logging.Logger | None = None,
) -> dict[str, int]:
    """Walk src_dir for `<CONTRACT>_tbbo_<start>_<end>.parquet` files,
    import each into the warehouse continuous-symbol partition.

    Files are processed in chronological order by their stated start
    date (filename), so roll-week duplicate dates resolve to the
    earlier contract (closer-to-expiry takes precedence)."""
    log = logger or _setup_logger()
    data_root = data_root or _data_root()

    files = sorted(
        (p for p in src_dir.glob("*.parquet") if FILENAME_RE.match(p.name)),
        key=lambda p: FILENAME_RE.match(p.name).group("start"),
    )
    if not files:
        log.warning(f"no matching files in {src_dir}")
        return {"files": 0, "scanned_days": 0, "written": 0, "skipped_existing": 0}

    totals = {"files": 0, "scanned_days": 0, "written": 0, "skipped_existing": 0}
    for src in files:
        m = FILENAME_RE.match(src.name)
        contract = m.group("contract")
        if continuous_override:
            continuous = continuous_override
        else:
            root = _root_from_contract(contract)
            if root is None or root not in ROOT_TO_CONTINUOUS:
                log.warning(
                    f"can't map contract {contract!r} to a continuous symbol; "
                    f"pass --continuous explicitly. Skipping."
                )
                continue
            continuous = ROOT_TO_CONTINUOUS[root]
        counts = import_one_file(
            src, continuous, rebuild=rebuild, data_root=data_root, logger=log
        )
        totals["files"] += 1
        totals["scanned_days"] += counts["scanned_days"]
        totals["written"] += counts["written"]
        totals["skipped_existing"] += counts["skipped_existing"]
    log.info(
        f"DONE: files={totals['files']} scanned_days={totals['scanned_days']} "
        f"written={totals['written']} skipped_existing={totals['skipped_existing']}"
    )
    return totals


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Import legacy TBBO parquet files into the warehouse."
    )
    p.add_argument("--src", required=True, type=Path, help="Directory of TBBO parquets.")
    p.add_argument(
        "--continuous",
        default=None,
        help="Override continuous symbol (e.g. NQ.c.0). Auto-detected from contract root if omitted.",
    )
    p.add_argument(
        "--rebuild",
        action="store_true",
        help="Overwrite existing partitions instead of skipping.",
    )
    args = p.parse_args(argv)

    log = _setup_logger()
    if not args.src.is_dir():
        log.error(f"src is not a directory: {args.src}")
        return 1
    totals = import_directory(
        args.src, continuous_override=args.continuous, rebuild=args.rebuild, logger=log
    )
    print(
        f"OK files={totals['files']} scanned_days={totals['scanned_days']} "
        f"written={totals['written']} skipped={totals['skipped_existing']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
