"""Deep-dive on v5 narrow winner + "drop YM" variant.

v5 winner = stop=2.0 / target=4.0 / tw=240 → +95R, 5/6 years positive,
max DD 34R. Materially more robust than v4 winner (cum_R was slightly
higher but had 72R DD and only 4/6 positive years).

Two checks:
  (a) Full per-year / per-symbol / equity curve / drawdown of v5 winner.
  (b) Re-run with YM dropped — does that flip 2025 (the one weak year)?
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
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-15_v5_winner_deepdive"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Two configs: v5 winner + v5 winner with YM filter at trade-time.
WINNER = Config(
    name="v5_winner_stop2.0_tgt4.0_tw240",
    description="V5 narrow grid winner: 2.0 ATR stop, 4.0 ATR target, 240min window, consensus + drop SMT/sweep",
    wait_for_confirmation=True,
    stop_atr_mult=2.0,
    target_atr_mult=4.0,
    trade_window_min=240,
    require_consensus=True,
    excluded_signals=("smt_pd_high_thesis", "sweep_failed_recovered_all"),
)


def _per_year(executed: pd.DataFrame, label: str) -> pd.DataFrame:
    rows = []
    for year, g in executed.groupby("test_year"):
        n = len(g)
        wins = int((g["pnl_r"] > 0).sum())
        cum_r = float(g["pnl_r"].sum())
        max_dd = float((g["pnl_r"].cumsum().cummax() - g["pnl_r"].cumsum()).max())
        rows.append({
            "label": label, "test_year": int(year), "n": n, "wins": wins,
            "win_rate": wins / n, "cum_r": cum_r, "max_dd": max_dd,
        })
    return pd.DataFrame(rows)


def _per_symbol(executed: pd.DataFrame, label: str) -> pd.DataFrame:
    rows = []
    for sym, g in executed.groupby("symbol"):
        n = len(g)
        wins = int((g["pnl_r"] > 0).sum())
        cum_r = float(g["pnl_r"].sum())
        max_dd = float((g["pnl_r"].cumsum().cummax() - g["pnl_r"].cumsum()).max())
        rows.append({
            "label": label, "symbol": sym, "n": n, "wins": wins,
            "win_rate": wins / n, "cum_r": cum_r, "max_dd": max_dd,
        })
    return pd.DataFrame(rows)


def main() -> int:
    device_info = resolve_device("auto")
    print(f"device: {device_info.resolved}")
    t0 = time_mod.time()

    print("Step 1: train all signals × years...")
    picks_records = []
    for sig in SIGNALS:
        for ty in TEST_YEARS:
            df = _train_and_score(sig, device_info.resolved, ty)
            if not df.empty:
                picks_records.append(df)
    picks_all = pd.concat(picks_records, ignore_index=True)
    print(f"  total picks: {len(picks_all):,}")

    bars = BarsCache()
    print(f"\nStep 2: run v5 winner...")
    trade_df = run_one_config(WINNER, picks_all, bars)
    executed = trade_df[trade_df["exit_reason"].isin(["target", "stop", "time_exit"])].copy()
    print(f"  v5 winner: {len(executed)} trades, cum_R={executed['pnl_r'].sum():+.1f}, win_rate={(executed['pnl_r']>0).mean():.3f}")

    # No-YM variant: take the v5 winner result, filter trades to NQ + ES.
    no_ym = executed[executed["symbol"].isin(["NQ.c.0", "ES.c.0"])].copy()
    print(f"  v5 winner no-YM: {len(no_ym)} trades, cum_R={no_ym['pnl_r'].sum():+.1f}, win_rate={(no_ym['pnl_r']>0).mean():.3f}")

    # Save trades.
    executed.to_csv(OUT_DIR / "v5_winner_trades.csv", index=False, float_format="%.4f")
    no_ym.to_csv(OUT_DIR / "v5_winner_no_ym_trades.csv", index=False, float_format="%.4f")

    # Per-year stats.
    print("\n=== v5 winner — per year ===")
    py_w = _per_year(executed, "v5_winner")
    print(py_w.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))
    print("\n=== v5 winner WITHOUT YM — per year ===")
    py_n = _per_year(no_ym, "v5_winner_no_ym")
    print(py_n.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))
    pd.concat([py_w, py_n], ignore_index=True).to_csv(OUT_DIR / "per_year.csv", index=False, float_format="%.4f")

    # Per-symbol stats.
    print("\n=== v5 winner — per symbol ===")
    ps = _per_symbol(executed, "v5_winner")
    print(ps.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))
    ps.to_csv(OUT_DIR / "per_symbol.csv", index=False, float_format="%.4f")

    # Per-signal × per-year (v5 winner).
    print("\n=== v5 winner — per signal × per year ===")
    pivot = executed.pivot_table(index="signal", columns="test_year", values="pnl_r", aggfunc="sum", fill_value=0)
    pivot["total"] = pivot.sum(axis=1)
    pivot.to_csv(OUT_DIR / "per_signal_per_year.csv", float_format="%.4f")
    print(pivot.to_string(float_format=lambda x: f"{x:.2f}"))

    # Equity curve plot (both variants).
    fig, ax = plt.subplots(figsize=(13, 6))
    for label, sub in [("v5 winner (NQ/ES/YM)", executed), ("v5 winner no-YM (NQ/ES)", no_ym)]:
        sub = sub.sort_values("fire_ts").copy()
        sub["cum_r"] = sub["pnl_r"].cumsum()
        ax.plot(sub["fire_ts"], sub["cum_r"], label=f"{label} (n={len(sub)}, R={sub['cum_r'].iloc[-1]:+.1f})", linewidth=1.5)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("date")
    ax.set_ylabel("cumulative R")
    ax.set_title("V5 winner — equity curve with and without YM\n(stop=2.0 ATR, target=4.0 ATR, tw=240min, consensus + drop SMT/sweep)")
    ax.legend(loc="best", fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "v5_winner_equity_compare.png", dpi=120)
    plt.close(fig)

    # Drawdown plot for v5 winner.
    sorted_df = executed.sort_values("fire_ts").copy()
    sorted_df["cum_r"] = sorted_df["pnl_r"].cumsum()
    cum_arr = sorted_df["cum_r"].to_numpy()
    high_water = pd.Series(cum_arr).cummax().to_numpy()
    drawdown = cum_arr - high_water
    fig, ax = plt.subplots(figsize=(13, 4))
    ax.fill_between(sorted_df["fire_ts"], drawdown, 0, color="firebrick", alpha=0.5)
    ax.set_xlabel("date")
    ax.set_ylabel("drawdown (R)")
    ax.set_title(f"V5 winner drawdown (max DD = {float((-drawdown).max()):.1f}R)")
    ax.grid(True, alpha=0.3)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "v5_winner_drawdown.png", dpi=120)
    plt.close(fig)

    summary = {
        "v5_winner": {
            "config": WINNER.name,
            "n_trades": int(len(executed)),
            "cum_r": float(executed["pnl_r"].sum()),
            "win_rate": float((executed["pnl_r"] > 0).mean()),
            "avg_r": float(executed["pnl_r"].mean()),
            "max_dd_r": float((sorted_df["cum_r"].cummax() - sorted_df["cum_r"]).max()),
            "years_positive": int(py_w["cum_r"].gt(0).sum()),
            "years_total": len(py_w),
        },
        "v5_winner_no_ym": {
            "n_trades": int(len(no_ym)),
            "cum_r": float(no_ym["pnl_r"].sum()),
            "win_rate": float((no_ym["pnl_r"] > 0).mean()) if len(no_ym) else None,
            "avg_r": float(no_ym["pnl_r"].mean()) if len(no_ym) else None,
            "years_positive": int(py_n["cum_r"].gt(0).sum()),
            "years_total": len(py_n),
        },
        "elapsed_min": round((time_mod.time() - t0) / 60, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
