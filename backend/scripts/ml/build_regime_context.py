"""Build completed interval true-range regime context for snapshot matrices."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from snapshot_feature_registry import registry_as_dict  # noqa: E402

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
FEATURES_DIR = ROOT / "data" / "ml" / "features"
ANCHORS_DIR = ROOT / "data" / "ml" / "anchors"
CONTEXT_DIR = ROOT / "data" / "ml" / "context"
DEFAULT_ITR_FEATURES = FEATURES_DIR / "itr.parquet"
DEFAULT_MATRIX = ANCHORS_DIR / "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom.parquet"
DEFAULT_SCHEMA = ANCHORS_DIR / "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom.schema.json"
DEFAULT_OUTPUT = ANCHORS_DIR / "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.parquet"
DEFAULT_SCHEMA_OUTPUT = ANCHORS_DIR / "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime.schema.json"
DEFAULT_CONTEXT_OUTPUT = CONTEXT_DIR / "sweep_regime_context.parquet"

NS_PER_MIN = 60 * 1_000_000_000
REGIME_TYPES = ("any_itr", "asia_itr", "london_itr", "ny_itr", "daily_itr", "weekly_itr")
SCOPES = ("same_primary", "any_symbol")


def _infer_anchor_short(matrix: pd.DataFrame, schema: dict[str, Any]) -> str | None:
    if "anchor.short_name" in matrix.columns:
        vals = matrix["anchor.short_name"].dropna().unique()
        if len(vals) == 1:
            return str(vals[0])
    anchor = schema.get("anchor") or {}
    short = anchor.get("short_name")
    if short:
        return str(short)
    feature = anchor.get("feature_name")
    by_feature = {
        "smt_htf_reference_divergence": "smt",
        "fvg_formation": "fvg",
        "liquidity_sweep": "sweep",
        "order_block": "ob",
        "displacement_candle": "disp",
        "psp_candle_divergence": "psp",
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
    return by_feature.get(feature)


def _to_ns(series: pd.Series) -> np.ndarray:
    return pd.to_datetime(series, utc=True).to_numpy("datetime64[ns]").astype("int64")


def _load_itr_events(path: Path) -> pd.DataFrame:
    cols = [
        "event_id",
        "event_type",
        "bar_end_utc",
        "primary_symbol",
        "side",
        "ed.interval_kind",
        "ed.session_name",
        "ed.interval_range_pts",
        "ed.interval_true_range_pts",
        "ed.interval_close_location",
        "ed.interval_direction",
        "ed.range_percentile_vs_prev_10_intervals",
        "ed.is_expansion_vs_prev_10_intervals",
        "ed.is_compression_vs_prev_10_intervals",
    ]
    itr = pd.read_parquet(path, columns=cols).copy()
    itr = itr[itr["event_type"].isin(REGIME_TYPES[1:])].copy()
    itr["bar_end_utc"] = pd.to_datetime(itr["bar_end_utc"], utc=True)
    # ITR event bars are timestamped at the final minute of the interval;
    # add one minute so the closed interval is not visible early.
    itr["knowable_ns"] = _to_ns(itr["bar_end_utc"] + pd.to_timedelta(1, unit="m"))
    itr["range_pts"] = pd.to_numeric(itr["ed.interval_range_pts"], errors="coerce").astype("float32")
    itr["true_range_pts"] = pd.to_numeric(itr["ed.interval_true_range_pts"], errors="coerce").astype("float32")
    itr["close_location"] = pd.to_numeric(itr["ed.interval_close_location"], errors="coerce").astype("float32")
    itr["range_percentile_prev10"] = pd.to_numeric(
        itr["ed.range_percentile_vs_prev_10_intervals"],
        errors="coerce",
    ).astype("float32")
    itr["is_expansion"] = (
        pd.to_numeric(itr["ed.is_expansion_vs_prev_10_intervals"], errors="coerce").fillna(0).astype("int8")
    )
    itr["is_compression"] = (
        pd.to_numeric(itr["ed.is_compression_vs_prev_10_intervals"], errors="coerce").fillna(0).astype("int8")
    )
    itr["direction"] = itr["ed.interval_direction"].astype(str)
    return itr.sort_values("knowable_ns").reset_index(drop=True)


def _empty_feature_data(n: int) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for scope in SCOPES:
        for regime_type in REGIME_TYPES:
            stem = f"{scope}_{regime_type}"
            data[f"regime.has_last_{stem}"] = np.zeros(n, dtype=bool)
            data[f"regime.minutes_since_last_{stem}"] = np.full(n, np.nan, dtype="float32")
            data[f"regime.last_range_pts_{stem}"] = np.full(n, np.nan, dtype="float32")
            data[f"regime.last_true_range_pts_{stem}"] = np.full(n, np.nan, dtype="float32")
            data[f"regime.last_close_location_{stem}"] = np.full(n, np.nan, dtype="float32")
            data[f"regime.last_range_percentile_prev10_{stem}"] = np.full(n, np.nan, dtype="float32")
            data[f"regime.last_direction_bullish_{stem}"] = np.zeros(n, dtype=bool)
            data[f"regime.last_direction_bearish_{stem}"] = np.zeros(n, dtype=bool)
            data[f"regime.last_is_expansion_{stem}"] = np.zeros(n, dtype=bool)
            data[f"regime.last_is_compression_{stem}"] = np.zeros(n, dtype=bool)
            data[f"regime.n_completed_24h_{stem}"] = np.zeros(n, dtype=np.int16)
            data[f"regime.n_expansion_7d_{stem}"] = np.zeros(n, dtype=np.int16)
            data[f"regime.n_compression_7d_{stem}"] = np.zeros(n, dtype=np.int16)
    return data


def _fill_last(
    data: dict[str, Any],
    row_idx: int,
    *,
    scope: str,
    regime_type: str,
    rows: pd.DataFrame,
    cutoff_ns: int,
) -> None:
    if rows.empty:
        return
    last = rows.iloc[-1]
    stem = f"{scope}_{regime_type}"
    data[f"regime.has_last_{stem}"][row_idx] = True
    data[f"regime.minutes_since_last_{stem}"][row_idx] = float((cutoff_ns - int(last["knowable_ns"])) / NS_PER_MIN)
    data[f"regime.last_range_pts_{stem}"][row_idx] = float(last["range_pts"])
    data[f"regime.last_true_range_pts_{stem}"][row_idx] = float(last["true_range_pts"])
    data[f"regime.last_close_location_{stem}"][row_idx] = float(last["close_location"])
    data[f"regime.last_range_percentile_prev10_{stem}"][row_idx] = float(last["range_percentile_prev10"])
    data[f"regime.last_direction_bullish_{stem}"][row_idx] = str(last["direction"]) == "bullish"
    data[f"regime.last_direction_bearish_{stem}"][row_idx] = str(last["direction"]) == "bearish"
    data[f"regime.last_is_expansion_{stem}"][row_idx] = bool(last["is_expansion"])
    data[f"regime.last_is_compression_{stem}"][row_idx] = bool(last["is_compression"])


def build_context(
    matrix: pd.DataFrame,
    *,
    itr: pd.DataFrame,
    max_age_days: int,
) -> pd.DataFrame:
    required = ["anchor.event_id", "asof.snapshot", "asof.feature_cutoff_ts", "anchor.primary_symbol"]
    missing = [c for c in required if c not in matrix.columns]
    if missing:
        raise KeyError(f"matrix missing required columns: {missing}")

    n = len(matrix)
    data = {
        "anchor.event_id": matrix["anchor.event_id"].to_numpy(),
        "asof.snapshot": matrix["asof.snapshot"].to_numpy(),
    }
    data.update(_empty_feature_data(n))

    cutoff_ns = _to_ns(matrix["asof.feature_cutoff_ts"])
    symbols = matrix["anchor.primary_symbol"].astype(str).to_numpy()
    knowable = itr["knowable_ns"].to_numpy(dtype="int64")
    itr_symbol = itr["primary_symbol"].astype(str).to_numpy()
    itr_type = itr["event_type"].astype(str).to_numpy()
    max_age_ns = max_age_days * 24 * 60 * NS_PER_MIN
    day_ns = 24 * 60 * NS_PER_MIN
    week_ns = 7 * day_ns

    for i, (cutoff, symbol) in enumerate(zip(cutoff_ns, symbols, strict=True)):
        start = np.searchsorted(knowable, cutoff - max_age_ns, side="left")
        end = np.searchsorted(knowable, cutoff, side="left")
        if end <= start:
            continue
        idx = np.arange(start, end)
        rows = itr.iloc[idx]
        same_primary = itr_symbol[idx] == symbol
        for scope in SCOPES:
            scope_mask = same_primary if scope == "same_primary" else np.ones(len(idx), dtype=bool)
            if not scope_mask.any():
                continue
            for regime_type in REGIME_TYPES:
                type_mask = np.ones(len(idx), dtype=bool) if regime_type == "any_itr" else (itr_type[idx] == regime_type)
                mask = scope_mask & type_mask
                if not mask.any():
                    continue
                sub = rows.iloc[np.where(mask)[0]]
                _fill_last(
                    data,
                    i,
                    scope=scope,
                    regime_type=regime_type,
                    rows=sub,
                    cutoff_ns=int(cutoff),
                )
                recent_24h = sub["knowable_ns"].to_numpy(dtype="int64") >= cutoff - day_ns
                recent_7d = sub["knowable_ns"].to_numpy(dtype="int64") >= cutoff - week_ns
                stem = f"{scope}_{regime_type}"
                data[f"regime.n_completed_24h_{stem}"][i] = int(np.sum(recent_24h))
                data[f"regime.n_expansion_7d_{stem}"][i] = int(
                    np.sum(sub["is_expansion"].to_numpy(dtype="int8")[recent_7d] == 1)
                )
                data[f"regime.n_compression_7d_{stem}"][i] = int(
                    np.sum(sub["is_compression"].to_numpy(dtype="int8")[recent_7d] == 1)
                )

    return pd.DataFrame(data)


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
            "builder": "backend/scripts/ml/build_regime_context.py",
            "source_schema": str(source_schema),
            "source_matrix": str(args.matrix),
            "rows": int(len(matrix)),
            "feature_columns": merged_features,
            "registry": registry_as_dict(),
            "regime_context": {
                "itr_features": str(args.itr_features),
                "max_age_days": args.max_age_days,
                "regime_types": list(REGIME_TYPES),
                "scopes": list(SCOPES),
                "context_columns": context_cols,
                "state_timing_note": (
                    "ITR intervals are visible only after the interval has closed; "
                    "bar_end_utc is shifted by one minute before features are assigned."
                ),
            },
            "notes": [
                *schema.get("notes", []),
                "regime.* features summarize completed session/day/week range regime known before the snapshot cutoff.",
            ],
        }
    )
    schema_output.parent.mkdir(parents=True, exist_ok=True)
    schema_output.write_text(json.dumps(schema, indent=2), encoding="utf-8")


def build(args: argparse.Namespace) -> tuple[Path, Path, Path, pd.DataFrame]:
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    matrix = pd.read_parquet(args.matrix)
    if args.event_type != "all":
        matrix = matrix[matrix["anchor.event_type"].eq(args.event_type)].copy()
    if args.side != "all":
        matrix = matrix[matrix["anchor.side"].eq(args.side)].copy()
    if matrix.empty:
        raise ValueError("no matrix rows after filters")

    _infer_anchor_short(matrix, schema)  # Keeps schema inference failures visible during debugging.
    itr = _load_itr_events(args.itr_features)
    context = build_context(matrix, itr=itr, max_age_days=args.max_age_days)
    context_cols = [c for c in context.columns if c.startswith("regime.")]
    merged = matrix.merge(
        context,
        on=["anchor.event_id", "asof.snapshot"],
        how="left",
        validate="one_to_one",
    )
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
    parser.add_argument("--itr-features", type=Path, default=DEFAULT_ITR_FEATURES)
    parser.add_argument("--event-type", default="all")
    parser.add_argument("--side", default="all")
    parser.add_argument("--max-age-days", type=int, default=30)
    args = parser.parse_args()
    out_path, schema_path, context_path, merged = build(args)
    n_regime = sum(c.startswith("regime.") for c in merged.columns)
    print(f"wrote {out_path}: {len(merged):,} rows x {len(merged.columns):,} cols")
    print(f"wrote {schema_path}")
    print(f"wrote {context_path}: {n_regime:,} regime feature cols")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
