"""Cross-asset v5-baseline screening test.

The 22-symbol local opening_gap matrix was rebuilt overnight. Now we
can answer: does the gap-rejection edge generalize across asset
classes, or is it index-specific?

Trains two models per test year on the local 22-symbol broad-label
opening_gap matrix:
  gap_down side → predict label.next_60m.resistance_rejection_3bar
  gap_up side   → predict label.next_60m.support_rejection_3bar

For each symbol × signal, computes top-10% precision and runs v8a-style
trades (vol-floored stops, 5×ATR target, 240-min window). NO consensus
filter (impossible — gap_down/gap_up never fire on same date+symbol).

Output: per-symbol heatmap of cum_R + win rate across all 22 contracts.
"""

from __future__ import annotations

import json
import sys
import time as time_mod
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
from scripts.ml.rigorous_backtest_v1 import BarsCache, TEST_YEARS, TOP_PCT, SYMBOL_COL, SIDE_COL, TIME_COL_CANDIDATES
from scripts.ml.rigorous_backtest_v7_stops import StopVariant, simulate_v7

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
LOCAL_MATRIX = ROOT / "data" / "ml" / "anchors" / "opening_gap_snapshots_xctx_gapctx.parquet"
LOCAL_SCHEMA = ROOT / "data" / "ml" / "anchors" / "opening_gap_snapshots_xctx_gapctx.schema.json"
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-16_cross_asset_screening"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# v8a stop variant (vol-floored, 5×ATR target, 240min).
V8A_VARIANT = StopVariant(
    name="v8a_cross_asset",
    description="v8a (vol-floored stop, 5×ATR target, 240min)",
    stop_atr_mult=2.0, target_atr_mult=5.0, trade_window_min=240,
    atr_timeframe_min=5, atr_floor_timeframe_min=30, atr_floor_mult=1.5,
)

CONFIGS = [
    ("gap_down_rejection", "gap_down", "label.next_60m.resistance_rejection_3bar", "short"),
    ("gap_up_rejection",   "gap_up",   "label.next_60m.support_rejection_3bar",    "long"),
]


def train_score(matrix_path: Path, schema_path: Path, side: str, label: str,
                device: str, test_year: int) -> pd.DataFrame:
    schema = load_schema(schema_path)
    feature_pool = schema_safe_feature_columns(schema, include_manual_cell=False)
    assert_no_label_leak(feature_pool)
    df = pd.read_parquet(matrix_path)
    df = filter_matrix(df, snapshot="at_fire", side=side, event_type="all")
    if label not in df.columns:
        return pd.DataFrame()
    y_series = coerce_binary_label(df[label])
    df = df.loc[y_series.notna()].copy()
    y = y_series.loc[df.index].astype(int).to_numpy()
    years = extract_years(df)
    result = run_fold(df=df, years=years, y=y, label=label,
                     feature_pool=feature_pool, test_year=test_year, device=device)
    if result["status"] != "ok":
        return pd.DataFrame()
    preds = result["predictions"]
    test_idx = preds["row_index"].to_numpy()
    test_rows = df.loc[test_idx].copy()
    test_rows["y_true"] = preds["y_true"].to_numpy()
    test_rows["p_test"] = preds["p_test"].to_numpy()
    time_col = next((c for c in TIME_COL_CANDIDATES if c in test_rows.columns), None)
    if time_col is None:
        return pd.DataFrame()
    test_rows["fire_ts"] = pd.to_datetime(test_rows[time_col], errors="coerce", utc=True)
    test_rows["symbol"] = test_rows[SYMBOL_COL]
    test_rows["anchor_side"] = test_rows.get(SIDE_COL, side)
    test_rows["test_year"] = test_year
    # Top-10% picks.
    k = max(1, int(round(len(test_rows) * TOP_PCT)))
    test_rows["top_10pct"] = test_rows["p_test"].rank(ascending=False, method="first") <= k
    return test_rows.loc[test_rows["top_10pct"], ["test_year", "fire_ts", "symbol",
                                                    "anchor_side", "p_test", "y_true"]].reset_index(drop=True)


