"""2025 regime diagnostic.

Every rigorous backtest variant (v3, v4, v5, v6) shows 2025 as the
weakest year. Earlier proxy work also flagged 2024 as weak on some
signals. This is the biggest open question: WHY does 2025 break?

Four-layer breakdown for each of the 3 OGAP signals in the v5 portfolio:

  L1 LABEL: base rate of the label across years
  L2 MODEL: walk-forward AUC across years
  L3 PICKS: top-10% precision across years (how well model is calibrated)
  L4 TRADES: per-trade pnl_r distribution from the v5 backtest

If L1 changes a lot in 2025 → the underlying event class became
  more/less frequent
If L2 changes → the model can't predict it as well
If L3 changes → high-confidence picks have lower precision
If L4 changes → predictions are right but trades convert worse

Output: docs/ML_2025_REGIME_DIAGNOSTIC.md with the matrix + plots.
"""

from __future__ import annotations

import json
import sys
import time as time_mod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.gpu_train_pipeline import filter_matrix, run_fold
from scripts.ml.gpu_train_schema_safe import (
    assert_no_label_leak, coerce_binary_label,
    load_schema, schema_safe_feature_columns,
)
from scripts.ml.gpu_train_walk_forward import extract_years
from scripts.ml.gpu_train_xgb import resolve_device
from scripts.ml.rigorous_backtest_v1 import Signal, TEST_YEARS, TOP_PCT, SYMBOL_COL, SIDE_COL, TIME_COL_CANDIDATES

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
ANCHORS_REACT = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_reactions") / "data" / "ml" / "anchors"
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-16_2025_regime_diagnostic"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# v5 baseline signals (3 OGAP signals after dropping SMT/sweep/YM).
SIGNALS = [
    Signal("ogap_gap_down_rejection", ANCHORS_REACT,
           "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime",
           "at_fire", "gap_down", "label.next_60m.resistance_rejection_3bar", "fixed_short"),
    Signal("ogap_gap_up_rejection", ANCHORS_REACT,
           "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime",
           "at_fire", "gap_up", "label.next_60m.support_rejection_3bar", "fixed_long"),
    Signal("ogap_strict_partial_touch", ANCHORS_REACT,
           "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict",
           "at_fire", "all", "label.strict.next_60m.partial_touch_rejected", "side_aware"),
]


def analyze_signal(sig: Signal, device: str) -> dict:
    """Run all 4 layers for one signal."""
    matrix_path = sig.anchors_dir / (sig.matrix_file + ".parquet")
    schema_path = sig.anchors_dir / (sig.matrix_file + ".schema.json")
    schema = load_schema(schema_path)
    feature_pool = schema_safe_feature_columns(schema, include_manual_cell=False)
    assert_no_label_leak(feature_pool)
    df = pd.read_parquet(matrix_path)
    df = filter_matrix(df, snapshot=sig.snapshot, side=sig.side, event_type="all")
    y_series = coerce_binary_label(df[sig.label])
    df = df.loc[y_series.notna()].copy()
    y = y_series.loc[df.index].astype(int).to_numpy()
    years = extract_years(df)

    # L1 LABEL — base rate by year (using whole matrix, not just test set).
    layer1_rows = []
    for year in sorted(set(years)):
        if year < 2015 or year > 2026:
            continue
        m = years == year
        if m.sum() == 0:
            continue
        layer1_rows.append({
            "year": int(year),
            "n_events": int(m.sum()),
            "base_rate": float(y[m].mean()),
        })

    # L2-L4 — train+score each test year, capture metrics.
    layer234_rows = []
    for ty in TEST_YEARS:
        result = run_fold(df=df, years=years, y=y, label=sig.label,
                         feature_pool=feature_pool, test_year=ty, device=device)
        if result["status"] != "ok":
            continue
        preds = result["predictions"]
        y_true = preds["y_true"].to_numpy()
        p_test = preds["p_test"].to_numpy()
        rec = result["record"]
        auc = float(rec["auc_test"])
        base = float(rec["base_rate_test"])
        n_test = int(rec["n_test"])
        # Top-10% precision.
        k = max(1, int(round(len(p_test) * TOP_PCT)))
        ranked = np.argsort(-p_test)
        top_idx = ranked[:k]
        top_prec = float(y_true[top_idx].mean())
        edge = top_prec - base
        # Save predictions for trade-level analysis later.
        layer234_rows.append({
            "year": int(ty),
            "n_test": n_test,
            "base_rate_test": base,
            "auc": auc,
            "top10_precision": top_prec,
            "top10_edge_vs_base": edge,
        })

    return {
        "signal_name": sig.name,
        "layer1_label": layer1_rows,
        "layer234_model": layer234_rows,
    }


