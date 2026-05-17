"""V17 — Slippage check on Sweep reversed + hour-filter sub-scenario.

Same pattern as v15 but on the v16 winning Sweep signal:
  matrix: sweep_snapshots_xctx_fvggeom
  side filter: all
  label: label.ob_confirmation.did_confirm
  direction_rule: side_aware -> REVERSED

3 slippage scenarios x 2 filters (all hours / drop Asia 22-06 UTC) = 6 rows.
Picks the deploy-ready Sweep number after friction + the per-hour finding.
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
ANCHORS_SWEEP = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_sweep") / "data" / "ml" / "anchors"
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-17_v17_sweep_slippage"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SWEEP_SIGNALS = [
    Signal("sweep_ob_confirm_all",
           ANCHORS_SWEEP, "sweep_snapshots_xctx_fvggeom",
           "at_fire", "all",
           "label.ob_confirmation.did_confirm",
           "side_aware"),
]

SLIPPAGES = [
    Slippage("no_slippage"),
    Slippage("1tick", entry_ticks=1.0, stop_ticks=1.0, time_exit_ticks=1.0),
    Slippage("2tick", entry_ticks=2.0, stop_ticks=2.0, time_exit_ticks=2.0),
]

# Hours to drop for "filtered" scenario (Asia overnight)
DROP_HOURS = {22, 23, 0, 1, 2, 3, 4, 5, 6}


def run_picks_with_slip(picks, bars, variant, slip):
    """Trade REVERSED direction for sweep (high->LONG, low->SHORT)."""
    picks = picks[picks["symbol"].isin(["NQ.c.0", "ES.c.0"])].copy()
    # Reverse the natural direction (this is the v13/v16 finding)
    picks["natural_dir"] = picks["anchor_side"].apply(resolve_dir)
    picks["direction"] = picks["natural_dir"].apply(lambda d: "long" if d == "short" else "short")
    trades = []
    for _, row in picks.iterrows():
        if pd.isna(row["fire_ts"]):
            continue
        sim = simulate_v7_slip(bars, row["symbol"], row["fire_ts"], row["direction"], variant, slip)
        trades.append({
            "slippage": slip.name,
            "test_year": int(row["test_year"]), "symbol": row["symbol"],
            "anchor_side": row["anchor_side"], "direction": row["direction"],
            "fire_ts": row["fire_ts"],
            **sim,
        })
    return pd.DataFrame(trades)


def stats(td: pd.DataFrame) -> dict:
    ex = td[td["exit_reason"].isin(["target", "stop", "time_exit"])]
    n = len(ex)
    if n == 0:
        return {"n": 0, "cum_r": 0.0, "avg_r": 0.0, "win_rate": 0.0, "max_dd": 0.0, "yrs_pos": 0}
    cumr = ex.sort_values("fire_ts")["pnl_r"].cumsum()
    return {
        "n": n,
        "cum_r": float(ex["pnl_r"].sum()),
        "avg_r": float(ex["pnl_r"].mean()),
        "win_rate": float((ex["pnl_r"] > 0).mean()),
        "max_dd": float((cumr.cummax() - cumr).max()),
        "yrs_pos": int(ex.groupby("test_year")["pnl_r"].sum().gt(0).sum()),
    }


def main() -> int:
    print("=== V17 — Sweep slippage + hour-filter ===")
    print(f"output: {OUT_DIR}")
    t0 = time_mod.time()

    print("\nStep 1: gather sweep events...")
    all_frames = [all_events_picks(sig) for sig in SWEEP_SIGNALS]
    all_picks = pd.concat(all_frames, ignore_index=True)
    print(f"  all-event picks: {len(all_picks):,}")

    bars = BarsCache()
    print(f"\nStep 2: simulate {len(SLIPPAGES)} slippage scenarios x 2 filters = 6 rows")

    rollup = []
    all_trades = []
    for slip in SLIPPAGES:
        td = run_picks_with_slip(all_picks, bars, V8A_STOP, slip)
        td["entry_hour_utc"] = pd.to_datetime(td["entry_ts"], utc=True, errors="coerce").dt.hour
        all_trades.append(td)

        for filter_name, mask in [("all_hours", pd.Series(True, index=td.index)),
                                   ("hour_filter_drop_22_06", ~td["entry_hour_utc"].isin(DROP_HOURS))]:
            sub = td[mask]
            s = stats(sub)
            rollup.append({
                "slippage": slip.name, "filter": filter_name,
                **s,
            })
            print(f"  [{slip.name:<11} / {filter_name:<24}] n={s['n']:5d}  cum_R={s['cum_r']:+8.1f}  "
                  f"avg_R={s['avg_r']:+5.3f}  win%={s['win_rate']:.3f}  DD={s['max_dd']:5.1f}  yrs+={s['yrs_pos']}/6")

    pd.DataFrame(rollup).to_csv(OUT_DIR / "slippage_filter_rollup.csv", index=False, float_format="%.4f")
    pd.concat(all_trades, ignore_index=True).to_csv(OUT_DIR / "trades_all.csv", index=False, float_format="%.4f")

    # Summary: deploy-ready number = 2tick + hour_filter
    deploy_row = next(r for r in rollup if r["slippage"] == "2tick" and r["filter"] == "hour_filter_drop_22_06")
    baseline_row = next(r for r in rollup if r["slippage"] == "no_slippage" and r["filter"] == "all_hours")
    print(f"\n=== Deploy-ready Sweep number ===")
    print(f"  Baseline (no slip, all hrs):  cum_R={baseline_row['cum_r']:+8.1f}  avg_R={baseline_row['avg_r']:+5.3f}  n={baseline_row['n']}")
    print(f"  Deploy (2tick + hr filter):   cum_R={deploy_row['cum_r']:+8.1f}  avg_R={deploy_row['avg_r']:+5.3f}  n={deploy_row['n']}")
    print(f"  Survival: {100*deploy_row['cum_r']/baseline_row['cum_r']:.0f}% of baseline")

    elapsed = (time_mod.time() - t0) / 60
    summary = {
        "rollup": rollup,
        "deploy_ready": deploy_row,
        "baseline": baseline_row,
        "elapsed_min": round(elapsed, 1),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== DONE in {elapsed:.1f} min ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
