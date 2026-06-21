"""The deployable ENERGY RV book -- the confirmed survivor, characterized as a bot spec.

cointegration_select.py confirmed RV holds OOS on clean daily closes, concentrated in the energy complex
(CL/BZ/RB/HO crack + brent-WTI). This builds that book explicitly (all crude/brent/product pairs), equal-
weighted, and reports full + OOS Sharpe / CAGR / maxDD + per-pair, with 2bp cost. This is the real edge to
turn into the first non-Mira bot.

Run: backend/.venv/Scripts/python.exe experiments/edge_hunt_v0/energy_rv_book.py
"""
from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd

R = pd.read_parquet(Path(__file__).resolve().parents[1] / "sync_regime_v0" / "out" / "daily_returns.parquet")
R.index = pd.to_datetime(R.index)
LOGP = R.cumsum()
ANN = np.sqrt(252.0)
SPLIT = pd.Timestamp("2023-01-01", tz="UTC")
BETAWIN, ZWIN, COST_BPS = 250, 60, 2.0
ENERGY = ["CL.c.0", "BZ.c.0", "HO.c.0", "RB.c.0"]   # crude, brent, heating oil, gasoline (NG excluded -- idiosyncratic)


def net_series(a: str, b: str) -> pd.Series:
    A, B = LOGP[a], LOGP[b]
    beta = A.rolling(BETAWIN).cov(B) / B.rolling(BETAWIN).var()
    spread = A - beta * B
    z = (spread - spread.rolling(ZWIN).mean()) / spread.rolling(ZWIN).std()
    pos = -(z / 2.0).clip(-1.0, 1.0)
    pnl = pos.shift(1) * (R[a] - beta * R[b])
    return pnl - pos.diff().abs() * (2.0 * COST_BPS) / 1e4


def stats(x: pd.Series) -> dict:
    x = x.dropna()
    if len(x) < 50 or x.std() == 0:
        return {"sh": np.nan, "cagr": np.nan, "dd": np.nan}
    eq = x.cumsum()
    return {"sh": float(x.mean() / x.std() * ANN), "cagr": float(x.mean() * 252), "dd": float((eq - eq.cummax()).min())}


def main() -> int:
    pairs = list(itertools.combinations(ENERGY, 2))
    nets = {p: net_series(*p) for p in pairs}
    print(f"ENERGY RV book: {len(pairs)} pairs (crude/brent/HO/RB), 2bp cost, OOS split {SPLIT.date()}\n")
    print(f"  {'pair':12} {'fullSh':>7} {'OOS_Sh':>7} {'CAGR':>7} {'maxDD':>7}")
    for p in pairs:
        n = nets[p]
        f, o = stats(n), stats(n[n.index >= SPLIT])
        print(f"  {p[0][:-4]+'/'+p[1][:-4]:12} {f['sh']:>7.2f} {o['sh']:>7.2f} {f['cagr']:>6.1%} {f['dd']:>7.3f}")
    book = pd.concat(nets.values(), axis=1).mean(axis=1)
    f, o = stats(book), stats(book[book.index >= SPLIT])
    print(f"\n  EQUAL-WEIGHT BOOK:  full Sharpe={f['sh']:+.2f}  OOS Sharpe={o['sh']:+.2f}  "
          f"full CAGR={f['cagr']:+.1%}  maxDD={f['dd']:.3f}")
    # yearly OOS consistency
    yr = book.groupby(book.index.year).apply(lambda s: stats(s)["sh"])
    print(f"  per-year Sharpe: " + "  ".join(f"{y}:{v:+.2f}" for y, v in yr.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
