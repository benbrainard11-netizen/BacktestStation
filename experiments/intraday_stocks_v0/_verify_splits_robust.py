"""ROBUST split detection + survivorship spot-check. DEV YEARS ONLY.

Split test (the real one): the gap uses RAW flat prev_close & RAW open. The adjusted daily set
(load_polygon_daily, split-adjusted, delisted incl) gives a clean gap that already removes splits.
For each cut row, recompute gap_adj = adj_open/adj_prev_close - 1 from the adjusted daily panel.
A real overnight move has gap_raw ~= gap_adj. A SPLIT shows up as a large multiplicative gap between
the two (raw says +100%, adjusted says ~0). Flag rows where (1+gap_raw)/(1+gap_adj) is near a split
factor -> those are split artifacts regardless of what the raw gap number happens to be.

Survivorship: list distinct tickers in the cut, check what fraction are flagged 'delisted/inactive'
in load_polygon_meta, and confirm a handful of known-delisted dev-era tickers appear in the raw files.
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
from data_io import load_polygon_daily, load_polygon_flat, load_polygon_meta  # noqa: E402
from opening_drive_cond_v0 import day_rows  # noqa: E402

QUARTERS = [(20180101, 20180329), (20200101, 20200331), (20220101, 20220331), (20240101, 20240329)]
GTHR, DRIVE_Q = 0.05, 0.6


def build_cut(start, end):
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
    return cut[["date", "ticker", "r_close", "gap", "o930"]]


def main():
    pd.set_option("display.width", 220)
    cut = pd.concat([build_cut(s, e) for s, e in QUARTERS], ignore_index=True)
    n = len(cut)
    print(f"=== cut reproduced: n={n} mean r_close={cut['r_close'].mean():+.3%} ===\n")

    # ---- adjusted daily panel for the dev years (split-adjusted, delisted incl) ----
    yrs = sorted({d // 10000 for d in cut["date"]})
    adj = pd.concat([load_polygon_daily(year=y) for y in yrs], ignore_index=True)
    adj = adj.sort_values(["ticker", "date"])
    adj["adj_prev_close"] = adj.groupby("ticker")["close"].shift(1)
    a = adj[["ticker", "date", "open", "adj_prev_close"]].rename(columns={"open": "adj_open"})
    cut = cut.merge(a, on=["ticker", "date"], how="left")
    cut["gap_adj"] = cut["adj_open"] / cut["adj_prev_close"] - 1.0

    have = cut["gap_adj"].notna()
    print(f"=== (A) RAW vs ADJUSTED gap reconciliation (adjusted panel = split-clean) ===")
    print(f"  rows matched to adjusted daily: {have.sum()}/{n} ({have.mean():.0%})")
    # ratio of raw-gap-factor to adjusted-gap-factor: ~1.0 = no split; ~2,3,0.5 = split distortion
    cut["distort"] = (1 + cut["gap"]) / (1 + cut["gap_adj"])
    d = cut.loc[have, "distort"]
    print(f"  distort = (1+gap_raw)/(1+gap_adj):  median={d.median():.3f}  "
          f"p01={d.quantile(.01):.3f}  p99={d.quantile(.99):.3f}")
    # flag rows where raw and adjusted disagree by >15% (a split or a bad adj)
    cut["split_like"] = (cut["distort"] - 1.0).abs() > 0.15
    sl = cut[cut["split_like"] & have]
    print(f"  rows where raw/adj gap disagree by >15% (split-distortion candidates): {len(sl)}")
    if len(sl):
        print(sl.sort_values("distort", ascending=False)
              .head(20)[["date", "ticker", "gap", "gap_adj", "distort", "r_close"]].to_string(index=False))

    # edge with vs without the split-distortion rows (those that we CAN check)
    checkable = cut[have]
    clean = checkable[~checkable["split_like"]]
    print(f"\n  edge (checkable rows)         mean r_close={checkable['r_close'].mean():+.3%} n={len(checkable)}")
    print(f"  edge EXCL split-distortion    mean r_close={clean['r_close'].mean():+.3%} n={len(clean)}")
    if len(sl):
        print(f"  split-distortion rows ONLY    mean r_close={sl['r_close'].mean():+.3%} n={len(sl)}")
    unmatched = cut[~have]
    print(f"\n  UNMATCHED-to-adjusted rows    mean r_close={unmatched['r_close'].mean():+.3%} n={len(unmatched)} "
          f"(can't split-check these; share of PnL={unmatched['r_close'].sum()/cut['r_close'].sum():+.0%})")

    # ---- (B) SURVIVORSHIP ----
    print("\n=== (B) SURVIVORSHIP: do delisted names appear in the cut? ===")
    try:
        meta = load_polygon_meta()
        mcol = "active" if "active" in meta.columns else None
        names = cut["ticker"].unique()
        mm = meta[meta["ticker"].isin(names)]
        if mcol:
            inactive = mm[~mm[mcol].astype(bool)]["ticker"].nunique()
            print(f"  distinct tickers in cut: {len(names)}")
            print(f"  matched in meta: {mm['ticker'].nunique()}  | flagged INACTIVE/delisted: {inactive}")
        else:
            print(f"  meta cols = {list(meta.columns)} (no 'active' flag)")
    except Exception as e:
        print(f"  meta load failed: {e}")

    # known delisted dev-era tickers that show up in the cut (from earlier recon): ISPO, SGBX, NAV, TCO...
    print("\n  Spot-check known-delisted dev-era tickers exist in RAW flat files on their event day:")
    for tkr, dt in [("SGBX", 20200331), ("NAV", 20200131), ("TCO", 20200210),
                    ("ISPO", 20220217), ("IMMX", 20220103)]:
        try:
            f = load_polygon_flat("minute", dt)
            present = tkr in set(f["ticker"].unique())
            print(f"    {tkr:6} {dt}: present in raw minute file = {present}")
        except Exception as e:
            print(f"    {tkr:6} {dt}: load fail {e}")


if __name__ == "__main__":
    main()
