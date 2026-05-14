"""Build state-aware order-block geometry context for snapshot matrices.

The generated `obgeom.*` features answer questions like:

  - where is the nearest active OB zone above/below/around the anchor price?
  - is that OB fresh, entry-tapped, body-touched, body-filled, or invalidated
    as of the anchor feature cutoff?
  - how old/wide/deeply retested is that nearby OB?

Important: OB final outcome fields are converted into transition timestamps
before use. A state is only visible when its transition timestamp is strictly
earlier than the anchor feature cutoff. Untapped/tapped-but-not-final states
expire after the reaction horizon because later state is unknown from the v1
outcome window.
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

from snapshot_feature_registry import OB_LAG_MIN, registry_as_dict  # noqa: E402

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
FEATURES_DIR = ROOT / "data" / "ml" / "features"
ANCHORS_DIR = ROOT / "data" / "ml" / "anchors"
CONTEXT_DIR = ROOT / "data" / "ml" / "context"
DEFAULT_OB_FEATURES = FEATURES_DIR / "ob.parquet"
DEFAULT_MATRIX = ANCHORS_DIR / "sweep_snapshots_xctx_fvggeom.parquet"
DEFAULT_SCHEMA = ANCHORS_DIR / "sweep_snapshots_xctx_fvggeom.schema.json"
DEFAULT_OUTPUT = ANCHORS_DIR / "sweep_snapshots_xctx_fvggeom_obgeom.parquet"
DEFAULT_SCHEMA_OUTPUT = ANCHORS_DIR / "sweep_snapshots_xctx_fvggeom_obgeom.schema.json"
DEFAULT_CONTEXT_OUTPUT = CONTEXT_DIR / "sweep_ob_geometry_context.parquet"

NS_PER_MIN = 60 * 1_000_000_000
INF_NS = np.iinfo("int64").max
REACTION_HORIZON_BARS = 50
STATES = ("fresh", "entry_tapped", "body_touched", "body_filled", "invalidated")
SIDES = ("any_side", "bullish", "bearish")
SCOPES = ("same_primary", "any_symbol")
RELATIONS = ("above", "below", "inside")
COUNT_THRESHOLDS = (10, 25, 50, 100)
DEPTH_LEVELS = (
    ("open", 0.0),
    ("q25", 0.25),
    ("q50", 0.50),
    ("q75", 0.75),
    ("close", 1.0),
    ("range_far", 1.25),
)

ANCHOR_PRICE_CANDIDATES = {
    "smt": ("smt.ed.first_break_price",),
    "fvg": ("fvg.ed.candle_3.close", "fvg.ed.fvg_mid"),
    "sweep": ("sweep.ed.manipulation_candle.close", "sweep.ed.swept_reference.level_price"),
    "ob": ("ob.ed.confirmation_candle.close", "ob.ed.ob_body_mid"),
    "disp": ("disp.ed.candle.close", "disp.ed.close"),
    "psp": ("psp.ed.primary.close", "psp.ed.primary_close"),
    "tp": ("tp.ed.parent_close",),
    "vp": ("vp.ed.period_close", "vp.ed.vwap"),
    "fvp": ("fvp.ed.asof_close", "fvp.ed.vwap"),
    "ogap": ("ogap.ed.current_open_price", "ogap.ed.gap_mid"),
    "itr": ("itr.ed.close", "itr.ed.mid"),
    "macro": ("macro.ed.pre_release.close", "macro.ed.pre_close"),
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
        "displacement_candle": "disp",
        "psp_candle_divergence": "psp",
        "time_profile": "tp",
        "volume_profile": "vp",
        "forming_volume_profile": "fvp",
        "opening_gap_levels": "ogap",
        "interval_true_range": "itr",
        "macro_event": "macro",
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
    for col in ANCHOR_PRICE_CANDIDATES.get(short or "", ()):  # pragma: no branch
        if col in matrix.columns:
            return col
    raise KeyError(
        "could not infer anchor price column; pass --anchor-price-col. "
        f"inferred_short={short!r}"
    )



def _to_ns(series: pd.Series) -> np.ndarray:
    return pd.to_datetime(series, utc=True).to_numpy("datetime64[ns]").astype("int64")



def _transition_ns(knowable_ns: np.ndarray, bars: pd.Series, lag_min: pd.Series) -> np.ndarray:
    out = np.full(len(knowable_ns), INF_NS, dtype="int64")
    b = pd.to_numeric(bars, errors="coerce")
    valid = b.notna()
    if valid.any():
        idx = np.where(valid.to_numpy())[0]
        out[idx] = (
            knowable_ns[idx]
            + b.iloc[idx].astype("int64").to_numpy()
            * lag_min.iloc[idx].astype("int64").to_numpy()
            * NS_PER_MIN
        )
    return out



def _load_ob_events(path: Path, *, max_age_days: int) -> pd.DataFrame:
    cols = [
        "event_id",
        "event_type",
        "bar_end_utc",
        "primary_symbol",
        "side",
        "ed.ob_body_top",
        "ed.ob_body_bottom",
        "ed.ob_body_mid",
        "ed.ob_body_width_pts",
        "ed.ob_range_top",
        "ed.ob_range_bottom",
        "ed.ob_range_width_pts",
        "oc.level_tags.open.bars_to_wick_tap",
        "oc.level_tags.q25.bars_to_wick_tap",
        "oc.level_tags.q50.bars_to_wick_tap",
        "oc.level_tags.q75.bars_to_wick_tap",
        "oc.level_tags.close.bars_to_wick_tap",
        "oc.level_tags.range_far.bars_to_wick_tap",
        "oc.invalidation.bars_to_invalidation",
    ]
    ob = pd.read_parquet(path, columns=cols)
    ob = ob[ob["event_type"].isin(OB_LAG_MIN) & ob["side"].isin(("bullish", "bearish"))].copy()
    ob["bar_end_utc"] = pd.to_datetime(ob["bar_end_utc"], utc=True)
    ob["lag_min"] = ob["event_type"].map(OB_LAG_MIN).astype("int64")
    ob["knowable_ts"] = ob["bar_end_utc"] + pd.to_timedelta(ob["lag_min"], unit="m")
    ob["knowable_ns"] = _to_ns(ob["knowable_ts"])
    knowable = ob["knowable_ns"].to_numpy(dtype="int64")
    for level, _ in DEPTH_LEVELS:
        ob[f"{level}_tap_ns"] = _transition_ns(
            knowable,
            ob[f"oc.level_tags.{level}.bars_to_wick_tap"],
            ob["lag_min"],
        )
    ob["invalidated_ns"] = _transition_ns(
        knowable,
        ob["oc.invalidation.bars_to_invalidation"],
        ob["lag_min"],
    )
    ob["horizon_ns"] = knowable + REACTION_HORIZON_BARS * ob["lag_min"].to_numpy(dtype="int64") * NS_PER_MIN
    ob["max_age_ns"] = max_age_days * 24 * 60 * NS_PER_MIN
    return ob.sort_values("knowable_ns").reset_index(drop=True)



def _empty_feature_data(n: int) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for scope in SCOPES:
        for side in SIDES:
            for state in STATES:
                for relation in RELATIONS:
                    stem = f"{scope}_{side}_{state}_{relation}"
                    data[f"obgeom.has_{stem}"] = np.zeros(n, dtype=bool)
                    data[f"obgeom.distance_pts_{stem}"] = np.full(n, np.nan, dtype="float64")
                    data[f"obgeom.age_min_{stem}"] = np.full(n, np.nan, dtype="float64")
                    data[f"obgeom.body_width_pts_{stem}"] = np.full(n, np.nan, dtype="float64")
                    data[f"obgeom.range_width_pts_{stem}"] = np.full(n, np.nan, dtype="float64")
                    data[f"obgeom.tap_depth_frac_{stem}"] = np.full(n, np.nan, dtype="float64")
                for threshold in COUNT_THRESHOLDS:
                    data[f"obgeom.n_{scope}_{side}_{state}_within_{threshold}pts"] = np.zeros(
                        n,
                        dtype=np.int16,
                    )
    return data



def _tap_depth_for_cutoff(events: pd.DataFrame, cutoff_ns: int) -> np.ndarray:
    depth = np.zeros(len(events), dtype="float64")
    for level, frac in DEPTH_LEVELS:
        reached = events[f"{level}_tap_ns"].to_numpy(dtype="int64") < cutoff_ns
        depth[reached] = np.maximum(depth[reached], frac)
    return depth



def _state_for_cutoff(events: pd.DataFrame, cutoff_ns: int) -> np.ndarray:
    invalidated = events["invalidated_ns"].to_numpy(dtype="int64") < cutoff_ns
    body_filled = (
        ~invalidated
        & (
            (events["close_tap_ns"].to_numpy(dtype="int64") < cutoff_ns)
            | (events["range_far_tap_ns"].to_numpy(dtype="int64") < cutoff_ns)
        )
    )
    within_horizon = cutoff_ns <= events["horizon_ns"].to_numpy(dtype="int64")
    body_touched = (
        ~invalidated
        & ~body_filled
        & within_horizon
        & (
            (events["q25_tap_ns"].to_numpy(dtype="int64") < cutoff_ns)
            | (events["q50_tap_ns"].to_numpy(dtype="int64") < cutoff_ns)
            | (events["q75_tap_ns"].to_numpy(dtype="int64") < cutoff_ns)
        )
    )
    entry_tapped = (
        ~invalidated
        & ~body_filled
        & ~body_touched
        & within_horizon
        & (events["open_tap_ns"].to_numpy(dtype="int64") < cutoff_ns)
    )
    fresh = (
        ~invalidated
        & ~body_filled
        & ~body_touched
        & ~entry_tapped
        & within_horizon
    )

    state = np.full(len(events), "", dtype=object)
    state[fresh] = "fresh"
    state[entry_tapped] = "entry_tapped"
    state[body_touched] = "body_touched"
    state[body_filled] = "body_filled"
    state[invalidated] = "invalidated"
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
    body_width: np.ndarray,
    range_width: np.ndarray,
    tap_depth: np.ndarray,
) -> None:
    if not mask.any():
        return
    masked_distance = distance[mask]
    nearest_local = int(np.nanargmin(masked_distance))
    idxs = np.where(mask)[0]
    idx = idxs[nearest_local]
    stem = f"{scope}_{side}_{state}_{relation}"
    data[f"obgeom.has_{stem}"][row_idx] = True
    data[f"obgeom.distance_pts_{stem}"][row_idx] = float(distance[idx])
    data[f"obgeom.age_min_{stem}"][row_idx] = float(age_min[idx])
    data[f"obgeom.body_width_pts_{stem}"][row_idx] = float(body_width[idx])
    data[f"obgeom.range_width_pts_{stem}"][row_idx] = float(range_width[idx])
    data[f"obgeom.tap_depth_frac_{stem}"][row_idx] = float(tap_depth[idx])



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
        data[f"obgeom.n_{scope}_{side}_{state}_within_{threshold}pts"][row_idx] = int(
            np.sum(d <= threshold)
        )



def build_context(
    matrix: pd.DataFrame,
    *,
    schema: dict[str, Any],
    ob: pd.DataFrame,
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
        "obgeom.anchor_price": pd.to_numeric(matrix[anchor_price_col], errors="coerce").to_numpy(dtype="float64"),
    }
    data.update(_empty_feature_data(n))

    cutoff_ns = _to_ns(pd.to_datetime(matrix["asof.feature_cutoff_ts"], utc=True))
    prices = data["obgeom.anchor_price"]
    symbols = matrix["anchor.primary_symbol"].astype(str).to_numpy()

    ob_knowable = ob["knowable_ns"].to_numpy(dtype="int64")
    ob_low = ob["ed.ob_range_bottom"].to_numpy(dtype="float64")
    ob_high = ob["ed.ob_range_top"].to_numpy(dtype="float64")
    ob_body_width = ob["ed.ob_body_width_pts"].to_numpy(dtype="float64")
    ob_range_width = ob["ed.ob_range_width_pts"].to_numpy(dtype="float64")
    ob_symbol = ob["primary_symbol"].astype(str).to_numpy()
    ob_side = ob["side"].astype(str).to_numpy()
    max_age_ns = max_age_days * 24 * 60 * NS_PER_MIN

    for i, (cutoff, price, symbol) in enumerate(zip(cutoff_ns, prices, symbols, strict=True)):
        if not np.isfinite(price):
            continue
        start = np.searchsorted(ob_knowable, cutoff - max_age_ns, side="left")
        end = np.searchsorted(ob_knowable, cutoff, side="left")
        if end <= start:
            continue
        idx = np.arange(start, end)
        events = ob.iloc[idx]
        state = _state_for_cutoff(events, int(cutoff))
        known = state != ""
        if not known.any():
            continue

        low = ob_low[idx]
        high = ob_high[idx]
        body_width = ob_body_width[idx]
        range_width = ob_range_width[idx]
        relation, distance = _zone_relation(float(price), low, high)
        age_min = (cutoff - ob_knowable[idx]) / NS_PER_MIN
        tap_depth = _tap_depth_for_cutoff(events, int(cutoff))
        same_primary = ob_symbol[idx] == symbol

        for scope in SCOPES:
            scope_mask = same_primary if scope == "same_primary" else np.ones(len(idx), dtype=bool)
            for side in SIDES:
                side_mask = np.ones(len(idx), dtype=bool) if side == "any_side" else (ob_side[idx] == side)
                for state_name in STATES:
                    state_mask = state == state_name
                    base_mask = known & scope_mask & side_mask & state_mask
                    _fill_counts(
                        data,
                        i,
                        scope=scope,
                        side=side,
                        state=state_name,
                        mask=base_mask,
                        distance=distance,
                    )
                    for rel in RELATIONS:
                        rel_mask = relation == rel
                        _fill_combo(
                            data,
                            i,
                            scope=scope,
                            side=side,
                            state=state_name,
                            relation=rel,
                            mask=base_mask & rel_mask,
                            distance=distance,
                            age_min=age_min,
                            body_width=body_width,
                            range_width=range_width,
                            tap_depth=tap_depth,
                        )

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
            "builder": "backend/scripts/ml/build_ob_geometry_context.py",
            "source_schema": str(source_schema),
            "source_matrix": str(args.matrix),
            "rows": int(len(matrix)),
            "feature_columns": merged_features,
            "registry": registry_as_dict(),
            "ob_geometry_context": {
                "ob_features": str(args.ob_features),
                "anchor_price_col": anchor_price_col,
                "max_age_days": args.max_age_days,
                "reaction_horizon_bars": REACTION_HORIZON_BARS,
                "states": list(STATES),
                "scopes": list(SCOPES),
                "sides": list(SIDES),
                "relations": list(RELATIONS),
                "count_thresholds_pts": list(COUNT_THRESHOLDS),
                "depth_levels": dict(DEPTH_LEVELS),
                "context_columns": context_cols,
                "state_timing_note": (
                    "OB bars_to_* outcomes are converted to conservative "
                    "bar-close knowable timestamps before state assignment; "
                    "fresh/entry/body_touched states expire after the v1 reaction horizon."
                ),
            },
            "notes": [
                *schema.get("notes", []),
                "obgeom.* features are state-aware order-block zone geometry known before the snapshot cutoff.",
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
    ob = _load_ob_events(args.ob_features, max_age_days=args.max_age_days)
    context = build_context(
        matrix,
        schema=schema,
        ob=ob,
        anchor_price_col=anchor_price_col,
        max_age_days=args.max_age_days,
    )
    context_cols = [c for c in context.columns if c.startswith("obgeom.")]
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
    parser.add_argument("--ob-features", type=Path, default=DEFAULT_OB_FEATURES)
    parser.add_argument("--anchor-price-col", default=None)
    parser.add_argument("--event-type", default="all")
    parser.add_argument("--side", default="all")
    parser.add_argument("--max-age-days", type=int, default=30)
    args = parser.parse_args()
    out_path, schema_path, context_path, merged = build(args)
    n_geom = sum(c.startswith("obgeom.") for c in merged.columns)
    print(f"wrote {out_path}: {len(merged):,} rows x {len(merged.columns):,} cols")
    print(f"wrote {schema_path}")
    print(f"wrote {context_path}: {n_geom:,} obgeom feature cols")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
