"""Convert raw DBN files to per-symbol parquet for fast query.

DBN remains the immutable source of truth. Parquet is a derived,
queryable mirror: per-symbol, per-day, columnar. If parquet ever gets
corrupted or the schema changes, regenerate from DBN — no data lost.

Run on the 24/7 collection node, hourly via Windows Task Scheduler:

    python -m app.ingest.parquet_mirror

Or one-shot from a developer machine when you want to query.

Behavior:
- Walks BS_DATA_ROOT/raw/live/ and /raw/historical/ for DBN files.
- For each DBN whose corresponding parquet doesn't exist or is older
  than the DBN, loads the DBN, splits by instrument symbol (raw_symbol
  in tbbo records / raw_symbol in mbp records), writes per-symbol
  parquet at /parquet/{symbol}/{schema}/{YYYY-MM-DD}.parquet.
- Skips DBN files modified in the last 60s — the live ingester might
  still be appending to them.
- Idempotent: running twice in a row produces the same parquet files
  with no duplicate rows.

Logs to BS_DATA_ROOT/logs/parquet_mirror.log.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import re
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

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "pyarrow not installed. Run: pip install pyarrow\n"
    )
    sys.exit(1)


SKIP_RECENT_SEC = 60

_DBN_RE = re.compile(
    r"^(?P<dataset>[A-Z]+\.[A-Z0-9]+)-(?P<schema>[a-z0-9-]+)-"
    r"(?P<date>\d{4}-\d{2}-\d{2})\.dbn(\.zst)?$"
)


@dataclass
class MirrorResult:
    scanned: int = 0
    converted: int = 0
    skipped_recent: int = 0
    skipped_unchanged: int = 0
    skipped_unrecognized: int = 0
    errors: list[str] = field(default_factory=list)


def _setup_logging(data_root: Path) -> logging.Logger:
    log_dir = data_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("parquet_mirror")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(log_dir / "parquet_mirror.log", encoding="utf-8")
        fh.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(fh)
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(fh.formatter)
        logger.addHandler(sh)
    return logger


def mirror_warehouse(data_root: Path) -> MirrorResult:
    """Walk raw/* and produce parquet/* for each unconverted DBN."""
    result = MirrorResult()
    if not data_root.exists():
        result.errors.append(f"data_root does not exist: {data_root}")
        return result

    logger = _setup_logging(data_root)
    logger.info(f"mirror starting; data_root={data_root}")

    parquet_root = data_root / "parquet"
    parquet_root.mkdir(parents=True, exist_ok=True)

    cutoff = dt.datetime.now(dt.timezone.utc).timestamp() - SKIP_RECENT_SEC

    for source_dir in [data_root / "raw" / "live", data_root / "raw" / "historical"]:
        if not source_dir.exists():
            continue
        for dbn_path in source_dir.rglob("*"):
            if not dbn_path.is_file():
                continue
            if not (dbn_path.suffix == ".dbn" or dbn_path.name.endswith(".dbn.zst")):
                continue

            result.scanned += 1
            m = _DBN_RE.match(dbn_path.name)
            if m is None:
                result.skipped_unrecognized += 1
                logger.debug(f"unrecognized DBN filename: {dbn_path.name}")
                continue

            mtime = dbn_path.stat().st_mtime
            if mtime > cutoff:
                result.skipped_recent += 1
                logger.debug(f"skipping recent file: {dbn_path.name}")
                continue

            try:
                converted = _convert_one(dbn_path, m, parquet_root, logger)
                if converted == 0:
                    result.skipped_unchanged += 1
                else:
                    result.converted += converted
            except Exception as e:
                msg = f"convert failed for {dbn_path}: {type(e).__name__}: {e}"
                logger.error(msg)
                result.errors.append(msg)

    logger.info(
        f"mirror done; scanned={result.scanned} converted={result.converted} "
        f"skipped_recent={result.skipped_recent} "
        f"skipped_unchanged={result.skipped_unchanged} "
        f"skipped_unrecognized={result.skipped_unrecognized} "
        f"errors={len(result.errors)}"
    )
    return result


def _convert_one(
    dbn_path: Path,
    matched: re.Match[str],
    parquet_root: Path,
    logger: logging.Logger,
) -> int:
    """Load one DBN, split by symbol, write per-symbol parquet.

    Returns the number of parquet files written. Returns 0 if all
    target parquet files already exist and are newer than the DBN
    (idempotent skip).
    """
    schema_name = matched.group("schema")
    date_str = matched.group("date")
    dbn_mtime = dbn_path.stat().st_mtime

    # Load DBN once. Databento's DBNStore reads the whole file into
    # memory; daily TBBO files are small enough that this is fine.
    store = db.DBNStore.from_file(str(dbn_path))
    df = store.to_df()

    if df.empty:
        logger.info(f"empty DBN, nothing to write: {dbn_path.name}")
        return 0

    # Split by symbol. The tbbo and mbp-1 schemas both expose symbol
    # via `symbol` (resolved by Databento) or `raw_symbol` columns.
    sym_col = "symbol" if "symbol" in df.columns else "raw_symbol"
    if sym_col not in df.columns:
        raise RuntimeError(
            f"DBN {dbn_path.name} has no symbol column (cols={list(df.columns)})"
        )

    written = 0
    for symbol, group in df.groupby(sym_col):
        out_path = (
            parquet_root / str(symbol) / schema_name / f"{date_str}.parquet"
        )
        if out_path.exists():
            existing_mtime = out_path.stat().st_mtime
            if existing_mtime >= dbn_mtime:
                continue  # already up-to-date

        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Index is a pandas timestamp; write_parquet handles that. Reset
        # the index so the timestamp lands as a column called `ts_event`
        # (databento's name for the record timestamp), making downstream
        # queries cleaner.
        out_df = group.reset_index()
        table = pa.Table.from_pandas(out_df, preserve_index=False)
        pq.write_table(table, out_path, compression="zstd")
        logger.info(
            f"wrote {out_path.relative_to(parquet_root.parent)} "
            f"({len(out_df)} rows)"
        )
        written += 1

    return written


def _data_root() -> Path:
    default = "C:/data" if os.name == "nt" else "./data"
    return Path(os.environ.get("BS_DATA_ROOT", default))


def main() -> int:
    result = mirror_warehouse(_data_root())
    return 0 if not result.errors else 1


if __name__ == "__main__":
    sys.exit(main())
