"""Multi-year consensus precision analysis.

Extends consensus_precision_check.py from single-year (2025) to all
6 test years. For each test year, trains all 5 signals, captures
top-10% picks, computes precision per consensus tier. Aggregates
across years.

Answers: does the "2-signal consensus doesn't help" finding from 2025
hold across 2020-2024 too?
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.gpu_train_pipeline import filter_matrix, run_fold
from scripts.ml.gpu_train_schema_safe import (
    assert_no_label_leak,
    coerce_binary_label,
    load_schema,
    schema_safe_feature_columns,
)
from scripts.ml.gpu_train_walk_forward import extract_years
from scripts.ml.gpu_train_xgb import resolve_device

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
ANCHORS_REACT = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_reactions") / "data" / "ml" / "anchors"
ANCHORS_SWEEP = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_sweep") / "data" / "ml" / "anchors"

TEST_YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
TOP_PCT = 0.10
SYMBOL_COL = "anchor.primary_symbol"
TIME_COL_CANDIDATES = ["ts.bar_end_utc", "anchor.bar_end_utc", "anchor.event_ts", "ts.bar_start_utc"]
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-15_consensus_multi_year"
OUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Signal:
    name: str
    anchors_dir: Path
    matrix_file: str
    snapshot: str
    side: str
    label: str


SIGNALS = [
    Signal("smt_pd_high_thesis", ANCHORS_REACT,
           "smt_previous_day_snapshots_xctx_fvggeom_obgeom_liqgeom_regime",
           "at_period_close", "high", "label.n1_thesis_confirmed_strict"),
    Signal("ogap_gap_down_rejection", ANCHORS_REACT,
           "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime",
           "at_fire", "gap_down", "label.next_60m.resistance_rejection_3bar"),
    Signal("ogap_gap_up_rejection", ANCHORS_REACT,
           "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime",
           "at_fire", "gap_up", "label.next_60m.support_rejection_3bar"),
    Signal("ogap_strict_partial_touch", ANCHORS_REACT,
           "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict",
           "at_fire", "all", "label.strict.next_60m.partial_touch_rejected"),
    Signal("sweep_failed_recovered_all", ANCHORS_SWEEP,
           "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict",
           "at_fire", "all", "label.strict.next_60m.sweep_failed_recovered"),
]


def _train_and_score(sig: Signal, device: str, test_year: int) -> pd.DataFrame:
    matrix_path = sig.anchors_dir / (sig.matrix_file + ".parquet")
    schema_path = sig.anchors_dir / (sig.matrix_file + ".schema.json")
    schema = load_schema(schema_path)
    feature_pool = schema_safe_feature_columns(schema, include_manual_cell=False)
    assert_no_label_leak(feature_pool)
    df = pd.read_parquet(matrix_path)
    df = filter_matrix(df, snapshot=sig.snapshot, side=sig.side, event_type="all")
    if sig.label not in df.columns:
        return pd.DataFrame()
    y_series = coerce_binary_label(df[sig.label])
    df = df.loc[y_series.notna()].copy()
    y = y_series.loc[df.index].astype(int).to_numpy()
    years = extract_years(df)
    result = run_fold(df=df, years=years, y=y, label=sig.label,
                     feature_pool=feature_pool, test_year=test_year, device=device)
    if result["status"] != "ok":
        return pd.DataFrame()
    preds = result["predictions"]
    test_idx = preds["row_index"].to_numpy()
    test_rows = df.loc[test_idx].copy()
    test_rows["y_true"] = preds["y_true"].to_numpy()
    test_rows["p_test"] = preds["p_test"].to_numpy()
    test_rows["signal_name"] = sig.name
    test_rows["symbol"] = test_rows.get(SYMBOL_COL, "?")
    time_col = next((c for c in TIME_COL_CANDIDATES if c in test_rows.columns), None)
    if time_col:
        test_rows["fire_ts"] = pd.to_datetime(test_rows[time_col], errors="coerce", utc=True)
        test_rows["fire_date"] = test_rows["fire_ts"].dt.date
    else:
        test_rows["fire_ts"] = pd.NaT
        # Fallback unique key per row.
        test_rows["fire_date"] = "row=" + np.arange(len(test_rows)).astype(str)
    k = max(1, int(round(len(test_rows) * TOP_PCT)))
    test_rows["top_10pct"] = test_rows["p_test"].rank(ascending=False, method="first") <= k
    test_rows["test_year"] = test_year
    return test_rows[["test_year", "signal_name", "fire_date", "symbol", "p_test", "y_true", "top_10pct"]].reset_index(drop=True)


def _consensus_for_year(year_preds: pd.DataFrame, year: int) -> dict:
    """Compute consensus precision tiers for a single year."""
    top = year_preds[year_preds["top_10pct"]].copy()
    if len(top) == 0:
        return {"year": year, "tiers": []}
    top["fire_key"] = top["fire_date"].astype(str) + " | " + top["symbol"].astype(str)
    pivot = top.pivot_table(index="fire_key", columns="signal_name",
                             values="top_10pct", aggfunc=lambda s: True, fill_value=False)
    pivot_y = top.pivot_table(index="fire_key", columns="signal_name",
                               values="y_true", aggfunc="max", fill_value=np.nan)
    pivot["n_signals"] = pivot.sum(axis=1)
    tiers = []
    for n_sigs, grp in pivot.groupby("n_signals"):
        n_combos = len(grp)
        trades = 0
        hits = 0
        for fire_key, row in grp.iterrows():
            for sig in pivot.columns:
                if sig == "n_signals":
                    continue
                if row[sig]:
                    trades += 1
                    if sig in pivot_y.columns:
                        y = pivot_y.loc[fire_key, sig]
                        if pd.notna(y):
                            hits += int(y)
        tiers.append({"n_signals": int(n_sigs), "n_combos": n_combos, "trades": trades,
                      "hits": hits, "precision": hits / max(1, trades)})
    return {"year": year, "tiers": tiers}


def main() -> int:
    device_info = resolve_device("auto")
    print(f"device: {device_info.resolved}")
    all_preds = []
    overall_t0 = time.time()
    for sig in SIGNALS:
        for ty in TEST_YEARS:
            t0 = time.time()
            df = _train_and_score(sig, device_info.resolved, ty)
            if df.empty:
                print(f"  {sig.name} year={ty}: failed")
                continue
            all_preds.append(df)
            print(f"  {sig.name} year={ty}: ok ({len(df)} rows, top10={int(df['top_10pct'].sum())}, {time.time()-t0:.0f}s)")
    combined = pd.concat(all_preds, ignore_index=True)
    combined.to_csv(OUT_DIR / "all_predictions.csv", index=False, float_format="%.4f")
    print(f"\nTotal predictions: {len(combined):,}")

    # Per-year consensus tier breakdown.
    print("\nPer-year consensus tiers:")
    all_tier_rows = []
    for year in TEST_YEARS:
        year_preds = combined[combined["test_year"] == year]
        if year_preds.empty:
            continue
        result = _consensus_for_year(year_preds, year)
        for t in result["tiers"]:
            all_tier_rows.append({
                "test_year": year,
                "n_signals": t["n_signals"],
                "n_combos": t["n_combos"],
                "trades": t["trades"],
                "hits": t["hits"],
                "precision": t["precision"],
            })
            print(f"  year={year} n_sigs={t['n_signals']}: combos={t['n_combos']} trades={t['trades']} prec={t['precision']:.3f}")
    tier_df = pd.DataFrame(all_tier_rows)
    tier_df.to_csv(OUT_DIR / "tier_by_year.csv", index=False, float_format="%.4f")

    # Aggregate across years.
    print("\n=== Aggregate across 6 years ===")
    agg = tier_df.groupby("n_signals").agg(
        years_with_tier=("test_year", "count"),
        total_combos=("n_combos", "sum"),
        total_trades=("trades", "sum"),
        total_hits=("hits", "sum"),
        mean_year_precision=("precision", "mean"),
        min_year_precision=("precision", "min"),
        max_year_precision=("precision", "max"),
    ).reset_index()
    agg["aggregate_precision"] = agg["total_hits"] / agg["total_trades"].clip(lower=1)
    agg.to_csv(OUT_DIR / "aggregate.csv", index=False, float_format="%.4f")
    print(agg.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Verdict.
    tier_1 = agg[agg["n_signals"] == 1].iloc[0] if (agg["n_signals"] == 1).any() else None
    tier_2 = agg[agg["n_signals"] == 2].iloc[0] if (agg["n_signals"] == 2).any() else None
    tier_3p = agg[agg["n_signals"] >= 3]
    verdict = {
        "test_years": TEST_YEARS,
        "tier_1_aggregate_precision": float(tier_1["aggregate_precision"]) if tier_1 is not None else None,
        "tier_2_aggregate_precision": float(tier_2["aggregate_precision"]) if tier_2 is not None else None,
        "tier_3_plus_aggregate_precision": float(tier_3p["total_hits"].sum() / max(1, tier_3p["total_trades"].sum())) if len(tier_3p) else None,
        "consensus_2_lift_vs_1": (
            float(tier_2["aggregate_precision"] - tier_1["aggregate_precision"])
            if tier_1 is not None and tier_2 is not None else None
        ),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "verdict.json").write_text(json.dumps(verdict, indent=2), encoding="utf-8")
    print("\n=== VERDICT ===")
    print(json.dumps(verdict, indent=2))
    print(f"\nDone in {(time.time()-overall_t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
