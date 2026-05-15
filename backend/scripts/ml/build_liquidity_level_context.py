"""Build state-aware swing/equal-level liquidity geometry for snapshots."""

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

from snapshot_feature_registry import EQL_LAG_MIN, SWING_LAG_MIN, registry_as_dict  # noqa: E402

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
FEATURES_DIR = ROOT / "data" / "ml" / "features"
ANCHORS_DIR = ROOT / "data" / "ml" / "anchors"
CONTEXT_DIR = ROOT / "data" / "ml" / "context"
DEFAULT_SWING_FEATURES = FEATURES_DIR / "swing.parquet"
DEFAULT_EQL_FEATURES = FEATURES_DIR / "eql.parquet"
DEFAULT_MATRIX = ANCHORS_DIR / "sweep_snapshots_xctx_fvggeom_obgeom.parquet"
DEFAULT_SCHEMA = ANCHORS_DIR / "sweep_snapshots_xctx_fvggeom_obgeom.schema.json"
DEFAULT_OUTPUT = ANCHORS_DIR / "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom.parquet"
DEFAULT_SCHEMA_OUTPUT = ANCHORS_DIR / "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom.schema.json"
DEFAULT_CONTEXT_OUTPUT = CONTEXT_DIR / "sweep_liquidity_level_context.parquet"

NS_PER_MIN = 60 * 1_000_000_000
INF_NS = np.iinfo("int64").max
SWING_HORIZON_BARS = 50
EQL_HORIZON_BARS = 250
SOURCES = ("any_source", "swing", "eql")
SCOPES = ("same_primary", "any_symbol")
SIDES = ("any_side", "high", "low")
STATES = ("fresh", "wick_taken", "close_taken", "horizon_expired")
RELATIONS = ("above", "below")
COUNT_THRESHOLDS = (10, 25, 50, 100)

ANCHOR_PRICE_CANDIDATES = {
    "smt": ("smt.ed.first_break_price",),
    "fvg": ("fvg.ed.candle_3.close", "fvg.ed.fvg_mid"),
    "sweep": ("sweep.ed.manipulation_candle.close", "sweep.ed.swept_reference.level_price"),
    "ob": ("ob.ed.confirmation_candle.close", "ob.ed.ob_body_mid"),
    "disp": ("disp.ed.candle.close", "disp.ed.close"),
    "psp": ("psp.ed.primary.close", "psp.ed.primary_close"),
    "ft": ("ft.ed.range_close", "ft.ed.reference_close"),
    "orb": ("orb.ed.range_close", "orb.ed.reference_close"),
    "tp": ("tp.ed.parent_close",),
    "vp": ("vp.ed.period_close", "vp.ed.vwap"),
    "fvp": ("fvp.ed.asof_close", "fvp.ed.vwap"),
    "ogap": ("ogap.ed.current_open_price", "ogap.ed.gap_mid"),
    "itr": ("itr.ed.interval_close", "itr.ed.interval_mid"),
    "macro": ("macro.ed.pre_release_reference_close", "macro.ed.pre_5m_close"),
}


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
        "time_profile": "tp",
        "volume_profile": "vp",
        "forming_volume_profile": "fvp",
        "opening_gap_levels": "ogap",
        "interval_true_range": "itr",
        "macro_event_anchor": "macro",
    }
    return by_feature.get(feature)


def _infer_anchor_price_col(matrix: pd.DataFrame, schema: dict[str, Any], explicit: str | None) -> str:
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


def _to_ns(series: pd.Series) -> np.ndarray:
    return pd.to_datetime(series, utc=True).to_numpy("datetime64[ns]").astype("int64")


def _transition_ns(
    start_ns: np.ndarray,
    bars: pd.Series,
    unit_min: pd.Series,
    *,
    min_visible_ns: np.ndarray,
) -> np.ndarray:
    out = np.full(len(start_ns), INF_NS, dtype="int64")
    b = pd.to_numeric(bars, errors="coerce")
    valid = b.notna()
    if valid.any():
        idx = np.where(valid.to_numpy())[0]
        raw = (
            start_ns[idx]
            + b.iloc[idx].astype("int64").to_numpy()
            * unit_min.iloc[idx].astype("int64").to_numpy()
            * NS_PER_MIN
        )
        out[idx] = np.maximum(raw, min_visible_ns[idx])
    return out


