"""Build state-aware FVG geometry context for snapshot matrices.

This is the first "level geometry" context layer. It answers questions like:

  - where is the nearest unfilled FVG above/below the anchor price?
  - is the nearest FVG untouched, tapped, midpoint-filled, fully-filled,
    or closed-through as of the anchor cutoff?
  - how old/wide is that nearby FVG?

Important: FVG final outcome labels are converted into state transition
timestamps before use. A state is only visible when its transition timestamp is
strictly earlier than the anchor feature cutoff.
"""

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

from snapshot_feature_registry import FVG_LAG_MIN, registry_as_dict  # noqa: E402

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
FEATURES_DIR = ROOT / "data" / "ml" / "features"
ANCHORS_DIR = ROOT / "data" / "ml" / "anchors"
CONTEXT_DIR = ROOT / "data" / "ml" / "context"
DEFAULT_FVG_FEATURES = FEATURES_DIR / "fvg.parquet"
DEFAULT_MATRIX = ANCHORS_DIR / "smt_previous_day_snapshots_xctx.parquet"
DEFAULT_SCHEMA = ANCHORS_DIR / "smt_previous_day_snapshots_xctx.schema.json"
DEFAULT_OUTPUT = ANCHORS_DIR / "smt_previous_day_snapshots_xctx_fvggeom.parquet"
DEFAULT_SCHEMA_OUTPUT = ANCHORS_DIR / "smt_previous_day_snapshots_xctx_fvggeom.schema.json"
DEFAULT_CONTEXT_OUTPUT = CONTEXT_DIR / "smt_previous_day_fvg_geometry_context.parquet"

NS_PER_MIN = 60 * 1_000_000_000
INF_NS = np.iinfo("int64").max
STATES = ("untouched", "tapped", "mid_filled", "fully_filled", "closed_through")
SIDES = ("any_side", "bullish", "bearish")
SCOPES = ("same_primary", "any_symbol")
RELATIONS = ("above", "below", "inside")
COUNT_THRESHOLDS = (10, 25, 50)

ANCHOR_PRICE_CANDIDATES = {
    "smt": ("smt.ed.first_break_price",),
    "fvg": ("fvg.ed.candle_3.close", "fvg.ed.fvg_mid"),
    "sweep": ("sweep.ed.manipulation_candle.close", "sweep.ed.swept_reference.level_price"),
    "ob": ("ob.ed.confirmation_candle.close", "ob.ed.ob_body_mid"),
    "tp": ("tp.ed.parent_close",),
    "vp": ("vp.ed.period_close", "vp.ed.vwap"),
}


def _parse_csv_arg(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


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
        "time_profile": "tp",
        "volume_profile": "vp",
    }
    return by_feature.get(feature)


def _infer_anchor_price_col(
    matrix: pd.DataFrame,
    schema: dict[str, Any],
    explicit: str | None,
) -> str:
    if explicit:
        if explicit not in matrix.columns:
            raise KeyError(f"explicit --anchor-price-col not in matrix: {explicit}")
        return explicit
    short = _infer_anchor_short(matrix, schema)
    for col in ANCHOR_PRICE_CANDIDATES.get(short or "", ()):
        if col in matrix.columns:
            return col
    raise KeyError(
        "could not infer anchor price column; pass --anchor-price-col. "
        f"inferred_short={short!r}"
    )


def _to_ns(s: pd.Series) -> np.ndarray:
    return pd.to_datetime(s, utc=True).to_numpy("datetime64[ns]").astype("int64")


def _transition_ns(
    knowable_ns: np.ndarray,
    bars: pd.Series,
    lag_min: pd.Series,
) -> np.ndarray:
    out = np.full(len(knowable_ns), INF_NS, dtype="int64")
    b = pd.to_numeric(bars, errors="coerce")
    valid = b.notna()
    if valid.any():
        idx = np.where(valid.to_numpy())[0]
        out[idx] = (
            knowable_ns[idx]
            + b.iloc[idx].astype("int64").to_numpy() * lag_min.iloc[idx].astype("int64").to_numpy() * NS_PER_MIN
        )
    return out


