"""V10 — slippage-realistic version of the raw-OB strategy.

The +8,390R from variant B of v9_ob_leak_audit is real data, real direction
prediction, no leak -- but the simulator assumes exact fills at stop/target.
This script verifies the result holds up under conservative slippage:

  Entry: 1 tick adverse (buy at ask, sell at bid)
  Stop exit: 1 tick adverse (market stop slips on fast moves)
  Target exit: 0 ticks (limit order, assumed filled at target)
  Time exit: 1 tick adverse (market order)

Per-contract tick sizes:
  NQ.c.0: 0.25 points
  ES.c.0: 0.25 points

5 slippage scenarios tested side-by-side:
  no_slippage (baseline = matches v9_ob_leak_audit variant B)
  1tick_entry_only
  1tick_entry_and_stop
  2tick_entry_and_stop  (worst-realistic case)
  3tick_entry_and_stop  (paranoid)
"""

from __future__ import annotations

import json
import sys
import time as time_mod
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.rigorous_backtest_v1 import (
    BarsCache, Signal, TEST_YEARS,
    SYMBOL_COL, SIDE_COL, TIME_COL_CANDIDATES,
)
from scripts.ml.rigorous_backtest_v7_stops import (
    StopVariant, compute_atr_flexible,
)
from scripts.ml.rigorous_backtest_v9_ob import V8A_STOP, OB_SIGNALS
from scripts.ml.v9_ob_leak_audit import all_events_picks

ROOT = Path(r"C:\Users\benbr\BacktestStation")
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-16_v10_raw_ob_slippage"
OUT_DIR.mkdir(parents=True, exist_ok=True)
UTC = timezone.utc

TICK_SIZE = {"NQ.c.0": 0.25, "ES.c.0": 0.25, "YM.c.0": 1.0}


@dataclass
class Slippage:
    name: str
    entry_ticks: float = 0.0
    stop_ticks: float = 0.0
    target_ticks: float = 0.0
    time_exit_ticks: float = 0.0


SLIPPAGES = [
    Slippage("no_slippage"),
    Slippage("1tick_entry_only", entry_ticks=1.0),
    Slippage("1tick_entry_and_stop", entry_ticks=1.0, stop_ticks=1.0, time_exit_ticks=1.0),
    Slippage("2tick_entry_and_stop", entry_ticks=2.0, stop_ticks=2.0, time_exit_ticks=2.0),
    Slippage("3tick_entry_and_stop", entry_ticks=3.0, stop_ticks=3.0, time_exit_ticks=3.0),
]


def simulate_v7_slip(bars: BarsCache, symbol: str, fire_ts: pd.Timestamp, direction: str,
                     variant: StopVariant, slip: Slippage) -> dict:
    """v7 simulator with slippage applied. Mirrors simulate_v7 closely."""
    tick = TICK_SIZE.get(symbol, 0.25)
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
        out["exit_reason"] = "no_atr"; return out
    out["atr"] = atr
    after = window.loc[window.index > fire_ts]
    if after.empty:
        out["exit_reason"] = "no_bars_after_fire"; return out
    confirm_end = fire_ts + pd.Timedelta(minutes=60)
    scan = after.loc[after.index <= confirm_end]
    confirm_bar = None
    for idx, row in scan.iterrows():
        if direction == "short" and row["close"] < row["open"]:
            confirm_bar = (idx, row); break
        if direction == "long" and row["close"] > row["open"]:
            confirm_bar = (idx, row); break
    if confirm_bar is None:
        out["exit_reason"] = "no_confirmation"; return out
    confirm_idx = confirm_bar[0]
    entry_candidates = after.loc[after.index > confirm_idx]
    if entry_candidates.empty:
        out["exit_reason"] = "no_bar_after_confirmation"; return out
    entry_ts = entry_candidates.index[0]
    raw_open = float(entry_candidates.iloc[0]["open"])
    # Entry slippage: buy higher (long) or sell lower (short).
    entry_slip = slip.entry_ticks * tick
    if direction == "short":
        entry_price = raw_open - entry_slip  # we get filled at a worse (lower) bid
    else:
        entry_price = raw_open + entry_slip  # we pay the ask
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
                # Stop slippage: filled higher than stop_price (worse for short).
                exit_ts = idx
                exit_price = stop_price + slip.stop_ticks * tick
                exit_reason = "stop"; break
            if row["low"] <= target_price:
                # Target: limit order, fill at target (conservative: 0 slip).
                exit_ts = idx
                exit_price = target_price + slip.target_ticks * tick
                exit_reason = "target"; break
        else:
            if row["low"] <= stop_price:
                exit_ts = idx
                exit_price = stop_price - slip.stop_ticks * tick
                exit_reason = "stop"; break
            if row["high"] >= target_price:
                exit_ts = idx
                exit_price = target_price - slip.target_ticks * tick
                exit_reason = "target"; break
    if exit_ts is None:
        if trade_bars.empty or len(trade_bars) < 2:
            out["exit_reason"] = "no_bars_in_trade_window"; return out
        exit_ts = trade_bars.index[-1]
        raw_close = float(trade_bars.iloc[-1]["close"])
        # Time exit: market sell/buy. Slip adversely.
        if direction == "short":
            exit_price = raw_close + slip.time_exit_ticks * tick
        else:
            exit_price = raw_close - slip.time_exit_ticks * tick
    out["exit_ts"] = exit_ts
    out["exit_price"] = exit_price
    out["exit_reason"] = exit_reason
    pnl_pts = (entry_price - exit_price) if direction == "short" else (exit_price - entry_price)
    out["pnl_pts"] = pnl_pts
    out["pnl_r"] = pnl_pts / stop_dist if stop_dist > 0 else None
    return out


