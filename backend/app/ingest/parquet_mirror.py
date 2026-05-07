"""Convert raw DBN files to Hive-partitioned parquet + 1m bars + manifests.

Three outputs per (UTC date, symbol):

    raw/databento/{schema}/symbol={X}/date={Y}/part-000.parquet
    processed/bars/timeframe=1m/symbol={X}/date={Y}/part-000.parquet
    manifests/ingest_runs/{Y}_{schema}_manifest.json (one per date+schema)

DBN remains the immutable source of truth. Parquet + bars are derived
and regeneratable. Manifests are the audit trail.

Run on the 24/7 collection node, hourly via Windows Task Scheduler:

    python -m app.ingest.parquet_mirror

Or to regenerate everything from DBN (e.g. after a schema change):

    python -m app.ingest.parquet_mirror --rebuild

Both modes are idempotent. Skips DBN files modified in the last 60s.

See [`docs/DATA_FORMAT.md`](../../../docs/DATA_FORMAT.md) for the
on-disk layout this script produces.
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import databento as db
except ImportError:  # pragma: no cover
    sys.stderr.write("databento package not installed.\n")
    sys.exit(1)

try:
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:  # pragma: no cover
    sys.stderr.write("pandas + pyarrow not installed.\n")
    sys.exit(1)

from app.data.manifest import (
    IngestManifest,
    ManifestGenerator,
    ManifestOutput,
    ManifestSource,
    ManifestValidation,
    now_utc_iso,
    relative_to_root,
    sha256_of_file,
    write_manifest,
)
from app.data.schema import (
    BARS_1M_SCHEMA,
    GENERATOR_VERSION,
    MBP1_SCHEMA,
    SCHEMA_VERSION,
    TBBO_SCHEMA,
    DataSchema,
    get_schema,
)


SKIP_RECENT_SEC = 60
GENERATOR_NAME = "parquet_mirror"

# Matches DBN files in two layouts:
#   Legacy (live + pre-2026-04-27 historical):   GLBX.MDP3-tbbo-2026-04-24.dbn
#   Per-symbol (historical from 2026-04-27 on):  GLBX.MDP3-mbp-1-2026-03-06-NQ.c.0.dbn
# Symbol group is optional. When present, the file already contains a single
# symbol; when absent, the file may be multi-symbol and the existing
# group-by-record-symbol code path handles partitioning.
_DBN_RE = re.compile(
    r"^(?P<dataset>[A-Z]+\.[A-Z0-9]+)-(?P<schema>[a-z0-9-]+)-"
    r"(?P<date>\d{4}-\d{2}-\d{2})"
    r"(?:-(?P<symbol>[A-Za-z0-9._]+))?"
    r"\.dbn(\.zst)?$"
)


# --- Continuous-symbol mapping ----------------------------------------

# Bases of continuous-symbol indices we publish partitions under, in
# addition to the resolved-contract partitions. The live ingester
# subscribes via "{BASE}.c.0" with stype_in='continuous', but databento
# delivers records keyed by the resolved contract symbol (e.g. NQM6) —
# so we pattern-match the resolved name back to its base here.
CONTINUOUS_BASES = ("NQ", "ES", "YM", "RTY")

# Quarterly futures contract: {BASE}{MONTH_CODE}{YEAR_DIGITS}.
# Quarter month codes: H=Mar, M=Jun, U=Sep, Z=Dec.
_CONTRACT_RE = re.compile(r"^([A-Z]{2,3})([HMUZ])(\d{1,2})$")


def _continuous_symbol(symbol: str) -> str | None:
    """Map a resolved quarterly contract (e.g. ``NQM6``) to its
    continuous symbol (``NQ.c.0``).

    Returns None if the symbol is not a recognized quarterly contract or
    if its base ticker isn't in `CONTINUOUS_BASES`.

    TODO(approach-a): cleaner long-term fix is to subscribe upstream
    with stype_out=continuous (or persist the symbology messages
    databento emits) so records carry the continuous symbol natively.
    That handles arbitrary roll dates correctly and isn't tied to a
    fixed list of bases. See live.py for the subscription site.
    """
    m = _CONTRACT_RE.match(str(symbol))
    if m is None:
        return None
    base = m.group(1)
    if base not in CONTINUOUS_BASES:
        return None
    return f"{base}.c.0"


@dataclass
class MirrorResult:
    scanned: int = 0
    converted_dbn: int = 0
    converted_partitions: int = 0  # one per (symbol, output kind)
    skipped_recent: int = 0
    skipped_unchanged: int = 0
    skipped_unrecognized: int = 0
    errors: list[str] = field(default_factory=list)


# --- Setup ---------------------------------------------------------------


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


def _data_root() -> Path:
    """Backwards-compat alias for `app.core.paths.warehouse_root`."""
    from app.core.paths import warehouse_root
    return warehouse_root()


# --- Path helpers -------------------------------------------------------


def _raw_partition_path(
    data_root: Path, schema: str, symbol: str, date: dt.date
) -> Path:
    return (
        data_root
        / "raw"
        / "databento"
        / schema
        / f"symbol={symbol}"
        / f"date={date.isoformat()}"
        / "part-000.parquet"
    )


def _bars_partition_path(
    data_root: Path, symbol: str, date: dt.date
) -> Path:
    return (
        data_root
        / "processed"
        / "bars"
        / "timeframe=1m"
        / f"symbol={symbol}"
        / f"date={date.isoformat()}"
        / "part-000.parquet"
    )


# --- Main entry ---------------------------------------------------------


def mirror_warehouse(
    data_root: Path, *, rebuild: bool = False
) -> MirrorResult:
    """Walk raw DBN tree, emit Hive parquet + bars + manifests.

    Args:
        data_root: warehouse root.
        rebuild: if True, ignores up-to-date check and re-emits every
            DBN. Useful for migrating from the legacy layout or after
            a schema/generator-version bump.
    """
    result = MirrorResult()
    if not data_root.exists():
        result.errors.append(f"data_root does not exist: {data_root}")
        return result

    logger = _setup_logging(data_root)
    logger.info(f"mirror starting; data_root={data_root} rebuild={rebuild}")

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
                converted = _process_one_dbn(
                    dbn_path, m, data_root, logger, rebuild=rebuild
                )
                if converted == 0:
                    result.skipped_unchanged += 1
                else:
                    result.converted_dbn += 1
                    result.converted_partitions += converted
            except Exception as e:
                msg = f"convert failed for {dbn_path}: {type(e).__name__}: {e}"
                logger.error(msg)
                result.errors.append(msg)

    logger.info(
        f"mirror done; scanned={result.scanned} converted_dbn={result.converted_dbn} "
        f"converted_partitions={result.converted_partitions} "
        f"skipped_recent={result.skipped_recent} "
        f"skipped_unchanged={result.skipped_unchanged} "
        f"skipped_unrecognized={result.skipped_unrecognized} "
        f"errors={len(result.errors)}"
    )
    return result


# --- Per-DBN processing -------------------------------------------------


def _process_one_dbn(
    dbn_path: Path,
    matched: re.Match[str],
    data_root: Path,
    logger: logging.Logger,
    *,
    rebuild: bool,
) -> int:
    """Convert one DBN to parquet partitions + bars + manifest.

    Two passes per DBN:

      1. **Resolved-contract partitions.** One per distinct symbol in the
         DBN (e.g. ``NQM6``).
      2. **Continuous-symbol partitions.** For each row whose resolved
         symbol maps to a continuous base (see `_continuous_symbol`),
         emit a second partition under the continuous name with the
         symbol column rewritten to match. Lets downstream code read by
         continuous symbol without a contract-resolution step.

    Returns the total partitions written this call. Returns 0 if every
    target already exists + is newer than the DBN, unless rebuild=True.
    """
    schema_name = matched.group("schema")
    date_str = matched.group("date")
    date_obj = dt.date.fromisoformat(date_str)
    dbn_mtime = dbn_path.stat().st_mtime

    schema = _safe_get_schema(schema_name)
    if schema is None:
        logger.info(
            f"no parquet schema registered for DBN schema {schema_name!r}, skipping"
        )
        return 0

    started_at = now_utc_iso()

    # The schema kwarg is required because live.py's DBN files contain
    # a mix of record types (TBBO + databento internal symbology /
    # system messages); without it, store.to_df() refuses with
    #   ValueError: a schema must be specified for mixed DBN data
    store = db.DBNStore.from_file(str(dbn_path))
    df = store.to_df(schema=schema_name)
    if df.empty:
        logger.info(f"empty DBN, nothing to write: {dbn_path.name}")
        return 0

    sym_col = "symbol" if "symbol" in df.columns else "raw_symbol"
    if sym_col not in df.columns:
        raise RuntimeError(
            f"DBN {dbn_path.name} has no symbol column (cols={list(df.columns)})"
        )

    outputs: list[ManifestOutput] = []
    validation_warnings: list[str] = []
    duplicate_count = 0
    monotonic_overall = True

    common = dict(
        schema=schema,
        schema_name=schema_name,
        date_obj=date_obj,
        data_root=data_root,
        dbn_path=dbn_path,
        dbn_mtime=dbn_mtime,
        rebuild=rebuild,
    )

    # Pass 1: resolved-contract partitions.
    for symbol, group in df.groupby(sym_col):
        outs, warns, dups, mono = _emit_partitions_for_symbol(
            symbol=str(symbol), group=group, **common
        )
        outputs.extend(outs)
        validation_warnings.extend(warns)
        duplicate_count += dups
        monotonic_overall = monotonic_overall and mono

    # Pass 2: continuous-symbol partitions. Rows for the same base across
    # multiple contracts (e.g. during a roll) get combined into one
    # partition.
    cont_df = df.assign(__continuous=df[sym_col].map(_continuous_symbol))
    cont_df = cont_df[cont_df["__continuous"].notna()]
    if not cont_df.empty:
        for cont_sym, group in cont_df.groupby("__continuous"):
            group = group.drop(columns=["__continuous"]).copy()
            # Rewrite symbol column so row contents match the partition
            # path they're being written under.
            group[sym_col] = cont_sym
            outs, warns, dups, mono = _emit_partitions_for_symbol(
                symbol=str(cont_sym), group=group, **common
            )
            outputs.extend(outs)
            validation_warnings.extend(warns)
            duplicate_count += dups
            monotonic_overall = monotonic_overall and mono

    # Write manifest only if we produced something.
    if outputs:
        manifest = IngestManifest(
            schema_version=int(SCHEMA_VERSION),
            date=date_str,
            data_schema=schema_name,
            source=ManifestSource(
                kind="dbn",
                path=relative_to_root(dbn_path, data_root),
                sha256=sha256_of_file(dbn_path),
                size_bytes=dbn_path.stat().st_size,
            ),
            outputs=outputs,
            validation=ManifestValidation(
                row_count_ok=True,
                schema_columns_ok=True,
                duplicate_ts_event_count=duplicate_count,
                monotonic_ts_event=monotonic_overall,
                warnings=validation_warnings,
            ),
            generator=ManifestGenerator(
                name=GENERATOR_NAME,
                version=GENERATOR_VERSION,
                started_at=started_at,
                completed_at=now_utc_iso(),
            ),
            status="complete",
        )
        write_manifest(data_root, manifest)
        logger.info(
            f"manifest written: {schema_name} {date_str} "
            f"({len(outputs)} partitions)"
        )

    return len(outputs)


def _emit_partitions_for_symbol(
    *,
    symbol: str,
    group: "pd.DataFrame",
    schema: DataSchema,
    schema_name: str,
    date_obj: dt.date,
    data_root: Path,
    dbn_path: Path,
    dbn_mtime: float,
    rebuild: bool,
) -> tuple[list[ManifestOutput], list[str], int, bool]:
    """Write raw + bars partitions for a single symbol's rows.

    Idempotent skip: if both raw and bars partition files already exist
    with mtime >= dbn_mtime, returns ([], [], 0, True) without writing.

    Returns (outputs, validation_warnings, dup_count, monotonic).
    """
    outputs: list[ManifestOutput] = []
    raw_path = _raw_partition_path(data_root, schema_name, symbol, date_obj)
    bars_path = _bars_partition_path(data_root, symbol, date_obj)

    if (
        not rebuild
        and raw_path.exists()
        and bars_path.exists()
        and raw_path.stat().st_mtime >= dbn_mtime
        and bars_path.stat().st_mtime >= dbn_mtime
    ):
        return outputs, [], 0, True

    raw_df = _normalize_for_schema(group, schema)
    raw_df = _ensure_utc(raw_df, ["ts_event", "ts_recv"])
    raw_df = raw_df.sort_values("ts_event").reset_index(drop=True)

    dups = int(raw_df["ts_event"].duplicated().sum())
    monotonic = bool(raw_df["ts_event"].is_monotonic_increasing)
    warnings = [f"{symbol}: {dups} duplicate ts_event"] if dups > 0 else []

    ts_min = raw_df["ts_event"].min() if not raw_df.empty else None
    ts_max = raw_df["ts_event"].max() if not raw_df.empty else None

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_table = pa.Table.from_pandas(
        raw_df, schema=schema.pa_schema, preserve_index=False
    )
    raw_table = _attach_metadata(
        raw_table,
        source_dbn=dbn_path,
        schema_name=schema_name,
        row_count=len(raw_df),
        ts_min=ts_min,
        ts_max=ts_max,
    )
    pq.write_table(raw_table, raw_path, compression="zstd")
    outputs.append(
        ManifestOutput(
            kind="raw_parquet",
            schema=schema_name,
            symbol=symbol,
            path=relative_to_root(raw_path, data_root),
            rows=len(raw_df),
            size_bytes=raw_path.stat().st_size,
            ts_event_min=ts_min.isoformat() if ts_min is not None else None,
            ts_event_max=ts_max.isoformat() if ts_max is not None else None,
        )
    )

    bars_df: "pd.DataFrame | None" = None
    if schema_name in {"tbbo", "mbp-1"}:
        bars_df = _compute_1m_bars(raw_df, symbol)
    elif schema_name == "ohlcv-1m":
        bars_df = _ohlcv_dbn_to_bars(raw_df, symbol)
    if bars_df is not None and not bars_df.empty:
        bars_path.parent.mkdir(parents=True, exist_ok=True)
        bars_table = pa.Table.from_pandas(
            bars_df,
            schema=BARS_1M_SCHEMA.pa_schema,
            preserve_index=False,
        )
        bars_table = _attach_metadata(
            bars_table,
            source_dbn=dbn_path,
            schema_name="ohlcv-1m",
            row_count=len(bars_df),
            ts_min=bars_df["ts_event"].min(),
            ts_max=bars_df["ts_event"].max(),
        )
        pq.write_table(bars_table, bars_path, compression="zstd")
        outputs.append(
            ManifestOutput(
                kind="bars_1m",
                schema="ohlcv-1m",
                symbol=symbol,
                path=relative_to_root(bars_path, data_root),
                rows=len(bars_df),
                size_bytes=bars_path.stat().st_size,
                ts_event_min=bars_df["ts_event"].min().isoformat(),
                ts_event_max=bars_df["ts_event"].max().isoformat(),
            )
        )

    return outputs, warnings, dups, monotonic


# --- Helpers ------------------------------------------------------------


def _safe_get_schema(name: str) -> DataSchema | None:
    try:
        return get_schema(name)
    except KeyError:
        return None


def _normalize_for_schema(
    df: "pd.DataFrame", schema: DataSchema
) -> "pd.DataFrame":
    """Reorder + project a databento-emitted DataFrame to match `schema`.

    Databento emits more columns than we store. We only keep what's in
    the schema. Missing optional columns get filled with sensible
    defaults; missing required columns raise.
    """
    need = list(schema.column_names)

    # Move ts_event from index to column FIRST — databento's to_df()
    # returns it as the index, but our schema treats it as a column.
    if (
        "ts_event" in need
        and "ts_event" not in df.columns
        and df.index.name == "ts_event"
    ):
        df = df.reset_index()

    # Map databento's column names to ours where they differ.
    rename_map = {
        "bid_px_00": "bid_px",
        "ask_px_00": "ask_px",
        "bid_sz_00": "bid_sz",
        "ask_sz_00": "ask_sz",
        "bid_ct_00": "bid_ct",
        "ask_ct_00": "ask_ct",
    }
    df = df.rename(
        columns={k: v for k, v in rename_map.items() if k in df.columns}
    )

    missing = [c for c in schema.required_columns if c not in df.columns]
    if missing:
        raise RuntimeError(
            f"DBN missing required columns for schema {schema.name}: {missing}"
        )

    # Fill optional columns with defaults if absent.
    defaults = {
        "ts_recv": pd.NaT,
        "ts_in_delta": 0,
        "depth": 0,
        "flags": 0,
        "bid_ct": 0,
        "ask_ct": 0,
        "publisher_id": 0,
        "instrument_id": 0,
        "sequence": 0,
        # ohlcv-1m DBN doesn't carry these; the bars schema requires
        # them as columns. Inject sane defaults so _normalize doesn't
        # KeyError before our pass-through path runs.
        "trade_count": 0,
        "vwap": float("nan"),
    }
    for col in need:
        if col not in df.columns and col in defaults:
            df[col] = defaults[col]

    # Project to schema columns in the right order.
    return df[need].copy()


def _ensure_utc(df: "pd.DataFrame", cols: list[str]) -> "pd.DataFrame":
    """Make sure tz-aware UTC for the given timestamp columns."""
    for col in cols:
        if col not in df.columns:
            continue
        s = pd.to_datetime(df[col], errors="coerce")
        if s.dt.tz is None:
            s = s.dt.tz_localize("UTC")
        else:
            s = s.dt.tz_convert("UTC")
        df[col] = s
    return df


def _compute_1m_bars(raw_df: "pd.DataFrame", symbol: str) -> "pd.DataFrame":
    """Build OHLCV 1m bars from a TBBO/MBP-1 DataFrame.

    Considers only trade actions (action == 'T'). Returns rows for every
    minute that had at least one trade. Empty minutes are not filled
    here; the read-time consumer can fill them if desired.
    """
    if "action" not in raw_df.columns:
        return pd.DataFrame()
    trades = raw_df[raw_df["action"] == "T"]
    if trades.empty:
        return pd.DataFrame()

    # Floor ts_event to the minute.
    floored = trades["ts_event"].dt.floor("1min")
    grouped = trades.groupby(floored)

    bars = pd.DataFrame(
        {
            "ts_event": grouped["ts_event"].first().dt.floor("1min"),
            "symbol": symbol,
            "open": grouped["price"].first().astype("float64"),
            "high": grouped["price"].max().astype("float64"),
            "low": grouped["price"].min().astype("float64"),
            "close": grouped["price"].last().astype("float64"),
            "volume": grouped["size"].sum().astype("uint64"),
            "trade_count": grouped.size().astype("uint32"),
        }
    )
    # VWAP = sum(price*size) / sum(size). Compute lazily.
    notional = (trades["price"] * trades["size"]).groupby(floored).sum()
    sizes = trades["size"].groupby(floored).sum()
    bars["vwap"] = (notional / sizes).astype("float64")

    bars = bars.reset_index(drop=True)
    # Force symbol to plain object/string dtype — broadcast can produce
    # categorical/dictionary which then doesn't match BARS_1M_SCHEMA's
    # pa.string() field type at write time.
    bars["symbol"] = bars["symbol"].astype("object")
    return bars


def _ohlcv_dbn_to_bars(raw_df: "pd.DataFrame", symbol: str) -> "pd.DataFrame":
    """Pass-through: ohlcv-1m DBN is already 1m bars. Just shape it
    to match BARS_1M_SCHEMA (add trade_count + vwap defaults, force
    types, ensure ts_event is a column not the index)."""
    if raw_df.empty:
        return pd.DataFrame()
    df = raw_df.copy()
    if "ts_event" not in df.columns:
        # Some normalization steps may leave ts_event in the index.
        df = df.reset_index().rename(columns={"index": "ts_event"})
    keep = ["ts_event", "open", "high", "low", "close", "volume"]
    df = df[keep].copy()
    df["symbol"] = symbol
    df["trade_count"] = 0  # not present in ohlcv-1m DBN
    df["vwap"] = float("nan")
    df["volume"] = df["volume"].astype("uint64")
    df["trade_count"] = df["trade_count"].astype("uint32")
    df["symbol"] = df["symbol"].astype("object")
    df = df[list(BARS_1M_SCHEMA.pa_schema.names)]
    return df.reset_index(drop=True)


def _attach_metadata(
    table: pa.Table,
    *,
    source_dbn: Path,
    schema_name: str,
    row_count: int,
    ts_min: dt.datetime | None,
    ts_max: dt.datetime | None,
) -> pa.Table:
    """Embed bs.* key/value metadata into the parquet footer."""
    md: dict[bytes, bytes] = {}
    md[b"bs.source.kind"] = b"dbn"
    md[b"bs.source.path"] = str(source_dbn).encode("utf-8")
    md[b"bs.source.sha256"] = sha256_of_file(source_dbn).encode("utf-8")
    md[b"bs.generator.name"] = GENERATOR_NAME.encode("utf-8")
    md[b"bs.generator.version"] = GENERATOR_VERSION.encode("utf-8")
    md[b"bs.generator.timestamp"] = now_utc_iso().encode("utf-8")
    md[b"bs.row_count"] = str(row_count).encode("utf-8")
    md[b"bs.schema.name"] = schema_name.encode("utf-8")
    md[b"bs.schema.version"] = SCHEMA_VERSION.encode("utf-8")
    if ts_min is not None:
        md[b"bs.ts_event.min"] = str(ts_min.isoformat()).encode("utf-8")
    if ts_max is not None:
        md[b"bs.ts_event.max"] = str(ts_max.isoformat()).encode("utf-8")

    existing = table.schema.metadata or {}
    merged = {**existing, **md}
    return table.replace_schema_metadata(merged)


# --- CLI ---------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Mirror DBN files to Hive-partitioned parquet + 1m bars."
    )
    p.add_argument(
        "--rebuild",
        action="store_true",
        help="ignore the up-to-date check and re-emit every DBN",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = mirror_warehouse(_data_root(), rebuild=args.rebuild)
    return 0 if not result.errors else 1


if __name__ == "__main__":
    sys.exit(main())
