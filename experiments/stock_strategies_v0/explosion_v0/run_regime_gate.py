"""Is the 'explosion regime' a usable self-gate? Measure: (1) FREQUENCY — monthly readings of the
top-decile's realized R + explosion rate; (2) PERSISTENCE — does 'hot' stay hot (lag-1 autocorrelation,
# of hot/cold switches)? A gate only works if the regime is persistent enough that a CAUSAL trailing
signal predicts next month; (3) IS IT GOOD — does a causal gate (trade only when trailing signal hot)
beat always-on? Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

oos = pd.read_parquet(Path(__file__).resolve().parent / "out" / "explosion_oos.parquet")
top = oos[oos["dec"] == 9].copy()
top["ym"] = pd.to_datetime(top["date"].astype(int).astype(str), format="%Y%m%d").dt.to_period("M")

m = top.groupby("ym").agg(R=("trade_R", "mean"), expl=("expl40", "mean"), n=("trade_R", "size"))
m = m[m["n"] >= 15]                                   # months with enough signals
print(f"months: {len(m)} ({m.index[0]}..{m.index[-1]}) | avg {m['n'].mean():.0f} top-decile trades/mo")
print(f"\n=== (1) FREQUENCY: you get a fresh read every month (strategy fires ~daily) ===")
print(f"  monthly top-decile R: mean {m['R'].mean():+.3f}  std {m['R'].std():.3f}  %hot(R>0) {(m['R']>0).mean()*100:.0f}%")

print(f"\n=== (2) PERSISTENCE: does HOT stay HOT? ===")
ac1 = m["R"].autocorr(1); ac2 = m["R"].autocorr(2); ac3 = m["R"].autocorr(3)
print(f"  autocorrelation of monthly R: lag1 {ac1:+.2f}  lag2 {ac2:+.2f}  lag3 {ac3:+.2f}  (>~0.3 = persistent/usable)")
sign = (m["R"] > 0).astype(int)
switches = (sign.diff().abs() == 1).sum()
print(f"  hot/cold switches: {switches} over {len(m)} months ({switches/ (len(m)/12):.1f}/yr) -> "
      f"avg streak {len(m)/max(switches,1):.1f} months")
# explosion-rate persistence too
print(f"  autocorr of monthly explosion-rate: lag1 {m['expl'].autocorr(1):+.2f}")

print(f"\n=== (3) IS IT GOOD: causal gate (trade month t only if trailing-3mo R > 0, decided BEFORE t) ===")
m = m.copy()
m["sig"] = m["R"].rolling(3).mean().shift(1)          # causal: trailing 3mo through t-1
g = m.dropna(subset=["sig"])
on = g[g["sig"] > 0]; off = g[g["sig"] <= 0]
print(f"  always-on:  mean monthly R {g['R'].mean():+.3f}  ({len(g)} mo)")
print(f"  GATE ON  (trailing hot):  mean monthly R {on['R'].mean():+.3f}  ({len(on)} mo, {len(on)/len(g)*100:.0f}% of time)")
print(f"  gate OFF (trailing cold): mean monthly R {off['R'].mean():+.3f}  ({len(off)} mo) <- what you'd skip")
print(f"  gate captures {on['R'].sum()/g['R'].clip(lower=-99).sum()*100 if g['R'].sum()!=0 else float('nan'):.0f}% of total R while trading {len(on)/len(g)*100:.0f}% of months")

print(f"\n=== the monthly tape (R = top-decile trade_R that month) ===")
for ym, row in m.iterrows():
    bar = "#" * int(min(max(row["R"] * 20 + 5, 0), 40))
    print(f"  {ym}  R {row['R']:+.2f}  expl {row['expl']*100:2.0f}%  n{int(row['n']):4d}  {bar}")
print("\nREAD: high autocorr + few switches + gate-on R >> gate-off => a usable regime gate.")
print("low autocorr + many switches + gate doesn't separate => regime flips too fast = whipsaw (unusable).")
