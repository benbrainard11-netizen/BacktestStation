"""Definitive clean earnings-gap verdict: is the robust rule a viable modest strategy? On the
survivorship-clean Benzinga x Polygon data (earnings_clean.parquet), test the SIMPLE robust rule
(big gap + positive surprise + dormant base, liquid) vs the broad ~0 baseline. Report per-trade
20d/40d MARKET-RELATIVE drift + bootstrap CI + BY-YEAR robustness + frequency + win rate, and the
implied annual alpha. No data-mined combo -- simple, interpretable cuts only.
Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

S = pd.read_parquet(Path(__file__).resolve().parent / "out" / "earnings_clean.parquet")
S["yr"] = S["date"] // 10000
S["price"] = np.exp(S["log_price"])
LIQ = (S["price"] >= 5) & (S["dvol"] >= 5e6)


def boot(x, n=4000):
    x = x.dropna().to_numpy()
    if len(x) < 20:
        return (np.nan, np.nan)
    idx = np.random.default_rng(0).integers(0, len(x), (n, len(x)))
    return tuple(np.percentile(x[idx].mean(1) * 100, [2.5, 97.5]))


def verdict(sub, label):
    n = len(sub)
    if n < 30:
        print(f"  {label:40s} n={n} (too few)"); return
    x20 = sub["x20"]; ci = boot(x20)
    yrs = sub.groupby("yr")["x20"].mean() * 100
    pos = (yrs > 0).sum()
    freq = n / sub["yr"].nunique()
    print(f"  {label:40s} n={n:5d}  x20 {x20.mean()*100:+.2f}% CI[{ci[0]:+.2f},{ci[1]:+.2f}]  "
          f"x40 {sub['x40'].mean()*100:+.2f}%  win {(x20>0).mean()*100:.0f}%  {pos}/{sub['yr'].nunique()}yr+  ~{freq:.0f}/yr")


up = S[LIQ & (S["above_high"] == 1)].copy()      # gap up above prior high (the doc setup core)
print(f"clean earnings setups (liquid, gap-up above prior high): {len(up):,}  {S['date'].min()}..{S['date'].max()}\n")

print("=== selection ladder (each adds a robust filter) — market-relative 20d drift ===")
verdict(up[up["gap"] >= 0.075], "broad: gap>=7.5%")
verdict(up[up["gap"] >= 0.15], "big gap: gap>=15%")
verdict(up[(up["gap"] >= 0.15) & (up["eps_surprise"] > 0)], "+ positive surprise")
verdict(up[(up["gap"] >= 0.15) & (up["eps_surprise"] > 0.05) & (up["ret_3m"] < 0.25)], "+ surprise>5% + dormant (the rule)")

rule = up[(up["gap"] >= 0.15) & (up["eps_surprise"] > 0.05) & (up["ret_3m"] < 0.25)]
print(f"\n=== THE RULE — by year (market-relative x20) ===")
for y in sorted(rule["yr"].unique()):
    s = rule[rule.yr == y]
    print(f"  {y}: {s['x20'].mean()*100:+5.2f}%  n={len(s):4d}  win {(s['x20']>0).mean()*100:.0f}%")

print(f"\n=== is it a viable book? (THE RULE) ===")
n_yr = len(rule) / rule["yr"].nunique()
edge = rule["x20"].mean()
print(f"  per-trade alpha {edge*100:+.2f}%/20d  x  ~{n_yr:.0f} trades/yr")
print(f"  if ~{n_yr:.0f} trades/yr held ~1mo (so ~{n_yr/12:.0f} concurrent), rough annual ALPHA ~ {edge*n_yr*100/ max(n_yr/ (n_yr/12),1):.1f}% "
      f"(crude); the honest read is the per-trade edge + CI + by-year above")
print(f"  drop-best-year: {[round((rule[rule.yr!=y]['x20'].mean())*100,2) for y in [2020,2021]]} (ex-2020, ex-2021)")
print("\nREAD: rule x20 CI>0 + most years + decent freq => a real (modest) tradeable earnings edge.")
print("CI touches 0 / few years / tiny freq => too thin to deploy standalone (use as a component or pass).")
