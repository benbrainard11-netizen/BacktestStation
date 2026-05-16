"""Deep-dive on the v4 grid winner: stop=1.5 / target=3.0 / tw=180.

Top question: is the +100R result robust year-to-year and per-symbol,
or did one good year / one good contract carry it?

Outputs:
  - per-year stats (n trades, win rate, cum R, max DD)
  - per-symbol stats
  - per-signal × per-year matrix
  - equity curve (chronological, full 6 years)
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
from scripts.ml.rigorous_backtest_v2_matrix import (
    Config, run_one_config, _train_and_score,
)
from scripts.ml.rigorous_backtest_v1 import BarsCache, SIGNALS, TEST_YEARS
from scripts.ml.gpu_train_xgb import resolve_device

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-15_v4_winner_deepdive"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# The winning config from v4 grid.
WINNER = Config(
    name="v4_winner_stop1.5_tgt3.0_tw180",
    description="V4 grid winner: 1.5 ATR stop, 3.0 ATR target, 180min window, consensus + drop SMT/sweep",
    wait_for_confirmation=True,
    stop_atr_mult=1.5,
    target_atr_mult=3.0,
    trade_window_min=180,
    require_consensus=True,
    excluded_signals=("smt_pd_high_thesis", "sweep_failed_recovered_all"),
)


def main() -> int:
    device_info = resolve_device("auto")
    print(f"device: {device_info.resolved}")
    print(f"output: {OUT_DIR}\n")
    t0 = time_mod.time()

    # Train + score (same as the grid).
    print("Step 1: train all signals × years...")
    picks_records = []
    for sig in SIGNALS:
        for ty in TEST_YEARS:
            df = _train_and_score(sig, device_info.resolved, ty)
            if not df.empty:
                picks_records.append(df)
    picks_all = pd.concat(picks_records, ignore_index=True)
    print(f"  total picks: {len(picks_all):,}")

    # Run winner config.
    bars = BarsCache()
    print(f"\nStep 2: run winner config...")
    trade_df = run_one_config(WINNER, picks_all, bars)
    trade_df.to_csv(OUT_DIR / "winner_trades.csv", index=False, float_format="%.4f")
    executed = trade_df[trade_df["exit_reason"].isin(["target", "stop", "time_exit"])].copy()
    print(f"  trades simulated: {len(trade_df)}, executed: {len(executed)}")
    print(f"  cum R: {executed['pnl_r'].sum():.2f}")
    print(f"  win rate: {(executed['pnl_r'] > 0).mean():.3f}")

    # Per-year stats.
    print(f"\n=== Per-year stats (winner) ===")
    per_year = []
    for year, g in executed.groupby("test_year"):
        n = len(g)
        wins = int((g["pnl_r"] > 0).sum())
        cum_r = float(g["pnl_r"].sum())
        avg_r = float(g["pnl_r"].mean())
        max_dd = float((g["pnl_r"].cumsum().cummax() - g["pnl_r"].cumsum()).max())
        per_year.append({
            "test_year": int(year), "n": n, "wins": wins,
            "win_rate": wins / n, "cum_r": cum_r, "avg_r": avg_r, "max_dd": max_dd,
        })
    per_year_df = pd.DataFrame(per_year)
    per_year_df.to_csv(OUT_DIR / "per_year.csv", index=False, float_format="%.4f")
    print(per_year_df.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Per-symbol stats.
    print(f"\n=== Per-symbol stats (winner) ===")
    per_sym = []
    for sym, g in executed.groupby("symbol"):
        n = len(g)
        wins = int((g["pnl_r"] > 0).sum())
        cum_r = float(g["pnl_r"].sum())
        avg_r = float(g["pnl_r"].mean())
        max_dd = float((g["pnl_r"].cumsum().cummax() - g["pnl_r"].cumsum()).max())
        per_sym.append({
            "symbol": sym, "n": n, "wins": wins,
            "win_rate": wins / n, "cum_r": cum_r, "avg_r": avg_r, "max_dd": max_dd,
        })
    per_sym_df = pd.DataFrame(per_sym)
    per_sym_df.to_csv(OUT_DIR / "per_symbol.csv", index=False, float_format="%.4f")
    print(per_sym_df.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Per-signal × per-year matrix.
    print(f"\n=== Per-signal × per-year cum_R matrix ===")
    pivot = executed.pivot_table(index="signal", columns="test_year",
                                  values="pnl_r", aggfunc="sum", fill_value=0)
    pivot["total"] = pivot.sum(axis=1)
    pivot.to_csv(OUT_DIR / "per_signal_per_year.csv", float_format="%.4f")
    print(pivot.to_string(float_format=lambda x: f"{x:.2f}"))

    # Exit reason breakdown.
    print(f"\n=== Exit reason × signal ===")
    exit_pivot = executed.groupby(["signal", "exit_reason"]).size().unstack(fill_value=0)
    exit_pivot["total"] = exit_pivot.sum(axis=1)
    exit_pivot.to_csv(OUT_DIR / "exit_reason_by_signal.csv")
    print(exit_pivot.to_string())

    # Equity curve plot.
    sorted_df = executed.sort_values("fire_ts").copy()
    sorted_df["cum_r"] = sorted_df["pnl_r"].cumsum()
    fig, ax = plt.subplots(figsize=(13, 6))
    ax.plot(sorted_df["fire_ts"], sorted_df["cum_r"], linewidth=1.2, color="steelblue")
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("date")
    ax.set_ylabel("cumulative R")
    ax.set_title(f"V4 winner equity curve — stop=1.5 ATR, target=3.0 ATR, tw=180min\n"
                 f"n={len(sorted_df)}, cum R={sorted_df['cum_r'].iloc[-1]:+.1f}, "
                 f"max DD={float((sorted_df['cum_r'].cummax() - sorted_df['cum_r']).max()):.1f}")
    ax.grid(True, alpha=0.3)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "winner_equity.png", dpi=120)
    plt.close(fig)

    # Per-year equity curves on one chart.
    fig, ax = plt.subplots(figsize=(13, 7))
    for year, g in sorted_df.groupby("test_year"):
        g = g.sort_values("fire_ts").copy()
        g["cum_r_year"] = g["pnl_r"].cumsum()
        ax.plot(np.arange(len(g)), g["cum_r_year"], label=f"{int(year)} (n={len(g)}, R={g['cum_r_year'].iloc[-1]:+.0f})", linewidth=1.5)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("trade index within year")
    ax.set_ylabel("cumulative R")
    ax.set_title("V4 winner — equity curve by test year")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(OUT_DIR / "winner_equity_by_year.png", dpi=120)
    plt.close(fig)

    # Drawdown plot.
    cum_arr = sorted_df["cum_r"].to_numpy()
    high_water = pd.Series(cum_arr).cummax().to_numpy()
    drawdown = cum_arr - high_water
    fig, ax = plt.subplots(figsize=(13, 4))
    ax.fill_between(sorted_df["fire_ts"], drawdown, 0, color="firebrick", alpha=0.5)
    ax.set_xlabel("date")
    ax.set_ylabel("drawdown (R)")
    ax.set_title(f"V4 winner drawdown over time (max DD = {float((-drawdown).max()):.1f}R)")
    ax.grid(True, alpha=0.3)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "winner_drawdown.png", dpi=120)
    plt.close(fig)

    elapsed = time_mod.time() - t0
    summary = {
        "config": WINNER.name,
        "n_trades": int(len(executed)),
        "cum_r": float(executed["pnl_r"].sum()),
        "win_rate": float((executed["pnl_r"] > 0).mean()),
        "avg_r": float(executed["pnl_r"].mean()),
        "max_dd_r": float((sorted_df["cum_r"].cummax() - sorted_df["cum_r"]).max()),
        "n_years_positive": int((per_year_df["cum_r"] > 0).sum()),
        "n_years_total": len(per_year_df),
        "n_symbols_positive": int((per_sym_df["cum_r"] > 0).sum()),
        "elapsed_min": round(elapsed / 60, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
