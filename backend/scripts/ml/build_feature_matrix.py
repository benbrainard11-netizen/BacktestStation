"""Phase 1: Build per-detector feature matrices for ML training.

For each of the 12 detectors, produces a parquet at
  data/ml/features/<detector>.parquet
with one row per event containing:
  - chronological metadata (year, month, day_of_week, hour)
  - categorical features (event_type, side, primary_symbol)
  - flattened event_data fields (numeric + bool only — JSON nested
    structures dropped unless explicitly extracted)
  - flattened outcome label fields (the things we predict)
  - cross-detector flags: for each OTHER detector D, a column
    `has_<D>_in_24h` = 1 iff D fired on same primary in the 24h
    before this event's bar_end_utc

Cross-detector flags use only events BEFORE this event's bar_end_utc
(no look-ahead). Per `feedback_zero_lookahead.md`.

Train/val/test splits done downstream by the model script using the
`year` column.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

UTC = timezone.utc

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "meta.sqlite"
OUT_DIR = ROOT / "data" / "ml" / "features"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DETECTORS: list[str] = [
    "smt_htf_reference_divergence",
    "psp_candle_divergence",
    "fvg_formation",
    "order_block",
    "liquidity_sweep",
    "displacement_candle",
    "swing_pivot",
    "first_third_range",
    "opening_range_breakout",
    "equal_levels",
    "time_profile",
    "volume_profile",
    "forming_volume_profile",
    "opening_gap_levels",
    "interval_true_range",
]

CROSS_DETECTOR_WINDOW_HOURS: int = 24
CHUNKED_DETECTORS: set[str] = {"forming_volume_profile"}
CHUNK_SIZE: int = 50_000

BASE_COLUMN_TYPES: dict[str, str] = {
    "event_id": "int",
    "bar_end_utc": "datetime",
    "year": "int",
    "month": "int",
    "day_of_week": "int",
    "hour_of_day_utc": "int",
    "event_type": "string",
    "side": "string",
    "primary_symbol": "string",
}


# ---------- flattening utilities ----------


def _flatten(obj: Any, prefix: str = "", out: dict | None = None) -> dict:
    """Flatten a nested dict/list into a flat dict with dot-separated
    keys. Only keeps numeric, bool, and string leaves. Lists/dicts
    that don't reduce to a scalar are dropped (rich structure lives
    in JSON; ML can't consume it directly)."""
    if out is None:
        out = {}
    if obj is None:
        return out
    if isinstance(obj, (int, float, bool, str)):
        out[prefix.rstrip(".")] = obj
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            _flatten(v, f"{prefix}{k}.", out)
        return out
    if isinstance(obj, list):
        # Skip lists for now — too detector-specific to flatten generically.
        # Specific lists (like sub_periods) can be extracted by detector-
        # specific overrides.
        out[prefix.rstrip(".") + "__len"] = len(obj)
        return out
    return out


def _safe_json(s: str | None) -> dict:
    if not s or s == "null":
        return {}
    try:
        parsed = json.loads(s)
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, TypeError):
        return {}


# ---------- main builder ----------


