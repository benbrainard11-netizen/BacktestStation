"""Deeper EX-2020 fragility for the gap-UP+strong-drive cut. Dev years only (2018/2022/2024 here;
2020 excluded by construction). Quantifies: drop-top-N decay, median vs mean, name-level robustness,
and whether the winners are microcaps that won't fill at size (dvol30 of the big trades).
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

# Only the EX-2020 dev years.
QUARTERS = [(20180101, 20180329), (20220101, 20220331), (20240101, 20240329)]


def build(start, end):
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
    big = big[big["prev_close"] > 0].copy()
    big["gap"] = big["o930"] / big["prev_close"] - 1.0
    return big


def main():
    allp = pd.concat([build(s, e) for s, e in QUARTERS], ignore_index=True)
    gp = allp[allp["gap"] >= 0.05]
    cut = gp[gp["drive"] > gp["drive"].quantile(0.6)].copy()
    cut["r"] = cut["r_close"].astype(float)
    cut = cut[np.isfinite(cut["r"])]
    r = cut["r"].to_numpy()
    n = len(r)
    print(f"EX-2020 (2018+2022+2024) gap5/top40/3M  n={n}")
    print(f"  mean   = {r.mean():+.3%}")
    print(f"  median = {np.median(r):+.3%}   <-- typical trade")
    print(f"  win    = {(r>0).mean():.0%}")
    print(f"  std    = {r.std():.2%}")

    print("\n  drop-top-N decay (mean after removing the N best trades):")
    srt = np.sort(r)[::-1]
    for k in (0, 1, 3, 5, 10, 20, 30):
        if n - k > 0:
            m = (r.sum() - srt[:k].sum()) / (n - k)
            print(f"    drop-top-{k:<3} mean={m:+.3%}   hc(-0.5%)={m-0.005:+.3%}")

    print("\n  trimmed mean (drop top & bottom k%):")
    for p in (0, 1, 5, 10):
        lo, hi = np.percentile(r, p), np.percentile(r, 100 - p)
        tm = r[(r >= lo) & (r <= hi)].mean()
        print(f"    trim {p}%/{p}% -> {tm:+.3%}")

    print("\n  liquidity of the monster trades — are the winners tradeable at size?")
    cut["bucket"] = pd.cut(cut["r"], [-1, 0, 0.1, 0.3, 1.0, 99],
                           labels=["loss", "0-10%", "10-30%", "30-100%", ">100%"])
    for b, g in cut.groupby("bucket", observed=True):
        print(f"    {str(b):>8}: n={len(g):>4}  median dvol30=${g['dvol30'].median()/1e6:.1f}M  "
              f"median px=${g['o930'].median():.1f}  PnL share={g['r'].sum()/r.sum():+.0%}")

    print("\n  restrict to ONLY >$10M dvol AND >$5 price (real liquidity), gap5/top40 recut:")
    liq = allp[(allp["gap"] >= 0.05) & (allp["dvol30"] >= 10e6) & (allp["o930"] >= 5.0)]
    lc = liq[liq["drive"] > liq["drive"].quantile(0.6)]["r_close"].to_numpy(float)
    lc = lc[np.isfinite(lc)]
    print(f"    n={len(lc)}  mean={lc.mean():+.3%}  median={np.median(lc):+.3%}  "
          f"hc(-0.5%)={(lc-0.005).mean():+.3%}  win={(lc>0).mean():.0%}")
    srt2 = np.sort(lc)[::-1]
    print(f"    drop-top-10 mean={(lc.sum()-srt2[:10].sum())/(len(lc)-10):+.3%}")


if __name__ == "__main__":
    main()