def _load_swing_events(path: Path) -> pd.DataFrame:
    cols = [
        "event_id",
        "event_type",
        "bar_end_utc",
        "primary_symbol",
        "side",
        "ed.pivot_price",
        "ed.knowable_ts_utc",
        "oc.breakout.bars_to_wick",
        "oc.breakout.bars_to_close",
    ]
    swing = pd.read_parquet(path, columns=cols)
    swing = swing[swing["event_type"].isin(SWING_LAG_MIN) & swing["side"].isin(("high", "low"))].copy()
    swing["source"] = "swing"
    swing["level_price"] = pd.to_numeric(swing["ed.pivot_price"], errors="coerce")
    swing["level_spread_pts"] = np.float32(0.0)
    swing["n_members"] = np.float32(1.0)
    swing["lag_min"] = swing["event_type"].map(SWING_LAG_MIN).astype("int64")
    swing["event_ns"] = _to_ns(swing["bar_end_utc"])
    knowable = pd.to_datetime(swing["ed.knowable_ts_utc"], utc=True, errors="coerce")
    missing = knowable.isna()
    if missing.any():
        knowable.loc[missing] = (
            pd.to_datetime(swing.loc[missing, "bar_end_utc"], utc=True)
            + pd.to_timedelta(swing.loc[missing, "lag_min"], unit="m")
        )
    swing["knowable_ns"] = knowable.to_numpy("datetime64[ns]").astype("int64")
    swing["transition_unit_min"] = swing["lag_min"]
    swing["wick_ns"] = _transition_ns(
        swing["knowable_ns"].to_numpy(dtype="int64"),
        swing["oc.breakout.bars_to_wick"],
        swing["transition_unit_min"],
        min_visible_ns=swing["knowable_ns"].to_numpy(dtype="int64"),
    )
    swing["close_ns"] = _transition_ns(
        swing["knowable_ns"].to_numpy(dtype="int64"),
        swing["oc.breakout.bars_to_close"],
        swing["transition_unit_min"],
        min_visible_ns=swing["knowable_ns"].to_numpy(dtype="int64"),
    )
    swing["horizon_ns"] = (
        swing["knowable_ns"].to_numpy(dtype="int64")
        + SWING_HORIZON_BARS * swing["transition_unit_min"].to_numpy(dtype="int64") * NS_PER_MIN
    )
    return swing


def _load_eql_events(path: Path) -> pd.DataFrame:
    cols = [
        "event_id",
        "event_type",
        "bar_end_utc",
        "primary_symbol",
        "side",
        "ed.level_price",
        "ed.cluster_spread_pts",
        "ed.n_members",
        "oc.take.bars_to_wick",
        "oc.take.bars_to_close",
        "oc.horizon_bars",
    ]
    eql = pd.read_parquet(path, columns=cols)
    eql = eql[eql["event_type"].isin(EQL_LAG_MIN) & eql["side"].isin(("high", "low"))].copy()
    eql["source"] = "eql"
    eql["level_price"] = pd.to_numeric(eql["ed.level_price"], errors="coerce")
    eql["level_spread_pts"] = pd.to_numeric(eql["ed.cluster_spread_pts"], errors="coerce").fillna(0.0)
    eql["n_members"] = pd.to_numeric(eql["ed.n_members"], errors="coerce").fillna(2.0)
    eql["lag_min"] = eql["event_type"].map(EQL_LAG_MIN).astype("int64")
    eql["event_ns"] = _to_ns(eql["bar_end_utc"])
    eql["knowable_ns"] = eql["event_ns"].to_numpy(dtype="int64") + eql["lag_min"].to_numpy(dtype="int64") * NS_PER_MIN
    eql["transition_unit_min"] = 60
    eql["wick_ns"] = _transition_ns(
        eql["event_ns"].to_numpy(dtype="int64"),
        eql["oc.take.bars_to_wick"],
        eql["transition_unit_min"],
        min_visible_ns=eql["knowable_ns"].to_numpy(dtype="int64"),
    )
    eql["close_ns"] = _transition_ns(
        eql["event_ns"].to_numpy(dtype="int64"),
        eql["oc.take.bars_to_close"],
        eql["transition_unit_min"],
        min_visible_ns=eql["knowable_ns"].to_numpy(dtype="int64"),
    )
    horizon_bars = pd.to_numeric(eql["oc.horizon_bars"], errors="coerce").fillna(EQL_HORIZON_BARS)
    raw_horizon = (
        eql["event_ns"].to_numpy(dtype="int64")
        + horizon_bars.astype("int64").to_numpy() * 60 * NS_PER_MIN
    )
    eql["horizon_ns"] = np.maximum(raw_horizon, eql["knowable_ns"].to_numpy(dtype="int64"))
    return eql


