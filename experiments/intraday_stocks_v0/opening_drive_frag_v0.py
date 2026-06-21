"""intraday_stocks_v0 — make-or-break checks on the gap-up + strong-drive CANDIDATE:
  (A) FRAGILITY: is the +0.57% broad or a few monster trades? (drop-top-5/10; per-year)
  (B) COST/SPREAD: does it survive a conservative round-trip haircut (proxy for gapper bid/ask, since
      the minute flat files carry no quotes)?
Pools the dev quarters (2018/2020/2022/2024 Q1); 2025-26 stays SEALED. Run: python opening_drive_frag_v0.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
from data_io import load_polygon_flat  # noqa: E402
from opening_drive_cond_v0 import day_rows  # noqa: E402

QUARTERS = [(20180101, 20180329), (20200101, 20200331), (20220101, 20220331), (20240101, 20240329)]
GTHR, DRIVE_Q = 0.05, 0.6


def gapper_cut(start, end):
    days = [int(d.strftime("%Y%m%d")) for d in pd.bdate_range(str(start), str(end))]
    big = pd.concat([r for d in days if not (r := day_rows(d)).empty], ignore_index=True)
    lead = (pd.Timestamp(str(start)) - pd.Timedelta(days=12)).strftime("%Y%m%d")
    dd = [int(d.strftime("%Y%m%d")) for d in pd.bdate_range(lead, str(end))]
    dp = []
    for d in dd:
        try:
            x = load_polygon_flat("day", d)[["ticker", "close"]].copy(); x["date"] = d; dp.append(x)
        except Exception:
            pass
    dp = pd.concat(dp, ignore_index=True).sort_values(["ticker", "date"])
    dp["prev_close"] = dp.groupby("ticker")["close"].shift(1)
    big = big.merge(dp[["ticker", "date", "prev_close"]], on=["ticker", "date"], how="left")
    big = big[big["prev_close"] > 0]
    big["gap"] = big["o930"] / big["prev_close"] - 1.0
    gp = big[big["gap"] >= GTHR]                                  # gap-UP
    cut = gp[gp["drive"] > gp["drive"].quantile(DRIVE_Q)]         # strong morning drive
    return cut[["date", "ticker", "r_close"]]


def main():
    allcut = pd.concat([gapper_cut(s, e) for s, e in QUARTERS], ignore_index=True)
    r = allcut["r_close"].to_numpy(float); r = r[np.isfinite(r)]
    allcut["yr"] = allcut["date"] // 10000
    n = len(r); top = np.sort(r)[::-1]
    print(f"gap-UP + strong-drive trades pooled (dev quarters): n={n}, mean r_close={r.mean():+.3%}\n")
    print("=== (A) FRAGILITY ===")
    print(f"  full mean      = {r.mean():+.3%}")
    print(f"  drop-top-5     = {(r.sum()-top[:5].sum())/(n-5):+.3%}")
    print(f"  drop-top-10    = {(r.sum()-top[:10].sum())/(n-10):+.3%}")
    print(f"  top-5 share    = {top[:5].sum()/r.sum():.0%} of total PnL   |  win rate = {(r>0).mean():.0%}")
    print("  by year:  " + "  ".join(f"{y}:{g['r_close'].mean():+.2%}(n{len(g)})" for y, g in allcut.groupby('yr')))
    print("\n=== (B) COST / SPREAD haircut (round-trip, proxy for gapper bid/ask) ===")
    for c in (0.001, 0.003, 0.005, 0.008):
        net = r - c
        print(f"  -{c:.1%} round-trip  -> mean {net.mean():+.3%}  win {(net>0).mean():.0%}  "
              f"{'ALIVE' if net.mean() > 0 else 'DEAD'}")
    print("\nIf it survives drop-top-10 AND a ~0.3-0.5% haircut, it's worth honest fills + the sealed holdout.")


if __name__ == "__main__":
    main()
