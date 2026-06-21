"""Clean overnight-realism check on UNBIASED random liquid days. Compare daily 'open' to the actual
09:30 tradeable open (first RTH minute) and re-measure the overnight premium with the REAL tradeable
price. Robust to bad-print outliers (clip + median/trimmed). If daily-open ~= 09:30-open and the
overnight means match, the +12.7%/yr premium is real & tradeable, not a stale-open artifact.
Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from datetime import time as T
from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
MIN = POLY / "minute"
man = pd.read_parquet(POLY / "random_minute_manifest.parquet")

# daily open/close + prior close for the sampled tickers
df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
df = df[df["ticker"].isin(set(man["ticker"]))].sort_values(["ticker", "date"])
df["pc"] = df.groupby("ticker")["close"].shift(1)
dk = {(r.ticker, int(r.date)): (r.open, r.close, r.pc) for r in df.itertuples(index=False)}

rows = []
for r in man.itertuples(index=False):
    fp = MIN / f"{r.ticker}__{int(r.date)}.parquet"
    if not fp.exists():
        continue
    m = pd.read_parquet(fp)
    if not len(m):
        continue
    et = pd.to_datetime(m["t"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    rth = m[(et.dt.time >= T(9, 30)) & (et.dt.time < T(16, 0))]
    if not len(rth):
        continue
    mo = float(rth["o"].iloc[0])                          # 09:30 tradeable open
    do, dc, pc = dk.get((r.ticker, int(r.date)), (np.nan, np.nan, np.nan))
    if not (np.isfinite(do) and np.isfinite(pc) and mo > 0 and pc > 0):
        continue
    # guard against split/print mismatches between minute & daily: skip if daily-vs-minute open off by >25%
    if abs(do / mo - 1) > 0.25:
        continue
    rows.append((do / mo - 1, do / pc - 1, mo / pc - 1))

R = pd.DataFrame(rows, columns=["open_diff", "on_daily", "on_930"])
print(f"clean random liquid stock-days: {len(R):,}\n")
print("=== is daily 'open' the actual 09:30 tradeable open? ===")
print(f"  daily-open vs 09:30-open:  median {R['open_diff'].median()*100:+.3f}%  mean {R['open_diff'].mean()*100:+.3f}%  "
      f"|diff|<0.1%: {(R['open_diff'].abs()<0.001).mean()*100:.0f}%  |diff|>0.5%: {(R['open_diff'].abs()>0.005).mean()*100:.1f}%")
print("\n=== overnight return measured DAILY-open vs 09:30-tradeable-open (mean & trimmed) ===")
for col, lbl in [("on_daily", "via DAILY open"), ("on_930", "via 09:30 tradeable open")]:
    x = R[col]
    tr = x[(x > x.quantile(0.005)) & (x < x.quantile(0.995))]
    print(f"  {lbl:26s} mean {x.mean()*100:+.3f}%/day  trimmed {tr.mean()*100:+.3f}%/day  (~{tr.mean()*252*100:+.1f}%/yr)")
print("\nREAD: median open-diff ~0 + the two overnight means MATCH => the daily-open overnight premium is")
print("real & tradeable (you can MOO into that price). Big gap between the two => daily open not tradeable.")