def _load_levels(swing_path: Path, eql_path: Path) -> pd.DataFrame:
    frames = [_load_swing_events(swing_path), _load_eql_events(eql_path)]
    cols = [
        "event_id",
        "source",
        "event_type",
        "primary_symbol",
        "side",
        "level_price",
        "level_spread_pts",
        "n_members",
        "knowable_ns",
        "wick_ns",
        "close_ns",
        "horizon_ns",
    ]
    levels = pd.concat([frame[cols] for frame in frames], ignore_index=True)
    levels = levels[np.isfinite(pd.to_numeric(levels["level_price"], errors="coerce"))].copy()
    levels["level_price"] = levels["level_price"].astype("float64")
    levels["level_spread_pts"] = levels["level_spread_pts"].astype("float32")
    levels["n_members"] = levels["n_members"].astype("float32")
    return levels.sort_values("knowable_ns").reset_index(drop=True)


def _state_for_cutoff(events: pd.DataFrame, cutoff_ns: int) -> np.ndarray:
    close_taken = events["close_ns"].to_numpy(dtype="int64") < cutoff_ns
    wick_taken = (~close_taken) & (events["wick_ns"].to_numpy(dtype="int64") < cutoff_ns)
    within_horizon = cutoff_ns <= events["horizon_ns"].to_numpy(dtype="int64")
    fresh = (~close_taken) & (~wick_taken) & within_horizon
    horizon_expired = (~close_taken) & (~wick_taken) & (~within_horizon)
    state = np.full(len(events), "", dtype=object)
    state[fresh] = "fresh"
    state[wick_taken] = "wick_taken"
    state[close_taken] = "close_taken"
    state[horizon_expired] = "horizon_expired"
    return state


