"""Probe ThetaData single-stock options reach for stock_options_flow_v0.

Stock bulk EOD requires an `exp` (expiration) — unlike the index path. So we first
list expirations per root (that reveals history floor + delisted coverage), then fetch
one historical + one recent expiration with greeks/OI to confirm gamma is carried and
gauge chain size.

Run: backend\\.venv\\Scripts\\python.exe -u experiments/stock_options_flow_v0/probe_stock_options.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments" / "options_signals_v0"))
import theta_store as TS  # noqa: E402


def list_exps(root: str):
    t0 = time.time()
    try:
        exps = sorted(TS.expirations(root))
    except Exception as e:
        print(f"  {root:6} expirations ERROR {type(e).__name__}: {str(e)[:80]}")
        return []
    dt = time.time() - t0
    if not exps:
        print(f"  {root:6} expirations EMPTY ({dt:.1f}s)")
        return []
    print(f"  {root:6} n_exp={len(exps):>4}  floor={exps[0]}  latest={exps[-1]}  ({dt:.1f}s)")
    return exps


def fetch_exp(root: str, exp: int, endpoint: str):
    """EOD over the ~45 trading days before an expiration, for that one expiration's chain."""
    end = pd.to_datetime(str(exp), format="%Y%m%d")
    start = end - pd.Timedelta(days=45)
    t0 = time.time()
    try:
        df = TS.fetch(endpoint, root=root, exp=exp,
                      start_date=start.strftime("%Y%m%d"), end_date=end.strftime("%Y%m%d"))
    except Exception as e:
        print(f"    {endpoint.split('/')[-1]:14} exp={exp} ERROR {type(e).__name__}: {str(e)[:70]}")
        return
    dt = time.time() - t0
    if df is None or df.empty:
        print(f"    {endpoint.split('/')[-1]:14} exp={exp} EMPTY ({dt:.1f}s)")
        return
    cols = [c.lower() for c in df.columns]
    greeky = [c for c in ("gamma", "delta", "implied_vol", "vega", "theta") if c in cols]
    print(f"    {endpoint.split('/')[-1]:14} exp={exp} rows={len(df):>6} strikes={df['strike'].nunique():>4} "
          f"greeks={greeky if greeky else 'none'} ({dt:.1f}s)  cols={list(df.columns)[:9]}")


print("=== expiration coverage (history floor + delisted survivorship) ===")
roots = ["AAPL", "NVDA", "TSLA", "SPY", "PLTR", "SOFI", "RIOT", "MARA", "SIVB"]
exps_by_root = {r: list_exps(r) for r in roots}

print("\n=== AAPL: historical vs recent expiration — is gamma carried? chain size? ===")
aapl = exps_by_root.get("AAPL", [])
if aapl:
    hist = next((e for e in aapl if e >= 20180101), aapl[0])
    recent = next((e for e in reversed(aapl) if e <= 20240601), aapl[-1])
    for exp in {hist, recent}:
        print(f"  --- AAPL exp {exp} ---")
        fetch_exp("AAPL", exp, "bulk_hist/option/eod")
        fetch_exp("AAPL", exp, "bulk_hist/option/eod_greeks")
        fetch_exp("AAPL", exp, "bulk_hist/option/open_interest")

print("\n=== mid-tier name (PLTR): one recent exp — confirm signal-grade chain exists ===")
pltr = exps_by_root.get("PLTR", [])
if pltr:
    exp = next((e for e in reversed(pltr) if e <= 20240601), pltr[-1])
    fetch_exp("PLTR", exp, "bulk_hist/option/eod_greeks")
    fetch_exp("PLTR", exp, "bulk_hist/option/open_interest")

print("\nDONE.")
