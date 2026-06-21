"""GEX gamma-regime filter across the REAL Jan-Jun trade set (funnel stage 2 validation).

The Jan finding (pos-gamma +0.57R vs neg-gamma +0.33R) was one window; the holdout was
~all pos-gamma so it couldn't confirm. With the train window rebuilt, every month now has
realized-R trades: does the pos-gamma lift replicate month by month?

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/gex_monthly_test.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import gate as G  # noqa: E402

OPP = "combined.sweep_setup_event_id"
SOURCES = ["jan_oos", "train", "oos_holdout"]
GEX = Path(r"C:\Users\benbr\BacktestStation\experiments\options_signals_v0\out\gex_levels_spx.parquet")


def st(x) -> str:
    x = pd.to_numeric(x, errors="coerce").dropna()
    if not len(x):
        return "n=  0"
    return f"n={len(x):4d} meanR={x.mean():+.3f} win={100 * (x > 0).mean():4.1f}% sumR={x.sum():+7.1f}"


def main() -> int:
    g = pd.read_parquet(GEX)
    g["d"] = pd.to_datetime(g["date"].astype(int).astype(str), format="%Y%m%d").dt.date
    gm = dict(zip(g["d"], g["total_gex"] > 0))

    gate = G.Gate()
    parts = []
    for name in SOURCES:
        d = pd.read_parquet(HERE / "data" / f"{name}.parquet")
        d["trigger_ts_utc"] = pd.to_datetime(d["trigger_ts_utc"], utc=True)
        parts.append(d)
    full = pd.concat(parts, ignore_index=True)
    full = full.sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
    full = full.drop_duplicates(subset=["symbol", "trigger_ts_utc", "trigger_id", OPP], keep="first")
    full["p"] = gate.score(full)
    gt = (full[full.p >= gate.threshold]
          .sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
          .groupby(OPP, sort=False).head(1).copy())
    gt["date"] = gt["trigger_ts_utc"].dt.date
    gt["pos_gamma"] = gt["date"].map(gm)
    gt["rr"] = pd.to_numeric(gt["realized_r"], errors="coerce")
    gt["_mo"] = gt["trigger_ts_utc"].dt.strftime("%Y-%m")

    unmapped = gt["pos_gamma"].isna().sum()
    print(f"gated/deduped={len(gt)}  gex-unmapped={unmapped}  "
          f"pos-gamma share of mapped trades={100 * (gt['pos_gamma'] == True).mean():.0f}%\n")

    print("=== POOLED (Jan 2 - Jun 5) ===")
    print(f"  ALL        {st(gt['rr'])}")
    print(f"  POS gamma  {st(gt.loc[gt.pos_gamma == True, 'rr'])}")
    print(f"  NEG gamma  {st(gt.loc[gt.pos_gamma == False, 'rr'])}")

    print("\n=== BY MONTH ===")
    for mo, sub in gt.groupby("_mo"):
        pos = sub.loc[sub.pos_gamma == True, "rr"]
        neg = sub.loc[sub.pos_gamma == False, "rr"]
        npos, nneg = len(pos.dropna()), len(neg.dropna())
        pm = pos.dropna().mean() if npos else np.nan
        nm = neg.dropna().mean() if nneg else np.nan
        diff = pm - nm if npos and nneg else np.nan
        print(f"{mo}  POS n={npos:3d} meanR={pm:+.3f}" if npos else f"{mo}  POS n=  0",
              f" | NEG n={nneg:3d} meanR={nm:+.3f}" if nneg else " | NEG n=  0",
              f" | lift={diff:+.3f}" if np.isfinite(diff) else " | lift=NA")

    print("\n=== BY SYMBOL (pooled) ===")
    for sym, sub in gt.groupby(gt["symbol"].astype(str)):
        pos = sub.loc[sub.pos_gamma == True, "rr"].dropna()
        neg = sub.loc[sub.pos_gamma == False, "rr"].dropna()
        print(f"{sym:8s} POS {st(pos)}   NEG {st(neg)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
