"""diag — does a cointegrated futures spread mean-revert INTRADAY (day-flat RV feasibility)?

The lab's one robust edge (energy_rv_v0/xsectional_rv_v0) is cointegration mean-reversion, but MULTI-DAY.
If the same spreads revert intraday, an automatable, market-neutral, DAY-FLAT RV strat is possible.
This is a feasibility probe (not a backtest): per pair, build the 1m intraday spread, measure the
AR(1) mean-reversion half-life of intraday deviations, and a 'fade the stretch' reversion test.

  python diag.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "prop_futures_v0"))
from orb_engine import build_dataset  # noqa: E402

PAIRS = [("CL.c.0", "BZ.c.0"), ("HO.c.0", "CL.c.0"), ("RB.c.0", "CL.c.0"),
         ("ZC.c.0", "ZW.c.0"), ("ZN.c.0", "ZF.c.0"), ("GC.c.0", "SI.c.0")]
START, END = "2024-01-01", "2025-12-31"
OPEN_M, CLOSE_M = 570, 960  # 09:30-16:00 ET common window


def diag_pair(a, b, W=60, H=30, THR=2.0):
    da = build_dataset(a, START, END); db = build_dataset(b, START, END)
    for d in (da, db):
        d.drop(d.index[(d["mod"] < OPEN_M) | (d["mod"] >= CLOSE_M)], inplace=True)
    m = da[["et", "close", "date_et"]].merge(db[["et", "close"]], on="et", suffixes=("_a", "_b"))
    if len(m) < 5000:
        print(f"  {a}-{b}: only {len(m)} aligned 1m bars, skip"); return
    beta = float(np.dot(m["close_a"], m["close_b"]) / np.dot(m["close_b"], m["close_b"]))
    m["spread"] = m["close_a"] - beta * m["close_b"]
    # CAUSAL trailing z: mean/std over the prior W bars within the day only (no future bars)
    g = m.groupby("date_et")["spread"]
    m["rm"] = g.transform(lambda s: s.rolling(W, min_periods=20).mean().shift(1))
    m["rs"] = g.transform(lambda s: s.rolling(W, min_periods=20).std().shift(1))
    m["z"] = (m["spread"] - m["rm"]) / m["rs"]
    m["fwd"] = m.groupby("date_et")["spread"].shift(-H)            # spread H bars later (same day)
    m = m[(m["rs"] > 0)].dropna(subset=["z", "fwd"])
    # honest trade: |z|>THR -> bet on reversion; PnL (spread pts) = -sign(z)*(fwd-spread); in std units
    e = m[m["z"].abs() > THR]
    pnl_std = (-np.sign(e["z"]) * (e["fwd"] - e["spread"]) / e["rs"]).to_numpy()
    # causal AR1 half-life of the trailing residual
    resid = (m["spread"] - m["rm"]).to_numpy()
    prv = m.groupby("date_et").apply(lambda d: (d["spread"] - d["rm"]).shift(1), include_groups=False).to_numpy()
    ok = ~np.isnan(prv) & ~np.isnan(resid)
    b1 = np.polyfit(prv[ok], resid[ok], 1)[0]
    half = -np.log(2) / np.log(b1) if 0 < b1 < 1 else np.inf
    print(f"  {a}-{b}: beta={beta:.3f} n={len(m)} | CAUSAL AR1={b1:.4f} half-life={half:.0f}min "
          f"| |z|>{THR} n={len(e)} fwd{H}m-PnL={np.nanmean(pnl_std):+.3f}std (frac>0 {np.mean(pnl_std>0):.2f}) "
          f"median={np.nanmedian(pnl_std):+.3f}std")


def main():
    print(f"intraday spread mean-reversion ({START}..{END}, RTH 09:30-16:00 ET)")
    for a, b in PAIRS:
        try:
            diag_pair(a, b)
        except Exception as e:
            print(f"  {a}-{b}: ERR {type(e).__name__}: {str(e)[:80]}")


if __name__ == "__main__":
    main()
