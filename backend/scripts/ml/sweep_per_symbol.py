"""Per-symbol breakdown of sweep_failed_recovered.

Mirrors v3 of resistance_rejection. Trains a fresh model for each
test year on the sweep_failed_recovered label (side=all), then splits
the test-year scoring by primary symbol. Answers: is the sweep edge
ES-driven (like resistance_rejection_3bar), all-symbol (like SMT),
or something else?
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
EXPORT = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_sweep")
ANCHORS = EXPORT / "data" / "ml" / "anchors"
MATRIX = ANCHORS / "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict.parquet"
SCHEMA = ANCHORS / "sweep_snapshots_xctx_fvggeom_obgeom_liqgeom_regime_strict.schema.json"

LABEL = "label.strict.next_60m.sweep_failed_recovered"
SIDE = "all"
SNAPSHOT = "at_fire"
SYMBOL_COL = "anchor.primary_symbol"
SYMBOLS = ["NQ.c.0", "ES.c.0", "YM.c.0"]
TEST_YEARS = [2020, 2021, 2022, 2023, 2024, 2025]
TOP_DECILES = [0.10, 0.20, 0.50]

OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-15_sweep_per_symbol"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> int:
    print(f"loading: {MATRIX.name}")
    schema = load_schema(SCHEMA)
    feature_pool = schema_safe_feature_columns(schema, include_manual_cell=False)
    assert_no_label_leak(feature_pool)
    df_full = pd.read_parquet(MATRIX)
    df = filter_matrix(df_full, snapshot=SNAPSHOT, side=SIDE, event_type="all")
    y_series = coerce_binary_label(df[LABEL])
    df = df.loc[y_series.notna()].copy()
    y = y_series.loc[df.index].astype(int).to_numpy()
    years = extract_years(df)
    symbols = df[SYMBOL_COL].to_numpy()
    print(f"  rows {len(df):,}  base rate {y.mean():.3f}")
    for s in SYMBOLS:
        m = symbols == s
        print(f"    {s}: n={int(m.sum()):,}  pos={int(y[m].sum()):,}  rate={(y[m].mean() if m.any() else 0):.3f}")

    device_info = resolve_device("auto")
    records = []
    for ty in TEST_YEARS:
        result = run_fold(df=df, years=years, y=y, label=LABEL,
                          feature_pool=feature_pool, test_year=ty, device=device_info.resolved)
        if result["status"] != "ok":
            continue
        preds = result["predictions"]
        y_true = preds["y_true"].to_numpy()
        p_test = preds["p_test"].to_numpy()
        test_idx = preds["row_index"].to_numpy()
        test_symbols = df.loc[test_idx, SYMBOL_COL].to_numpy()
        for sym in SYMBOLS + ["pooled"]:
            mask = np.ones(len(test_idx), dtype=bool) if sym == "pooled" else (test_symbols == sym)
            n_sym = int(mask.sum())
            if n_sym == 0:
                continue
            y_sym = y_true[mask]
            p_sym = p_test[mask]
            sym_base = float(y_sym.mean())
            ranked = np.argsort(-p_sym)
            for top_pct in TOP_DECILES:
                k = max(1, int(round(len(ranked) * top_pct)))
                idx = ranked[:k]
                prec = float(y_sym[idx].mean())
                edge = prec - sym_base
                cum_r = float(2 * y_sym[idx].sum() - k)
                records.append({
                    "test_year": ty, "symbol": sym, "top_pct": top_pct,
                    "n_total": n_sym, "n_signals": k,
                    "base_rate": sym_base, "precision": prec, "edge_vs_base": edge,
                    "cum_r": cum_r,
                })
        print(f"  year {ty}: ok ({len(test_idx)} test rows)")

    out_df = pd.DataFrame(records)
    out_df.to_csv(OUT_DIR / "per_symbol_per_year.csv", index=False, float_format="%.4f")

    agg = out_df.groupby(["symbol", "top_pct"]).agg(
        mean_precision=("precision", "mean"),
        mean_base_rate=("base_rate", "mean"),
        mean_edge=("edge_vs_base", "mean"),
        min_precision=("precision", "min"),
        min_edge=("edge_vs_base", "min"),
        years=("precision", "count"),
        total_signals=("n_signals", "sum"),
    ).reset_index()
    agg.to_csv(OUT_DIR / "per_symbol_aggregate.csv", index=False, float_format="%.4f")
    print("\nPer-symbol aggregate (mean across 6 test years):")
    print(agg.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Plot top-10% precision per (symbol, year).
    top10 = out_df[out_df["top_pct"] == 0.10]
    fig, ax = plt.subplots(figsize=(12, 6))
    width = 0.2
    x = np.arange(len(TEST_YEARS))
    for i, sym in enumerate(SYMBOLS + ["pooled"]):
        precs = []
        for year in TEST_YEARS:
            row = top10[(top10["test_year"] == year) & (top10["symbol"] == sym)]
            precs.append(float(row["precision"].iloc[0]) if len(row) else np.nan)
        ax.bar(x + i * width, precs, width, label=sym)
    ax.set_xticks(x + width * 1.5)
    ax.set_xticklabels([str(y) for y in TEST_YEARS])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("top-10% precision")
    ax.set_title(f"sweep_failed_recovered top-10% precision by symbol × year\n{LABEL}")
    ax.legend(loc="lower right")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "top10_precision_by_symbol_year.png", dpi=120)
    plt.close(fig)

    by_symbol = agg[agg["top_pct"] == 0.10].set_index("symbol")
    verdict = {
        "label": LABEL,
        "test_years": TEST_YEARS,
        "per_symbol_top10": {
            sym: {
                "mean_precision": float(by_symbol.loc[sym, "mean_precision"]),
                "min_precision": float(by_symbol.loc[sym, "min_precision"]),
                "mean_edge": float(by_symbol.loc[sym, "mean_edge"]),
                "min_edge": float(by_symbol.loc[sym, "min_edge"]),
                "total_signals_over_6yr": int(by_symbol.loc[sym, "total_signals"]),
            }
            for sym in by_symbol.index
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "verdict.json").write_text(json.dumps(verdict, indent=2), encoding="utf-8")
    print("\n=== VERDICT ===")
    print(json.dumps(verdict, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