def build_for_detector(
    con: sqlite3.Connection,
    feature_name: str,
    all_event_times: dict[str, dict[str, np.ndarray]],
) -> pd.DataFrame | None:
    """Build feature matrix for one detector.

    `all_event_times` is a dict {detector_name: {primary_symbol: sorted ts array}}
    used to compute cross-detector flags efficiently.
    """
    sql = """
        SELECT id, event_type, side, primary_symbol, bar_end_utc,
               event_data, outcomes, context
        FROM research_events
        WHERE feature_name = ?
        ORDER BY bar_end_utc
    """
    df = pd.read_sql_query(sql, con, params=(feature_name,))
    if df.empty:
        return None
    df["bar_end_utc"] = pd.to_datetime(df["bar_end_utc"], utc=True)
    df["event_data"] = df["event_data"].apply(_safe_json)
    df["outcomes"] = df["outcomes"].apply(_safe_json)
    df["context"] = df["context"].apply(_safe_json)

    rows: list[dict] = []
    for r in df.itertuples(index=False):
        ed_flat = _flatten(r.event_data, prefix="ed.")
        oc_flat = _flatten(r.outcomes, prefix="oc.")
        ctx_flat = _flatten(r.context, prefix="ctx.")
        ts = r.bar_end_utc
        row = {
            "event_id": r.id,
            "bar_end_utc": ts,
            "year": ts.year,
            "month": ts.month,
            "day_of_week": ts.dayofweek,
            "hour_of_day_utc": ts.hour,
            "event_type": r.event_type,
            "side": r.side,
            "primary_symbol": r.primary_symbol,
            **ed_flat,
            **oc_flat,
            **ctx_flat,
        }
        rows.append(row)
    out = pd.DataFrame(rows)

    # Coerce dtypes — pandas will infer, but we want consistent numeric
    # types where possible. Object/string columns stay as-is.
    for col in out.columns:
        if out[col].dtype == "object":
            # try numeric first
            num = pd.to_numeric(out[col], errors="coerce")
            if num.notna().sum() > 0.95 * out[col].notna().sum():
                # Mostly numeric — convert.
                out[col] = num

    # ---------- cross-detector flags ----------
    # For each OTHER detector, mark has_<det>_in_24h based on whether
    # that detector fired on the same primary in [t - 24h, t).
    ts_ns = out["bar_end_utc"].astype("int64").to_numpy()
    primary_arr = out["primary_symbol"].to_numpy()
    window_ns = CROSS_DETECTOR_WINDOW_HOURS * 3600 * 10**9
    flag_cols: dict[str, np.ndarray] = {}
    for other_det in DETECTORS:
        if other_det == feature_name:
            continue
        flag = np.zeros(len(out), dtype=bool)
        other_ts_by_primary = all_event_times.get(other_det, {})
        for primary in pd.unique(primary_arr):
            primary_mask = primary_arr == primary
            other_ts = other_ts_by_primary.get(primary)
            if other_ts is None or len(other_ts) == 0:
                continue
            idx = np.where(primary_mask)[0]
            sub_ts = ts_ns[idx]
            lo = sub_ts - window_ns
            left = np.searchsorted(other_ts, lo, side="left")
            right = np.searchsorted(other_ts, sub_ts, side="left")
            flag[idx] = right > left
        col = f"xd.has_{_short_name(other_det)}_in_{CROSS_DETECTOR_WINDOW_HOURS}h"
        flag_cols[col] = flag
    if flag_cols:
        out = pd.concat([out, pd.DataFrame(flag_cols, index=out.index)], axis=1)

    return out


def _event_sql() -> str:
    return """
        SELECT id, event_type, side, primary_symbol, bar_end_utc,
               event_data, outcomes, context
        FROM research_events
        WHERE feature_name = ?
        ORDER BY bar_end_utc
    """


def _matrix_from_events(
    df: pd.DataFrame,
    *,
    feature_name: str,
    all_event_times: dict[str, dict[str, np.ndarray]],
) -> pd.DataFrame:
    df["bar_end_utc"] = pd.to_datetime(df["bar_end_utc"], utc=True)
    df["event_data"] = df["event_data"].apply(_safe_json)
    df["outcomes"] = df["outcomes"].apply(_safe_json)
    df["context"] = df["context"].apply(_safe_json)

    rows: list[dict] = []
    for r in df.itertuples(index=False):
        ts = r.bar_end_utc
        rows.append({
            "event_id": r.id,
            "bar_end_utc": ts,
            "year": ts.year,
            "month": ts.month,
            "day_of_week": ts.dayofweek,
            "hour_of_day_utc": ts.hour,
            "event_type": r.event_type,
            "side": r.side,
            "primary_symbol": r.primary_symbol,
            **_flatten(r.event_data, prefix="ed."),
            **_flatten(r.outcomes, prefix="oc."),
            **_flatten(r.context, prefix="ctx."),
        })
    out = pd.DataFrame(rows)
    _coerce_object_columns(out)

    ts_ns = out["bar_end_utc"].astype("int64").to_numpy()
    primary_arr = out["primary_symbol"].to_numpy()
    window_ns = CROSS_DETECTOR_WINDOW_HOURS * 3600 * 10**9
    flag_cols: dict[str, np.ndarray] = {}
    for other_det in DETECTORS:
        if other_det == feature_name:
            continue
        flag = np.zeros(len(out), dtype=bool)
        other_ts_by_primary = all_event_times.get(other_det, {})
        for primary in pd.unique(primary_arr):
            primary_mask = primary_arr == primary
            other_ts = other_ts_by_primary.get(primary)
            if other_ts is None or len(other_ts) == 0:
                continue
            idx = np.where(primary_mask)[0]
            sub_ts = ts_ns[idx]
            lo = sub_ts - window_ns
            left = np.searchsorted(other_ts, lo, side="left")
            right = np.searchsorted(other_ts, sub_ts, side="left")
            flag[idx] = right > left
        col = f"xd.has_{_short_name(other_det)}_in_{CROSS_DETECTOR_WINDOW_HOURS}h"
        flag_cols[col] = flag
    if flag_cols:
        out = pd.concat([out, pd.DataFrame(flag_cols, index=out.index)], axis=1)
    return out


