"""Give the advice's FULL construction its best shot, then apply the kill tests.

Tests, all on the TRIGGERED +2R/-1R trades:
  1. Decisive null control: gated setup vs random liquid day (same mechanic), by year + ex-2020.
  2. Sector top-quartile filter: does "only top-quartile sectors" help?
  3. Scorecard top-decile: does the advice's 0-100 ranking concentrate winners?
  4. ROBUSTNESS: drop-top-1% winners, ex-2020, net at 0/10/15/30 bps.

A construction "works" only if a ranked/filtered subset beats the null ACROSS years (not just
pooled, not just 2020), survives dropping the top 1% of trades, and clears cost. Run with
backend\\.venv\\Scripts\\python.exe -u.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import common as C
from scorecard import score


def _stat(d, col="netR"):
    return f"win {d['win'].mean():.1%}  meanR {d[col].mean():+.3f}  n {len(d):,}"


def _by_year(g, n, label):
    print(f"\n  {label} by year (gated meanR / null meanR / delta):")
    deltas = []
    for y in sorted(set(g["yr"]) & set(n["yr"])):
        gm, nm = g[g.yr == y]["netR"].mean(), n[n.yr == y]["netR"].mean()
        deltas.append(gm - nm)
        print(f"    {y}: gated {gm:+.3f}  null {nm:+.3f}  delta {gm - nm:+.3f}")
    pos = sum(d > 0 for d in deltas)
    print(f"    -> delta>0 in {pos}/{len(deltas)} years; mean delta {np.mean(deltas):+.3f}")


def main():
    S = pd.read_parquet(C.OUT / "setups.parquet")
    N = pd.read_parquet(C.OUT / "null.parquet")
    g = S[S["triggered"] == 1].copy()
    n = N[N["triggered"] == 1].copy()
    g["score"] = score(g)

    print(f"triggered: gated {len(g):,} | null {len(n):,}")
    print("\n=== 1. DECISIVE NULL CONTROL (net 15bps) ===")
    print(f"  GATED  {_stat(g)}")
    print(f"  NULL   {_stat(n)}")
    print(f"  DELTA meanR {g['netR'].mean() - n['netR'].mean():+.3f}")
    _by_year(g, n, "all-gated vs null")

    print("\n=== 2. SECTOR TOP-QUARTILE FILTER (sector_pct >= 0.75) ===")
    gq = g[g["sector_pct"] >= 0.75]
    print(f"  GATED+topQ sector  {_stat(gq)}   (vs null {_stat(n)})")
    print(f"  delta vs null meanR {gq['netR'].mean() - n['netR'].mean():+.3f}")

    print("\n=== 3. SCORECARD TOP-DECILE (advice's 0-100 ranking, in-sample) ===")
    for q, lab in [(0.9, "top-decile"), (0.75, "top-quartile"), (0.5, "top-half")]:
        sub = g[g["score"] >= g["score"].quantile(q)]
        print(f"  {lab:12s} {_stat(sub)}   delta vs null {sub['netR'].mean() - n['netR'].mean():+.3f}")
    top = g[g["score"] >= g["score"].quantile(0.9)]
    _by_year(top, n, "scorecard top-decile vs null")

    print("\n=== 4. ROBUSTNESS (on all-gated) ===")
    g_ex20 = g[g["yr"] != 2020]
    print(f"  ex-2020            {_stat(g_ex20)}")
    cut = g["grossR"].quantile(0.99)
    print(f"  drop-top-1% (gross) gross meanR {g[g['grossR'] < cut]['grossR'].mean():+.3f} "
          f"(full gross {g['grossR'].mean():+.3f})")
    print("  net at cost levels (cost_R = 2*bps*entry/risk = 2*bps/risk_pct):")
    for bps in (0, 10, 15, 30):
        adj = g["grossR"] - 2 * (bps / 1e4) / g["risk_pct"]
        print(f"    {bps:2d}bps: meanR {np.clip(adj, -C.RCAP, C.RCAP).mean():+.3f}  win {g['win'].mean():.1%}")

    print("\nVERDICT READ: the construction is alive only if a ranked/filtered subset beats the")
    print("null in MOST years AND ex-2020 AND after drop-top-1% AND at >=15bps. Else it's dead.")


if __name__ == "__main__":
    main()
