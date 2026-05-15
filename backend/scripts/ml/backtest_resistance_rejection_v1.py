"""First-pass proxy backtest of the top-ranked ML signal.

Target: label.next_60m.resistance_rejection_3bar (opening_gap broad
matrix). The 112-config scoreboard ranked this #1 on top-bucket lift
over base rate (+0.613). This script tests whether high-confidence
model signals translate into a positive R-multiple equity curve when
traded blindly with synthetic +/-1R outcomes.

Method:
  - Load opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime.parquet
  - Filter side=gap_up, snapshot=at_fire (rejection-from-resistance
    direction makes sense only on gap_ups -- we'd short the rejection)
  - Walk-forward fold: train <= 2023, val 2024, test 2025
  - Train GPU XGBoost with the project's standard hyperparameters
  - For test-year predictions, compute precision/recall/R-curve at
    thresholds 0.5, 0.6, 0.7, 0.8, 0.9
  - Compare to baseline of "trade every gap_up blindly" in 2025

This is a PROXY backtest: +1R on correct prediction, -1R on incorrect.
Real P&L (with OHLCV stops/targets) is a separate follow-up build.
"""

from __future__ import annotations

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
SIDE = "gap_down"  # resistance_rejection_3bar is only non-zero on gap_down rows
SNAPSHOT = "at_fire"
TEST_YEAR = 2025
THRESHOLDS = [0.5, 0.6, 0.7, 0.8, 0.9]
# Top-N decile bands for "precision at top of model score distribution" reporting.
TOP_DECILES = [0.01, 0.05, 0.10, 0.20, 0.50]

OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-15_resistance_rejection_v1"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _proxy_pnl(y_true: np.ndarray, predicted: np.ndarray) -> np.ndarray:
    """+1R when predicted==1 and y_true==1, -1R when predicted==1 and y_true==0."""
    # Trades only fire when we said "yes". Skip otherwise.
    pnl = np.where(predicted == 1, np.where(y_true == 1, 1.0, -1.0), 0.0)
    return pnl


