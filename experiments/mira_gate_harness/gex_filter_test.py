"""Test options-derived GAMMA REGIME (SPX total_gex sign) as a FILTER on the gated Mira trades.
Hypothesis: mean-reversion reclaims work better in POSITIVE gamma (dealers fade -> pin/mean-revert)
and fail in NEGATIVE gamma (dealers chase -> trend). Cheap: precomputed GEX join + split, no rebuild.
SPX GEX = market-wide regime applied to all symbols (NDX-for-NQ is a later refinement).

Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/gex_filter_test.py
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
GATE = G.Gate()
GEX = Path(r"C:\Users\benbr\BacktestStation\experiments\options_signals_v0\out\gex_levels_spx.parquet")


def gex_map() -> dict:
    g = pd.read_parquet(GEX)
    g["d"] = pd.to_datetime(g["date"].astype(int).astype(str), format="%Y%m%d").dt.date
    return dict(zip(g["d"], g["total_gex"] > 0))


def gated(name: str) -> pd.DataFrame:
    d = pd.read_parquet(HERE / "data" / f"{name}.parquet")
    d["trigger_ts_utc"] = pd.to_datetime(d["trigger_ts_utc"], utc=True)
    d["p"] = GATE.score(d)
    gt = (d[d.p >= GATE.threshold].sort_values(["trigger_ts_utc", "trigger_id"], kind="stable")
          .groupby(OPP, sort=False).head(1).copy())
    gt["date"] = gt["trigger_ts_utc"].dt.date
    gt["rr"] = pd.to_numeric(gt["realized_r"], errors="coerce")
    return gt


def st(x):
    x = x.dropna()
    return f"n={len(x):3d} meanR={x.mean():+.3f} win={100*(x>0).mean():.0f}% sumR={x.sum():+.1f}" if len(x) else "n=0"


def main() -> int:
    gm = gex_map()
    print(f"GEX days loaded: {len(gm)} (pos_gamma share {100*np.mean(list(gm.values())):.0f}%)\n")
    for name in ["jan_oos", "oos_holdout", "jan_plus"]:
        p = HERE / "data" / f"{name}.parquet"
        if not p.exists():
            print(f"{name}: (not built)"); continue
        gt = gated(name)
        gt["pos_gamma"] = gt["date"].map(gm)
        mapped = gt["pos_gamma"].notna().sum()
        print(f"=== {name} (gated {len(gt)}, gex-mapped {mapped}) ===")
        print(f"  ALL          {st(gt['rr'])}")
        print(f"  POS gamma    {st(gt[gt.pos_gamma == True]['rr'])}")
        print(f"  NEG gamma    {st(gt[gt.pos_gamma == False]['rr'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