def _load_fvg_events(path: Path, *, max_age_days: int) -> pd.DataFrame:
    cols = [
        "event_id",
        "event_type",
        "bar_end_utc",
        "primary_symbol",
        "side",
        "ed.fvg_high",
        "ed.fvg_low",
        "ed.fvg_mid",
        "ed.fvg_width_pts",
        "oc.mitigation.bars_to_tap",
        "oc.mitigation.bars_to_mid",
        "oc.mitigation.bars_to_full",
        "oc.mitigation.bars_to_close_through",
        "oc.mitigation.horizon_bars",
    ]
    fvg = pd.read_parquet(path, columns=cols)
    fvg = fvg[fvg["event_type"].isin(FVG_LAG_MIN)].copy()
    fvg["bar_end_utc"] = pd.to_datetime(fvg["bar_end_utc"], utc=True)
    fvg["lag_min"] = fvg["event_type"].map(FVG_LAG_MIN).astype("int64")
    fvg["knowable_ts"] = fvg["bar_end_utc"] + pd.to_timedelta(fvg["lag_min"], unit="m")
    fvg["knowable_ns"] = _to_ns(fvg["knowable_ts"])
    fvg["tap_ns"] = _transition_ns(
        fvg["knowable_ns"].to_numpy(dtype="int64"),
        fvg["oc.mitigation.bars_to_tap"],
        fvg["lag_min"],
    )
    fvg["mid_ns"] = _transition_ns(
        fvg["knowable_ns"].to_numpy(dtype="int64"),
        fvg["oc.mitigation.bars_to_mid"],
        fvg["lag_min"],
    )
    fvg["full_ns"] = _transition_ns(
        fvg["knowable_ns"].to_numpy(dtype="int64"),
        fvg["oc.mitigation.bars_to_full"],
        fvg["lag_min"],
    )
    fvg["close_through_ns"] = _transition_ns(
        fvg["knowable_ns"].to_numpy(dtype="int64"),
        fvg["oc.mitigation.bars_to_close_through"],
        fvg["lag_min"],
    )
    horizon_bars = pd.to_numeric(fvg["oc.mitigation.horizon_bars"], errors="coerce").fillna(50)
    fvg["horizon_ns"] = (
        fvg["knowable_ns"].to_numpy(dtype="int64")
        + horizon_bars.astype("int64").to_numpy() * fvg["lag_min"].to_numpy(dtype="int64") * NS_PER_MIN
    )
    fvg["max_age_ns"] = max_age_days * 24 * 60 * NS_PER_MIN
    return fvg.sort_values("knowable_ns").reset_index(drop=True)


def _empty_feature_data(n: int) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for scope in SCOPES:
        for side in SIDES:
            for state in STATES:
                for relation in RELATIONS:
                    stem = f"{scope}_{side}_{state}_{relation}"
                    data[f"fvggeom.has_{stem}"] = np.zeros(n, dtype=bool)
                    data[f"fvggeom.distance_pts_{stem}"] = np.full(n, np.nan, dtype="float64")
                    data[f"fvggeom.age_min_{stem}"] = np.full(n, np.nan, dtype="float64")
                    data[f"fvggeom.width_pts_{stem}"] = np.full(n, np.nan, dtype="float64")
                for threshold in COUNT_THRESHOLDS:
                    data[f"fvggeom.n_{scope}_{side}_{state}_within_{threshold}pts"] = np.zeros(
                        n,
                        dtype=np.int16,
                    )
    return data


def _state_for_cutoff(events: pd.DataFrame, cutoff_ns: int) -> np.ndarray:
    state = np.full(len(events), "", dtype=object)
    close_through = events["close_through_ns"].to_numpy(dtype="int64") < cutoff_ns
    full = (~close_through) & (events["full_ns"].to_numpy(dtype="int64") < cutoff_ns)
    mid = (
        (~close_through)
        & (~full)
        & (events["mid_ns"].to_numpy(dtype="int64") < cutoff_ns)
        & (cutoff_ns <= events["horizon_ns"].to_numpy(dtype="int64"))
    )
    tapped = (
        (~close_through)
        & (~full)
        & (~mid)
        & (events["tap_ns"].to_numpy(dtype="int64") < cutoff_ns)
        & (cutoff_ns <= events["horizon_ns"].to_numpy(dtype="int64"))
    )
    untouched = (
        (~close_through)
        & (~full)
        & (~mid)
        & (~tapped)
        & (cutoff_ns <= events["horizon_ns"].to_numpy(dtype="int64"))
    )
    state[untouched] = "untouched"
    state[tapped] = "tapped"
    state[mid] = "mid_filled"
    state[full] = "fully_filled"
    state[close_through] = "closed_through"
    return state


