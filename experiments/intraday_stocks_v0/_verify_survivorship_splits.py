"""DATA-SANITY / SURVIVORSHIP verification for the gap-up + strong-drive candidate.
DEV YEARS ONLY (2018/2020/2022/2024 Q1). 2025+ is SEALED -- never touched here.

Checks:
  (1) SURVIVORSHIP: do the raw flat files contain names that delisted 2018-2024?
  (2) SPLIT ARTIFACTS: gap = raw_open / raw_prev_close - 1. A split between prev close and
      today's open creates a FAKE gap. Estimate how many gap>=5% events look like split ratios
      (~2x, ~3x, ~0.5x, ~1/3) and whether excluding them changes the edge.
  (3) Reconcile a few big winners on raw minute rows.
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


def build_cut(start, end):
    """Reproduce the frag cut but KEEP gap, prev_close, o930, p1000, drive so we can test splits."""
    days = [int(d.strftime("%Y%m%d")) for d in pd.bdate_range(str(start), str(end))]
    big = pd.concat([r for d in days if not (r := day_rows(d)).empty], ignore_index=True)
    lead = (pd.Timestamp(str(start)) - pd.Timedelta(days=12)).strftime("%Y%m%d")
    dd = [int(d.strftime("%Y%m%d")) for d in pd.bdate_range(lead, str(end))]
    dp = []
    for d in dd:
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
    gp = big[big["gap"] >= GTHR]
    cut = gp[gp["drive"] > gp["drive"].quantile(DRIVE_Q)].copy()
    return cut[["date", "ticker", "r_close", "gap", "prev_close", "o930", "p1000", "pclose", "drive"]]


def split_flag(gap):
    """Flag a gap whose 1+gap ratio is near a common split factor.
    Forward splits make ratio < 1 (price drops): 1/2=0.5, 1/3=0.333, 2/3=0.667, 1/4=0.25.
    Reverse splits make ratio > 1: 2,3,4,5,10. tol = +-3%.
    """
    ratio = 1.0 + gap
    factors = [0.5, 1.0 / 3.0, 2.0 / 3.0, 0.25, 0.2, 0.1, 2.0, 3.0, 4.0, 5.0, 1.5, 2.5, 10.0]
    for f in factors:
        if abs(ratio / f - 1.0) <= 0.03:
            return f
    return np.nan


def main():
    pd.set_option("display.width", 200)
    cut = pd.concat([build_cut(s, e) for s, e in QUARTERS], ignore_index=True)
    cut["yr"] = cut["date"] // 10000
    n = len(cut)
    print(f"=== CANDIDATE REPRODUCED: n={n}, mean r_close={cut['r_close'].mean():+.3%} ===\n")

    # ---- (2) SPLIT-ARTIFACT scan on the gap-up cut ----
    cut["split_factor"] = cut["gap"].apply(split_flag)
    susp = cut[cut["split_factor"].notna()]
    print("=== (2) SPLIT-ARTIFACT scan: gaps whose 1+gap is near a common split ratio (+-3%) ===")
    print(f"  flagged near-split-ratio: {len(susp)}/{n} = {len(susp)/n:.1%} of the cut")
    if len(susp):
        print("  flagged-by-factor counts:")
        print(susp["split_factor"].value_counts().to_string())
        print("\n  sample flagged rows:")
        print(susp.sort_values("gap", ascending=False)
              .head(15)[["date", "ticker", "gap", "r_close", "split_factor"]].to_string(index=False))

    # In a gap-UP cut, gap>=5% so ratio>=1.05. Forward-split (ratio<1) can't be here -> only
    # REVERSE-split factors (2x,3x,...) are reachable. Recompute edge excluding them.
    clean = cut[cut["split_factor"].isna()]
    print(f"\n  edge WITH flagged rows:    mean r_close={cut['r_close'].mean():+.3%}  n={n}")
    print(f"  edge EXCL flagged rows:    mean r_close={clean['r_close'].mean():+.3%}  n={len(clean)}")
    print(f"  flagged-rows-only mean:    {susp['r_close'].mean():+.3%}  n={len(susp)}" if len(susp) else "")

    # ---- (2b) ROBUST split detection via daily adjusted basis would need adj set; instead use the
    # behavioural test: a real split-gap should have intraday return ~0 distortion. Look at how
    # extreme gaps (>=50%, >=100%) distribute -- a forward split shows as a NEGATIVE ~ -50% open
    # gap (filtered out by gap>=5%>0), a reverse split as +100%/+200% gaps. Tabulate big gaps.
    print("\n=== (2b) Extreme-gap tail (the zone where reverse-split artifacts hide) ===")
    for lo in (0.20, 0.50, 1.0, 2.0):
        sub = cut[cut["gap"] >= lo]
        print(f"  gap>= {lo:>4.0%}: n={len(sub):>4}  mean r_close={sub['r_close'].mean():+.3%}  "
              f"share of total PnL={sub['r_close'].sum()/cut['r_close'].sum():+.0%}")

    # ---- (3) Big-winner reconciliation on raw minute rows ----
    print("\n=== (3) RECONCILE top-8 winners on raw minute flat rows ===")
    top = cut.sort_values("r_close", ascending=False).head(8)
    for _, row in top.iterrows():
        recon_one(row)

    # ---- (1) SURVIVORSHIP spot-check handled separately (needs known delisted tickers) ----


def recon_one(row):
    d = int(row["date"])
    tkr = row["ticker"]
    try:
        df = load_polygon_flat("minute", d)
    except Exception as e:
        print(f"  {tkr} {d}: LOAD FAIL {e}")
        return
    et = pd.to_datetime(df["window_start"], utc=True).dt.tz_convert("America/New_York")
    df = df.assign(mod=et.dt.hour * 60 + et.dt.minute)
    sub = df[df["ticker"] == tkr].sort_values("mod")
    o930 = sub.loc[sub["mod"] == 570, "open"]
    p1000 = sub.loc[sub["mod"] == 600, "open"]
    clo = sub.loc[sub["mod"] <= 959]
    pclose = clo.sort_values("mod")["close"].iloc[-1] if len(clo) else np.nan
    n_bars = len(sub[(sub["mod"] >= 570) & (sub["mod"] <= 959)])
    o = o930.iloc[0] if len(o930) else np.nan
    p = p1000.iloc[0] if len(p1000) else np.nan
    print(f"  {tkr:6} {d}  rec_r_close={row['r_close']:+.2%} | stored o930={row['o930']:.2f} "
          f"p1000={row['p1000']:.2f} pclose={row['pclose']:.2f} gap={row['gap']:+.1%} | "
          f"RAW o930={o:.2f} p1000={p:.2f} pclose={pclose:.2f} bars={n_bars} "
          f"recomputed_r_close={pclose/p-1:+.2%}")


if __name__ == "__main__":
    main()
