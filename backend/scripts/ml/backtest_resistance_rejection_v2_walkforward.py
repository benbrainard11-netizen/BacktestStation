"""Multi-year walk-forward extension of the resistance_rejection proxy backtest.

Sanity test for v1's 2025-only result. Trains a fresh model for each
test year in {2020..2025}, scores the held-out year, and computes the
same precision/recall/R-curve metrics. The question this answers:

  "Was 2025's 100% top-decile precision real edge or a regime fluke?"

If multiple years show top-decile precision >= 85%, the signal is
robust. If only 2025 stands alone, v1 was lucky.
"""

from __future__ import annotations

import json
import sys
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
    assert_no_label_leak,
    coerce_binary_label,
    load_schema,
    schema_safe_feature_columns,
)
from scripts.ml.gpu_train_walk_forward import extract_years
from scripts.ml.gpu_train_xgb import resolve_device

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
EXPORT = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_reactions")
ANCHORS = EXPORT / "data" / "ml" / "anchors"
MATRIX = ANCHORS / "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime.parquet"
SCHEMA = ANCHORS / "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime.schema.json"

LABEL = "label.next_60m.resistance_rejection_3bar"
SIDE = "gap_down"
SNAPSHOT = "at_fire"
TEST_YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
THRESHOLDS = [0.5, 0.6, 0.7, 0.8, 0.9]
TOP_DECILES = [0.01, 0.05, 0.10, 0.20, 0.50]

OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-15_resistance_rejection_v2_walkforward"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _proxy_pnl(y_true, predicted):
    return np.where(predicted == 1, np.where(y_true == 1, 1.0, -1.0), 0.0)


