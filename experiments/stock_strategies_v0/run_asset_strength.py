"""Asset relative strength (cross-sectional momentum) on the CLEAN Polygon universe
(delisted-included common stocks). Rank stocks by trailing 12-1mo return; do the leaders
keep winning next month? rank-IC + decile spreads. Honest (survivorship-clean). Also tells
us if 'strength' is a useful FEATURE for the earnings ML model. 2021-2026.
Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

POLY = Path(r"D:\data\processed\stocks\polygon")
df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
cs = set(pd.read_parquet(POLY / "meta.parquet")["ticker"])
df = df[df["ticker"].isin(cs)].copy()
df["dt"] = pd.to_datetime(df["date"].astype(int).astype(str), format="%Y%m%d")
df["dvol"] = df["close"] * df["volume"]

me = df.groupby("ticker").resample("ME", on="dt").agg(close=("close", "last"), dvol=("dvol", "mean"))
close = me["close"].unstack(0)            # months x tickers
dvol = me["dvol"].unstack(0)
liq = (close >= 5) & (dvol >= 1e6)        # tradeable filter at formation

trail = close.shift(1) / close.shift(12) - 1     # 12-1mo momentum (causal at month t)
fwd = close.shift(-1) / close - 1                # next-month return
print(f"{close.shape[1]} stocks, {close.shape[0]} months ({close.index[0].date()}..{close.index[-1].date()})\n")

ics, ls, td, bd = [], [], [], []
for t in close.index:
    tr, fr, lq = trail.loc[t], fwd.loc[t], liq.loc[t]
    ok = tr.notna() & fr.notna() & lq
    if ok.sum() < 30:
        continue
    x, y = tr[ok], fr[ok]
    ics.append(spearmanr(x, y).correlation)
    q = x.rank(pct=True)
    top, bot = y[q >= 0.9], y[q <= 0.1]       # decile portfolios
    td.append(top.mean()); bd.append(bot.mean()); ls.append(top.mean() - bot.mean())

ic = np.array(ics); LS = np.array(ls)
print(f"months scored: {len(ic)} | avg cross-section size ~{int(liq.sum(1).mean())}")
print(f"rank-IC (trailing 12-1mo vs next-month): mean {np.nanmean(ic):+.3f}  (t~{np.nanmean(ic)/ (np.nanstd(ic)/len(ic)**.5):.1f})")
print(f"top decile next-mo:    {np.nanmean(td)*100:+.2f}%/mo")
print(f"bottom decile next-mo: {np.nanmean(bd)*100:+.2f}%/mo")
print(f"LONG-SHORT (top-bottom): {np.nanmean(LS)*100:+.2f}%/mo = {((1+np.nanmean(LS))**12-1)*100:+.1f}%/yr | win {np.mean(LS>0)*100:.0f}% of months")
print("\nREAD: positive rank-IC + positive long-short = relative strength persists (real signal,")
print("usable as an ML feature and maybe standalone). ~0 => 'strength' adds nothing.")
