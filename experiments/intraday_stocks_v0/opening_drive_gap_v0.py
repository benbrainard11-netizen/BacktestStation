"""intraday_stocks_v0 — CATALYST cut. Generic opening drive = untradeable fade. Now isolate real overnight
GAPS (information events): do gappers CONTINUE (gap-and-go, tradeable momentum) where generic names fade?

Adds overnight gap = open@09:30 / prior-day close - 1 (raw daily flat files for prev close). Tests:
  (1) gap -> rest-of-day  (do gaps themselves continue or fill?)
  (2) among GAPPERS (|gap|>=5%): drive(09:30-10:00) -> rest-of-day  (does the morning follow-through pay?)
  (3) split by gap direction.
Dev slice. Run: python opening_drive_gap_v0.py [START] [END]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
from data_io import load_polygon_flat  # noqa: E402
from opening_drive_cond_v0 import day_rows  # noqa: E402

START = int(sys.argv[1]) if len(sys.argv) > 1 else 20240101
END = int(sys.argv[2]) if len(sys.argv) > 2 else 20240329


def ic(x, y):
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 100:
        return (np.nan, int(m.sum()))
    return (stats.spearmanr(x[m], y[m])[0], int(m.sum()))


def main():
    days = [int(d.strftime("%Y%m%d")) for d in pd.bdate_range(str(START), str(END))]
    big = pd.concat([r for d in days if not (r := day_rows(d)).empty], ignore_index=True)

    # daily-close panel for prev_close (a few days of lead-in for the shift)
    lead = (pd.Timestamp(str(START)) - pd.Timedelta(days=12)).strftime("%Y%m%d")
    dd_days = [int(d.strftime("%Y%m%d")) for d in pd.bdate_range(lead, str(END))]
    dp = []
    for d in dd_days:
        try:
            x = load_polygon_flat("day", d)[["ticker", "close"]].copy()
            x["date"] = d
            dp.append(x)
        except Exception:
            pass
    dp = pd.concat(dp, ignore_index=True).sort_values(["ticker", "date"])
    dp["prev_close"] = dp.groupby("ticker")["close"].shift(1)
    big = big.merge(dp[["ticker", "date", "prev_close"]], on=["ticker", "date"], how="left")
    big = big[big["prev_close"] > 0]
    big["gap"] = big["o930"] / big["prev_close"] - 1.0

    print(f"pooled name-days with gap: {len(big):,}\n")

    print("=== (1) does the GAP itself continue or fill? IC(gap -> r_close) + by decile ===")
    r, n = ic(big["gap"].to_numpy(), big["r_close"].to_numpy())
    print(f"  IC(gap -> rest-of-day) = {r:+.4f}  n={n:,}  (>0 = gap-and-go, <0 = gap fill)")
    big["gd"] = pd.qcut(big["gap"], 10, labels=False, duplicates="drop")
    for d, g in big.groupby("gd"):
        print(f"  D{int(d):>2} gap={g['gap'].mean():+.2%} -> r_close {g['r_close'].mean():+.3%}  n={len(g)}")

    for thr in (0.05, 0.10):
        gp = big[big["gap"].abs() >= thr]
        up, dn = gp[gp["gap"] > 0], gp[gp["gap"] < 0]
        print(f"\n=== (2) GAPPERS |gap|>={thr:.0%} (n={len(gp):,}): does the 30-min DRIVE continue? ===")
        for lab, sub in (("all gappers", gp), ("gap-UPs", up), ("gap-DOWNs", dn)):
            rd, nd = ic(sub["drive"].to_numpy(), sub["r_close"].to_numpy())
            mo = sub["r_close"].mean()
            print(f"  {lab:11} IC(drive->r_close)={rd:+.4f}  n={nd:>5,}  mean r_close={mo:+.3%}")
        # the tradeable cut: gap-up AND strong morning drive -> does it run?
        cont = gp[(gp["gap"] > 0) & (gp["drive"] > gp["drive"].quantile(0.6))]
        print(f"  gap-UP + strong drive (top-40% drive): mean r_close={cont['r_close'].mean():+.3%} "
              f"win={ (cont['r_close']>0).mean():.0%} n={len(cont)}  (vs ~0.1% cost)")
    print("\nEXPLORATORY dev slice. A clear tradeable-sized continuation here = the line is alive.")


if __name__ == "__main__":
    main()