def main() -> int:
    print(f"loading matrix: {MATRIX.name}")
    schema = load_schema(SCHEMA)
    feature_pool = schema_safe_feature_columns(schema, include_manual_cell=False)
    assert_no_label_leak(feature_pool)
    df_full = pd.read_parquet(MATRIX)
    df = filter_matrix(df_full, snapshot=SNAPSHOT, side=SIDE, event_type="all")
    if LABEL not in df.columns:
        raise KeyError(f"label column missing: {LABEL}")
    y_series = coerce_binary_label(df[LABEL])
    df = df.loc[y_series.notna()].copy()
    y = y_series.loc[df.index].astype(int).to_numpy()
    years = extract_years(df)
    print(f"  filtered rows: {len(df):,}  base rate: {y.mean():.3f}  years: {int(years.min())}-{int(years.max())}")

    device_info = resolve_device("auto")
    print(f"  device: {device_info.resolved}")

    per_year_records = []
    per_threshold_records = []
    per_decile_records = []
    equity_curves = {}

    for test_year in TEST_YEARS:
        print(f"\n=== test_year={test_year} ===")
        result = run_fold(
            df=df, years=years, y=y, label=LABEL,
            feature_pool=feature_pool, test_year=test_year, device=device_info.resolved,
        )
        if result["status"] != "ok":
            print(f"  SKIPPED: {result['status']}")
            per_year_records.append({
                "test_year": test_year,
                "status": result["status"],
                "n_test": result.get("n_test"),
            })
            continue

        preds = result["predictions"]
        rec = result["record"]
        test_base_rate = float(rec["base_rate_test"])
        n_test = int(rec["n_test"])
        test_auc = float(rec["auc_test"])
        print(f"  n_train={rec['n_train']} n_test={n_test} AUC={test_auc:.3f} base_rate={test_base_rate:.3f}")

        y_true = preds["y_true"].to_numpy()
        p_test = preds["p_test"].to_numpy()

        # Per-year summary line.
        per_year_records.append({
            "test_year": test_year,
            "status": "ok",
            "n_test": n_test,
            "test_auc": test_auc,
            "test_base_rate": test_base_rate,
            "blind_cum_r": float(np.where(y_true == 1, 1.0, -1.0).sum()),
        })

        # Per-threshold rows.
        for thr in THRESHOLDS:
            predicted = (p_test >= thr).astype(int)
            n = int(predicted.sum())
            if n == 0:
                per_threshold_records.append({
                    "test_year": test_year, "threshold": thr, "n_signals": 0,
                    "precision": None, "recall": None, "cum_r": 0.0, "avg_r": None,
                })
                continue
            hits = int(((predicted == 1) & (y_true == 1)).sum())
            prec = hits / n
            recall = hits / max(1, int(y_true.sum()))
            pnl = _proxy_pnl(y_true, predicted)
            cum_r = float(pnl.sum())
            per_threshold_records.append({
                "test_year": test_year, "threshold": thr, "n_signals": n,
                "precision": prec, "recall": recall, "cum_r": cum_r, "avg_r": cum_r / n,
            })

        # Top-N decile precision rows.
        ranked = np.argsort(-p_test)
        for top_pct in TOP_DECILES:
            k = max(1, int(round(len(ranked) * top_pct)))
            idx = ranked[:k]
            y_top = y_true[idx]
            prec = float(y_top.mean())
            edge = prec - test_base_rate
            cum_r = float(2 * y_top.sum() - k)
            per_decile_records.append({
                "test_year": test_year, "top_pct": top_pct, "n_signals": k,
                "precision": prec, "edge_vs_base": edge, "cum_r": cum_r, "avg_r": cum_r / k,
            })

        # Equity curve at threshold 0.7 (the "best" total-R band in v1).
        best_thr = 0.7
        predicted = (p_test >= best_thr).astype(int)
        cum = _proxy_pnl(y_true, predicted).cumsum()
        equity_curves[test_year] = cum

    # === Save tables ===
    pd.DataFrame(per_year_records).to_csv(OUT_DIR / "per_year_summary.csv", index=False, float_format="%.4f")
    pd.DataFrame(per_threshold_records).to_csv(OUT_DIR / "per_year_by_threshold.csv", index=False, float_format="%.4f")
    pd.DataFrame(per_decile_records).to_csv(OUT_DIR / "per_year_by_top_pct.csv", index=False, float_format="%.4f")

    # === Aggregate across years (only OK rows) ===
    deciles_df = pd.DataFrame(per_decile_records)
    pivot = deciles_df.pivot_table(index="top_pct", columns="test_year",
                                    values="precision", aggfunc="first")
    pivot["mean"] = pivot.mean(axis=1)
    pivot["min"] = pivot[TEST_YEARS].min(axis=1)
    pivot["max"] = pivot[TEST_YEARS].max(axis=1)
    pivot.to_csv(OUT_DIR / "top_pct_precision_pivot.csv", float_format="%.4f")
    print("\nTop-N precision pivot (rows=top_pct, cols=year):")
    print(pivot.to_string(float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # === Plots ===
    # 1) Equity curves at threshold 0.7 — one line per test year, normalized to start at 0.
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = plt.cm.viridis(np.linspace(0, 0.85, len(TEST_YEARS)))
    for year, color in zip(TEST_YEARS, colors):
        if year not in equity_curves:
            continue
        cum = equity_curves[year]
        ax.plot(np.arange(len(cum)), cum, label=f"test_year={year} ({int(len(cum))} events)", color=color, linewidth=1.5)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_title(f"Proxy R-curve at threshold 0.7 (one line per test year)\n{LABEL}, side={SIDE}")
    ax.set_xlabel("event index within year")
    ax.set_ylabel("cumulative R")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "equity_curves_by_year.png", dpi=120)
    plt.close(fig)

    # 2) Top-N precision bar chart by year — shows whether 2025 stands alone.
    fig, ax = plt.subplots(figsize=(12, 6))
    top_pcts_to_plot = [0.05, 0.10, 0.20, 0.50]
    width = 0.2
    x = np.arange(len(TEST_YEARS))
    for i, top_pct in enumerate(top_pcts_to_plot):
        precisions = []
        for year in TEST_YEARS:
            row = deciles_df[(deciles_df["test_year"] == year) & (deciles_df["top_pct"] == top_pct)]
            precisions.append(float(row["precision"].iloc[0]) if len(row) else np.nan)
        ax.bar(x + i * width, precisions, width, label=f"top {int(top_pct*100)}%")
    # Add base-rate reference line per year.
    base_rates = [r["test_base_rate"] for r in per_year_records if r.get("status") == "ok"]
    if len(base_rates) == len(TEST_YEARS):
        for xi, br in zip(x, base_rates):
            ax.plot([xi - 0.1, xi + len(top_pcts_to_plot) * width - 0.1], [br, br], color="red", linestyle="--", linewidth=1)
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels([str(y) for y in TEST_YEARS])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("precision")
    ax.set_title(f"Top-N model score precision by test year (red dashed = per-year base rate)\n{LABEL}, side={SIDE}")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "top_pct_precision_by_year.png", dpi=120)
    plt.close(fig)

    # === Verdict ===
    top10 = deciles_df[deciles_df["top_pct"] == 0.10]
    top10_precs = top10["precision"].dropna()
    top10_mean = float(top10_precs.mean()) if len(top10_precs) else None
    top10_min = float(top10_precs.min()) if len(top10_precs) else None
    top10_n_years_above_85 = int((top10_precs >= 0.85).sum())

    verdict = {
        "label": LABEL,
        "matrix": MATRIX.name,
        "side": SIDE,
        "test_years": TEST_YEARS,
        "n_years_ok": int(sum(1 for r in per_year_records if r.get("status") == "ok")),
        "top_10pct_precision_mean": top10_mean,
        "top_10pct_precision_min": top10_min,
        "top_10pct_years_above_85pct": top10_n_years_above_85,
        "verdict": (
            "ROBUST — top-10% precision >= 0.85 in >= 5 of 6 years"
            if top10_n_years_above_85 >= 5
            else "MIXED — top-10% holds in some years but not all"
            if top10_n_years_above_85 >= 3
            else "NOT ROBUST — top-10% rarely beats baseline strongly"
        ),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "verdict.json").write_text(json.dumps(verdict, indent=2), encoding="utf-8")
    print("\n=== VERDICT ===")
    print(json.dumps(verdict, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
