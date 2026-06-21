"""Earnings as an OVERLAY (the right deployment): hold SPY fully (no cash drag) and layer the earnings
trades' MARKET-RELATIVE return (the pure alpha) on top via extra notional. Net = SPY + L * alpha_stream.
Does adding the real-but-thin, defensive earnings alpha to beta beat SPY on Sharpe/Calmar? Sweep overlay
size L. Also report the alpha stream's own stats + a vol-matched comparison. Run w/ backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
HERE = Path(__file__).resolve().parent
HOLD, COST = 20, 0.003
S = pd.read_parquet(HERE / "out" / "earnings_clean.parquet")
S["price"] = np.exp(S["log_price"])
rule = S[(S["price"] >= 5) & (S["dvol"] >= 5e6) & (S["above_high"] == 1) &
         (S["gap"] >= 0.15) & (S["eps_surprise"] > 0)].copy()

df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
spy = df[df["ticker"] == "SPY"].sort_values("date")
cal = spy["date"].to_numpy().astype(int); cal_idx = {int(d): i for i, d in enumerate(cal)}
spy_ret = np.nan_to_num(pd.Series(spy["close"].to_numpy()).pct_change().to_numpy())
D = {t: (g["close"].to_numpy(), {int(x): i for i, x in enumerate(g["date"].to_numpy().astype(int))})
     for t, g in df[df["ticker"].isin(set(rule["ticker"]))].sort_values(["ticker", "date"]).groupby("ticker", sort=False)}

# alpha stream: each day, mean over active trades of (trade daily ret - SPY daily ret)
nC = len(cal)
alpha_sum = np.zeros(nC); alpha_cnt = np.zeros(nC)
for r in rule.itertuples(index=False):
    c, idx = D.get(r.ticker, (None, None))
    if idx is None or int(r.date) not in idx or int(r.date) not in cal_idx:
        continue
    i = idx[int(r.date)]
    if i + HOLD >= len(c):
        continue
    g0 = cal_idx[int(r.date)]
    rets = c[i + 1:i + HOLD + 1] / c[i:i + HOLD] - 1
    rets = rets.copy(); rets[0] -= COST / 2; rets[-1] -= COST / 2
    for k in range(HOLD):
        g = g0 + 1 + k
        if g < nC:
            alpha_sum[g] += rets[k] - spy_ret[g]      # market-relative (pure alpha) contribution
            alpha_cnt[g] += 1
alpha = np.where(alpha_cnt > 0, alpha_sum / alpha_cnt, 0.0)   # equal-weight active earnings alpha


def stats(x, label):
    x = x[252:]
    ann = np.prod(1 + x) ** (252 / len(x)) - 1
    vol = x.std() * np.sqrt(252); shp = x.mean() / x.std() * np.sqrt(252) if x.std() else 0
    eq = np.cumprod(1 + x); dd = (eq / np.maximum.accumulate(eq) - 1).min()
    print(f"  {label:30s} CAGR {ann*100:+6.1f}%  vol {vol*100:3.0f}%  Sharpe {shp:+.2f}  maxDD {dd*100:5.0f}%  Calmar {ann/abs(dd) if dd else 0:+.2f}")
    return shp


print(f"rule trades: {len(rule):,} | active earnings days: {(alpha_cnt>0).sum()}/{nC} ({(alpha_cnt>0).mean()*100:.0f}%)\n")
print("=== the pure earnings ALPHA stream (market-relative, equal-weight active) ===")
stats(alpha, "alpha stream alone")
print(f"  corr(alpha, SPY) = {np.corrcoef(alpha[252:], spy_ret[252:])[0,1]:+.2f}  (low = good diversifier)")

print("\n=== SPY  vs  SPY + L x earnings-alpha overlay ===")
stats(spy_ret, "SPY buy&hold")
for L in (0.5, 1.0, 2.0, 3.0):
    stats(spy_ret + L * alpha, f"SPY + {L:.1f}x overlay")

print("\n=== by year: SPY vs SPY + 2x overlay ===")
net = spy_ret + 2.0 * alpha; yrs = cal // 10000
for y in range(2017, 2027):
    m = (yrs == y) & (np.arange(nC) >= 252)
    if m.sum() > 50:
        print(f"  {y}: SPY {((np.prod(1+spy_ret[m]))-1)*100:+6.1f}%   +overlay {((np.prod(1+net[m]))-1)*100:+6.1f}%")
print("\nREAD: SPY+overlay Sharpe/Calmar > SPY alone => the earnings alpha adds real value as an overlay.")
print("no improvement => the alpha is too thin/costly even deployed efficiently.")