def _coerce_object_columns(out: pd.DataFrame) -> None:
    for col in out.columns:
        if out[col].dtype == "object":
            num = pd.to_numeric(out[col], errors="coerce")
            if num.notna().sum() > 0.95 * out[col].notna().sum():
                out[col] = num


def _merge_type(existing: str | None, observed: str) -> str:
    if existing is None:
        return observed
    if existing == observed:
        return existing
    if "string" in {existing, observed}:
        return "string"
    if "float" in {existing, observed}:
        return "float"
    if {existing, observed} == {"bool", "int"}:
        return "float"
    return observed


def _observe_type(col: str, series: pd.Series) -> str:
    if col in BASE_COLUMN_TYPES:
        return BASE_COLUMN_TYPES[col]
    if col.startswith("xd."):
        return "bool"
    if pd.api.types.is_bool_dtype(series):
        return "bool"
    if pd.api.types.is_numeric_dtype(series):
        return "float"
    return "string"


def _arrow_type(kind: str) -> pa.DataType:
    return {
        "bool": pa.bool_(),
        "datetime": pa.timestamp("ns", tz="UTC"),
        "float": pa.float64(),
        "int": pa.int64(),
        "string": pa.string(),
    }[kind]


def _prepare_chunk_for_schema(
    df: pd.DataFrame,
    *,
    columns: list[str],
    type_map: dict[str, str],
) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            out[col] = pd.NA
    out = out[columns]
    for col in columns:
        kind = type_map[col]
        if kind == "bool":
            out[col] = out[col].astype("boolean")
        elif kind == "datetime":
            out[col] = pd.to_datetime(out[col], utc=True)
        elif kind == "float":
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("float64")
        elif kind == "int":
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0).astype("int64")
        elif kind == "string":
            out[col] = out[col].astype("string")
    return out