def _level_relation(price: float, levels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    relation = np.where(levels >= price, "above", "below")
    return relation, np.abs(levels - price).astype("float32")


def _empty_feature_data(n: int) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for source in SOURCES:
        for scope in SCOPES:
            for side in SIDES:
                for state in STATES:
                    for relation in RELATIONS:
                        stem = f"{source}_{scope}_{side}_{state}_{relation}"
                        data[f"liqgeom.has_{stem}"] = np.zeros(n, dtype=bool)
                        data[f"liqgeom.distance_pts_{stem}"] = np.full(n, np.nan, dtype="float32")
                        data[f"liqgeom.age_min_{stem}"] = np.full(n, np.nan, dtype="float32")
                        data[f"liqgeom.spread_pts_{stem}"] = np.full(n, np.nan, dtype="float32")
                        data[f"liqgeom.n_members_{stem}"] = np.full(n, np.nan, dtype="float32")
                    for threshold in COUNT_THRESHOLDS:
                        data[f"liqgeom.n_{source}_{scope}_{side}_{state}_within_{threshold}pts"] = np.zeros(
                            n,
                            dtype=np.int16,
                        )
    return data


def _fill_nearest(
    data: dict[str, Any],
    row_idx: int,
    *,
    source: str,
    scope: str,
    side: str,
    state: str,
    relation: str,
    mask: np.ndarray,
    distance: np.ndarray,
    age_min: np.ndarray,
    spread: np.ndarray,
    n_members: np.ndarray,
) -> None:
    if not mask.any():
        return
    idxs = np.where(mask)[0]
    nearest = idxs[int(np.nanargmin(distance[mask]))]
    stem = f"{source}_{scope}_{side}_{state}_{relation}"
    data[f"liqgeom.has_{stem}"][row_idx] = True
    data[f"liqgeom.distance_pts_{stem}"][row_idx] = float(distance[nearest])
    data[f"liqgeom.age_min_{stem}"][row_idx] = float(age_min[nearest])
    data[f"liqgeom.spread_pts_{stem}"][row_idx] = float(spread[nearest])
    data[f"liqgeom.n_members_{stem}"][row_idx] = float(n_members[nearest])


def _fill_counts(
    data: dict[str, Any],
    row_idx: int,
    *,
    source: str,
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
        data[f"liqgeom.n_{source}_{scope}_{side}_{state}_within_{threshold}pts"][row_idx] = int(
            np.sum(d <= threshold)
        )


def build_context(
    matrix: pd.DataFrame,
    *,
    levels: pd.DataFrame,
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
        "liqgeom.anchor_price": pd.to_numeric(matrix[anchor_price_col], errors="coerce").to_numpy(dtype="float32"),
    }
    data.update(_empty_feature_data(n))

    cutoff_ns = _to_ns(matrix["asof.feature_cutoff_ts"])
    prices = data["liqgeom.anchor_price"].astype("float64")
    symbols = matrix["anchor.primary_symbol"].astype(str).to_numpy()
    level_knowable = levels["knowable_ns"].to_numpy(dtype="int64")
    level_price = levels["level_price"].to_numpy(dtype="float64")
    level_symbol = levels["primary_symbol"].astype(str).to_numpy()
    level_side = levels["side"].astype(str).to_numpy()
    level_source = levels["source"].astype(str).to_numpy()
    level_spread = levels["level_spread_pts"].to_numpy(dtype="float32")
    level_members = levels["n_members"].to_numpy(dtype="float32")
    max_age_ns = max_age_days * 24 * 60 * NS_PER_MIN

    for i, (cutoff, price, symbol) in enumerate(zip(cutoff_ns, prices, symbols, strict=True)):
        if not np.isfinite(price):
            continue
        start = np.searchsorted(level_knowable, cutoff - max_age_ns, side="left")
        end = np.searchsorted(level_knowable, cutoff, side="left")
        if end <= start:
            continue
        idx = np.arange(start, end)
        events = levels.iloc[idx]
        state = _state_for_cutoff(events, int(cutoff))
        known = state != ""
        if not known.any():
            continue

        relation, distance = _level_relation(float(price), level_price[idx])
        age_min = ((cutoff - level_knowable[idx]) / NS_PER_MIN).astype("float32")
        same_primary = level_symbol[idx] == symbol

        for source in SOURCES:
            source_mask = np.ones(len(idx), dtype=bool) if source == "any_source" else (level_source[idx] == source)
            for scope in SCOPES:
                scope_mask = same_primary if scope == "same_primary" else np.ones(len(idx), dtype=bool)
                for side in SIDES:
                    side_mask = np.ones(len(idx), dtype=bool) if side == "any_side" else (level_side[idx] == side)
                    for state_name in STATES:
                        base_mask = known & source_mask & scope_mask & side_mask & (state == state_name)
                        _fill_counts(
                            data,
                            i,
                            source=source,
                            scope=scope,
                            side=side,
                            state=state_name,
                            mask=base_mask,
                            distance=distance,
                        )
                        for rel in RELATIONS:
                            _fill_nearest(
                                data,
                                i,
                                source=source,
                                scope=scope,
                                side=side,
                                state=state_name,
                                relation=rel,
                                mask=base_mask & (relation == rel),
                                distance=distance,
                                age_min=age_min,
                                spread=level_spread[idx],
                                n_members=level_members[idx],
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
            "builder": "backend/scripts/ml/build_liquidity_level_context.py",
            "source_schema": str(source_schema),
            "source_matrix": str(args.matrix),
            "rows": int(len(matrix)),
            "feature_columns": merged_features,
            "registry": registry_as_dict(),
            "liquidity_level_context": {
                "swing_features": str(args.swing_features),
                "equal_level_features": str(args.eql_features),
                "anchor_price_col": anchor_price_col,
                "max_age_days": args.max_age_days,
                "sources": list(SOURCES),
                "states": list(STATES),
                "scopes": list(SCOPES),
                "sides": list(SIDES),
                "relations": list(RELATIONS),
                "count_thresholds_pts": list(COUNT_THRESHOLDS),
                "swing_horizon_bars": SWING_HORIZON_BARS,
                "equal_level_horizon_bars": EQL_HORIZON_BARS,
                "context_columns": context_cols,
                "state_timing_note": (
                    "Swing/equal-level bars_to_* outcomes are converted into "
                    "transition timestamps, then clamped so no state is visible "
                    "before the underlying level is knowable."
                ),
            },
            "notes": [
                *schema.get("notes", []),
                "liqgeom.* features are state-aware swing/equal-level liquidity geometry known before the snapshot cutoff.",
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
    levels = _load_levels(args.swing_features, args.eql_features)
    context = build_context(
        matrix,
        levels=levels,
        anchor_price_col=anchor_price_col,
        max_age_days=args.max_age_days,
    )
    context_cols = [c for c in context.columns if c.startswith("liqgeom.")]
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
    parser.add_argument("--swing-features", type=Path, default=DEFAULT_SWING_FEATURES)
    parser.add_argument("--eql-features", type=Path, default=DEFAULT_EQL_FEATURES)
    parser.add_argument("--anchor-price-col", default=None)
    parser.add_argument("--event-type", default="all")
    parser.add_argument("--side", default="all")
    parser.add_argument("--max-age-days", type=int, default=60)
    args = parser.parse_args()
    out_path, schema_path, context_path, merged = build(args)
    n_geom = sum(c.startswith("liqgeom.") for c in merged.columns)
    print(f"wrote {out_path}: {len(merged):,} rows x {len(merged.columns):,} cols")
    print(f"wrote {schema_path}")
    print(f"wrote {context_path}: {n_geom:,} liqgeom feature cols")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
