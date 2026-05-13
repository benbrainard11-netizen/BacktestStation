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

UTC = timezone.utc

DB_PATH = Path(r"C:\Users\benbr\BacktestStation\data\meta.sqlite")
OUT_DIR = Path(r"C:\Users\benbr\BacktestStation\data\ml\features")
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
]

CROSS_DETECTOR_WINDOW_HOURS: int = 24


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
        out[col] = flag

    return out


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
            ts = sub["bar_end_utc"].astype("int64").to_numpy()
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
        out = build_for_detector(con, det, all_event_times)
        if out is None or out.empty:
            print(f"   (no events, skipping)")
            continue
        out_path = OUT_DIR / f"{_short_name(det)}.parquet"
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