def main() -> int:
    print(f"loading matrix: {MATRIX.name}")
    schema = load_schema(SCHEMA)
    feature_pool = schema_safe_feature_columns(schema, include_manual_cell=False)
    assert_no_label_leak(feature_pool)
    df_full = pd.read_parquet(MATRIX)
    df = filter_matrix(df_full, snapshot=SNAPSHOT, side=SIDE, event_type="all")
    print(f"  filtered rows: {len(df):,}  (snapshot={SNAPSHOT} side={SIDE})")
    if LABEL not in df.columns:
        raise KeyError(f"label column missing: {LABEL}")
    y_series = coerce_binary_label(df[LABEL])
    df = df.loc[y_series.notna()].copy()
    y = y_series.loc[df.index].astype(int).to_numpy()
    years = extract_years(df)
    print(f"  rows w/ valid label: {len(df):,}")
    print(f"  year span: {int(years.min())} - {int(years.max())}")
    print(f"  base rate (overall): {y.mean():.3f}")

    device_info = resolve_device("auto")
    print(f"  device: {device_info.resolved}  xgb: {device_info.xgboost_version}")

    # Single fold.
    print(f"training single fold test_year={TEST_YEAR} ...")
    result = run_fold(
        df=df, years=years, y=y, label=LABEL,
        feature_pool=feature_pool, test_year=TEST_YEAR, device=device_info.resolved,
    )
    if result["status"] != "ok":
        print(f"!! fold not ok: {result['status']}")
        return 1
    preds = result["predictions"]  # cols: fold_test_year, row_index, y_true, p_test
    rec = result["record"]
    print(f"  train rows: {rec['n_train']:,}   val: {rec['n_val']:,}   test: {rec['n_test']:,}")
    print(f"  test AUC: {rec['auc_test']:.3f}   base rate (test): {rec['base_rate_test']:.3f}")
    test_base_rate = float(rec["base_rate_test"])

    # Test-row index into the original df for time-axis plotting.
    test_idx = preds["row_index"].to_numpy()
    test_rows = df.loc[test_idx].copy()
    test_rows["y_true"] = preds["y_true"].to_numpy()
    test_rows["p_test"] = preds["p_test"].to_numpy()

    # Look up a usable timestamp column for time-axis.
    time_col = None
    for cand in ["ts.bar_end_utc", "anchor.bar_end_utc", "ts.bar_start_utc", "anchor.event_ts"]:
        if cand in test_rows.columns:
            time_col = cand
            break
    if time_col:
        test_rows["_ts"] = pd.to_datetime(test_rows[time_col], errors="coerce", utc=True)
    else:
        test_rows["_ts"] = pd.NaT
    test_rows = test_rows.sort_values("_ts").reset_index(drop=True)

    # Per-threshold table.
    summary_rows = []
    for thr in THRESHOLDS:
        predicted = (test_rows["p_test"].to_numpy() >= thr).astype(int)
        n_signals = int(predicted.sum())
        if n_signals == 0:
            summary_rows.append({
                "threshold": thr, "n_signals": 0,
                "precision": None, "recall": None,
                "cum_r": 0.0, "avg_r": None,
            })
            continue
        y_true = test_rows["y_true"].to_numpy()
        hits = int(((predicted == 1) & (y_true == 1)).sum())
        precision = hits / n_signals
        recall = hits / max(1, int(y_true.sum()))
        pnl = _proxy_pnl(y_true, predicted)
        cum_r = float(pnl.sum())
        avg_r = cum_r / n_signals
        summary_rows.append({
            "threshold": thr, "n_signals": n_signals,
            "precision": precision, "recall": recall,
            "cum_r": cum_r, "avg_r": avg_r,
        })

    summary = pd.DataFrame(summary_rows)
    summary_path = OUT_DIR / "summary_by_threshold.csv"
    summary.to_csv(summary_path, index=False, float_format="%.4f")
    print("\nSummary by threshold:")
    print(summary.to_string(index=False, float_format=lambda x: f"{x:.4f}" if isinstance(x, float) else str(x)))

    # Top-N decile precision (the cleaner edge metric when base rate is high).
    p_test = test_rows["p_test"].to_numpy()
    y_test = test_rows["y_true"].to_numpy()
    ranked = np.argsort(-p_test)  # descending
    decile_rows = []
    for top_pct in TOP_DECILES:
        n = max(1, int(round(len(ranked) * top_pct)))
        idx = ranked[:n]
        y_top = y_test[idx]
        prec = float(y_top.mean())
        # Edge over base rate: signed lift.
        edge = prec - test_base_rate
        # Cum R if we traded all in this band: +1R per hit, -1R per miss.
        cum_r = float(2 * y_top.sum() - n)
        decile_rows.append({
            "top_pct": top_pct, "n_signals": n,
            "precision": prec, "edge_vs_base": edge,
            "cum_r": cum_r, "avg_r": cum_r / n,
        })
    deciles = pd.DataFrame(decile_rows)
    deciles_path = OUT_DIR / "summary_by_top_pct.csv"
    deciles.to_csv(deciles_path, index=False, float_format="%.4f")
    print("\nTop-N decile precision (edge over base rate):")
    print(deciles.to_string(index=False, float_format=lambda x: f"{x:.4f}" if isinstance(x, float) else str(x)))

    # Baseline: trade every gap_up blindly (predict 1 always).
    blind_predicted = np.ones_like(test_rows["y_true"].to_numpy())
    blind_pnl = _proxy_pnl(test_rows["y_true"].to_numpy(), blind_predicted)
    blind_cum_r = float(blind_pnl.sum())
    blind_n = int(blind_predicted.sum())
    blind_precision = float(test_rows["y_true"].mean())
    print(f"\nBaseline 'trade every gap_up blindly': n={blind_n} precision={blind_precision:.3f} cum_R={blind_cum_r:+.1f} avg_R={blind_cum_r/blind_n:+.3f}")

    # Pick the threshold with highest cum_R with at least 5 signals.
    eligible = summary[(summary["n_signals"] >= 5) & summary["cum_r"].notna()]
    if len(eligible) == 0:
        best = summary.iloc[summary["cum_r"].idxmax()]
    else:
        best = eligible.loc[eligible["cum_r"].idxmax()]
    print(f"\nBest threshold (n>=5): {best['threshold']:.2f}  n={int(best['n_signals'])}  precision={best['precision']:.3f}  cum_R={best['cum_r']:+.1f}")

    # === Plots ===
    # 1) R-multiple equity curve across thresholds.
    fig, ax = plt.subplots(figsize=(12, 5))
    x_vals = test_rows["_ts"] if test_rows["_ts"].notna().any() else np.arange(len(test_rows))
    for thr in THRESHOLDS:
        predicted = (test_rows["p_test"].to_numpy() >= thr).astype(int)
        pnl = _proxy_pnl(test_rows["y_true"].to_numpy(), predicted)
        cum = pnl.cumsum()
        ax.plot(x_vals, cum, label=f"thr={thr} (n={int(predicted.sum())})", linewidth=1.5)
    # Blind baseline.
    blind_cum = blind_pnl.cumsum()
    ax.plot(x_vals, blind_cum, label=f"blind gap_up (n={blind_n})", linewidth=1.5, linestyle="--", color="gray")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_title(f"R-multiple equity — {LABEL}\nside={SIDE}, test_year={TEST_YEAR}")
    ax.set_xlabel("event time" if test_rows["_ts"].notna().any() else "event index")
    ax.set_ylabel("cumulative R")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    eq_path = OUT_DIR / "equity_curve.png"
    fig.savefig(eq_path, dpi=120)
    plt.close(fig)
    print(f"wrote {eq_path}")

    # 2) Signal density over time (best threshold).
    best_thr = float(best["threshold"])
    predicted_best = (test_rows["p_test"].to_numpy() >= best_thr).astype(int)
    fig, ax = plt.subplots(figsize=(12, 4))
    sig_ts = test_rows.loc[predicted_best == 1, "_ts"]
    if sig_ts.notna().any():
        sig_ts = sig_ts.dropna()
        # Monthly histogram.
        monthly = sig_ts.dt.to_period("M").value_counts().sort_index()
        ax.bar(monthly.index.astype(str), monthly.values, color="steelblue")
        ax.set_title(f"Signal density (monthly) at threshold {best_thr:.2f} — n_total={int(predicted_best.sum())}")
        ax.set_xlabel("month")
        ax.set_ylabel("# signals")
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    else:
        ax.text(0.5, 0.5, "no timestamps available", ha="center", va="center", transform=ax.transAxes)
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    sd_path = OUT_DIR / "signal_density.png"
    fig.savefig(sd_path, dpi=120)
    plt.close(fig)
    print(f"wrote {sd_path}")

    # 3) Per-signal trade log.
    log_rows = []
    for thr in THRESHOLDS:
        predicted = (test_rows["p_test"].to_numpy() >= thr).astype(int)
        rows = test_rows.loc[predicted == 1, ["_ts", "y_true", "p_test"]].copy()
        rows["threshold"] = thr
        rows["pnl_r"] = np.where(rows["y_true"] == 1, 1.0, -1.0)
        log_rows.append(rows)
    if log_rows:
        trade_log = pd.concat(log_rows, ignore_index=True)
        log_path = OUT_DIR / "trade_log.csv"
        trade_log.to_csv(log_path, index=False, float_format="%.4f")
        print(f"wrote {log_path} ({len(trade_log)} rows across all thresholds)")

    # 4) Summary metadata for the writeup.
    meta = {
        "label": LABEL,
        "matrix": MATRIX.name,
        "side": SIDE,
        "snapshot": SNAPSHOT,
        "test_year": TEST_YEAR,
        "n_train": int(rec["n_train"]),
        "n_val": int(rec["n_val"]),
        "n_test": int(rec["n_test"]),
        "test_auc": float(rec["auc_test"]),
        "test_base_rate": test_base_rate,
        "blind_n": blind_n,
        "blind_precision": blind_precision,
        "blind_cum_r": blind_cum_r,
        "best_threshold": float(best["threshold"]),
        "best_n_signals": int(best["n_signals"]),
        "best_precision": float(best["precision"]),
        "best_cum_r": float(best["cum_r"]),
        "best_avg_r": float(best["avg_r"]),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    import json
    meta_path = OUT_DIR / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"wrote {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