def main() -> int:
    device_info = resolve_device("auto")
    print(f"device: {device_info.resolved}")
    print(f"matrix: {LOCAL_MATRIX.name}")
    print(f"output: {OUT_DIR}\n")
    t0 = time_mod.time()

    if not LOCAL_MATRIX.exists():
        print(f"MISSING: {LOCAL_MATRIX}")
        return 1

    # Step 1: train + score both signals × 6 years.
    print("Step 1: train both signals × 6 years on 22-symbol matrix...")
    all_picks = []
    for cfg_name, side, label, direction in CONFIGS:
        for ty in TEST_YEARS:
            df = train_score(LOCAL_MATRIX, LOCAL_SCHEMA, side, label, device_info.resolved, ty)
            if df.empty:
                print(f"  {cfg_name} year={ty}: no picks")
                continue
            df["signal"] = cfg_name
            df["direction"] = direction
            all_picks.append(df)
            print(f"  {cfg_name} year={ty}: {len(df)} top-10% picks")
    picks = pd.concat(all_picks, ignore_index=True)
    print(f"\n  total picks: {len(picks):,}")

    # Step 2: simulate trades on every pick.
    bars = BarsCache()
    print("\nStep 2: simulate trades with v8a rules...")
    trades = []
    for idx, row in picks.iterrows():
        if pd.isna(row["fire_ts"]):
            continue
        sim = simulate_v7(bars, row["symbol"], row["fire_ts"], row["direction"], V8A_VARIANT)
        trades.append({
            "signal": row["signal"],
            "test_year": int(row["test_year"]),
            "symbol": row["symbol"],
            "anchor_side": row["anchor_side"],
            "direction": row["direction"],
            "fire_ts": row["fire_ts"],
            "p_test": float(row["p_test"]),
            "label_y_true": int(row["y_true"]),
            **sim,
        })
    trade_df = pd.DataFrame(trades)
    trade_df.to_csv(OUT_DIR / "trades.csv", index=False, float_format="%.4f")
    executed = trade_df[trade_df["exit_reason"].isin(["target", "stop", "time_exit"])]
    print(f"  trades simulated: {len(trade_df)}, executed: {len(executed)}")

    # Step 3: per-symbol aggregate stats.
    print("\n=== Per-symbol stats (executed trades, both signals pooled) ===")
    per_sym = []
    for sym, g in executed.groupby("symbol"):
        n = len(g)
        wins = int((g["pnl_r"] > 0).sum())
        cum_r = float(g["pnl_r"].sum())
        avg_r = float(g["pnl_r"].mean())
        cumr = g.sort_values("fire_ts")["pnl_r"].cumsum()
        max_dd = float((cumr.cummax() - cumr).max())
        per_sym.append({
            "symbol": sym, "n_trades": n, "wins": wins,
            "win_rate": wins / n, "cum_r": cum_r, "avg_r": avg_r, "max_dd": max_dd,
        })
    per_sym_df = pd.DataFrame(per_sym).sort_values("cum_r", ascending=False)
    per_sym_df.to_csv(OUT_DIR / "per_symbol.csv", index=False, float_format="%.4f")
    print(per_sym_df.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Step 4: per (symbol, signal) breakdown.
    per_sig_sym = []
    for (sym, sig_name), g in executed.groupby(["symbol", "signal"]):
        n = len(g)
        wins = int((g["pnl_r"] > 0).sum())
        cum_r = float(g["pnl_r"].sum())
        per_sig_sym.append({
            "symbol": sym, "signal": sig_name, "n_trades": n,
            "wins": wins, "win_rate": wins / n if n else 0.0, "cum_r": cum_r,
            "avg_r": cum_r / n if n else 0.0,
        })
    per_sig_sym_df = pd.DataFrame(per_sig_sym).sort_values("cum_r", ascending=False)
    per_sig_sym_df.to_csv(OUT_DIR / "per_signal_per_symbol.csv", index=False, float_format="%.4f")

    # Asset-class groupings.
    asset_class = {
        "ES.c.0": "index", "NQ.c.0": "index", "YM.c.0": "index", "RTY.c.0": "index",
        "ZB.c.0": "rates", "ZN.c.0": "rates", "ZF.c.0": "rates", "ZT.c.0": "rates",
        "CL.c.0": "energy", "BZ.c.0": "energy", "HO.c.0": "energy", "RB.c.0": "energy", "NG.c.0": "energy",
        "GC.c.0": "metal", "SI.c.0": "metal", "HG.c.0": "metal", "PA.c.0": "metal", "PL.c.0": "metal",
        "ZC.c.0": "grain", "ZS.c.0": "grain", "ZW.c.0": "grain",
        "6A.c.0": "fx", "6B.c.0": "fx", "6C.c.0": "fx", "6E.c.0": "fx", "6J.c.0": "fx", "6N.c.0": "fx", "6S.c.0": "fx",
    }
    executed = executed.copy()
    executed["asset_class"] = executed["symbol"].map(asset_class).fillna("unknown")
    print("\n=== Per-asset-class stats ===")
    per_ac = []
    for ac, g in executed.groupby("asset_class"):
        n = len(g)
        wins = int((g["pnl_r"] > 0).sum())
        cum_r = float(g["pnl_r"].sum())
        per_ac.append({
            "asset_class": ac, "n_trades": n, "n_symbols": int(g["symbol"].nunique()),
            "wins": wins, "win_rate": wins / n, "cum_r": cum_r,
            "avg_r": cum_r / n,
        })
    per_ac_df = pd.DataFrame(per_ac).sort_values("cum_r", ascending=False)
    per_ac_df.to_csv(OUT_DIR / "per_asset_class.csv", index=False, float_format="%.4f")
    print(per_ac_df.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Plot: per-symbol cum_R as bar chart, colored by asset class.
    fig, ax = plt.subplots(figsize=(14, 7))
    ranked = per_sym_df.copy()
    ranked["asset_class"] = ranked["symbol"].map(asset_class).fillna("unknown")
    class_colors = {"index": "tab:blue", "rates": "tab:green", "energy": "tab:orange",
                    "metal": "tab:purple", "grain": "tab:brown", "fx": "tab:red", "unknown": "gray"}
    bars_obj = ax.bar(np.arange(len(ranked)), ranked["cum_r"].values,
                       color=[class_colors[ac] for ac in ranked["asset_class"]],
                       edgecolor="black")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xticks(np.arange(len(ranked)))
    ax.set_xticklabels(ranked["symbol"].values, rotation=45, ha="right")
    ax.set_ylabel("cum R over 6 years (v8a rules)")
    ax.set_title("Cross-asset screening — v8a rules applied to broad gap-rejection labels on 22-symbol matrix")
    # Add legend.
    from matplotlib.patches import Patch
    legend_elements = [Patch(color=v, label=k) for k, v in class_colors.items() if k != "unknown"]
    ax.legend(handles=legend_elements, loc="best")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "per_symbol_bar.png", dpi=120)
    plt.close(fig)

    summary = {
        "test_years": TEST_YEARS,
        "n_trades_total": int(len(trade_df)),
        "n_trades_executed": int(len(executed)),
        "cum_r_pooled": float(executed["pnl_r"].sum()),
        "win_rate_pooled": float((executed["pnl_r"] > 0).mean()),
        "n_symbols_positive": int((per_sym_df["cum_r"] > 0).sum()),
        "n_symbols_total": int(len(per_sym_df)),
        "asset_classes_positive": int((per_ac_df["cum_r"] > 0).sum()),
        "asset_classes_total": int(len(per_ac_df)),
        "elapsed_min": round((time_mod.time() - t0) / 60, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
