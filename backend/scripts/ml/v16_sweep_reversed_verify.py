"""V16 — verify v13's sweep reversed-direction +4,362R finding.

v13 cluster #5: Sweep all-reversed +4,362R / 6/6 yrs / 0.300 avg_R / 14,541 trades
  matrix: sweep_snapshots_xctx_fvggeom
  side filter: all
  direction_rule: side_aware -> REVERSED
  label (one of 10 clones): label.ob_confirmation.did_confirm

This script re-runs the same simulation independently and breaks results down
by year, symbol, and anchor.side (sweep subtype). The breakdown should reveal:
  - Whether all 6 years contribute or one dominates
  - NQ vs ES split (informs sizing)
  - side=high vs side=low (do both contribute equally?)
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
from scripts.ml.v9_ob_leak_audit import all_events_picks, simulate_picks

ROOT = Path(r"C:\Users\benbr\BacktestStation")
ANCHORS_SWEEP = Path(r"D:\BacktestStationData\strategy_lab_core_2026_05_15_strict_sweep") / "data" / "ml" / "anchors"
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-17_v16_sweep_reversed_verify"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# v13 cluster #5 — pick one label from the 10 clones
SWEEP_VERIFY_SIGNALS = [
    Signal("sweep_ob_confirm_all",
           ANCHORS_SWEEP, "sweep_snapshots_xctx_fvggeom",
           "at_fire", "all",
           "label.ob_confirmation.did_confirm",
           "side_aware"),
]


def main() -> int:
    print("=== V16 — verify sweep reversed +4,362R ===")
    print(f"output: {OUT_DIR}")
    t0 = time_mod.time()

    print("\nStep 1: gather ALL sweep events...")
    all_frames = [all_events_picks(sig) for sig in SWEEP_VERIFY_SIGNALS]
    all_picks = pd.concat(all_frames, ignore_index=True)
    print(f"  all-event picks: {len(all_picks):,}")

    bars = BarsCache()
    print("Step 2: simulate REVERSED direction (high->LONG, low->SHORT)...")
    td = simulate_picks(all_picks, bars, V8A_STOP, reverse_direction=True, label="B_sweep_REVERSED")
    ex = td[td["exit_reason"].isin(["target", "stop", "time_exit"])]
    n = len(ex)
    cum_r = float(ex["pnl_r"].sum()) if n else 0.0
    avg_r = float(ex["pnl_r"].mean()) if n else 0.0
    win_rate = float((ex["pnl_r"] > 0).mean()) if n else 0.0
    cumr = ex.sort_values("fire_ts")["pnl_r"].cumsum()
    max_dd = float((cumr.cummax() - cumr).max())
    years_pos = int(ex.groupby("test_year")["pnl_r"].sum().gt(0).sum())
    print(f"\n  Sweep all-events REVERSED: n={n} cum_R={cum_r:+.1f} avg_R={avg_r:+.3f} win%={win_rate:.3f} DD={max_dd:.1f} yrs+={years_pos}/6")
    print(f"  v13 prediction: +4,362R, 0.300 avg_R, 6/6 yrs (would match within ~10%)")

    per_year = ex.groupby("test_year")["pnl_r"].agg(["count", "sum", "mean"])
    per_year.columns = ["n", "cum_r", "avg_r"]
    print("\n=== Per-year ===")
    print(per_year.to_string(float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    per_sym = ex.groupby("symbol")["pnl_r"].agg(["count", "sum", "mean"])
    per_sym.columns = ["n", "cum_r", "avg_r"]
    print("\n=== Per-symbol ===")
    print(per_sym.to_string(float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    per_side = ex.groupby("anchor_side")["pnl_r"].agg(["count", "sum", "mean"])
    per_side.columns = ["n", "cum_r", "avg_r"]
    print("\n=== Per anchor.side (sweep type) ===")
    print(per_side.to_string(float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    ex.to_csv(OUT_DIR / "trades.csv", index=False, float_format="%.4f")
    summary = {
        "n_trades": int(n), "cum_r": cum_r, "avg_r": avg_r, "win_rate": win_rate,
        "max_dd_r": max_dd, "years_positive": years_pos,
        "per_year": {int(k): {"n": int(r["n"]), "cum_r": float(r["cum_r"]), "avg_r": float(r["avg_r"])}
                     for k, r in per_year.iterrows()},
        "per_symbol": {sym: {"n": int(r["n"]), "cum_r": float(r["cum_r"]), "avg_r": float(r["avg_r"])}
                       for sym, r in per_sym.iterrows()},
        "per_anchor_side": {side: {"n": int(r["n"]), "cum_r": float(r["cum_r"]), "avg_r": float(r["avg_r"])}
                            for side, r in per_side.iterrows()},
        "v13_prediction": {"cum_r": 4362.0, "avg_r": 0.300, "years_positive": 6},
        "elapsed_min": round((time_mod.time() - t0) / 60, 1),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== DONE in {(time_mod.time()-t0)/60:.1f} min ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