def _zone_relation(price: float, low: np.ndarray, high: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    relation = np.full(len(low), "inside", dtype=object)
    distance = np.zeros(len(low), dtype="float64")
    above = price < low
    below = price > high
    relation[above] = "above"
    relation[below] = "below"
    distance[above] = low[above] - price
    distance[below] = price - high[below]
    return relation, distance


def _fill_combo(
    data: dict[str, Any],
    row_idx: int,
    *,
    scope: str,
    side: str,
    state: str,
    relation: str,
    mask: np.ndarray,
    distance: np.ndarray,
    age_min: np.ndarray,
    width: np.ndarray,
) -> None:
    if not mask.any():
        return
    masked_distance = distance[mask]
    nearest_local = int(np.nanargmin(masked_distance))
    idxs = np.where(mask)[0]
    idx = idxs[nearest_local]
    stem = f"{scope}_{side}_{state}_{relation}"
    data[f"fvggeom.has_{stem}"][row_idx] = True
    data[f"fvggeom.distance_pts_{stem}"][row_idx] = float(distance[idx])
    data[f"fvggeom.age_min_{stem}"][row_idx] = float(age_min[idx])
    data[f"fvggeom.width_pts_{stem}"][row_idx] = float(width[idx])


def _fill_counts(
    data: dict[str, Any],
    row_idx: int,
    *,
    scope: str,
    side: str,
    state: str,
    mask: np.ndarray,
    distance: np.ndarray,
) -> None:
    if not mask.any():
        return
    d = distance[mask]
    for threshold in COUNT_THRESHOLDS:
        data[f"fvggeom.n_{scope}_{side}_{state}_within_{threshold}pts"][row_idx] = int(
            np.sum(d <= threshold)
        )


def build_context(
    matrix: pd.DataFrame,
    *,
    schema: dict[str, Any],
    fvg: pd.DataFrame,
    anchor_price_col: str,
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
        "fvggeom.anchor_price": pd.to_numeric(matrix[anchor_price_col], errors="coerce").to_numpy(dtype="float64"),
    }
    data.update(_empty_feature_data(n))

    cutoff_ns = _to_ns(pd.to_datetime(matrix["asof.feature_cutoff_ts"], utc=True))
    prices = data["fvggeom.anchor_price"]
    symbols = matrix["anchor.primary_symbol"].astype(str).to_numpy()

    fvg_knowable = fvg["knowable_ns"].to_numpy(dtype="int64")
    fvg_low = fvg["ed.fvg_low"].to_numpy(dtype="float64")
    fvg_high = fvg["ed.fvg_high"].to_numpy(dtype="float64")
    fvg_width = fvg["ed.fvg_width_pts"].to_numpy(dtype="float64")
    fvg_symbol = fvg["primary_symbol"].astype(str).to_numpy()
    fvg_side = fvg["side"].astype(str).to_numpy()
    tap_ns = fvg["tap_ns"].to_numpy(dtype="int64")
    mid_ns = fvg["mid_ns"].to_numpy(dtype="int64")
    full_ns = fvg["full_ns"].to_numpy(dtype="int64")
    close_through_ns = fvg["close_through_ns"].to_numpy(dtype="int64")
    horizon_ns = fvg["horizon_ns"].to_numpy(dtype="int64")
    max_age_ns = max_age_days * 24 * 60 * NS_PER_MIN

    for i, (cutoff, price, symbol) in enumerate(zip(cutoff_ns, prices, symbols, strict=True)):
        if not np.isfinite(price):
            continue
        start = np.searchsorted(fvg_knowable, cutoff - max_age_ns, side="left")
        end = np.searchsorted(fvg_knowable, cutoff, side="left")
        if end <= start:
            continue
        row_slice = slice(start, end)
        cutoff_int = int(cutoff)

        close_through = close_through_ns[row_slice] < cutoff_int
        full = (~close_through) & (full_ns[row_slice] < cutoff_int)
        mid = (
            (~close_through)
            & (~full)
            & (mid_ns[row_slice] < cutoff_int)
            & (cutoff_int <= horizon_ns[row_slice])
        )
        tapped = (
            (~close_through)
            & (~full)
            & (~mid)
            & (tap_ns[row_slice] < cutoff_int)
            & (cutoff_int <= horizon_ns[row_slice])
        )
        untouched = (
            (~close_through)
            & (~full)
            & (~mid)
            & (~tapped)
            & (cutoff_int <= horizon_ns[row_slice])
        )

        state_code = np.full(end - start, -1, dtype=np.int8)
        state_code[untouched] = 0
        state_code[tapped] = 1
        state_code[mid] = 2
        state_code[full] = 3
        state_code[close_through] = 4
        known = state_code >= 0
        if not known.any():
            continue

        low = fvg_low[row_slice]
        high = fvg_high[row_slice]
        width = fvg_width[row_slice]
        relation_code = np.full(end - start, 2, dtype=np.int8)
        distance = np.zeros(end - start, dtype="float64")
        above = price < low
        below = price > high
        relation_code[above] = 0
        relation_code[below] = 1
        distance[above] = low[above] - price
        distance[below] = price - high[below]
        age_min = (cutoff - fvg_knowable[row_slice]) / NS_PER_MIN

        scope_masks = (
            ("same_primary", fvg_symbol[row_slice] == symbol),
            ("any_symbol", None),
        )
        side_masks = (
            ("any_side", None),
            ("bullish", fvg_side[row_slice] == "bullish"),
            ("bearish", fvg_side[row_slice] == "bearish"),
        )
        for scope, scope_mask in scope_masks:
            for side, side_mask in side_masks:
                for state_idx, state_name in enumerate(STATES):
                    base_mask = known & (state_code == state_idx)
                    if scope_mask is not None:
                        base_mask = base_mask & scope_mask
                    if side_mask is not None:
                        base_mask = base_mask & side_mask
                    base_idx = np.flatnonzero(base_mask)
                    if len(base_idx) == 0:
                        continue

                    base_distance = distance[base_idx]
                    for threshold in COUNT_THRESHOLDS:
                        data[f"fvggeom.n_{scope}_{side}_{state_name}_within_{threshold}pts"][i] = int(
                            np.count_nonzero(base_distance <= threshold)
                        )

                    for rel_idx, rel in enumerate(RELATIONS):
                        rel_matches = base_idx[relation_code[base_idx] == rel_idx]
                        if len(rel_matches) == 0:
                            continue
                        pick = rel_matches[int(np.argmin(distance[rel_matches]))]
                        stem = f"{scope}_{side}_{state_name}_{rel}"
                        data[f"fvggeom.has_{stem}"][i] = True
                        data[f"fvggeom.distance_pts_{stem}"][i] = float(distance[pick])
                        data[f"fvggeom.age_min_{stem}"][i] = float(age_min[pick])
                        data[f"fvggeom.width_pts_{stem}"][i] = float(width[pick])

    return pd.DataFrame(data)


def _write_schema(
    schema_output: Path,
    *,
    source_schema: Path,
    matrix: pd.DataFrame,
    context_cols: list[str],
    args: argparse.Namespace,
    anchor_price_col: str,
) -> None:
    schema = json.loads(source_schema.read_text(encoding="utf-8"))
    old_features = list(schema.get("feature_columns", []))
    merged_features = [*old_features, *[c for c in context_cols if c not in old_features]]
    schema.update(
        {
            "generated_utc": datetime.now(UTC).isoformat(),
            "builder": "backend/scripts/ml/build_fvg_geometry_context.py",
            "source_schema": str(source_schema),
            "source_matrix": str(args.matrix),
            "rows": int(len(matrix)),
            "feature_columns": merged_features,
            "registry": registry_as_dict(),
            "fvg_geometry_context": {
                "fvg_features": str(args.fvg_features),
                "anchor_price_col": anchor_price_col,
                "max_age_days": args.max_age_days,
                "states": list(STATES),
                "scopes": list(SCOPES),
                "sides": list(SIDES),
                "relations": list(RELATIONS),
                "count_thresholds_pts": list(COUNT_THRESHOLDS),
                "context_columns": context_cols,
                "state_timing_note": (
                    "FVG bars_to_* outcomes are converted to conservative "
                    "bar-close knowable timestamps before state assignment."
                ),
            },
            "notes": [
                *schema.get("notes", []),
                "fvggeom.* features are state-aware FVG zone geometry known before the snapshot cutoff.",
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

    anchor_price_col = _infer_anchor_price_col(matrix, schema, args.anchor_price_col)
    fvg = _load_fvg_events(args.fvg_features, max_age_days=args.max_age_days)
    context = build_context(
        matrix,
        schema=schema,
        fvg=fvg,
        anchor_price_col=anchor_price_col,
        max_age_days=args.max_age_days,
    )
    context_cols = [c for c in context.columns if c.startswith("fvggeom.")]
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
        anchor_price_col=anchor_price_col,
    )
    return args.output, args.schema_output, args.context_output, merged


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--schema-output", type=Path, default=DEFAULT_SCHEMA_OUTPUT)
    parser.add_argument("--context-output", type=Path, default=DEFAULT_CONTEXT_OUTPUT)
    parser.add_argument("--fvg-features", type=Path, default=DEFAULT_FVG_FEATURES)
    parser.add_argument("--anchor-price-col", default=None)
    parser.add_argument("--event-type", default="all")
    parser.add_argument("--side", default="all")
    parser.add_argument("--max-age-days", type=int, default=30)
    args = parser.parse_args()
    out_path, schema_path, context_path, merged = build(args)
    n_geom = sum(c.startswith("fvggeom.") for c in merged.columns)
    print(f"wrote {out_path}: {len(merged):,} rows x {len(merged.columns):,} cols")
    print(f"wrote {schema_path}")
    print(f"wrote {context_path}: {n_geom:,} fvggeom feature cols")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