def build_for_detector_chunked(
    con: sqlite3.Connection,
    feature_name: str,
    all_event_times: dict[str, dict[str, np.ndarray]],
    out_path: Path,
) -> dict | None:
    columns: list[str] = []
    seen_cols: set[str] = set()
    type_map: dict[str, str] = {}
    n_rows = 0
    print(f"   discovering schema in {CHUNK_SIZE:,}-row chunks...")
    for chunk in pd.read_sql_query(_event_sql(), con, params=(feature_name,), chunksize=CHUNK_SIZE):
        if chunk.empty:
            continue
        matrix = _matrix_from_events(
            chunk,
            feature_name=feature_name,
            all_event_times=all_event_times,
        )
        n_rows += len(matrix)
        for col in matrix.columns:
            if col not in seen_cols:
                seen_cols.add(col)
                columns.append(col)
            type_map[col] = _merge_type(type_map.get(col), _observe_type(col, matrix[col]))
    if n_rows == 0:
        return None

    schema = pa.schema([(col, _arrow_type(type_map[col])) for col in columns])
    writer: pq.ParquetWriter | None = None
    written = 0
    print(f"   writing {n_rows:,} rows in chunks...")
    try:
        for chunk in pd.read_sql_query(_event_sql(), con, params=(feature_name,), chunksize=CHUNK_SIZE):
            matrix = _matrix_from_events(
                chunk,
                feature_name=feature_name,
                all_event_times=all_event_times,
            )
            matrix = _prepare_chunk_for_schema(
                matrix,
                columns=columns,
                type_map=type_map,
            )
            table = pa.Table.from_pandas(matrix, schema=schema, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(out_path, schema)
            writer.write_table(table)
            written += len(matrix)
            print(f"      wrote {written:,}/{n_rows:,} rows")
    finally:
        if writer is not None:
            writer.close()
    return {
        "detector": feature_name,
        "rows": n_rows,
        "cols": len(columns),
        "path": str(out_path),
    }


def _short_name(detector: str) -> str:
    """Short, parquet-friendly column abbreviation."""
    return {
        "smt_htf_reference_divergence": "smt",
        "psp_candle_divergence": "psp",
        "fvg_formation": "fvg",
        "order_block": "ob",
        "liquidity_sweep": "sweep",
        "displacement_candle": "disp",
        "swing_pivot": "swing",
        "first_third_range": "ft",
        "opening_range_breakout": "orb",
        "equal_levels": "eql",
        "time_profile": "tp",
        "volume_profile": "vp",
        "forming_volume_profile": "fvp",
        "opening_gap_levels": "ogap",
        "interval_true_range": "itr",
    }.get(detector, detector[:8])


def load_all_event_times(con: sqlite3.Connection) -> dict[str, dict[str, np.ndarray]]:
    """Pre-load bar_end_utc for every (detector, primary_symbol) into
    sorted int64 numpy arrays. Used for fast cross-detector flag lookup.
    """
    out: dict[str, dict[str, np.ndarray]] = {}
    for det in DETECTORS:
        sql = """
            SELECT primary_symbol, bar_end_utc
            FROM research_events
            WHERE feature_name = ?
            ORDER BY primary_symbol, bar_end_utc
        """
        df = pd.read_sql_query(sql, con, params=(det,))
        if df.empty:
            out[det] = {}
            continue
        df["bar_end_utc"] = pd.to_datetime(df["bar_end_utc"], utc=True)
        by_sym = {}
        for sym, sub in df.groupby("primary_symbol"):
            ts = sub["bar_end_utc"].astype("int64").to_numpy(copy=True)
            ts.sort()
            by_sym[sym] = ts
        out[det] = by_sym
        print(f"  pre-loaded {det}: {len(df):,} events across "
              f"{len(by_sym)} symbols")
    return out


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    print(">>> pre-loading cross-detector timestamps...")
    all_event_times = load_all_event_times(con)

    summary: list[dict] = []
    for det in DETECTORS:
        print(f"\n>>> building feature matrix for {det}...")
        out_path = OUT_DIR / f"{_short_name(det)}.parquet"
        if det in CHUNKED_DETECTORS:
            chunked_summary = build_for_detector_chunked(con, det, all_event_times, out_path)
            if chunked_summary is None:
                print(f"   (no events, skipping)")
                continue
            print(
                f"   wrote {out_path}: {chunked_summary['rows']:,} rows × "
                f"{chunked_summary['cols']} cols"
            )
            summary.append(chunked_summary)
            continue
        out = build_for_detector(con, det, all_event_times)
        if out is None or out.empty:
            print(f"   (no events, skipping)")
            continue
        out.to_parquet(out_path, index=False)
        n_cols = len(out.columns)
        n_rows = len(out)
        print(f"   wrote {out_path}: {n_rows:,} rows × {n_cols} cols")
        summary.append({
            "detector": det, "rows": n_rows, "cols": n_cols,
            "path": str(out_path),
        })

    print("\n=== summary ===")
    for s in summary:
        print(f"  {s['detector']:35s}  {s['rows']:>7,} rows  {s['cols']:>4} cols")
    print(f"\nTotal feature matrix files: {len(summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
