"""V12 — slippage-realistic version of raw-FVG tap_failed_1x_against.

Mirror of v10_raw_ob_slippage but for FVG. 3 slippage scenarios
(no slippage, 1-tick entry+stop, 2-tick) to verify the +12,848R
event-class edge survives realistic friction.

Also saves per-trade output so overlap analysis can combine OB + FVG + Swing.
"""

from __future__ import annotations

import json
import sys
import time as time_mod
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.rigorous_backtest_v1 import BarsCache, TEST_YEARS
from scripts.ml.rigorous_backtest_v9_ob import V8A_STOP
from scripts.ml.v9_ob_leak_audit import all_events_picks
from scripts.ml.v10_raw_ob_slippage import (
    Slippage, simulate_v7_slip, resolve_dir, TICK_SIZE,
)
from scripts.ml.v11_multi_family_event_audit import FVG_SIGNALS

ROOT = Path(r"C:\Users\benbr\BacktestStation")
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-16_v12_fvg_slippage"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Cut to 3 scenarios for speed (76K trades × 5 = 380K sims = too long).
SLIPPAGES = [
    Slippage("no_slippage"),
    Slippage("1tick_entry_and_stop", entry_ticks=1.0, stop_ticks=1.0, time_exit_ticks=1.0),
    Slippage("2tick_entry_and_stop", entry_ticks=2.0, stop_ticks=2.0, time_exit_ticks=2.0),
]


def run_picks_with_slip(picks, bars, variant, slip):
    picks = picks[picks["symbol"].isin(["NQ.c.0", "ES.c.0"])].copy()
    picks["direction"] = picks["anchor_side"].apply(resolve_dir)
    trades = []
    for _, row in picks.iterrows():
        if pd.isna(row["fire_ts"]):
            continue
        sim = simulate_v7_slip(bars, row["symbol"], row["fire_ts"], row["direction"], variant, slip)
        trades.append({
            "slippage": slip.name, "signal": row["signal_name"],
            "test_year": int(row["test_year"]), "symbol": row["symbol"],
            "anchor_side": row["anchor_side"], "direction": row["direction"],
            "fire_ts": row["fire_ts"],
            **sim,
        })
    return pd.DataFrame(trades)


def main() -> int:
    print("=== V12 — FVG slippage-realistic check ===")
    print(f"output: {OUT_DIR}")
    t0 = time_mod.time()

    print("\nStep 1: gather ALL FVG events...")
    all_frames = [all_events_picks(sig) for sig in FVG_SIGNALS]
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
        print(f"  [{slip.name:<25}] n={n:5d} cum_R={cum_r:+8.1f} avg_R={avg_r:+5.3f} win%={win_rate:.3f} DD={max_dd:5.1f} yrs+={years_pos}/6")
        all_trades.append(td)
        rollup.append({"slippage": slip.name, "n_trades": n, "cum_r": cum_r,
                       "avg_r": avg_r, "win_rate": win_rate, "max_dd_r": max_dd,
                       "years_positive": years_pos})

    combined = pd.concat(all_trades, ignore_index=True)
    combined.to_csv(OUT_DIR / "trades_all_slippage.csv", index=False, float_format="%.4f")
    rollup_df = pd.DataFrame(rollup)
    rollup_df.to_csv(OUT_DIR / "rollup.csv", index=False, float_format="%.4f")
    print("\n=== Rollup ===")
    print(rollup_df.to_string(index=False, float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    executed = combined[combined["exit_reason"].isin(["target", "stop", "time_exit"])].copy()
    pivot = executed.pivot_table(index="slippage", columns="test_year", values="pnl_r",
                                  aggfunc="sum", fill_value=0)
    pivot["total"] = pivot.sum(axis=1)
    pivot.to_csv(OUT_DIR / "per_slippage_per_year.csv", float_format="%.4f")
    print("\n=== Per-slippage per-year cum_R ===")
    print(pivot.to_string(float_format=lambda x: f"{x:.1f}"))

    baseline = rollup[0]["cum_r"]
    summary = {
        "no_slippage_cum_r": baseline,
        "1tick_cum_r": rollup[1]["cum_r"],
        "2tick_cum_r": rollup[2]["cum_r"],
        "survival_1tick": rollup[1]["cum_r"] / baseline if baseline else 0,
        "survival_2tick": rollup[2]["cum_r"] / baseline if baseline else 0,
        "verdict": (
            "SURVIVES" if rollup[2]["cum_r"] > 0.5 * baseline else
            "MARGINAL" if rollup[2]["cum_r"] > 0 else
            "FAILS"
        ),
        "elapsed_min": round((time_mod.time() - t0) / 60, 1),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== DONE in {(time_mod.time()-t0)/60:.1f} min ===")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
