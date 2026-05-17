"""V15 — slippage-realistic check on v13's FVG zone_reaction +10,420R headline.

Same pattern as v12_fvg_slippage but uses the broader v13-winning label
`label.zone_reaction.took_fvg_high` / `took_fvg_low` on matrix
`fvg_snapshots_xctx_fvggeom_obgeom` (not the strict matrix that v12 used).

Three slippage scenarios on NQ+ES, side-aware direction, v8a trade rules.
"""

from __future__ import annotations

import json
import sys
import time as time_mod
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from scripts.ml.rigorous_backtest_v1 import BarsCache, Signal, TEST_YEARS
from scripts.ml.rigorous_backtest_v9_ob import V8A_STOP
from scripts.ml.v9_ob_leak_audit import all_events_picks
from scripts.ml.v10_raw_ob_slippage import Slippage, simulate_v7_slip, resolve_dir

ROOT = Path(r"C:\Users\benbr\BacktestStation")
ANCHORS_FVG = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_sweep") / "data" / "ml" / "anchors"
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-17_v15_fvg_zone_reaction_slippage"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# v13 cluster #2 — the +10,420R / 6/6 yrs / 0.150 avg_R finding
# Multiple zone_reaction labels share the same event population; pick one.
FVG_ZONE_SIGNALS = [
    Signal("fvg_zone_took_high_all",
           ANCHORS_FVG, "fvg_snapshots_xctx_fvggeom_obgeom",
           "at_fire", "all",
           "label.zone_reaction.took_fvg_high",
           "side_aware"),
]

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
    print("=== V15 — FVG zone_reaction slippage check ===")
    print(f"output: {OUT_DIR}")
    t0 = time_mod.time()

    print("\nStep 1: gather ALL events under fvg_snapshots_xctx_fvggeom_obgeom / zone_reaction.took_fvg_high...")
    all_frames = [all_events_picks(sig) for sig in FVG_ZONE_SIGNALS]
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
        yrs_pos = int(ex.groupby("test_year")["pnl_r"].sum().gt(0).sum()) if n else 0
        rollup.append({"slippage": slip.name, "n_trades": n, "cum_r": cum_r, "avg_r": avg_r,
                       "win_rate": win_rate, "max_dd_r": max_dd, "years_positive": yrs_pos})
        print(f"  [{slip.name:<25}] n={n:5d}  cum_R={cum_r:+8.1f}  avg_R={avg_r:+5.3f}  win%={win_rate:.3f}  DD={max_dd:5.1f}  yrs+={yrs_pos}/6")
        all_trades.append(td)

    pd.DataFrame(rollup).to_csv(OUT_DIR / "slippage_rollup.csv", index=False, float_format="%.4f")
    pd.concat(all_trades, ignore_index=True).to_csv(OUT_DIR / "trades_all_slippage.csv", index=False, float_format="%.4f")

    # Survival rates vs no_slippage baseline
    base = rollup[0]["cum_r"]
    print("\n=== Survival vs no_slippage baseline ===")
    for r in rollup:
        if base:
            pct = 100 * r["cum_r"] / base
            print(f"  {r['slippage']:<25}  cum_R={r['cum_r']:+8.1f}  ({pct:5.1f}% of baseline)")

    elapsed = (time_mod.time() - t0) / 60
    summary = {
        "label": "label.zone_reaction.took_fvg_high",
        "matrix": "fvg_snapshots_xctx_fvggeom_obgeom",
        "side": "all (side_aware direction)",
        "rollup": rollup,
        "elapsed_min": round(elapsed, 1),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== DONE in {elapsed:.1f} min ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
