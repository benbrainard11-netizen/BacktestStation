"""Build SMT anchor snapshot matrices for ML.

This is the first reusable "as-of" dataset builder. It creates two rows per
SMT anchor by default:

  - at_fire: features known at the first divergent break
  - at_period_close: at_fire features plus period-close aligned-event features

Labels are stored under label.* and are never feature columns by convention.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from baseline_per_detector import _feature_columns  # noqa: E402
from snapshot_feature_registry import (  # noqa: E402
    DISP_LAG_MIN,
    FVG_LAG_MIN,
    OB_LAG_MIN,
    PSP_LAG_MIN,
    SMT_LAG_MIN,
    SWEEP_LAG_MIN,
    registry_as_dict,
)

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
DB_PATH = ROOT / "data" / "meta.sqlite"
SMT_FEATURES_PATH = ROOT / "data" / "ml" / "features" / "smt.parquet"
OUT_DIR = ROOT / "data" / "ml" / "anchors"
DEFAULT_OUT = OUT_DIR / "smt_previous_day_snapshots.parquet"
DEFAULT_SCHEMA = OUT_DIR / "smt_previous_day_snapshots.schema.json"
NAT_INT = np.iinfo("int64").min
NS_PER_MIN = 60 * 1_000_000_000


def _aligned_counts(
    start_ns: np.ndarray,
    end_ns: np.ndarray,
    event_ns: np.ndarray,
) -> np.ndarray:
    out = np.zeros(len(start_ns), dtype=np.int16)
    if len(event_ns) == 0:
        return out
    left = np.searchsorted(event_ns, start_ns, side="right")
    right = np.searchsorted(event_ns, end_ns, side="right")
    valid = (start_ns != NAT_INT) & (end_ns != NAT_INT) & (end_ns >= start_ns)
    out[valid] = np.maximum(right[valid] - left[valid], 0).astype(np.int16)
    return out


def _aligned_minutes_since_last(
    start_ns: np.ndarray,
    end_ns: np.ndarray,
    event_ns: np.ndarray,
) -> np.ndarray:
    out = np.full(len(start_ns), np.nan, dtype="float64")
    if len(event_ns) == 0:
        return out
    left = np.searchsorted(event_ns, start_ns, side="right")
    right = np.searchsorted(event_ns, end_ns, side="right")
    valid = (
        (start_ns != NAT_INT)
        & (end_ns != NAT_INT)
        & (end_ns >= start_ns)
        & (right > left)
    )
    out[valid] = (end_ns[valid] - event_ns[right[valid] - 1]) / NS_PER_MIN
    return out


def _aligned_metrics(
    start_ns: np.ndarray,
    end_ns: np.ndarray,
    event_ns: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    counts = _aligned_counts(start_ns, end_ns, event_ns)
    minutes = _aligned_minutes_since_last(start_ns, end_ns, event_ns)
    return counts > 0, counts, minutes


def _global_metrics(
    start_ns: np.ndarray,
    end_ns: np.ndarray,
    events: pd.DataFrame,
    time_col: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    event_ns = (
        events[time_col]
        .dropna()
        .sort_values()
        .to_numpy("datetime64[ns]")
        .astype("int64")
    )
    return _aligned_metrics(start_ns, end_ns, event_ns)


def _primary_metrics(
    start_ns: np.ndarray,
    end_ns: np.ndarray,
    primary: np.ndarray,
    events: pd.DataFrame,
    time_col: str,
    primary_col: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    has = np.zeros(len(start_ns), dtype=bool)
    counts = np.zeros(len(start_ns), dtype=np.int16)
    minutes = np.full(len(start_ns), np.nan, dtype="float64")
    if events.empty:
        return has, counts, minutes
    for sym in pd.unique(primary):
        if pd.isna(sym):
            continue
        idx = np.where(primary == sym)[0]
        event_ns = (
            events[events[primary_col] == sym][time_col]
            .dropna()
            .sort_values()
            .to_numpy("datetime64[ns]")
            .astype("int64")
        )
        has_i, counts_i, minutes_i = _aligned_metrics(
            start_ns[idx], end_ns[idx], event_ns,
        )
        has[idx] = has_i
        counts[idx] = counts_i
        minutes[idx] = minutes_i
    return has, counts, minutes


def _assign_window_metrics(
    out: pd.DataFrame,
    name: str,
    metrics: tuple[np.ndarray, np.ndarray, np.ndarray],
    mask: np.ndarray,
) -> None:
    has, counts, minutes = metrics
    masked_has = has & mask
    out[f"pc.has_{name}_in_window"] = masked_has
    out[f"pc.n_{name}_in_window"] = np.where(mask, counts, 0).astype(np.int16)
    out[f"pc.minutes_since_last_{name}_in_window"] = np.where(
        masked_has, minutes, np.nan,
    )


def _read_events(con: sqlite3.Connection, feature_name: str, columns: str) -> pd.DataFrame:
    return pd.read_sql_query(
        f"""
        SELECT {columns}
        FROM research_events
        WHERE feature_name=?
        """,
        con,
        params=(feature_name,),
    )


def _load_period_close_features(
    con: sqlite3.Connection,
    anchors: pd.DataFrame,
) -> pd.DataFrame:
    event_ids = anchors["anchor.event_id"].astype(int)
    smt = pd.read_sql_query(
        """
        SELECT id AS event_id, primary_symbol, bar_end_utc AS smt_bar_end,
               json_extract(outcomes, '$.period_close.ts_utc') AS period_close_ts,
               json_extract(outcomes, '$.period_close.smt_active_for_side_at_close') AS active_at_close
        FROM research_events
        WHERE feature_name='smt_htf_reference_divergence'
          AND id IN ({})
        """.format(",".join("?" for _ in event_ids)),
        con,
        params=tuple(int(x) for x in event_ids),
    )
    smt["smt_bar_end"] = pd.to_datetime(smt["smt_bar_end"], utc=True)
    smt["period_close_ts"] = pd.to_datetime(smt["period_close_ts"], utc=True)
    smt["smt_knowable_ts"] = smt["smt_bar_end"] + pd.to_timedelta(
        smt["event_id"].map(
            anchors.set_index("anchor.event_id")["anchor.event_type"].map(SMT_LAG_MIN)
        ).to_numpy(),
        unit="m",
    )
    smt = smt.set_index("event_id").reindex(event_ids).reset_index()

    start_ns = smt["smt_knowable_ts"].to_numpy("datetime64[ns]").astype("int64")
    end_ns = smt["period_close_ts"].to_numpy("datetime64[ns]").astype("int64")
    primary = smt["primary_symbol"].to_numpy()
    side = anchors["anchor.side"].to_numpy()
    target_side = np.where(side == "low", "bullish", "bearish")
    target_ref_side = np.where(side == "low", "low", "high")

    out = pd.DataFrame(index=anchors.index)
    out["pc.active_at_close"] = (
        pd.to_numeric(smt["active_at_close"], errors="coerce").fillna(0).astype(int)
    )

    psp = _read_events(
        con,
        "psp_candle_divergence",
        "bar_end_utc AS bar_end, event_type, side",
    )
    psp["bar_end"] = pd.to_datetime(psp["bar_end"], utc=True)
    psp["lag_min"] = psp["event_type"].map(PSP_LAG_MIN).astype("Int64")
    psp["knowable_ts"] = psp["bar_end"] + pd.to_timedelta(psp["lag_min"], unit="m")
    for psp_type in PSP_LAG_MIN:
        for direction in ("bullish", "bearish"):
            events = psp[(psp["event_type"] == psp_type) & (psp["side"] == direction)]
            _assign_window_metrics(
                out,
                f"{psp_type}_{direction}",
                _global_metrics(start_ns, end_ns, events, "knowable_ts"),
                target_side == direction,
            )

    fvg = _read_events(
        con,
        "fvg_formation",
        "bar_end_utc AS bar_end, event_type, side, primary_symbol",
    )
    fvg["bar_end"] = pd.to_datetime(fvg["bar_end"], utc=True)
    fvg["lag_min"] = fvg["event_type"].map(FVG_LAG_MIN).astype("Int64")
    fvg["knowable_ts"] = fvg["bar_end"] + pd.to_timedelta(fvg["lag_min"], unit="m")
    for fvg_type in FVG_LAG_MIN:
        for direction in ("bullish", "bearish"):
            events = fvg[(fvg["event_type"] == fvg_type) & (fvg["side"] == direction)]
            _assign_window_metrics(
                out,
                f"{fvg_type}_{direction}_same_primary",
                _primary_metrics(
                    start_ns, end_ns, primary, events, "knowable_ts", "primary_symbol",
                ),
                target_side == direction,
            )

    ob = _read_events(
        con,
        "order_block",
        "bar_end_utc AS bar_end, event_type, side, primary_symbol",
    )
    ob["bar_end"] = pd.to_datetime(ob["bar_end"], utc=True)
    ob["lag_min"] = ob["event_type"].map(OB_LAG_MIN).astype("Int64")
    ob["knowable_ts"] = ob["bar_end"] + pd.to_timedelta(ob["lag_min"], unit="m")
    for direction in ("bullish", "bearish"):
        events = ob[ob["side"] == direction]
        _assign_window_metrics(
            out,
            f"ob_{direction}_same_primary",
            _primary_metrics(
                start_ns, end_ns, primary, events, "knowable_ts", "primary_symbol",
            ),
            target_side == direction,
        )
    for ob_mode in OB_LAG_MIN:
        for direction in ("bullish", "bearish"):
            events = ob[(ob["event_type"] == ob_mode) & (ob["side"] == direction)]
            _assign_window_metrics(
                out,
                f"ob_{ob_mode}_{direction}_same_primary",
                _primary_metrics(
                    start_ns, end_ns, primary, events, "knowable_ts", "primary_symbol",
                ),
                target_side == direction,
            )

    sweep = _read_events(
        con,
        "liquidity_sweep",
        "bar_end_utc AS bar_end, event_type, side, primary_symbol",
    )
    sweep["bar_end"] = pd.to_datetime(sweep["bar_end"], utc=True)
    sweep["lag_min"] = sweep["event_type"].map(SWEEP_LAG_MIN).astype("Int64")
    sweep["knowable_ts"] = sweep["bar_end"] + pd.to_timedelta(sweep["lag_min"], unit="m")
    for ref_side in ("low", "high"):
        events = sweep[sweep["side"] == ref_side]
        _assign_window_metrics(
            out,
            f"sweep_{ref_side}_same_primary",
            _primary_metrics(
                start_ns, end_ns, primary, events, "knowable_ts", "primary_symbol",
            ),
            target_ref_side == ref_side,
        )
    for sweep_mode in SWEEP_LAG_MIN:
        for ref_side in ("low", "high"):
            events = sweep[(sweep["event_type"] == sweep_mode) & (sweep["side"] == ref_side)]
            _assign_window_metrics(
                out,
                f"sweep_{sweep_mode}_{ref_side}_same_primary",
                _primary_metrics(
                    start_ns, end_ns, primary, events, "knowable_ts", "primary_symbol",
                ),
                target_ref_side == ref_side,
            )

    disp = _read_events(
        con,
        "displacement_candle",
        "bar_end_utc AS bar_end, event_type, side, primary_symbol",
    )
    disp["bar_end"] = pd.to_datetime(disp["bar_end"], utc=True)
    disp["lag_min"] = disp["event_type"].map(DISP_LAG_MIN).astype("Int64")
    disp["knowable_ts"] = disp["bar_end"] + pd.to_timedelta(disp["lag_min"], unit="m")
    for disp_type in DISP_LAG_MIN:
        for direction in ("bullish", "bearish"):
            events = disp[(disp["event_type"] == disp_type) & (disp["side"] == direction)]
            _assign_window_metrics(
                out,
                f"{disp_type}_{direction}_same_primary",
                _primary_metrics(
                    start_ns, end_ns, primary, events, "knowable_ts", "primary_symbol",
                ),
                target_side == direction,
            )

    out["pc.manual_active_1hpsp_4hfvg_cell"] = (
        out["pc.active_at_close"].astype(bool)
        & (
            out["pc.has_1h_psp_bullish_in_window"]
            | out["pc.has_1h_psp_bearish_in_window"]
        )
        & (
            out["pc.has_4h_fvg_bullish_same_primary_in_window"]
            | out["pc.has_4h_fvg_bearish_same_primary_in_window"]
        )
    )
    return out


def _build_anchor_rows(
    smt: pd.DataFrame,
    con: sqlite3.Connection,
    include_period_close: bool,
) -> pd.DataFrame:
    numeric_cols, categorical_cols = _feature_columns(smt, "smt")
    raw_cols = numeric_cols + categorical_cols
    labels = pd.DataFrame(index=smt.index)

    def add_label(name: str, source_col: str) -> None:
        labels[name] = pd.to_numeric(smt[source_col], errors="coerce")

    label_map = {
        "n1": "oc.next_period",
        "n2": "oc.n_plus_2",
    }
    for horizon, source_prefix in label_map.items():
        for field in (
            "thesis_confirmed_strict",
            "close_moved_with_thesis",
            "primary_return_pts",
            "primary_return_pct",
            "primary_took_period_n_high",
            "primary_took_period_n_low",
            "mfe_pts_in_thesis",
            "mae_pts_against_thesis",
        ):
            add_label(f"label.{horizon}_{field}", f"{source_prefix}.{field}")

    labels["label.n1_or_n2_thesis_confirmed_strict"] = (
        (labels["label.n1_thesis_confirmed_strict"].fillna(0).astype(int) == 1)
        | (labels["label.n2_thesis_confirmed_strict"].fillna(0).astype(int) == 1)
    )
    labels["label.n1_or_n2_close_moved_with_thesis"] = (
        (labels["label.n1_close_moved_with_thesis"].fillna(0).astype(int) == 1)
        | (labels["label.n2_close_moved_with_thesis"].fillna(0).astype(int) == 1)
    )

    base = pd.DataFrame(index=smt.index)
    base["anchor.event_id"] = smt["event_id"].astype(int)
    base["anchor.feature_name"] = "smt_htf_reference_divergence"
    base["anchor.event_type"] = smt["event_type"]
    base["anchor.side"] = smt["side"]
    base["anchor.primary_symbol"] = smt["primary_symbol"]
    base["anchor.bar_end_utc"] = smt["bar_end_utc"]
    base["asof.label_start_ts"] = pd.to_datetime(
        smt["oc.next_period.ts_utc_start"], utc=True,
    )
    base["asof.label_end_ts"] = pd.to_datetime(
        smt["oc.next_period.ts_utc_close"], utc=True,
    )

    fire_features = smt[raw_cols].rename(
        columns={col: f"smt.{col}" for col in raw_cols if not col.startswith("xd.")}
    )
    fire_features = fire_features.rename(
        columns={col: col for col in raw_cols if col.startswith("xd.")}
    )

    rows: list[pd.DataFrame] = []
    for snapshot in ("at_fire", "at_period_close"):
        if snapshot == "at_period_close" and not include_period_close:
            continue
        frame = pd.concat([base, fire_features, labels], axis=1)
        frame.insert(1, "asof.snapshot", snapshot)
        if snapshot == "at_fire":
            frame["asof.snapshot_ts"] = smt["bar_end_utc"] + pd.to_timedelta(
                smt["event_type"].map(SMT_LAG_MIN), unit="m",
            )
        else:
            frame["asof.snapshot_ts"] = pd.to_datetime(
                smt["oc.period_close.ts_utc"], utc=True,
            )
            frame = pd.concat([frame, _load_period_close_features(con, base)], axis=1)
        frame["asof.feature_cutoff_ts"] = frame["asof.snapshot_ts"]
        ts = pd.to_datetime(frame["asof.snapshot_ts"], utc=True)
        frame["ts.year"] = ts.dt.year
        frame["ts.month"] = ts.dt.month
        frame["ts.day_of_week"] = ts.dt.dayofweek
        frame["ts.hour_of_day_utc"] = ts.dt.hour
        rows.append(frame)
    return pd.concat(rows, ignore_index=True)


def _write_schema(path: Path, matrix: pd.DataFrame, args: argparse.Namespace) -> None:
    feature_cols = [
        c for c in matrix.columns
        if c.startswith(("smt.", "xd.", "pc.", "ts."))
    ]
    label_cols = [c for c in matrix.columns if c.startswith("label.")]
    meta = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "builder": "backend/scripts/ml/build_smt_anchor_snapshot_matrix.py",
        "anchor": {
            "feature_name": "smt_htf_reference_divergence",
            "event_type": args.event_type,
            "side": args.side,
        },
        "snapshot_names": sorted(matrix["asof.snapshot"].unique().tolist()),
        "rows": int(len(matrix)),
        "feature_columns": feature_cols,
        "label_columns": label_cols,
        "registry": registry_as_dict(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-type", default="previous_day_smt")
    parser.add_argument("--side", choices=["low", "high", "all"], default="all")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--schema-output", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--fire-only", action="store_true")
    args = parser.parse_args()

    smt = pd.read_parquet(SMT_FEATURES_PATH)
    smt["bar_end_utc"] = pd.to_datetime(smt["bar_end_utc"], utc=True)
    smt = smt[smt["event_type"] == args.event_type].copy()
    if args.side != "all":
        smt = smt[smt["side"] == args.side].copy()
    smt = smt[smt["oc.next_period.thesis_confirmed_strict"].notna()].copy()
    smt = smt.sort_values("bar_end_utc").reset_index(drop=True)

    con = sqlite3.connect(DB_PATH)
    matrix = _build_anchor_rows(smt, con, include_period_close=not args.fire_only)
    con.close()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    matrix.to_parquet(args.output, index=False)
    _write_schema(args.schema_output, matrix, args)
    print(
        f"wrote {args.output}: {len(matrix):,} rows x {len(matrix.columns)} cols"
    )
    print(f"wrote {args.schema_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