def main() -> int:
    device_info = resolve_device("auto")
    print(f"device: {device_info.resolved}")
    print(f"output: {OUT_DIR}\n")
    t0 = time_mod.time()

    all_results = {}
    for sig in SIGNALS:
        print(f"\n=== Analyzing {sig.name} ===")
        all_results[sig.name] = analyze_signal(sig, device_info.resolved)
        print(f"  L1 LABEL base_rate by year:")
        for r in all_results[sig.name]["layer1_label"]:
            print(f"    {r['year']}: n={r['n_events']:>5} base_rate={r['base_rate']:.3f}")
        print(f"  L2-L4 by test year:")
        for r in all_results[sig.name]["layer234_model"]:
            print(f"    {r['year']}: n={r['n_test']:>4} base={r['base_rate_test']:.3f} "
                  f"AUC={r['auc']:.3f} top10_prec={r['top10_precision']:.3f} edge={r['top10_edge_vs_base']:+.3f}")

    # Build summary tables.
    # L1: matrix-wide base rate by year (across all signals).
    l1_table = []
    for name, res in all_results.items():
        for r in res["layer1_label"]:
            l1_table.append({"signal": name, **r})
    l1_df = pd.DataFrame(l1_table)
    l1_pivot = l1_df.pivot(index="signal", columns="year", values="base_rate")
    l1_pivot.to_csv(OUT_DIR / "layer1_base_rate_by_year.csv", float_format="%.4f")
    print("\n=== L1: Label base rate by year (matrix-wide) ===")
    print(l1_pivot.to_string(float_format=lambda x: f"{x:.3f}"))

    # L2: test AUC by year.
    l2_table = []
    for name, res in all_results.items():
        for r in res["layer234_model"]:
            l2_table.append({"signal": name, **r})
    l2_df = pd.DataFrame(l2_table)
    l2_pivot = l2_df.pivot(index="signal", columns="year", values="auc")
    l2_pivot.to_csv(OUT_DIR / "layer2_auc_by_year.csv", float_format="%.4f")
    print("\n=== L2: Walk-forward test AUC by year ===")
    print(l2_pivot.to_string(float_format=lambda x: f"{x:.3f}"))

    # L3: top-10 precision by year.
    l3_pivot = l2_df.pivot(index="signal", columns="year", values="top10_precision")
    l3_pivot.to_csv(OUT_DIR / "layer3_top10_precision_by_year.csv", float_format="%.4f")
    print("\n=== L3: Top-10% precision by year ===")
    print(l3_pivot.to_string(float_format=lambda x: f"{x:.3f}"))

    # L3b: top-10 edge by year.
    l3b_pivot = l2_df.pivot(index="signal", columns="year", values="top10_edge_vs_base")
    l3b_pivot.to_csv(OUT_DIR / "layer3b_top10_edge_by_year.csv", float_format="%.4f")
    print("\n=== L3b: Top-10% edge over base rate by year ===")
    print(l3b_pivot.to_string(float_format=lambda x: f"{x:+.3f}"))

    # L4: trade-level pnl_r distribution by year (from the v5 winner trades.csv).
    v5_trades_path = ROOT / "experiments" / "backtests" / "2026-05-15_v5_winner_deepdive" / "v5_winner_no_ym_trades.csv"
    if v5_trades_path.exists():
        v5_trades = pd.read_csv(v5_trades_path)
        v5_trades = v5_trades[v5_trades["exit_reason"].isin(["target", "stop", "time_exit"])]
        print("\n=== L4: v5 winner trade-level metrics by year (no-YM) ===")
        l4_rows = []
        for year, g in v5_trades.groupby("test_year"):
            n = len(g)
            wins = int((g["pnl_r"] > 0).sum())
            cum_r = float(g["pnl_r"].sum())
            avg_r = float(g["pnl_r"].mean())
            avg_win = float(g[g["pnl_r"] > 0]["pnl_r"].mean()) if wins else 0.0
            avg_loss = float(g[g["pnl_r"] <= 0]["pnl_r"].mean()) if (n - wins) else 0.0
            target_rate = float((g["exit_reason"] == "target").mean())
            stop_rate = float((g["exit_reason"] == "stop").mean())
            time_rate = float((g["exit_reason"] == "time_exit").mean())
            row = {
                "year": int(year), "n": n, "wins": wins, "win_rate": wins / n,
                "cum_r": cum_r, "avg_r": avg_r, "avg_win_r": avg_win, "avg_loss_r": avg_loss,
                "target_rate": target_rate, "stop_rate": stop_rate, "time_rate": time_rate,
            }
            l4_rows.append(row)
            print(f"  {row['year']}: n={n:3d} win%={row['win_rate']:.3f} cum_R={cum_r:+.1f} "
                  f"avg_R={avg_r:+.3f} target%={target_rate:.2f} stop%={stop_rate:.2f} time%={time_rate:.2f}")
        l4_df = pd.DataFrame(l4_rows)
        l4_df.to_csv(OUT_DIR / "layer4_trade_metrics_by_year.csv", index=False, float_format="%.4f")

    # === Plot the layer-by-layer breakdown ===
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    years = TEST_YEARS

    # L2: AUC by year per signal.
    ax = axes[0, 0]
    for sig_name in l2_pivot.index:
        ax.plot(years, l2_pivot.loc[sig_name].reindex(years).values, marker="o", label=sig_name, linewidth=1.5)
    ax.set_xlabel("test year"); ax.set_ylabel("walk-forward AUC")
    ax.set_title("L2 — Model AUC by year")
    ax.grid(True, alpha=0.3); ax.legend(fontsize=8); ax.set_ylim(0.5, 1.0)

    # L3: Top-10 precision by year.
    ax = axes[0, 1]
    for sig_name in l3_pivot.index:
        ax.plot(years, l3_pivot.loc[sig_name].reindex(years).values, marker="o", label=sig_name, linewidth=1.5)
    ax.set_xlabel("test year"); ax.set_ylabel("top-10% precision")
    ax.set_title("L3 — Top-10% precision by year")
    ax.grid(True, alpha=0.3); ax.legend(fontsize=8); ax.set_ylim(0, 1.05)

    # L3b: edge over base rate.
    ax = axes[1, 0]
    for sig_name in l3b_pivot.index:
        ax.plot(years, l3b_pivot.loc[sig_name].reindex(years).values, marker="o", label=sig_name, linewidth=1.5)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("test year"); ax.set_ylabel("top-10% edge vs base rate")
    ax.set_title("L3b — Top-10% edge over base rate")
    ax.grid(True, alpha=0.3); ax.legend(fontsize=8)

    # L4: v5 trade-level avg_R.
    ax = axes[1, 1]
    if v5_trades_path.exists():
        ax.plot(l4_df["year"], l4_df["avg_r"], marker="o", color="firebrick", linewidth=1.5)
        ax.axhline(0, color="black", linewidth=0.5)
        ax.set_xlabel("test year"); ax.set_ylabel("avg R per trade (v5 winner no-YM)")
        ax.set_title("L4 — Trade-level avg R by year (v5 winner)")
        ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "regime_layers.png", dpi=120)
    plt.close(fig)

    # Save raw JSON.
    summary = {
        "signals": list(all_results.keys()),
        "test_years": TEST_YEARS,
        "elapsed_min": round((time_mod.time() - t0) / 60, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== DONE in {(time_mod.time()-t0)/60:.1f} min ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
