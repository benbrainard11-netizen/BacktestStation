"""Translate measured Leg-B bookproxy drift -> gate-score shift -> implied arm loss.

Takes the frozen gate's ARMED Jan setups (full Databento feature vectors), scales their
cluster.bookproxy features by a drift factor (Rithmic/Databento), re-scores through the FROZEN
gate, and counts how many cross below the 0.5818 threshold (= arms a long-only live bot would lose
to that much feature drift). Runs the MEASURED drift plus a sensitivity sweep so the result is
placed on a curve.

No gate retuning, no live connection.
Run: backend/.venv/Scripts/python.exe experiments/sizing_v1/legb_gate_impact.py --add 0.99 --cancel 0.99
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import gate as G  # noqa: E402

GATE = G.Gate()
THR = GATE.threshold
OPP = "combined.sweep_setup_event_id"
JAN_COMBINED = Path(r"C:\Users\benbr\bs-mira-v15\experiments\mira_v15_gate_validation"
                    r"\work_2026jan_mbo_oos\combined\mira_combined.parquet")


def jan_armed() -> pd.DataFrame:
    df = pd.read_parquet(JAN_COMBINED)
    df["trigger_ts_utc"] = pd.to_datetime(df["trigger_ts_utc"], utc=True)
    m = ((df["trigger_type"] == "post_sweep_smt") & (df["smt_anchor_side"].isin(["low", "high"]))
         & df["trigger_price"].notna() & df[OPP].notna())
    pss = df[m].copy()
    pss["gate_score"] = GATE.score(pss)
    g = pss[pss["gate_score"] >= THR].copy()
    keep = (g.sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
            .groupby(OPP, sort=False).head(1).index)
    return pss.loc[keep].copy()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--add", type=float, default=0.99, help="measured Rithmic/Databento ADD ratio")
    ap.add_argument("--cancel", type=float, default=0.99, help="measured CANCEL ratio")
    args = ap.parse_args()

    armed = jan_armed()
    base = GATE.score(armed)
    n = len(armed)
    bp = [c for c in GATE.raw_features if "bookproxy" in c.lower()]
    add_feats = [c for c in bp if "cancel_to_add" not in c]      # add-size features
    ratio_feats = [c for c in bp if "cancel_to_add" in c]        # the cancel/add ratio feature
    print(f"frozen gate THR={THR:.4f}  Jan armed n={n}  bookproxy feats={len(bp)} "
          f"(add={len(add_feats)}, ratio={len(ratio_feats)})")
    print(f"base mean score={base.mean():.4f}  (all >= THR by construction)\n")

    print(f"  {'scenario':22s} {'add x':>6s} {'can x':>6s} {'mean Δscore':>11s} {'arms<THR':>9s} {'% arms lost':>11s}")
    scen = [("MEASURED", args.add, args.cancel)]
    scen += [(f"down {int((1-s)*100)}%", s, s) for s in [0.95, 0.90, 0.80, 0.70, 0.60, 0.50]]
    rows = []
    for name, s, c in scen:
        pert = armed.copy()
        for col in add_feats:
            pert[col] = pd.to_numeric(pert[col], errors="coerce") * s
        for col in ratio_feats:
            pert[col] = pd.to_numeric(pert[col], errors="coerce") * (c / s if s else 1.0)
        sc = GATE.score(pert)
        lost = int((sc < THR).sum())
        d = float((sc - base).mean())
        print(f"  {name:22s} {s:>6.2f} {c:>6.2f} {d:>+11.4f} {lost:>9d} {100*lost/n:>10.1f}%")
        rows.append({"scenario": name, "add_x": s, "cancel_x": c, "mean_dscore": d,
                     "arms_lost": lost, "pct_arms_lost": round(100 * lost / n, 1)})
    out = Path(r"C:\Users\benbr\BacktestStation\experiments\sizing_v1\out\mira_short_revalidation"
               r"\legb_gate_impact.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
