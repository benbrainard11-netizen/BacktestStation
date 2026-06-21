"""One-day footprint + quality sample for the SCOPED intraday options pull (per Ben's spec).
Scope: NDX + SPX, 1-min greeks, <=45 DTE, strikes within +-BAND of spot. Measures before pulling
the whole span. Answers: (1) is NDX implied_vol/underlying_price populated? (2) band footprint
rows+MB/day -> extrapolated full span; (3) is ms_of_day ET covering through 16:15 ET (58,500,000ms)?
"""
from __future__ import annotations

import os

os.environ.setdefault("THETA_TIMEOUT", "180")
os.environ.setdefault("THETA_RETRIES", "1")
os.environ.setdefault("THETA_PORT", "25510")

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theta_store as TS  # noqa: E402

DATE = 20260609
BAND = 0.06
END45 = int((pd.Timestamp(str(DATE)) + pd.Timedelta(days=45)).strftime("%Y%m%d"))
KEEP = ["date", "ms_of_day", "strike", "right", "expiration", "bid", "ask", "underlying_price",
        "implied_vol", "delta", "theta", "vega", "rho"]
TMP = Path(__file__).resolve().parent / "out" / "_sample_band.parquet"
SPAN_DAYS = 285  # ~2025-05-01 .. 2026-06 trading days, for extrapolation

for root in ["NDXP", "SPXW"]:
    exps = sorted(int(e) for e in TS.expirations(root) if DATE <= int(e) <= END45)
    print(f"\n========== {root}: {len(exps)} expirations <=45 DTE on {DATE} ==========")
    if not exps:
        print("  none"); continue
    probe = sorted(set([exps[0], exps[min(1, len(exps) - 1)], exps[len(exps) // 2], exps[-1]]))
    band_rows = []
    for exp in probe:
        dte = (pd.Timestamp(str(exp)) - pd.Timestamp(str(DATE))).days
        try:
            df = TS.fetch("bulk_hist/option/greeks", root=root, exp=exp, start_date=DATE, end_date=DATE, ivl=60000)
        except Exception as e:
            print(f"  exp {exp} (DTE {dte}): FETCH FAIL {type(e).__name__} {str(e)[:45]}"); continue
        if df.empty:
            print(f"  exp {exp} (DTE {dte}): EMPTY"); continue
        spot = float(pd.to_numeric(df["underlying_price"], errors="coerce").median())
        band = df[(df["strike"] >= spot * (1 - BAND)) & (df["strike"] <= spot * (1 + BAND))].copy()
        iv = pd.to_numeric(df["implied_vol"], errors="coerce")
        und = pd.to_numeric(df["underlying_price"], errors="coerce")
        ms = pd.to_numeric(df["ms_of_day"], errors="coerce")
        n_strk = band["strike"].nunique()
        print(f"  exp {exp} (DTE {dte:>2}): allrows={len(df):>6} band(±{BAND:.0%})={len(band):>6} "
              f"strikes={n_strk:>3} spot={spot:>8.0f} | IV>0={ (iv>0).mean():.0%} und>0={(und>0).mean():.0%} "
              f"| ms[{int(ms.min())}..{int(ms.max())}]")
        band_rows.append(len(band))
        if root == "NDXP" and dte <= 7:
            band[KEEP].to_parquet(TMP)  # measure real parquet MB on a representative near-term band
    if band_rows:
        avg = sum(band_rows) / len(band_rows)
        day_rows = avg * len(exps)
        mb_per_row = (TMP.stat().st_size / band_rows[0]) if (root == "NDXP" and TMP.exists() and band_rows) else 0
        print(f"  --> avg band rows/exp = {avg:,.0f}; est ONE-DAY band rows ({len(exps)} exps) = {day_rows:,.0f}")
        if mb_per_row:
            day_mb = day_rows * mb_per_row / 1e6
            print(f"  --> est ONE-DAY band parquet ~= {day_mb:,.1f} MB; FULL SPAN ({SPAN_DAYS} days) ~= {day_mb*SPAN_DAYS/1024:,.1f} GB")
print(f"\n(ms_of_day check: 09:30 ET=34,200,000 ; 16:00=57,600,000 ; 16:15=58,500,000)")
