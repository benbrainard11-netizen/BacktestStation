"""Honest earnings-gap PORTFOLIO on clean data: turn the validated rule (gap>=15% + positive surprise,
liquid, above prior high) into a real book. Event-driven daily sim with N equal-weight slots (cash drag
when fewer signals than slots -> earnings are seasonal), 20-day hold, round-trip costs. Reports CAGR/
vol/Sharpe/maxDD/Calmar vs SPY + by-year + avg exposure. The test: does ~+1%/trade alpha survive
concurrency + costs into a viable book? Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
HERE = Path(__file__).resolve().parent
HOLD, COST = 20, 0.003                       # 20-day hold, 0.3% round-trip
S = pd.read_parquet(HERE / "out" / "earnings_clean.parquet")
S["price"] = np.exp(S["log_price"])
rule = S[(S["price"] >= 5) & (S["dvol"] >= 5e6) & (S["above_high"] == 1) &
         (S["gap"] >= 0.15) & (S["eps_surprise"] > 0)].copy()
print(f"rule trades: {len(rule):,}  {rule['date'].min()}..{rule['date'].max()}")

# daily closes for rule tickers + SPY
df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
spy = df[df["ticker"] == "SPY"].sort_values("date")
cal = spy["date"].to_numpy().astype(int)                       # global trading calendar
cal_idx = {int(d): i for i, d in enumerate(cal)}
spy_ret = pd.Series(spy["close"].to_numpy()).pct_change().to_numpy()
D = {}
for t, g in df[df["ticker"].isin(set(rule["ticker"]))].sort_values(["ticker", "date"]).groupby("ticker", sort=False):
    D[t] = (g["close"].to_numpy(), {int(x): i for i, x in enumerate(g["date"].to_numpy().astype(int))})

# build each trade's daily return path over the hold window, on the GLOBAL calendar
trades = []
for r in rule.itertuples(index=False):
    c, idx = D.get(r.ticker, (None, None))
    if idx is None or int(r.date) not in idx:
        continue
    i = idx[int(r.date)]
    if i + HOLD >= len(c) or int(r.date) not in cal_idx:
        continue
    g0 = cal_idx[int(r.date)]
    rets = c[i + 1:i + HOLD + 1] / c[i:i + HOLD] - 1            # daily returns days 1..HOLD
    if len(rets) < HOLD:
        continue
    rets = rets.copy(); rets[0] -= COST / 2; rets[-1] -= COST / 2
    trades.append((g0, g0 + HOLD, rets, r.eps_surprise))

print(f"simulated trades: {len(trades):,}")


def sim(N):
    nC = len(cal)
    book = np.zeros(nC); filled = np.zeros(nC)
    # assign trades to slots greedily (by surprise priority when oversubscribed)
    active = []   # (end_g, rets, start_g)
    by_start = {}
    for g0, g1, rets, sup in sorted(trades, key=lambda x: (x[0], -x[3])):
        by_start.setdefault(g0, []).append((g1, rets))
    open_pos = []     # list of (end_g, rets, start_g)
    for g in range(nC):
        open_pos = [p for p in open_pos if p[0] > g]
        for g1, rets in by_start.get(g, []):
            if len(open_pos) < N:
                open_pos.append((g1, rets, g))
        # today's return: each open slot earns its day's return; empty slots = cash(0)
        day = 0.0
        for g1, rets, gs in open_pos:
            k = g - gs
            if 0 <= k - 1 < len(rets):
                day += rets[k - 1]
        book[g] = day / N
        filled[g] = len(open_pos)
    eq = np.cumprod(1 + book)
    return book, eq, filled.mean()


def metrics(book, label, bench=None):
    book = book[252:]                                  # drop warmup
    ann = (np.prod(1 + book)) ** (252 / len(book)) - 1
    vol = book.std() * np.sqrt(252); shp = book.mean() / book.std() * np.sqrt(252) if book.std() else 0
    eq = np.cumprod(1 + book); dd = (eq / np.maximum.accumulate(eq) - 1).min()
    cal_ = ann / abs(dd) if dd else 0
    ex = ""
    if bench is not None:
        ex = f"  alpha/yr {((book - bench[252:]).mean()*252)*100:+.1f}%"
    print(f"  {label:24s} CAGR {ann*100:+6.1f}%  vol {vol*100:3.0f}%  Sharpe {shp:+.2f}  maxDD {dd*100:5.0f}%  Calmar {cal_:+.2f}{ex}")


print("\n=== earnings-gap book (event-driven, 20d hold, 0.3% round-trip) ===")
for N in (5, 10, 20):
    book, eq, expo = sim(N)
    metrics(book, f"{N} slots (expo {expo/N*100:.0f}%)", bench=spy_ret)
metrics(spy_ret, "SPY buy & hold")

book, eq, expo = sim(10)
print(f"\n=== 10-slot book by year (avg {expo:.1f} positions held) ===")
yrs = (cal // 10000)
for y in range(2017, 2027):
    m = (yrs == y) & (np.arange(len(cal)) >= 252)
    if m.sum() > 50:
        r = book[m]; s = spy_ret[m]
        print(f"  {y}: book {((np.prod(1+r))-1)*100:+6.1f}%   SPY {((np.prod(1+np.nan_to_num(s)))-1)*100:+6.1f}%")
print("\nREAD: positive CAGR + alpha + Calmar comparable-or-better than SPY => viable modest book.")
print("heavy cash drag / Sharpe << SPY / alpha ~0 after costs => real edge but too thin/seasonal to run alone.")
