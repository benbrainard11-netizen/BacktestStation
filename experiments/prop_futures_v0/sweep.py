"""sweep — deterministic design-window ORB parameter sweep for prop_futures_v0 Phase C.

Runs a fixed grid of ORB configs on the DESIGN window only (no holdout touched unless --holdout
is passed for a single pre-registered config). Vol-gate thresholds are derived on the design
window only (causal). Writes the full grid to out/sweep_design_<SYM>.csv and prints survivors.

Survivor rule (all must hold) — the design-window bar a config must clear to earn a holdout shot:
  net_R > 0  AND  both design halves net_R > 0 (two-regime same-sign, the btc_edge_v0 lesson)
  AND net_R excluding 2020 > 0 (no single-crisis-year mirage — the CL-AR2 trap)
  AND worst calendar year net_R > -0.20  AND  n >= 150 trades.

  python sweep.py --symbol CL.c.0
  python sweep.py --symbol CL.c.0 --holdout   # after review: ONE shot, the best design survivor
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from orb_engine import ORBConfig, build_dataset, derive_gate_threshold, get_spec, run_orb, summarize

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

START = "2016-01-01"
DESIGN_END = "2025-06-09"       # bar-only 12-month holdout: design ends here
HOLDOUT_START = "2025-06-10"
HOLDOUT_END = "2026-06-09"
GATE_PCTILE = 0.6               # gated configs trade only the top ~40% vol days


def build_grid():
    """(ORBConfig, pctile) cells. 3 OR lengths x 3 exits x 3 gates = 27 per symbol."""
    cells = []
    for om in (5, 15, 30):
        for tr in (1.0, 2.0, 0.0):  # 0.0 = ride to EOD (day-flat, no fixed target)
            cells.append((ORBConfig(or_minutes=om, target_R=tr, vol_gate="none"), None))
            cells.append((ORBConfig(or_minutes=om, target_R=tr, vol_gate="or_width"), GATE_PCTILE))
            cells.append((ORBConfig(or_minutes=om, target_R=tr, vol_gate="prior_atr"), GATE_PCTILE))
    return cells


def _survivor(r: dict) -> bool:
    return (r["n"] >= 150 and r["net_R"] > 0 and r["net_R_h1"] > 0 and r["net_R_h2"] > 0
            and r["net_R_ex2020"] > 0 and r["worst_year"] > -0.20)


def run_symbol(symbol: str, do_holdout: bool = False):
    spec = get_spec(symbol)
    df = build_dataset(symbol, START, HOLDOUT_END)
    design = df[df["date_et"] <= pd.Timestamp(DESIGN_END, tz=df["date_et"].dt.tz)]
    holdout = df[(df["date_et"] >= pd.Timestamp(HOLDOUT_START, tz=df["date_et"].dt.tz))
                 & (df["date_et"] <= pd.Timestamp(HOLDOUT_END, tz=df["date_et"].dt.tz))]
    n_design_days = design["date_et"].nunique()
    n_holdout_days = holdout["date_et"].nunique()

    recs = []
    for cfg, pct in build_grid():
        thr = derive_gate_threshold(design, spec, cfg, pct) if cfg.vol_gate != "none" else float("nan")
        cfg2 = replace(cfg, gate_threshold=thr)
        s = summarize(run_orb(design, spec, cfg2))
        s.update({"symbol": symbol, "or_minutes": cfg.or_minutes, "target_R": cfg.target_R,
                  "vol_gate": cfg.vol_gate, "gate_pctile": pct, "gate_threshold": thr})
        recs.append(s)
    grid = pd.DataFrame(recs)
    grid["survivor"] = grid.apply(lambda r: _survivor(r.to_dict()), axis=1)
    cols = ["symbol", "or_minutes", "target_R", "vol_gate", "gate_pctile", "gate_threshold",
            "n", "net_R", "win", "net_R_h1", "net_R_h2", "net_R_ex2020", "worst_year",
            "trades_per_year", "survivor"]
    grid = grid[cols].sort_values("net_R", ascending=False)
    path = OUT / f"sweep_design_{symbol.split('.')[0]}.csv"
    grid.to_csv(path, index=False)

    n_surv = int(grid["survivor"].sum())
    print(f"\n===== {symbol}  (design {n_design_days}d {START}..{DESIGN_END}, holdout {n_holdout_days}d) =====")
    print(f"cells tested: {len(grid)}   survivors: {n_surv}   -> {path.name}")
    print(grid.head(8).to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    if n_surv:
        print("\nSURVIVORS:")
        print(grid[grid["survivor"]].to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    if do_holdout:
        surv = grid[grid["survivor"]]
        if surv.empty:
            print("\nHOLDOUT: no design survivor -> NO SHOT FIRED (logged null).")
            return grid
        best = surv.iloc[0]  # single pre-registered config = best design survivor
        cfg = ORBConfig(or_minutes=int(best["or_minutes"]), target_R=float(best["target_R"]),
                        vol_gate=str(best["vol_gate"]),
                        gate_threshold=float(best["gate_threshold"]) if not pd.isna(best["gate_threshold"]) else float("nan"))
        hs = summarize(run_orb(holdout, spec, cfg))
        print(f"\n*** HOLDOUT SHOT {symbol}: cfg(or={cfg.or_minutes},tR={cfg.target_R},gate={cfg.vol_gate}) ***")
        print(f"    design net_R={best['net_R']:.3f} (n={int(best['n'])})  ->  HOLDOUT net_R={hs['net_R']:.3f} "
              f"(n={hs['n']}, win={hs['win']:.3f})")
        print(f"    VERDICT: {'PASS (net_R>0 OOS)' if hs['net_R'] > 0 else 'FAIL (net_R<=0 OOS)'}")
    return grid


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--holdout", action="store_true")
    a = ap.parse_args()
    run_symbol(a.symbol, a.holdout)
