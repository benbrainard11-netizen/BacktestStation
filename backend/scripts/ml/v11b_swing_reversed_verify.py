"""V11b — verify that swing reversed-correct delivers ~+8,625R as predicted.

The v11 multi-family audit found:
  swing_continuation A (my direction):  -1,633R
  swing_continuation C (REVERSED dir):  +1,471R (same picks, reversed direction)
  swing_continuation B (ALL events, my direction):  -8,625R

The prediction: all events with REVERSED direction should be ~+8,625R.

This script verifies that prediction: trade every swing event with the
opposite direction my v11 rules used (side=high -> SHORT, side=low -> LONG).
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
from scripts.ml.rigorous_backtest_v7_stops import StopVariant
from scripts.ml.rigorous_backtest_v9_ob import V8A_STOP
from scripts.ml.v9_ob_leak_audit import all_events_picks, simulate_picks
from scripts.ml.v11_multi_family_event_audit import SWING_SIGNALS

ROOT = Path(r"C:\Users\benbr\BacktestStation")
OUT_DIR = ROOT / "experiments" / "backtests" / "2026-05-16_v11b_swing_reversed"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> int:
    print("=== V11b — verify swing reversed-correct B variant ===")
    t0 = time_mod.time()

    print("\nStep 1: gather ALL swing events...")
    all_frames = [all_events_picks(sig) for sig in SWING_SIGNALS]
    all_picks = pd.concat(all_frames, ignore_index=True)
    print(f"  all-event picks: {len(all_picks):,}")

    bars = BarsCache()
    print("Step 2: simulate B with REVERSED direction (= correct direction for swing)...")
    td = simulate_picks(all_picks, bars, V8A_STOP, reverse_direction=True, label="B_swing_REVERSED")
    ex = td[td["exit_reason"].isin(["target", "stop", "time_exit"])]
    n = len(ex)
    cum_r = float(ex["pnl_r"].sum()) if n else 0.0
    avg_r = float(ex["pnl_r"].mean()) if n else 0.0
    win_rate = float((ex["pnl_r"] > 0).mean()) if n else 0.0
    cumr = ex.sort_values("fire_ts")["pnl_r"].cumsum()
    max_dd = float((cumr.cummax() - cumr).max())
    years_pos = int(ex.groupby("test_year")["pnl_r"].sum().gt(0).sum())
    print(f"\n  swing_all_events_REVERSED: n={n} cum_R={cum_r:+.1f} avg_R={avg_r:+.3f} win%={win_rate:.3f} DD={max_dd:.1f} yrs+={years_pos}/6")

    per_year = ex.groupby("test_year")["pnl_r"].sum()
    print("\n=== Per-year ===")
    for y in TEST_YEARS:
        print(f"  {y}: {per_year.get(y, 0):+.1f}")

    per_sym = ex.groupby("symbol")["pnl_r"].agg(["count", "sum", "mean"])
    per_sym.columns = ["n", "cum_r", "avg_r"]
    print("\n=== Per-symbol ===")
    print(per_sym.to_string(float_format=lambda x: f"{x:.3f}" if isinstance(x, float) else str(x)))

    ex.to_csv(OUT_DIR / "trades.csv", index=False, float_format="%.4f")
    summary = {
        "n_trades": int(n), "cum_r": cum_r, "avg_r": avg_r, "win_rate": win_rate,
        "max_dd_r": max_dd, "years_positive": years_pos,
        "per_year": {int(k): float(v) for k, v in per_year.items()},
        "per_symbol": {sym: {"n": int(r["n"]), "cum_r": float(r["cum_r"]), "avg_r": float(r["avg_r"])}
                       for sym, r in per_sym.iterrows()},
        "elapsed_min": round((time_mod.time() - t0) / 60, 1),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n=== DONE in {(time_mod.time()-t0)/60:.1f} min ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
