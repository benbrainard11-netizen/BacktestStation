"""V6: add strict swing pivot to the v5-winner portfolio.

247 shipped strategy-lab-core-2026-05-15-strict-swing-pivot with 9 new
strict swing labels. The strongest per their walk-forward:
  label.strict.next_60m.pivot_broken_through_continuation   AUC 0.804
  label.strict.next_240m.pivot_broken_through_continuation  AUC 0.792
  label.strict.next_60m.pivot_failed_immediately            AUC 0.775

This script adds the top swing signal as a 4th independent family to
the v5-winner portfolio (already has 3 OGAP signals after dropping
SMT/sweep/YM). Runs the same v5-winner config + a few variants.

Key change: NEW direction rule "continuation"
  side=high  → long (broke through resistance, continuation up)
  side=low   → short (broke through support, continuation down)
This is OPPOSITE the existing "side_aware" rule which is mean-reversion.

Then asks: does adding swing improve the v5 +110R (no-YM) result?
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
from scripts.ml.rigorous_backtest_v2_matrix import (
    Config, simulate_trade_cfg, _apply_consensus_filter,
)
from scripts.ml.rigorous_backtest_v1 import (
    BarsCache, SIGNALS as OLD_SIGNALS, Signal, TEST_YEARS, TOP_PCT,
    SYMBOL_COL, SIDE_COL, TIME_COL_CANDIDATES,
)
from scripts.ml.gpu_train_pipeline import filter_matrix, run_fold
from scripts.ml.gpu_train_schema_safe import (
    assert_no_label_leak, coerce_binary_label,
    load_schema, schema_safe_feature_columns,
)
from scripts.ml.gpu_train_walk_forward import extract_years
from scripts.ml.gpu_train_xgb import resolve_device

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
ANCHORS_REACT = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_reactions") / "data" / "ml" / "anchors"
ANCHORS_SWEEP = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_sweep") / "data" / "ml" / "anchors"
ANCHORS_SWING = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_swing_pivot") / "data" / "ml" / "anchors"
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-16_rigorous_v6_with_swing"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Override resolve_direction so we can add "continuation" rule for swing.
def resolve_direction_v6(rule: str, side: str) -> str:
    if rule == "fixed_short":
        return "short"
    if rule == "fixed_long":
        return "long"
    if rule == "continuation":
        # Break-through continuation: high→long, low→short
        if side == "high":
            return "long"
        if side == "low":
            return "short"
        return "short"
    # side_aware (mean-reversion at level):
    if side in ("gap_down", "high"):
        return "short"
    if side in ("gap_up", "low"):
        return "long"
    return "short"


# === Signals ===
# v5-winner used: ogap_gap_down_rejection, ogap_gap_up_rejection,
# ogap_strict_partial_touch  (3 OGAP signals; SMT + sweep dropped, YM filtered).
# v6 adds swing_broken_60m and swing_broken_240m (or single).
SIGNALS_V6 = [
    Signal("ogap_gap_down_rejection", ANCHORS_REACT,
           "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime",
           "at_fire", "gap_down", "label.next_60m.resistance_rejection_3bar", "fixed_short"),
    Signal("ogap_gap_up_rejection", ANCHORS_REACT,
           "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime",
           "at_fire", "gap_up", "label.next_60m.support_rejection_3bar", "fixed_long"),
    Signal("ogap_strict_partial_touch", ANCHORS_REACT,
           "opening_gap_snapshots_xctx_gapctx_obgeom_liqgeom_regime_strict",
           "at_fire", "all", "label.strict.next_60m.partial_touch_rejected", "side_aware"),
    Signal("swing_broken_60m", ANCHORS_SWING,
           "swing_snapshots_strict",
           "at_fire", "all", "label.strict.next_60m.pivot_broken_through_continuation", "continuation"),
    Signal("swing_broken_240m", ANCHORS_SWING,
           "swing_snapshots_strict",
           "at_fire", "all", "label.strict.next_240m.pivot_broken_through_continuation", "continuation"),
]


# V5-winner config (the baseline before swing).
V5_WINNER_CFG = Config(
    name="v5_winner_baseline",
    description="V5 winner: stop=2.0 ATR / target=4.0 ATR / tw=240, consensus + drop SMT/sweep",
    wait_for_confirmation=True,
    stop_atr_mult=2.0, target_atr_mult=4.0, trade_window_min=240,
    require_consensus=True,
    excluded_signals=(),  # we'll filter signal list directly instead
)

# V6 configs to test.
V6_CONFIGS = [
    Config("v6a_add_swing_60m_only", "v5 winner + swing_broken_60m only (4 signals)",
           wait_for_confirmation=True, stop_atr_mult=2.0, target_atr_mult=4.0,
           trade_window_min=240, require_consensus=True, excluded_signals=("swing_broken_240m",)),
    Config("v6b_add_swing_both", "v5 winner + both swing horizons (5 signals)",
           wait_for_confirmation=True, stop_atr_mult=2.0, target_atr_mult=4.0,
           trade_window_min=240, require_consensus=True, excluded_signals=()),
    Config("v6c_add_swing_240m_only", "v5 winner + swing_broken_240m only (4 signals)",
           wait_for_confirmation=True, stop_atr_mult=2.0, target_atr_mult=4.0,
           trade_window_min=240, require_consensus=True, excluded_signals=("swing_broken_60m",)),
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
    time_col = next((c for c in TIME_COL_CANDIDATES if c in test_rows.columns), None)
    if time_col is None:
        return pd.DataFrame()
    test_rows["fire_ts"] = pd.to_datetime(test_rows[time_col], errors="coerce", utc=True)
    test_rows["symbol"] = test_rows[SYMBOL_COL]
    test_rows["anchor_side"] = test_rows.get(SIDE_COL, "?")
    test_rows["test_year"] = test_year
    test_rows["signal_name"] = sig.name
    test_rows["direction_rule"] = sig.direction_rule
    k = max(1, int(round(len(test_rows) * TOP_PCT)))
    test_rows["top_10pct"] = test_rows["p_test"].rank(ascending=False, method="first") <= k
    return test_rows.loc[test_rows["top_10pct"], ["test_year", "signal_name", "fire_ts",
                                                    "symbol", "anchor_side", "p_test", "y_true",
                                                    "direction_rule"]].reset_index(drop=True)


def run_with_v6_signals(cfg: Config, picks_all: pd.DataFrame, bars: BarsCache,
                          symbols_keep: tuple[str, ...] = ("NQ.c.0", "ES.c.0")) -> pd.DataFrame:
    """Run a config across v6 picks, filtering YM out (no-YM)."""
    picks = picks_all
    if cfg.excluded_signals:
        picks = picks[~picks["signal_name"].isin(cfg.excluded_signals)]
    if cfg.require_consensus:
        picks = _apply_consensus_filter(picks)
    # Drop YM trades.
    picks = picks[picks["symbol"].isin(symbols_keep)].copy()
    picks["direction"] = picks.apply(
        lambda r: resolve_direction_v6(r["direction_rule"], r["anchor_side"]), axis=1
    )
    trades = []
    for _, row in picks.iterrows():
        if pd.isna(row["fire_ts"]):
            continue
        sim = simulate_trade_cfg(bars, row["symbol"], row["fire_ts"], row["direction"], cfg)
        trades.append({
            "config": cfg.name,
            "signal": row["signal_name"],
            "test_year": int(row["test_year"]),
            "symbol": row["symbol"],
            "anchor_side": row["anchor_side"],
            "direction": row["direction"],
            "fire_ts": row["fire_ts"],
            "p_test": float(row["p_test"]),
            "label_y_true": int(row["y_true"]),
            **sim,
        })
    return pd.DataFrame(trades)


def main() -> int:
    device_info = resolve_device("auto")
    print(f"device: {device_info.resolved}")
    print(f"output: {OUT_DIR}\n")
    overall_t0 = time_mod.time()

    # Step 1: train all v6 signals (3 OGAP + 2 swing) × 6 years.
    print("Step 1: train v6 signals × 6 years...")
    picks_records = []
    for sig in SIGNALS_V6:
        for ty in TEST_YEARS:
            t0 = time_mod.time()
            df = _train_and_score(sig, device_info.resolved, ty)
            if not df.empty:
                picks_records.append(df)
                print(f"  {sig.name:<30} year={ty}: {len(df)} picks ({time_mod.time()-t0:.0f}s)")
            else:
                print(f"  {sig.name:<30} year={ty}: NO PICKS")
    picks_all = pd.concat(picks_records, ignore_index=True)
    print(f"\n  total picks across all v6 signals × years: {len(picks_all):,}")
    picks_all.to_csv(OUT_DIR / "all_picks.csv", index=False, float_format="%.4f")

    # Step 2: also build v5 baseline (no swing) for comparison.
    print("\nStep 2: run v5 baseline + 3 v6 variants...")
    bars = BarsCache()

    # Baseline: same trades as v5 winner no-YM (only the 3 OGAP signals).
    v5_picks = picks_all[~picks_all["signal_name"].isin(["swing_broken_60m", "swing_broken_240m"])]
    v5_trades = run_with_v6_signals(V5_WINNER_CFG, v5_picks, bars)
    v5_exec = v5_trades[v5_trades["exit_reason"].isin(["target", "stop", "time_exit"])]
    print(f"  v5_baseline (no swing):    n={len(v5_exec)} cum_R={v5_exec['pnl_r'].sum():+.1f} win%={(v5_exec['pnl_r']>0).mean():.3f}")

    all_trades = [v5_trades.assign(config="v5_baseline")]
    for cfg in V6_CONFIGS:
        td = run_with_v6_signals(cfg, picks_all, bars)
        ex = td[td["exit_reason"].isin(["target", "stop", "time_exit"])]
        print(f"  {cfg.name:<30} n={len(ex):4d} cum_R={ex['pnl_r'].sum():+7.1f} win%={(ex['pnl_r']>0).mean():.3f}")
        all_trades.append(td)
    combined = pd.concat(all_trades, ignore_index=True)
    combined.to_csv(OUT_DIR / "all_trades.csv", index=False, float_format="%.4f")

    # Step 3: per-config × per-year breakdown.
    print("\n=== Per-config × per-year cum_R ===")
    exec_all = combined[combined["exit_reason"].isin(["target", "stop", "time_exit"])].copy()
    pivot = exec_all.pivot_table(index=["config", "test_year"], values="pnl_r", aggfunc="sum").reset_index()
    wide = pivot.pivot(index="config", columns="test_year", values="pnl_r").fillna(0)
    wide["total"] = wide.sum(axis=1)
    wide["years_positive"] = (wide.drop(columns=["total"]) > 0).sum(axis=1)
    wide.to_csv(OUT_DIR / "per_config_per_year.csv", float_format="%.4f")
    print(wide.to_string(float_format=lambda x: f"{x:.2f}"))

    # Step 4: rollup.
    rollup_rows = []
    for cfg_name, g in exec_all.groupby("config"):
        n = len(g)
        wins = int((g["pnl_r"] > 0).sum())
        cum_r = float(g["pnl_r"].sum())
        cumr_series = g.sort_values("fire_ts")["pnl_r"].cumsum()
        max_dd = float((cumr_series.cummax() - cumr_series).max())
        years_pos = int(g.groupby("test_year")["pnl_r"].sum().gt(0).sum())
        rollup_rows.append({
            "config": cfg_name, "n_trades": n, "wins": wins,
            "win_rate": wins / n, "cum_r": cum_r, "avg_r": cum_r / n,
            "max_dd_r": max_dd, "years_positive": years_pos,
            "years_total": int(g["test_year"].nunique()),
        })
    rollup_df = pd.DataFrame(rollup_rows).sort_values("cum_r", ascending=False)
    rollup_df.to_csv(OUT_DIR / "rollup.csv", index=False, float_format="%.4f")
    print("\n=== Rollup ===")
    print(rollup_df.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Step 5: equity curves overlaid.
    fig, ax = plt.subplots(figsize=(13, 7))
    for cfg_name, g in exec_all.groupby("config"):
        g_sorted = g.sort_values("fire_ts").copy()
        g_sorted["cum_r"] = g_sorted["pnl_r"].cumsum()
        ax.plot(g_sorted["fire_ts"], g_sorted["cum_r"],
                label=f"{cfg_name} (n={len(g_sorted)}, R={g_sorted['cum_r'].iloc[-1]:+.0f})", linewidth=1.5)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("date")
    ax.set_ylabel("cumulative R")
    ax.set_title("V6 — adding swing strict to the v5-winner portfolio\n(stop=2.0 ATR, target=4.0 ATR, tw=240min, consensus + NQ/ES only)")
    ax.legend(loc="best", fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "v6_equity_compare.png", dpi=120)
    plt.close(fig)

    elapsed = time_mod.time() - overall_t0
    summary = {
        "v5_baseline_cum_r": float(rollup_df.loc[rollup_df["config"] == "v5_baseline", "cum_r"].iloc[0]),
        "best_v6_config": rollup_df.iloc[0]["config"] if rollup_df.iloc[0]["config"] != "v5_baseline" else (rollup_df.iloc[1]["config"] if len(rollup_df) > 1 else None),
        "best_v6_cum_r": float(rollup_df.iloc[0]["cum_r"]),
        "elapsed_min": round(elapsed / 60, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\n=== DONE in {elapsed/60:.1f} min ===")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
