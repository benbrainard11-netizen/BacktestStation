"""V9 — integrate 247's strict order-block continuation labels into v8a.

v8a is the current best deploy candidate:
  - 3 OGAP signals (gap_down rejection, gap_up rejection, strict partial_touch)
  - stop = max(2.0 × ATR(14, 5m), 1.5 × ATR(14, 30m))
  - target = 5.0 × stop ATR
  - tw = 240 min
  - consensus filter (2+ distinct signals on same date+symbol)
  - NQ + ES (drop YM)
  - Result: +79R / 27R DD / 58% win / 5/6 yrs / 2025 at -5R

247 just shipped strict OB labels. GPU walk-forward verified them (all
matched CPU AUC within +/-0.006). The standout:

    label.strict.next_60m.ob_broken_through_continuation
        AUC=0.797, base_rate=0.187, top_lift=+0.37

That's a CONTINUATION signal -- fundamentally different from the 3
mean-reversion signals in v8a. Question: does adding it help, hurt,
or just dilute v8a?

Test 3 configs on the v8a trade-rule shape:
  v9a: v8a replication (3 OGAP only, 2+ consensus) -- sanity baseline
  v9b: OB standalone (2 OB continuation signals, no consensus)
  v9c: v8a + OB (5 signals, 2+ consensus)

To avoid the same-matrix multi-horizon consensus-filter bug, we use
ONLY next_60m OB and split by anchor.side (bullish/bearish) into two
signals with fixed-direction continuation rules. This way the consensus
counter sees OB as 1 family signal per fire (whichever side fires).
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
from scripts.ml.rigorous_backtest_v1 import (
    BarsCache, Signal, SIGNALS as OLD_SIGNALS, TEST_YEARS, TOP_PCT,
    SYMBOL_COL, SIDE_COL, TIME_COL_CANDIDATES,
)
from scripts.ml.rigorous_backtest_v2_matrix import _apply_consensus_filter, _train_and_score
from scripts.ml.rigorous_backtest_v7_stops import StopVariant, simulate_v7, V5_SIGNALS
from scripts.ml.gpu_train_xgb import resolve_device

UTC = timezone.utc
ROOT = Path(r"C:\Users\benbr\BacktestStation")
ANCHORS_OB = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_16_strict_order_block") / "data" / "ml" / "anchors"
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-16_rigorous_v9_ob"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# v8a stop variant (re-defined here for clarity; identical to v7_stops VARIANTS[1]).
V8A_STOP = StopVariant(
    "v8a", "v9 base trade-rule shape (stop=max(2*ATR5m,1.5*ATR30m), target=5*ATR, tw=240)",
    stop_atr_mult=2.0, target_atr_mult=5.0, trade_window_min=240,
    atr_timeframe_min=5, atr_floor_timeframe_min=30, atr_floor_mult=1.5,
)


# OB strict continuation signals. Two side-specific signals so each
# gets a fixed direction; this also keeps the consensus filter honest
# (multi-side does NOT count as multi-signal because gap_down xor gap_up
# is mutually exclusive, ditto bullish xor bearish for OB).
OB_SIGNALS = [
    Signal("ob_continuation_bullish", ANCHORS_OB,
           "ob_snapshots_xctx_strict",
           "at_fire", "bullish", "label.strict.next_60m.ob_broken_through_continuation",
           "fixed_long"),
    Signal("ob_continuation_bearish", ANCHORS_OB,
           "ob_snapshots_xctx_strict",
           "at_fire", "bearish", "label.strict.next_60m.ob_broken_through_continuation",
           "fixed_short"),
]


@dataclass
class V9Config:
    name: str
    description: str
    signals: tuple
    require_consensus: bool


CONFIGS = [
    V9Config("v9a_v8a_replicate", "v8a baseline: 3 OGAP + 2+ consensus, NQ+ES",
             tuple(V5_SIGNALS), True),
    V9Config("v9b_ob_standalone", "2 OB continuation signals only, no consensus, NQ+ES",
             tuple(OB_SIGNALS), False),
    V9Config("v9c_v8a_plus_ob",   "v8a + 2 OB continuation, 2+ consensus on 5 signals, NQ+ES",
             tuple(V5_SIGNALS + OB_SIGNALS), True),
]


def resolve_dir(rule: str, side: str) -> str:
    if rule == "fixed_short": return "short"
    if rule == "fixed_long": return "long"
    if side in ("gap_down", "high", "bearish"): return "short"
    if side in ("gap_up", "low", "bullish"): return "long"
    return "short"


def run_config(cfg: V9Config, picks_by_sig: dict[str, pd.DataFrame], bars: BarsCache,
               variant: StopVariant) -> pd.DataFrame:
    # Gather only this config's signals.
    frames = [picks_by_sig[s.name] for s in cfg.signals if s.name in picks_by_sig and not picks_by_sig[s.name].empty]
    if not frames:
        return pd.DataFrame()
    picks = pd.concat(frames, ignore_index=True)
    if cfg.require_consensus:
        picks = _apply_consensus_filter(picks)
    picks = picks[picks["symbol"].isin(["NQ.c.0", "ES.c.0"])].copy()
    picks["direction"] = picks.apply(lambda r: resolve_dir(r["direction_rule"], r["anchor_side"]), axis=1)
    trades = []
    for _, row in picks.iterrows():
        if pd.isna(row["fire_ts"]):
            continue
        sim = simulate_v7(bars, row["symbol"], row["fire_ts"], row["direction"], variant)
        trades.append({
            "config": cfg.name,
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
    device_info = resolve_device("auto")
    print(f"=== V9 — OB integration into v8a ===")
    print(f"device: {device_info.resolved}")
    print(f"output: {OUT_DIR}")
    t0 = time_mod.time()

    # Step 1: train+score all signals used by any config.
    all_signals = {s.name: s for c in CONFIGS for s in c.signals}
    print(f"\nStep 1: train {len(all_signals)} signals × {len(TEST_YEARS)} years...")
    picks_by_sig: dict[str, pd.DataFrame] = {n: [] for n in all_signals}
    for name, sig in all_signals.items():
        for ty in TEST_YEARS:
            df = _train_and_score(sig, device_info.resolved, ty)
            if not df.empty:
                picks_by_sig[name].append(df)
        merged = pd.concat(picks_by_sig[name], ignore_index=True) if picks_by_sig[name] else pd.DataFrame()
        picks_by_sig[name] = merged
        print(f"  {name:<30} picks={len(merged):>5}")

    # Step 2: simulate trades per config.
    bars = BarsCache()
    all_trades = []
    for cfg in CONFIGS:
        td = run_config(cfg, picks_by_sig, bars, V8A_STOP)
        if td.empty:
            print(f"  [{cfg.name}] no trades produced")
            continue
        ex = td[td["exit_reason"].isin(["target", "stop", "time_exit"])]
        n = len(ex)
        cum_r = float(ex["pnl_r"].sum()) if n else 0.0
        win_rate = float((ex["pnl_r"] > 0).mean()) if n else 0.0
        cumr = ex.sort_values("fire_ts")["pnl_r"].cumsum() if n else pd.Series([0.0])
        max_dd = float((cumr.cummax() - cumr).max()) if n else 0.0
        years_pos = int(ex.groupby("test_year")["pnl_r"].sum().gt(0).sum()) if n else 0
        print(f"  [{cfg.name:<22}] n={n:4d} cum_R={cum_r:+7.1f} win%={win_rate:.3f} DD={max_dd:5.1f} years_pos={years_pos}/6")
        all_trades.append(td)
    combined = pd.concat(all_trades, ignore_index=True)
    combined.to_csv(OUT_DIR / "trades_all_configs.csv", index=False, float_format="%.4f")

    executed = combined[combined["exit_reason"].isin(["target", "stop", "time_exit"])].copy()

    # Per-config × per-year pivot.
    pivot = executed.pivot_table(index="config", columns="test_year", values="pnl_r", aggfunc="sum", fill_value=0)
    pivot["total"] = pivot.sum(axis=1)
    pivot["years_positive"] = (pivot.drop(columns=["total"]) > 0).sum(axis=1)
    pivot.to_csv(OUT_DIR / "per_config_per_year.csv", float_format="%.4f")
    print("\n=== Per-config per-year cum_R ===")
    print(pivot.to_string(float_format=lambda x: f"{x:.2f}"))

    # Per-config × per-signal contribution.
    per_cs = executed.groupby(["config", "signal"]).agg(
        n=("pnl_r", "count"),
        cum_r=("pnl_r", "sum"),
        win_rate=("pnl_r", lambda s: float((s > 0).mean())),
        avg_r=("pnl_r", "mean"),
    ).reset_index()
    per_cs.to_csv(OUT_DIR / "per_config_per_signal.csv", index=False, float_format="%.4f")
    print("\n=== Per-config × per-signal ===")
    print(per_cs.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Rollup.
    rollup_rows = []
    for cfg_name, g in executed.groupby("config"):
        n = len(g)
        wins = int((g["pnl_r"] > 0).sum())
        cum_r = float(g["pnl_r"].sum())
        cumr = g.sort_values("fire_ts")["pnl_r"].cumsum()
        max_dd = float((cumr.cummax() - cumr).max())
        years_pos = int(g.groupby("test_year")["pnl_r"].sum().gt(0).sum())
        rollup_rows.append({
            "config": cfg_name, "n_trades": n, "win_rate": wins / n if n else 0.0,
            "cum_r": cum_r, "avg_r": cum_r / n if n else 0.0,
            "max_dd_r": max_dd, "dd_per_cum_r": max_dd / cum_r if cum_r > 0 else float("inf"),
            "years_positive": years_pos,
        })
    rollup = pd.DataFrame(rollup_rows).sort_values("cum_r", ascending=False)
    rollup.to_csv(OUT_DIR / "rollup.csv", index=False, float_format="%.4f")
    print("\n=== Rollup ===")
    print(rollup.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    # Equity curves.
    fig, ax = plt.subplots(figsize=(13, 7))
    for cfg_name, g in executed.groupby("config"):
        gs = g.sort_values("fire_ts").copy()
        gs["cum_r"] = gs["pnl_r"].cumsum()
        ax.plot(gs["fire_ts"], gs["cum_r"],
                label=f"{cfg_name} (n={len(gs)}, R={gs['cum_r'].iloc[-1]:+.0f})", linewidth=1.6)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xlabel("date"); ax.set_ylabel("cumulative R")
    ax.set_title("V9 — does adding strict OB continuation help v8a?\n(v8a trade rules: floor stop, 5×ATR target, 240 min, NQ+ES)")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    plt.tight_layout()
    fig.savefig(OUT_DIR / "v9_equity.png", dpi=120)
    plt.close(fig)

    summary = {
        "best_by_cum_r": rollup.iloc[0]["config"] if not rollup.empty else None,
        "best_cum_r": float(rollup.iloc[0]["cum_r"]) if not rollup.empty else None,
        "v8a_baseline_cum_r": float(rollup.loc[rollup["config"] == "v9a_v8a_replicate", "cum_r"].iloc[0]) if (rollup["config"] == "v9a_v8a_replicate").any() else None,
        "ob_standalone_cum_r": float(rollup.loc[rollup["config"] == "v9b_ob_standalone", "cum_r"].iloc[0]) if (rollup["config"] == "v9b_ob_standalone").any() else None,
        "combined_cum_r": float(rollup.loc[rollup["config"] == "v9c_v8a_plus_ob", "cum_r"].iloc[0]) if (rollup["config"] == "v9c_v8a_plus_ob").any() else None,
        "elapsed_min": round((time_mod.time() - t0) / 60, 1),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\n=== DONE in {(time_mod.time()-t0)/60:.1f} min ===")
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