def resolve_dir(side: str) -> str:
    if side in ("bearish", "gap_down", "high"): return "short"
    if side in ("bullish", "gap_up", "low"): return "long"
    return "short"


def run_picks_with_slip(picks: pd.DataFrame, bars: BarsCache, variant: StopVariant,
                        slip: Slippage) -> pd.DataFrame:
    picks = picks[picks["symbol"].isin(["NQ.c.0", "ES.c.0"])].copy()
    picks["direction"] = picks["anchor_side"].apply(resolve_dir)
    trades = []
    for _, row in picks.iterrows():
        if pd.isna(row["fire_ts"]):
            continue
        sim = simulate_v7_slip(bars, row["symbol"], row["fire_ts"], row["direction"], variant, slip)
        trades.append({
            "slippage": slip.name,
            "signal": row["signal_name"],
            "test_year": int(row["test_year"]),
            "symbol": row["symbol"],
            "anchor_side": row["anchor_side"],
            "direction": row["direction"],
            "fire_ts": row["fire_ts"],
            **sim,
        })
    return pd.DataFrame(trades)


def main() -> int:
    print(f"=== V10 — slippage-realistic raw-OB check ===")
    print(f"output: {OUT_DIR}")
    t0 = time_mod.time()

    print("\nStep 1: gather ALL OB events in test years...")
    all_frames = [all_events_picks(sig) for sig in OB_SIGNALS]
    all_picks = pd.concat(all_frames, ignore_index=True)
    print(f"  all-event picks: {len(all_picks):,}")

    bars = BarsCache()
    print(f"\nStep 2: simulate with {len(SLIPPAGES)} slippage scenarios...")
    rollup = []
    all_trades = []
    for slip in SLIPPAGES:
        td = run_picks_with_slip(all_picks, bars, V8A_STOP, slip)
        ex = td[td["exit_reason"].isin(["target", "stop", "time_exit"])]
        n = len(ex)
        cum_r = float(ex["pnl_r"].sum()) if n else 0.0
        avg_r = float(ex["pnl_r"].mean()) if n else 0.0
        win_rate = float((ex["pnl_r"] > 0).mean()) if n else 0.0
        cumr = ex.sort_values("fire_ts")["pnl_r"].cumsum() if n else pd.Series([0.0])
        max_dd = float((cumr.cummax() - cumr).max()) if n else 0.0
        years_pos = int(ex.groupby("test_year")["pnl_r"].sum().gt(0).sum()) if n else 0
        # Stop/target/time breakdown
        stops = int((ex["exit_reason"] == "stop").sum())
        targets = int((ex["exit_reason"] == "target").sum())
        times = int((ex["exit_reason"] == "time_exit").sum())
        print(f"  [{slip.name:<25}] n={n:5d} cum_R={cum_r:+8.1f} avg_R={avg_r:+5.3f} win%={win_rate:.3f} DD={max_dd:5.1f} yrs+={years_pos}/6  stop/tgt/time={stops}/{targets}/{times}")
        all_trades.append(td)
        rollup.append({
            "slippage": slip.name, "n_trades": n, "cum_r": cum_r, "avg_r": avg_r,
            "win_rate": win_rate, "max_dd_r": max_dd, "years_positive": years_pos,
            "n_stops": stops, "n_targets": targets, "n_times": times,
            "entry_ticks": slip.entry_ticks, "stop_ticks": slip.stop_ticks,
            "target_ticks": slip.target_ticks, "time_exit_ticks": slip.time_exit_ticks,
        })

    combined = pd.concat(all_trades, ignore_index=True)
    combined.to_csv(OUT_DIR / "trades_all_slippage.csv", index=False, float_format="%.4f")
    rollup_df = pd.DataFrame(rollup)
    rollup_df.to_csv(OUT_DIR / "rollup.csv", index=False, float_format="%.4f")
    print("\n=== Rollup ===")
    print(rollup_df.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Per-year for each slippage
    executed = combined[combined["exit_reason"].isin(["target", "stop", "time_exit"])].copy()
    pivot = executed.pivot_table(index="slippage", columns="test_year", values="pnl_r",
                                  aggfunc="sum", fill_value=0)
    pivot["total"] = pivot.sum(axis=1)
    pivot.to_csv(OUT_DIR / "per_slippage_per_year.csv", float_format="%.4f")
    print("\n=== Per-slippage per-year cum_R ===")
    print(pivot.to_string(float_format=lambda x: f"{x:.1f}"))

    baseline_cum_r = rollup[0]["cum_r"]
    summary = {
        "no_slippage_cum_r": baseline_cum_r,
        "1tick_entry_stop_cum_r": rollup[2]["cum_r"],
        "2tick_entry_stop_cum_r": rollup[3]["cum_r"],
        "3tick_entry_stop_cum_r": rollup[4]["cum_r"],
        "survival_rate_1tick": rollup[2]["cum_r"] / baseline_cum_r if baseline_cum_r else 0,
        "survival_rate_2tick": rollup[3]["cum_r"] / baseline_cum_r if baseline_cum_r else 0,
        "survival_rate_3tick": rollup[4]["cum_r"] / baseline_cum_r if baseline_cum_r else 0,
        "verdict": (
            "SURVIVES — raw-OB tradeable even under conservative slippage"
            if rollup[3]["cum_r"] > 0.5 * baseline_cum_r else
            "MARGINAL — slippage cuts >50% of edge; needs careful execution"
            if rollup[3]["cum_r"] > 0 else
            "FAILS — slippage destroys the edge; not deployable"
        ),
        "elapsed_min": round((time_mod.time() - t0) / 60, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== DONE in {(time_mod.time()-t0)/60:.1f} min ===")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
