"""V7 — test stop-rule variants that address the 2025 high-vol regime.

The 2025 diagnostic showed: model AUC and top-10% precision are the
HIGHEST EVER in 2025. The break is at the stop layer -- 68% stop-out
rate vs 29-57% in prior years.

This script tests stop variants on the v5-winner portfolio (3 OGAP
signals, no SMT, no sweep, no YM, consensus filter, target=4 ATR,
tw=240):

  v5_baseline  stop = 2.0 × ATR(14, 5m)        v5 winner
  v7a          stop = 2.0 × ATR(14, 30m)       30m timeframe (wider)
  v7b          stop = 3.0 × ATR(14, 5m)        wider stop, same TF
  v7c          stop = 4.0 × ATR(14, 5m)        much wider stop
  v7d          stop = max(2.0 × ATR(14, 5m), 1.5 × ATR(14, 30m))   floor

If any of these flips 2025 from -35R to flat or positive while
keeping prior years acceptable, we have v7 winner.
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
from scripts.ml.rigorous_backtest_v1 import (
    BarsCache, Signal, SIGNALS as OLD_SIGNALS, TEST_YEARS, TOP_PCT,
    SYMBOL_COL, SIDE_COL, TIME_COL_CANDIDATES,
)
from scripts.ml.rigorous_backtest_v2_matrix import _apply_consensus_filter, _train_and_score

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-16_rigorous_v7_stops"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# Custom ATR with configurable timeframe and floor.
def compute_atr_flexible(bars_1m: pd.DataFrame, at_ts: pd.Timestamp,
                        periods: int = 14, timeframe_min: int = 5,
                        floor_atr: float | None = None) -> float | None:
    if bars_1m.empty:
        return None
    before = bars_1m.loc[bars_1m.index < at_ts]
    needed_1m_bars = (periods + 5) * timeframe_min
    if len(before) < needed_1m_bars:
        return None
    sliced = before.tail(needed_1m_bars)
    agg = sliced.resample(f"{timeframe_min}min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    if len(agg) < periods + 1:
        return None
    prev_close = agg["close"].shift(1)
    tr = pd.concat([
        agg["high"] - agg["low"],
        (agg["high"] - prev_close).abs(),
        (agg["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.tail(periods + 1).iloc[1:].mean()
    val = float(atr) if pd.notna(atr) else None
    if val is None:
        return None
    if floor_atr is not None and floor_atr > val:
        return floor_atr
    return val


@dataclass
class StopVariant:
    name: str
    description: str
    stop_atr_mult: float
    target_atr_mult: float
    trade_window_min: int = 240
    atr_timeframe_min: int = 5
    atr_floor_timeframe_min: int | None = None
    atr_floor_mult: float = 0.0  # how much of 30m ATR to use as floor


VARIANTS = [
    StopVariant("v5_baseline",  "stop=2 × ATR(14, 5m)",      2.0, 4.0, 240, 5),
    StopVariant("v7a_atr30m",   "stop=2 × ATR(14, 30m)",     2.0, 4.0, 240, 30),
    StopVariant("v7b_stop3",    "stop=3 × ATR(14, 5m)",      3.0, 6.0, 240, 5),
    StopVariant("v7c_stop4",    "stop=4 × ATR(14, 5m)",      4.0, 8.0, 240, 5),
    StopVariant("v7d_floor",    "stop=max(2×ATR5m, 1.5×ATR30m)", 2.0, 4.0, 240, 5,
                atr_floor_timeframe_min=30, atr_floor_mult=1.5),
]


# Reuse v5 signals (3 OGAP, no SMT/sweep).
V5_SIGNALS = [s for s in OLD_SIGNALS if s.name in (
    "ogap_gap_down_rejection", "ogap_gap_up_rejection", "ogap_strict_partial_touch"
)]


def resolve_dir(rule: str, side: str) -> str:
    if rule == "fixed_short": return "short"
    if rule == "fixed_long": return "long"
    if side in ("gap_down", "high"): return "short"
    if side in ("gap_up", "low"): return "long"
    return "short"


def simulate_v7(bars: BarsCache, symbol: str, fire_ts: pd.Timestamp, direction: str,
                variant: StopVariant) -> dict:
    out = {
        "entry_ts": None, "entry_price": None, "exit_ts": None, "exit_price": None,
        "exit_reason": "no_bars", "atr": None, "stop_price": None, "target_price": None,
        "pnl_pts": None, "pnl_r": None,
    }
    pre = fire_ts - pd.Timedelta(days=4)
    post = fire_ts + pd.Timedelta(minutes=60 + variant.trade_window_min + 5)
    window = bars.get_window(symbol, pre, post)
    if window.empty or len(window) < 10:
        return out
    pre_at_fire = window.loc[window.index <= fire_ts]
    # Compute ATR with the right timeframe + optional floor.
    floor_val = None
    if variant.atr_floor_timeframe_min is not None and variant.atr_floor_mult > 0:
        floor_atr = compute_atr_flexible(pre_at_fire, fire_ts,
                                         timeframe_min=variant.atr_floor_timeframe_min)
        if floor_atr is not None:
            floor_val = floor_atr * variant.atr_floor_mult / max(variant.stop_atr_mult, 1e-9)
    atr = compute_atr_flexible(pre_at_fire, fire_ts,
                               timeframe_min=variant.atr_timeframe_min,
                               floor_atr=floor_val)
    if atr is None or atr <= 0:
        out["exit_reason"] = "no_atr"
        return out
    out["atr"] = atr
    after = window.loc[window.index > fire_ts]
    if after.empty:
        out["exit_reason"] = "no_bars_after_fire"
        return out
    # Confirmation bar.
    confirm_end = fire_ts + pd.Timedelta(minutes=60)
    scan = after.loc[after.index <= confirm_end]
    confirm_bar = None
    for idx, row in scan.iterrows():
        if direction == "short" and row["close"] < row["open"]:
            confirm_bar = (idx, row); break
        if direction == "long" and row["close"] > row["open"]:
            confirm_bar = (idx, row); break
    if confirm_bar is None:
        out["exit_reason"] = "no_confirmation"
        return out
    confirm_idx = confirm_bar[0]
    entry_candidates = after.loc[after.index > confirm_idx]
    if entry_candidates.empty:
        out["exit_reason"] = "no_bar_after_confirmation"
        return out
    entry_ts = entry_candidates.index[0]
    entry_price = float(entry_candidates.iloc[0]["open"])
    out["entry_ts"] = entry_ts
    out["entry_price"] = entry_price
    stop_dist = variant.stop_atr_mult * atr
    target_dist = variant.target_atr_mult * atr
    if direction == "short":
        stop_price = entry_price + stop_dist
        target_price = entry_price - target_dist
    else:
        stop_price = entry_price - stop_dist
        target_price = entry_price + target_dist
    out["stop_price"] = stop_price
    out["target_price"] = target_price
    time_exit_ts = entry_ts + pd.Timedelta(minutes=variant.trade_window_min)
    trade_bars = after.loc[(after.index >= entry_ts) & (after.index <= time_exit_ts)]
    exit_ts, exit_price, exit_reason = None, None, "time_exit"
    for idx, row in trade_bars.iterrows():
        if idx == entry_ts:
            continue
        if direction == "short":
            if row["high"] >= stop_price:
                exit_ts, exit_price, exit_reason = idx, stop_price, "stop"; break
            if row["low"] <= target_price:
                exit_ts, exit_price, exit_reason = idx, target_price, "target"; break
        else:
            if row["low"] <= stop_price:
                exit_ts, exit_price, exit_reason = idx, stop_price, "stop"; break
            if row["high"] >= target_price:
                exit_ts, exit_price, exit_reason = idx, target_price, "target"; break
    if exit_ts is None:
        if trade_bars.empty or len(trade_bars) < 2:
            out["exit_reason"] = "no_bars_in_trade_window"
            return out
        exit_ts = trade_bars.index[-1]
        exit_price = float(trade_bars.iloc[-1]["close"])
    out["exit_ts"] = exit_ts
    out["exit_price"] = exit_price
    out["exit_reason"] = exit_reason
    pnl_pts = (entry_price - exit_price) if direction == "short" else (exit_price - entry_price)
    out["pnl_pts"] = pnl_pts
    out["pnl_r"] = pnl_pts / stop_dist if stop_dist > 0 else None
    return out


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

    # Train + score the 3 OGAP signals.
    print("Step 1: train OGAP signals × 6 years...")
    picks_records = []
    for sig in V5_SIGNALS:
        for ty in TEST_YEARS:
            df = _train_and_score(sig, device_info.resolved, ty)
            if not df.empty:
                picks_records.append(df)
    picks_all = pd.concat(picks_records, ignore_index=True)
    print(f"  total picks: {len(picks_all):,}")

    # Run all variants.
    bars = BarsCache()
    all_trades = []
    for v in VARIANTS:
        td = run_variant(v, picks_all, bars)
        ex = td[td["exit_reason"].isin(["target", "stop", "time_exit"])]
        n = len(ex)
        cum_r = float(ex["pnl_r"].sum()) if n else 0.0
        win_rate = float((ex["pnl_r"] > 0).mean()) if n else 0.0
        print(f"  [{v.name:<15}] {v.description:<45} n={n:4d} cum_R={cum_r:+7.1f} win%={win_rate:.3f}")
        all_trades.append(td)
    combined = pd.concat(all_trades, ignore_index=True)
    combined.to_csv(OUT_DIR / "trades_all_variants.csv", index=False, float_format="%.4f")

    # Per-variant per-year cum_R.
    executed = combined[combined["exit_reason"].isin(["target", "stop", "time_exit"])].copy()
    pivot = executed.pivot_table(index="variant", columns="test_year", values="pnl_r", aggfunc="sum", fill_value=0)
    pivot["total"] = pivot.sum(axis=1)
    pivot["years_positive"] = (pivot.drop(columns=["total"]) > 0).sum(axis=1)
    pivot.to_csv(OUT_DIR / "per_variant_per_year.csv", float_format="%.4f")
    print("\n=== Per-variant per-year cum_R ===")
    print(pivot.to_string(float_format=lambda x: f"{x:.2f}"))

    # Rollup.
    rollup_rows = []
    for v_name, g in executed.groupby("variant"):
        n = len(g)
        wins = int((g["pnl_r"] > 0).sum())
        cum_r = float(g["pnl_r"].sum())
        avg_r = float(g["pnl_r"].mean())
        # stops vs targets.
        stops = int((g["exit_reason"] == "stop").sum())
        targets = int((g["exit_reason"] == "target").sum())
        timed = int((g["exit_reason"] == "time_exit").sum())
        cumr = g.sort_values("fire_ts")["pnl_r"].cumsum()
        max_dd = float((cumr.cummax() - cumr).max())
        years_pos = int(g.groupby("test_year")["pnl_r"].sum().gt(0).sum())
        rollup_rows.append({
            "variant": v_name, "n_trades": n, "wins": wins, "win_rate": wins / n,
            "cum_r": cum_r, "avg_r": avg_r,
            "stops_%": stops / n, "targets_%": targets / n, "time_%": timed / n,
            "max_dd_r": max_dd, "years_positive": years_pos,
        })
    rollup_df = pd.DataFrame(rollup_rows).sort_values("cum_r", ascending=False)
    rollup_df.to_csv(OUT_DIR / "rollup.csv", index=False, float_format="%.4f")
    print("\n=== Rollup ===")
    print(rollup_df.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Equity curves.
    fig, ax = plt.subplots(figsize=(13, 7))
    for v_name, g in executed.groupby("variant"):
        gs = g.sort_values("fire_ts").copy()
        gs["cum_r"] = gs["pnl_r"].cumsum()
        ax.plot(gs["fire_ts"], gs["cum_r"], label=f"{v_name} (n={len(gs)}, R={gs['cum_r'].iloc[-1]:+.0f})", linewidth=1.5)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("date"); ax.set_ylabel("cumulative R")
    ax.set_title("V7 stop variants — equity curves\n(v5 portfolio: 3 OGAP signals, consensus filter, NQ+ES)")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "v7_equity.png", dpi=120)
    plt.close(fig)

    summary = {
        "best_variant": rollup_df.iloc[0]["variant"],
        "best_cum_r": float(rollup_df.iloc[0]["cum_r"]),
        "best_years_positive": int(rollup_df.iloc[0]["years_positive"]),
        "elapsed_min": round((time_mod.time() - t0) / 60, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\n=== DONE in {(time_mod.time()-t0)/60:.1f} min ===")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
