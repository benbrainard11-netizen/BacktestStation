"""V8 — last overnight iteration. Tweak v7d's target + time-window
to see if any single change pushes v7d (current best deploy candidate)
further on Cum R while keeping the low DD.

Base: v7d_floor (stop = max(2×ATR5m, 1.5×ATR30m), target=4×ATR, tw=240)
gave +73R / 27R DD / 5/6 years / 2025 at -5R.

Test 4 small tweaks on top of v7d:
  v8a: target = 5 × ATR (wider target, catch more drift moves)
  v8b: target = 3 × ATR (tighter target, more clean exits)
  v8c: tw = 120 min (faster cycling)
  v8d: tw = 60 min (very fast)
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
from scripts.ml.rigorous_backtest_v1 import BarsCache, SIGNALS as OLD_SIGNALS, TEST_YEARS
from scripts.ml.rigorous_backtest_v2_matrix import _apply_consensus_filter, _train_and_score
from scripts.ml.rigorous_backtest_v7_stops import (
    StopVariant, simulate_v7, resolve_dir, V5_SIGNALS,
)
from scripts.ml.gpu_train_xgb import resolve_device

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-16_rigorous_v8_tweaks"
OUT_DIR.mkdir(parents=True, exist_ok=True)


VARIANTS = [
    StopVariant("v7d_baseline", "v7d as-is (target=4ATR, tw=240)", 2.0, 4.0, 240, 5,
                atr_floor_timeframe_min=30, atr_floor_mult=1.5),
    StopVariant("v8a_target5",  "v7d + target=5ATR",              2.0, 5.0, 240, 5,
                atr_floor_timeframe_min=30, atr_floor_mult=1.5),
    StopVariant("v8b_target3",  "v7d + target=3ATR (tighter)",    2.0, 3.0, 240, 5,
                atr_floor_timeframe_min=30, atr_floor_mult=1.5),
    StopVariant("v8c_tw120",    "v7d + tw=120",                   2.0, 4.0, 120, 5,
                atr_floor_timeframe_min=30, atr_floor_mult=1.5),
    StopVariant("v8d_tw60",     "v7d + tw=60",                    2.0, 4.0,  60, 5,
                atr_floor_timeframe_min=30, atr_floor_mult=1.5),
]


def run_variant(variant: StopVariant, picks_all: pd.DataFrame, bars: BarsCache) -> pd.DataFrame:
    picks = _apply_consensus_filter(picks_all)
    picks = picks[picks["symbol"].isin(["NQ.c.0", "ES.c.0"])].copy()
    picks["direction"] = picks.apply(lambda r: resolve_dir(r["direction_rule"], r["anchor_side"]), axis=1)
    trades = []
    for _, row in picks.iterrows():
        if pd.isna(row["fire_ts"]):
            continue
        sim = simulate_v7(bars, row["symbol"], row["fire_ts"], row["direction"], variant)
        trades.append({
            "variant": variant.name,
            "signal": row["signal_name"],
            "test_year": int(row["test_year"]),
            "symbol": row["symbol"],
            "direction": row["direction"],
            "fire_ts": row["fire_ts"],
            **sim,
        })
    return pd.DataFrame(trades)


def main() -> int:
    device_info = resolve_device("auto")
    print(f"device: {device_info.resolved}")
    t0 = time_mod.time()

    print("Step 1: train OGAP signals × 6 years...")
    picks_records = []
    for sig in V5_SIGNALS:
        for ty in TEST_YEARS:
            df = _train_and_score(sig, device_info.resolved, ty)
            if not df.empty:
                picks_records.append(df)
    picks_all = pd.concat(picks_records, ignore_index=True)
    print(f"  total picks: {len(picks_all):,}")

    bars = BarsCache()
    all_trades = []
    for v in VARIANTS:
        td = run_variant(v, picks_all, bars)
        ex = td[td["exit_reason"].isin(["target", "stop", "time_exit"])]
        n = len(ex)
        cum_r = float(ex["pnl_r"].sum()) if n else 0.0
        win_rate = float((ex["pnl_r"] > 0).mean()) if n else 0.0
        max_dd = float((ex.sort_values("fire_ts")["pnl_r"].cumsum().cummax() - ex.sort_values("fire_ts")["pnl_r"].cumsum()).max())
        print(f"  [{v.name:<15}] {v.description:<45} n={n:4d} cum_R={cum_r:+7.1f} win%={win_rate:.3f} DD={max_dd:5.1f}")
        all_trades.append(td)
    combined = pd.concat(all_trades, ignore_index=True)
    combined.to_csv(OUT_DIR / "trades_all_variants.csv", index=False, float_format="%.4f")

    executed = combined[combined["exit_reason"].isin(["target", "stop", "time_exit"])].copy()
    pivot = executed.pivot_table(index="variant", columns="test_year", values="pnl_r", aggfunc="sum", fill_value=0)
    pivot["total"] = pivot.sum(axis=1)
    pivot["years_positive"] = (pivot.drop(columns=["total"]) > 0).sum(axis=1)
    pivot.to_csv(OUT_DIR / "per_variant_per_year.csv", float_format="%.4f")
    print("\n=== Per-variant per-year cum_R ===")
    print(pivot.to_string(float_format=lambda x: f"{x:.2f}"))

    rollup_rows = []
    for v_name, g in executed.groupby("variant"):
        n = len(g)
        wins = int((g["pnl_r"] > 0).sum())
        cum_r = float(g["pnl_r"].sum())
        avg_r = float(g["pnl_r"].mean())
        cumr = g.sort_values("fire_ts")["pnl_r"].cumsum()
        max_dd = float((cumr.cummax() - cumr).max())
        years_pos = int(g.groupby("test_year")["pnl_r"].sum().gt(0).sum())
        rollup_rows.append({
            "variant": v_name, "n_trades": n, "win_rate": wins / n,
            "cum_r": cum_r, "avg_r": avg_r, "max_dd_r": max_dd,
            "dd_per_cum_r": max_dd / cum_r if cum_r > 0 else float("inf"),
            "years_positive": years_pos,
        })
    rollup_df = pd.DataFrame(rollup_rows).sort_values("cum_r", ascending=False)
    rollup_df.to_csv(OUT_DIR / "rollup.csv", index=False, float_format="%.4f")
    print("\n=== Rollup ===")
    print(rollup_df.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    fig, ax = plt.subplots(figsize=(13, 7))
    for v_name, g in executed.groupby("variant"):
        gs = g.sort_values("fire_ts").copy()
        gs["cum_r"] = gs["pnl_r"].cumsum()
        ax.plot(gs["fire_ts"], gs["cum_r"], label=f"{v_name} (n={len(gs)}, R={gs['cum_r'].iloc[-1]:+.0f})", linewidth=1.5)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("date"); ax.set_ylabel("cumulative R")
    ax.set_title("V8 — small tweaks to v7d (target × time-window grid)")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "v8_equity.png", dpi=120)
    plt.close(fig)

    summary = {
        "best_by_cum_r": rollup_df.iloc[0]["variant"],
        "best_cum_r": float(rollup_df.iloc[0]["cum_r"]),
        "best_dd_per_cum_r": float(rollup_df["dd_per_cum_r"].min()),
        "elapsed_min": round((time_mod.time() - t0) / 60, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\n=== DONE in {(time_mod.time()-t0)/60:.1f} min ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
