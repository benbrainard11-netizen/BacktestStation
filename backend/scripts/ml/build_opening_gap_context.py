"""Build state-aware NDOG/NWOG memory context for snapshot matrices.

The generated `gapctx.*` features use only gaps created before the anchor
feature cutoff. Fill/touch state is also evaluated as-of the cutoff using
transition timestamps from opening-gap outcomes.
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

from snapshot_feature_registry import registry_as_dict  # noqa: E402

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
FEATURES_DIR = ROOT / "data" / "ml" / "features"
ANCHORS_DIR = ROOT / "data" / "ml" / "anchors"
CONTEXT_DIR = ROOT / "data" / "ml" / "context"
DEFAULT_GAP_FEATURES = FEATURES_DIR / "ogap.parquet"
DEFAULT_MATRIX = ANCHORS_DIR / "forming_vp_snapshots_xctx.parquet"
DEFAULT_SCHEMA = ANCHORS_DIR / "forming_vp_snapshots_xctx.schema.json"
DEFAULT_OUTPUT = ANCHORS_DIR / "forming_vp_snapshots_xctx_gapctx.parquet"
DEFAULT_SCHEMA_OUTPUT = ANCHORS_DIR / "forming_vp_snapshots_xctx_gapctx.schema.json"
DEFAULT_CONTEXT_OUTPUT = CONTEXT_DIR / "forming_vp_opening_gap_context.parquet"

NS_PER_MIN = 60 * 1_000_000_000
INF_NS = np.iinfo("int64").max
GAP_TYPES = ("any", "ndog", "nwog")
STATE_GROUPS = ("any", "unfilled", "filled")
RELATIONS = ("above", "below", "inside")
COUNT_THRESHOLDS = (10, 25, 50, 100)

ANCHOR_PRICE_CANDIDATES = {
    "smt": ("smt.ed.first_break_price",),
    "fvg": ("fvg.ed.candle_3.close", "fvg.ed.fvg_mid"),
    "sweep": ("sweep.ed.manipulation_candle.close", "sweep.ed.swept_reference.level_price"),
    "ob": ("ob.ed.confirmation_candle.close", "ob.ed.ob_body_mid"),
    "tp": ("tp.ed.parent_close",),
    "vp": ("vp.ed.period_close", "vp.ed.vwap"),
    "fvp": ("fvp.ed.asof_close", "fvp.ed.vwap"),
    "ogap": ("ogap.ed.current_open_price", "ogap.ed.gap_mid"),
}


def _infer_anchor_short(matrix: pd.DataFrame, schema: dict[str, Any]) -> str | None:
    if "anchor.short_name" in matrix.columns:
        vals = matrix["anchor.short_name"].dropna().unique()
        if len(vals) == 1:
            return str(vals[0])
    anchor = schema.get("anchor") or {}
    short = anchor.get("short_name")
    return str(short) if short else None


def _infer_anchor_price_col(matrix: pd.DataFrame, schema: dict[str, Any], explicit: str | None) -> str:
    if explicit:
        if explicit not in matrix.columns:
            raise KeyError(f"--anchor-price-col not in matrix: {explicit}")
        return explicit
    short = _infer_anchor_short(matrix, schema)
    for col in ANCHOR_PRICE_CANDIDATES.get(short or "", ()):
        if col in matrix.columns:
            return col
    raise KeyError(f"could not infer anchor price column for short={short!r}")


def _to_ns(series: pd.Series) -> np.ndarray:
    return pd.to_datetime(series, utc=True).to_numpy("datetime64[ns]").astype("int64")


def _transition_ns(series: pd.Series) -> np.ndarray:
    ts = pd.to_datetime(series, utc=True, errors="coerce")
    out = np.full(len(series), INF_NS, dtype="int64")
    valid = ts.notna().to_numpy()
    if valid.any():
        out[valid] = ts[valid].to_numpy("datetime64[ns]").astype("int64")
    return out


def _load_gap_events(path: Path) -> pd.DataFrame:
    cols = [
        "event_id",
        "event_type",
        "bar_end_utc",
        "primary_symbol",
        "side",
        "ed.gap_high",
        "ed.gap_low",
        "ed.gap_mid",
        "ed.gap_size_pts",
        "ed.gap_direction",
        "oc.full_horizon.first_touch_ts_utc",
        "oc.full_horizon.first_midpoint_ts_utc",
        "oc.full_horizon.first_full_fill_ts_utc",
        "oc.full_horizon.first_close_through_ts_utc",
    ]
    gap = pd.read_parquet(path)
    for col in cols:
        if col not in gap.columns:
            gap[col] = None
    gap = gap[cols]
    gap = gap[gap["event_type"].isin(("ndog", "nwog"))].copy()
    gap["bar_end_utc"] = pd.to_datetime(gap["bar_end_utc"], utc=True)
    gap["knowable_ns"] = _to_ns(gap["bar_end_utc"])
    for col in (
        "oc.full_horizon.first_touch_ts_utc",
        "oc.full_horizon.first_midpoint_ts_utc",
        "oc.full_horizon.first_full_fill_ts_utc",
        "oc.full_horizon.first_close_through_ts_utc",
    ):
        if col not in gap.columns:
            gap[col] = None
    gap["touch_ns"] = _transition_ns(gap["oc.full_horizon.first_touch_ts_utc"])
    gap["mid_ns"] = _transition_ns(gap["oc.full_horizon.first_midpoint_ts_utc"])
    gap["fill_ns"] = _transition_ns(gap["oc.full_horizon.first_full_fill_ts_utc"])
    gap["through_ns"] = _transition_ns(gap["oc.full_horizon.first_close_through_ts_utc"])
    return gap.sort_values("knowable_ns").reset_index(drop=True)


def _empty_data(n: int) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for gap_type in GAP_TYPES:
        for state in STATE_GROUPS:
            for relation in RELATIONS:
                stem = f"{gap_type}_{state}_{relation}"
                data[f"gapctx.has_{stem}"] = np.zeros(n, dtype=bool)
                data[f"gapctx.distance_pts_{stem}"] = np.full(n, np.nan)
                data[f"gapctx.age_days_{stem}"] = np.full(n, np.nan)
                data[f"gapctx.size_pts_{stem}"] = np.full(n, np.nan)
                data[f"gapctx.fill_state_code_{stem}"] = np.full(n, np.nan)
                data[f"gapctx.mid_distance_pts_{stem}"] = np.full(n, np.nan)
            for threshold in COUNT_THRESHOLDS:
                data[f"gapctx.n_{gap_type}_{state}_within_{threshold}pts"] = np.zeros(n, dtype=np.int16)
    return data


def _state_code(events: pd.DataFrame, cutoff_ns: int) -> np.ndarray:
    fill = events["fill_ns"].to_numpy(dtype="int64") < cutoff_ns
    mid = (~fill) & (events["mid_ns"].to_numpy(dtype="int64") < cutoff_ns)
    touch = (~fill) & (~mid) & (events["touch_ns"].to_numpy(dtype="int64") < cutoff_ns)
    out = np.zeros(len(events), dtype=np.int8)
    out[touch] = 1
    out[mid] = 2
    out[fill] = 3
    return out


def _relation_masks(events: pd.DataFrame, price: float) -> dict[str, np.ndarray]:
    lows = events["ed.gap_low"].astype(float).to_numpy()
    highs = events["ed.gap_high"].astype(float).to_numpy()
    return {
        "above": lows > price,
        "below": highs < price,
        "inside": (lows <= price) & (highs >= price),
    }


def _distance(events: pd.DataFrame, price: float, relation: str) -> np.ndarray:
    lows = events["ed.gap_low"].astype(float).to_numpy()
    highs = events["ed.gap_high"].astype(float).to_numpy()
    mids = events["ed.gap_mid"].astype(float).to_numpy()
    if relation == "above":
        return lows - price
    if relation == "below":
        return price - highs
    if relation == "inside":
        return np.zeros(len(events))
    return np.abs(mids - price)


def build_context(
    anchors: pd.DataFrame,
    gaps: pd.DataFrame,
    *,
    anchor_price_col: str,
    max_age_days: int,
) -> pd.DataFrame:
    required = ["anchor.event_id", "asof.snapshot", "asof.feature_cutoff_ts", "anchor.primary_symbol"]
    missing = [c for c in required if c not in anchors.columns]
    if missing:
        raise KeyError(f"anchor matrix missing required columns: {missing}")

    n = len(anchors)
    data = _empty_data(n)
    data["anchor.event_id"] = anchors["anchor.event_id"].to_numpy()
    data["asof.snapshot"] = anchors["asof.snapshot"].to_numpy()

    cutoff_ns = _to_ns(anchors["asof.feature_cutoff_ts"])
    prices = pd.to_numeric(anchors[anchor_price_col], errors="coerce").to_numpy()
    primary = anchors["anchor.primary_symbol"].astype(str).to_numpy()
    max_age_ns = max_age_days * 24 * 60 * NS_PER_MIN

    by_primary = {
        sym: sub.sort_values("knowable_ns").reset_index(drop=True)
        for sym, sub in gaps.groupby("primary_symbol")
    }

    for i in range(n):
        price = prices[i]
        if not np.isfinite(price):
            continue
        sym_gaps = by_primary.get(primary[i])
        if sym_gaps is None or sym_gaps.empty:
            continue
        knowable = sym_gaps["knowable_ns"].to_numpy(dtype="int64")
        right = np.searchsorted(knowable, cutoff_ns[i], side="left")
        left = np.searchsorted(knowable, cutoff_ns[i] - max_age_ns, side="left")
        cand = sym_gaps.iloc[left:right].copy()
        if cand.empty:
            continue

        state_codes = _state_code(cand, int(cutoff_ns[i]))
        cand["_state_code"] = state_codes
        cand["_filled"] = state_codes == 3
        cand["_age_days"] = (cutoff_ns[i] - cand["knowable_ns"].to_numpy(dtype="int64")) / (24 * 60 * NS_PER_MIN)
        cand["_mid_distance"] = np.abs(cand["ed.gap_mid"].astype(float).to_numpy() - price)
        rel_masks = _relation_masks(cand, float(price))

        for gap_type in GAP_TYPES:
            type_mask = np.ones(len(cand), dtype=bool) if gap_type == "any" else cand["event_type"].eq(gap_type).to_numpy()
            for state in STATE_GROUPS:
                if state == "any":
                    state_mask = np.ones(len(cand), dtype=bool)
                elif state == "unfilled":
                    state_mask = ~cand["_filled"].to_numpy()
                else:
                    state_mask = cand["_filled"].to_numpy()
                base_mask = type_mask & state_mask
                if not base_mask.any():
                    continue

                all_dist = np.full(len(cand), np.nan)
                # Counts are nearest-zone distance regardless of above/below/inside.
                lows = cand["ed.gap_low"].astype(float).to_numpy()
                highs = cand["ed.gap_high"].astype(float).to_numpy()
                all_dist[base_mask & (lows > price)] = lows[base_mask & (lows > price)] - price
                all_dist[base_mask & (highs < price)] = price - highs[base_mask & (highs < price)]
                all_dist[base_mask & (lows <= price) & (highs >= price)] = 0.0
                for threshold in COUNT_THRESHOLDS:
                    data[f"gapctx.n_{gap_type}_{state}_within_{threshold}pts"][i] = int(
                        np.nansum(all_dist <= threshold)
                    )

                for relation in RELATIONS:
                    mask = base_mask & rel_masks[relation]
                    if not mask.any():
                        continue
                    sub = cand.loc[mask].copy()
                    dist = _distance(sub, float(price), relation)
                    pick = int(np.nanargmin(dist))
                    row = sub.iloc[pick]
                    stem = f"{gap_type}_{state}_{relation}"
                    data[f"gapctx.has_{stem}"][i] = True
                    data[f"gapctx.distance_pts_{stem}"][i] = float(dist[pick])
                    data[f"gapctx.age_days_{stem}"][i] = float(row["_age_days"])
                    data[f"gapctx.size_pts_{stem}"][i] = float(row["ed.gap_size_pts"])
                    data[f"gapctx.fill_state_code_{stem}"][i] = float(row["_state_code"])
                    data[f"gapctx.mid_distance_pts_{stem}"][i] = float(row["_mid_distance"])

    out = pd.DataFrame(data)
    gapctx_cols = sorted(c for c in out.columns if c.startswith("gapctx."))
    return out[["anchor.event_id", "asof.snapshot", *gapctx_cols]]


def _write_schema(
    path: Path,
    *,
    source_schema: Path,
    matrix: pd.DataFrame,
    context_cols: list[str],
    args: argparse.Namespace,
) -> None:
    schema = json.loads(source_schema.read_text(encoding="utf-8"))
    old_features = list(schema.get("feature_columns", []))
    schema.update(
        {
            "generated_utc": datetime.now(UTC).isoformat(),
            "builder": "backend/scripts/ml/build_opening_gap_context.py",
            "source_schema": str(source_schema),
            "source_matrix": str(args.matrix),
            "rows": int(len(matrix)),
            "feature_columns": [*old_features, *[c for c in context_cols if c not in old_features]],
            "registry": registry_as_dict(),
            "opening_gap_context": {
                "gap_features": str(args.gap_features),
                "anchor_price_col": args.anchor_price_col,
                "max_age_days": args.max_age_days,
                "context_columns": context_cols,
                "state_code": {
                    "0": "untouched_unfilled",
                    "1": "touched_unfilled",
                    "2": "midpoint_touched_unfilled",
                    "3": "filled",
                },
            },
            "notes": [
                *schema.get("notes", []),
                "gapctx.* features are state-aware NDOG/NWOG memory context.",
                "Only gaps with gap_open_ts strictly before feature_cutoff_ts are visible.",
                "Fill/touch state uses transition timestamps strictly before feature_cutoff_ts.",
            ],
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(schema, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--gap-features", type=Path, default=DEFAULT_GAP_FEATURES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--schema-output", type=Path, default=DEFAULT_SCHEMA_OUTPUT)
    parser.add_argument("--context-output", type=Path, default=DEFAULT_CONTEXT_OUTPUT)
    parser.add_argument("--anchor-price-col", default=None)
    parser.add_argument("--max-age-days", type=int, default=90)
    args = parser.parse_args()

    matrix = pd.read_parquet(args.matrix)
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    args.anchor_price_col = _infer_anchor_price_col(matrix, schema, args.anchor_price_col)
    gaps = _load_gap_events(args.gap_features)
    context = build_context(
        matrix,
        gaps,
        anchor_price_col=args.anchor_price_col,
        max_age_days=args.max_age_days,
    )
    context_cols = [c for c in context.columns if c.startswith("gapctx.")]
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
    print(f"wrote {args.output}: {len(merged):,} rows x {len(merged.columns):,} cols")
    print(f"wrote {args.schema_output}")
    print(f"wrote {args.context_output}: {len(context_cols):,} gapctx feature cols")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
