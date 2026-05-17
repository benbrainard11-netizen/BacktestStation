"""Build and merge cross-concept context features into a snapshot matrix.

The script is intentionally conservative:

  - context events are converted to detector knowable timestamps
  - only events with knowable_ts < anchor feature_cutoff_ts are counted
  - the anchor concept itself is excluded by default to avoid self-counting
  - generated features are written under xctx.*

First target: SMT previous-day snapshots. The implementation is generic enough
to reuse for other snapshot matrices after the first comparison pass.
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

from snapshot_feature_registry import (  # noqa: E402
    DISP_LAG_MIN,
    EQL_LAG_MIN,
    FVG_LAG_MIN,
    OB_LAG_MIN,
    PSP_LAG_MIN,
    SMT_LAG_MIN,
    SMT_MTF_LAG_MIN,
    SWEEP_LAG_MIN,
    SWING_LAG_MIN,
    registry_as_dict,
)

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
DB_PATH = ROOT / "data" / "meta.sqlite"
ANCHORS_DIR = ROOT / "data" / "ml" / "anchors"
CONTEXT_DIR = ROOT / "data" / "ml" / "context"
DEFAULT_MATRIX = ANCHORS_DIR / "smt_previous_day_snapshots.parquet"
DEFAULT_SCHEMA = ANCHORS_DIR / "smt_previous_day_snapshots.schema.json"
DEFAULT_OUTPUT = ANCHORS_DIR / "smt_previous_day_snapshots_xctx.parquet"
DEFAULT_SCHEMA_OUTPUT = ANCHORS_DIR / "smt_previous_day_snapshots_xctx.schema.json"
DEFAULT_CONTEXT_OUTPUT = CONTEXT_DIR / "smt_previous_day_cross_concept_context.parquet"

NS_PER_MIN = 60 * 1_000_000_000
WINDOWS_MIN = {
    "1h": 60,
    "4h": 4 * 60,
    "24h": 24 * 60,
    "7d": 7 * 24 * 60,
}

DETECTOR_TO_SHORT = {
    "smt_htf_reference_divergence": "smt",
    "smt_prev_candle_divergence": "smt_mtf",
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
    "macro_event_anchor": "macro",
}
SHORT_TO_DETECTOR = {v: k for k, v in DETECTOR_TO_SHORT.items()}

LAG_BY_SHORT = {
    "smt": SMT_LAG_MIN,
    "smt_mtf": SMT_MTF_LAG_MIN,
    "psp": PSP_LAG_MIN,
    "fvg": FVG_LAG_MIN,
    "ob": OB_LAG_MIN,
    "sweep": SWEEP_LAG_MIN,
    "disp": DISP_LAG_MIN,
    "swing": SWING_LAG_MIN,
    "eql": EQL_LAG_MIN,
}


def _parse_csv_arg(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _safe_name(value: Any) -> str:
    out = str(value).strip().lower()
    for old, new in [
        (" ", "_"),
        (".", "_"),
        ("-", "_"),
        ("/", "_"),
        ("+", "plus"),
    ]:
        out = out.replace(old, new)
    return "".join(ch for ch in out if ch.isalnum() or ch == "_").strip("_")


def _read_research_events(db_path: Path) -> pd.DataFrame:
    with sqlite3.connect(db_path) as con:
        df = pd.read_sql_query(
            """
            SELECT
                id AS event_id,
                feature_name,
                event_type,
                bar_end_utc,
                primary_symbol,
                side,
                json_extract(event_data, '$.knowable_ts_utc') AS ed_knowable_ts_utc,
                json_extract(event_data, '$.first_third_end_utc') AS ed_first_third_end_utc,
                json_extract(event_data, '$.range_end_utc') AS ed_range_end_utc,
                json_extract(event_data, '$.parent_period_end_utc') AS ed_parent_period_end_utc,
                json_extract(event_data, '$.asof_ts_utc') AS ed_asof_ts_utc,
                json_extract(event_data, '$.gap_open_ts_utc') AS ed_gap_open_ts_utc,
                json_extract(event_data, '$.interval_end_utc') AS ed_interval_end_utc,
                json_extract(event_data, '$.known_ts_utc') AS ed_macro_known_ts_utc
            FROM research_events
            """,
            con,
        )
    df["short_name"] = df["feature_name"].map(DETECTOR_TO_SHORT)
    df = df[df["short_name"].notna()].copy()
    df["bar_end_utc"] = pd.to_datetime(df["bar_end_utc"], utc=True)
    return df


def _compute_knowable_ts(events: pd.DataFrame) -> pd.Series:
    out = pd.Series(pd.NaT, index=events.index, dtype="datetime64[ns, UTC]")

    for short, lag_map in LAG_BY_SHORT.items():
        mask = events["short_name"].eq(short)
        if not mask.any():
            continue
        lag = events.loc[mask, "event_type"].map(lag_map)
        if lag.isna().any():
            missing = sorted(str(x) for x in events.loc[mask & lag.isna(), "event_type"].unique())
            raise ValueError(f"{short} missing knowable lag rules for event_type={missing}")
        out.loc[mask] = events.loc[mask, "bar_end_utc"] + pd.to_timedelta(
            lag.astype(int),
            unit="m",
        )

    ft = events["short_name"].eq("ft")
    if ft.any():
        ts = pd.to_datetime(events.loc[ft, "ed_first_third_end_utc"], utc=True, errors="coerce")
        fallback = events.loc[ft, "bar_end_utc"]
        out.loc[ft] = ts.fillna(fallback) + pd.to_timedelta(1, unit="m")

    orb = events["short_name"].eq("orb")
    if orb.any():
        ts = pd.to_datetime(events.loc[orb, "ed_range_end_utc"], utc=True, errors="coerce")
        out.loc[orb] = ts.fillna(events.loc[orb, "bar_end_utc"])

    for short in ("tp", "vp"):
        mask = events["short_name"].eq(short)
        if mask.any():
            ts = pd.to_datetime(
                events.loc[mask, "ed_parent_period_end_utc"],
                utc=True,
                errors="coerce",
            )
            out.loc[mask] = ts.fillna(events.loc[mask, "bar_end_utc"])

    fvp = events["short_name"].eq("fvp")
    if fvp.any():
        ts = pd.to_datetime(events.loc[fvp, "ed_asof_ts_utc"], utc=True, errors="coerce")
        out.loc[fvp] = ts.fillna(events.loc[fvp, "bar_end_utc"])

    ogap = events["short_name"].eq("ogap")
    if ogap.any():
        ts = pd.to_datetime(events.loc[ogap, "ed_gap_open_ts_utc"], utc=True, errors="coerce")
        out.loc[ogap] = ts.fillna(events.loc[ogap, "bar_end_utc"])

    itr = events["short_name"].eq("itr")
    if itr.any():
        ts = pd.to_datetime(events.loc[itr, "ed_interval_end_utc"], utc=True, errors="coerce")
        out.loc[itr] = ts.fillna(events.loc[itr, "bar_end_utc"])

    macro = events["short_name"].eq("macro")
    if macro.any():
        ts = pd.to_datetime(events.loc[macro, "ed_macro_known_ts_utc"], utc=True, errors="coerce")
        out.loc[macro] = ts.fillna(events.loc[macro, "bar_end_utc"])

    missing = events[out.isna()]
    if not missing.empty:
        grouped = missing.groupby(["short_name", "event_type"]).size().reset_index(name="rows")
        raise ValueError(f"missing knowable timestamps:\n{grouped.to_string(index=False)}")

    return out


def _window_metrics(
    cutoff_ns: np.ndarray,
    event_ns: np.ndarray,
    window_min: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    counts = np.zeros(len(cutoff_ns), dtype=np.int32)
    minutes = np.full(len(cutoff_ns), np.nan, dtype="float64")
    if len(event_ns) == 0:
        return counts > 0, counts, minutes

    event_ns = np.sort(event_ns.astype("int64"))
    start_ns = cutoff_ns - window_min * NS_PER_MIN
    left = np.searchsorted(event_ns, start_ns, side="left")
    right = np.searchsorted(event_ns, cutoff_ns, side="left")
    counts = np.maximum(right - left, 0).astype(np.int32)
    has = counts > 0
    if has.any():
        minutes[has] = (cutoff_ns[has] - event_ns[right[has] - 1]) / NS_PER_MIN
    return has, counts, minutes


def _assign_metrics(
    data: dict[str, Any],
    prefix: str,
    cutoff_ns: np.ndarray,
    event_ns: np.ndarray,
    window_key: str,
    window_min: int,
) -> tuple[np.ndarray, np.ndarray]:
    has, counts, minutes = _window_metrics(cutoff_ns, event_ns, window_min)
    stem = f"{prefix}_{window_key}"
    data[f"xctx.has_{stem}"] = has
    data[f"xctx.n_{stem}"] = counts
    data[f"xctx.minutes_since_last_{stem}"] = minutes
    return has, counts


def _assign_group_metrics(
    data: dict[str, Any],
    prefix: str,
    cutoff_ns: np.ndarray,
    anchor_values: np.ndarray,
    events: pd.DataFrame,
    group_col: str,
    window_key: str,
    window_min: int,
) -> tuple[np.ndarray, np.ndarray]:
    has_all = np.zeros(len(cutoff_ns), dtype=bool)
    counts_all = np.zeros(len(cutoff_ns), dtype=np.int32)
    minutes_all = np.full(len(cutoff_ns), np.nan, dtype="float64")

    for value in pd.unique(anchor_values):
        if pd.isna(value):
            continue
        row_idx = np.where(anchor_values == value)[0]
        event_ns = events.loc[events[group_col].eq(value), "knowable_ts_ns"].to_numpy(dtype="int64")
        has, counts, minutes = _window_metrics(cutoff_ns[row_idx], event_ns, window_min)
        has_all[row_idx] = has
        counts_all[row_idx] = counts
        minutes_all[row_idx] = minutes

    stem = f"{prefix}_{window_key}"
    data[f"xctx.has_{stem}"] = has_all
    data[f"xctx.n_{stem}"] = counts_all
    data[f"xctx.minutes_since_last_{stem}"] = minutes_all
    return has_all, counts_all


def build_context(
    anchors: pd.DataFrame,
    events: pd.DataFrame,
    *,
    context_shorts: list[str],
    windows: dict[str, int],
    exclude_anchor_short: str | None,
) -> pd.DataFrame:
    base_cols = [
        "anchor.event_id",
        "asof.snapshot",
        "asof.feature_cutoff_ts",
        "anchor.primary_symbol",
    ]
    missing = [c for c in base_cols if c not in anchors.columns]
    if missing:
        raise KeyError(f"anchor matrix missing required columns: {missing}")

    data: dict[str, Any] = {
        "anchor.event_id": anchors["anchor.event_id"].to_numpy(),
        "asof.snapshot": anchors["asof.snapshot"].to_numpy(),
    }
    cutoff = pd.to_datetime(anchors["asof.feature_cutoff_ts"], utc=True)
    cutoff_ns = cutoff.to_numpy("datetime64[ns]").astype("int64")
    anchor_primary = anchors["anchor.primary_symbol"].to_numpy()

    usable_events = events[events["short_name"].isin(context_shorts)].copy()
    if exclude_anchor_short:
        usable_events = usable_events[~usable_events["short_name"].eq(exclude_anchor_short)].copy()

    active_by_window = {key: np.zeros(len(anchors), dtype=np.int16) for key in windows}
    total_by_window = {key: np.zeros(len(anchors), dtype=np.int32) for key in windows}
    same_primary_active_by_window = {key: np.zeros(len(anchors), dtype=np.int16) for key in windows}
    same_primary_total_by_window = {key: np.zeros(len(anchors), dtype=np.int32) for key in windows}

    for short in sorted(usable_events["short_name"].dropna().unique()):
        concept_events = usable_events[usable_events["short_name"].eq(short)].copy()
        for window_key, window_min in windows.items():
            event_ns = concept_events["knowable_ts_ns"].to_numpy(dtype="int64")
            has, counts = _assign_metrics(
                data,
                short,
                cutoff_ns,
                event_ns,
                window_key,
                window_min,
            )
            active_by_window[window_key] += has.astype(np.int16)
            total_by_window[window_key] += counts

            has_sp, counts_sp = _assign_group_metrics(
                data,
                f"{short}_same_primary",
                cutoff_ns,
                anchor_primary,
                concept_events,
                "primary_symbol",
                window_key,
                window_min,
            )
            same_primary_active_by_window[window_key] += has_sp.astype(np.int16)
            same_primary_total_by_window[window_key] += counts_sp

        for side in sorted(str(x) for x in concept_events["side"].dropna().unique()):
            side_events = concept_events[concept_events["side"].astype(str).eq(side)]
            safe_side = _safe_name(side)
            for window_key, window_min in windows.items():
                _assign_metrics(
                    data,
                    f"{short}_side_{safe_side}",
                    cutoff_ns,
                    side_events["knowable_ts_ns"].to_numpy(dtype="int64"),
                    window_key,
                    window_min,
                )

    for window_key in windows:
        data[f"xctx.active_concepts_{window_key}"] = active_by_window[window_key]
        data[f"xctx.total_events_{window_key}"] = total_by_window[window_key]
        data[f"xctx.active_same_primary_concepts_{window_key}"] = same_primary_active_by_window[window_key]
        data[f"xctx.total_same_primary_events_{window_key}"] = same_primary_total_by_window[window_key]

    out = pd.DataFrame(data)
    xctx_cols = sorted(c for c in out.columns if c.startswith("xctx."))
    return out[["anchor.event_id", "asof.snapshot", *xctx_cols]]


def _write_schema(
    schema_output: Path,
    *,
    source_schema: Path,
    matrix: pd.DataFrame,
    context_cols: list[str],
    args: argparse.Namespace,
) -> None:
    schema = json.loads(source_schema.read_text(encoding="utf-8"))
    old_features = list(schema.get("feature_columns", []))
    merged_features = [*old_features, *[c for c in context_cols if c not in old_features]]
    schema.update(
        {
            "generated_utc": datetime.now(UTC).isoformat(),
            "builder": "backend/scripts/ml/build_cross_concept_context.py",
            "source_schema": str(source_schema),
            "source_matrix": str(args.matrix),
            "rows": int(len(matrix)),
            "feature_columns": merged_features,
            "registry": registry_as_dict(),
            "cross_concept_context": {
                "context_shorts": args.context_shorts,
                "windows_min": args.windows,
                "exclude_anchor_short": args.exclude_anchor_short,
                "context_columns": context_cols,
            },
            "notes": [
                *schema.get("notes", []),
                "xctx.* features are prior cross-concept context generated from research_events.",
                "Context uses detector knowable timestamps and excludes events at or after feature_cutoff_ts.",
            ],
        }
    )
    schema_output.parent.mkdir(parents=True, exist_ok=True)
    schema_output.write_text(json.dumps(schema, indent=2), encoding="utf-8")


def build(args: argparse.Namespace) -> tuple[Path, Path, Path, pd.DataFrame]:
    matrix = pd.read_parquet(args.matrix)
    if args.event_type != "all":
        matrix = matrix[matrix["anchor.event_type"].eq(args.event_type)].copy()
    if args.side != "all":
        matrix = matrix[matrix["anchor.side"].eq(args.side)].copy()
    if matrix.empty:
        raise ValueError("no anchor rows after filters")

    events = _read_research_events(args.db)
    events["knowable_ts"] = _compute_knowable_ts(events)
    events = events[events["knowable_ts"].notna()].copy()
    events["knowable_ts_ns"] = events["knowable_ts"].to_numpy("datetime64[ns]").astype("int64")

    context = build_context(
        matrix,
        events,
        context_shorts=args.context_shorts,
        windows=args.windows,
        exclude_anchor_short=args.exclude_anchor_short,
    )
    context_cols = [c for c in context.columns if c.startswith("xctx.")]
    merged = matrix.merge(
        context,
        on=["anchor.event_id", "asof.snapshot"],
        how="left",
        validate="one_to_one",
    )
    if merged[context_cols].isna().all(axis=None):
        raise ValueError("all generated context columns are null")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.context_output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(args.output, index=False)
    context.to_parquet(args.context_output, index=False)
    _write_schema(
        args.schema_output,
        source_schema=args.schema,
        matrix=merged,
        context_cols=context_cols,
        args=args,
    )
    return args.output, args.schema_output, args.context_output, merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--schema-output", type=Path, default=DEFAULT_SCHEMA_OUTPUT)
    parser.add_argument("--context-output", type=Path, default=DEFAULT_CONTEXT_OUTPUT)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--event-type", default="all")
    parser.add_argument("--side", default="all")
    parser.add_argument(
        "--context-shorts",
        type=_parse_csv_arg,
        default=sorted(SHORT_TO_DETECTOR),
        help="Comma-separated short feature keys to use as context.",
    )
    parser.add_argument(
        "--exclude-anchor-short",
        default="smt",
        help="Short feature key to exclude from context; use empty string to include all.",
    )
    parser.add_argument(
        "--windows",
        type=lambda value: {
            k: int(v)
            for k, v in (
                part.split(":", 1)
                for part in value.split(",")
                if part.strip()
            )
        },
        default=WINDOWS_MIN,
        help="Comma-separated window_key:minutes pairs.",
    )
    args = parser.parse_args()
    if args.exclude_anchor_short == "":
        args.exclude_anchor_short = None

    unknown = sorted(set(args.context_shorts) - set(SHORT_TO_DETECTOR))
    if unknown:
        raise KeyError(f"unknown context short names: {unknown}; choices={sorted(SHORT_TO_DETECTOR)}")

    out_path, schema_path, context_path, merged = build(args)
    n_xctx = sum(c.startswith("xctx.") for c in merged.columns)
    print(f"wrote {out_path}: {len(merged):,} rows x {len(merged.columns):,} cols")
    print(f"wrote {schema_path}")
    print(f"wrote {context_path}: {n_xctx:,} xctx feature cols")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
