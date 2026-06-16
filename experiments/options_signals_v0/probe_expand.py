"""Feasibility probe for the data-expansion plan: what can the ThetaData sub pull FOR FREE, and
roughly how big is it? Three unknowns:
  1. STOCK prices (NVDA) — does the sub cover equities at all?
  2. STOCK OPTIONS (NVDA/AAPL) — does it cover equity options (the valuable, expensive lane)?
  3. INTRADAY INDEX options (NDX 5-min greeks) — confirm + size (rows/day -> extrapolate cost).
471 = no permission (would need a sub upgrade or Databento $). rows>0 = pullable free.
"""
from __future__ import annotations

import os

os.environ.setdefault("THETA_TIMEOUT", "30")
os.environ.setdefault("THETA_RETRIES", "1")
os.environ.setdefault("THETA_PORT", "25511")

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theta_store as TS  # noqa: E402


def try_(label, fn):
    try:
        r = fn()
        n = len(r) if r is not None else 0
        print(f"  {label}: OK rows={n}")
        return r
    except Exception as e:
        print(f"  {label}: FAIL {type(e).__name__} {str(e)[:60]}")
        return None


print("=== 1. STOCK PRICES (equities covered?) ===")
try_("NVDA hist/stock/eod", lambda: TS.fetch_flat("hist/stock/eod", root="NVDA", start_date=20260601, end_date=20260609))
try_("NVDA hist/stock/ohlc 1m (1day)", lambda: TS.fetch_flat("hist/stock/ohlc", root="NVDA", start_date=20260609, end_date=20260609, ivl=60000))

print("\n=== 2. STOCK OPTIONS (equity options covered?) ===")
for root in ("NVDA", "AAPL"):
    try:
        exps = sorted(int(x) for x in TS.expirations(root))
        ne = [e for e in exps if e >= 20260601]
        pick = ne[0] if ne else exps[-1]
        print(f"  {root}: {len(exps)} expirations listed ({exps[0]}..{exps[-1]}); probing exp {pick}")
        try_(f"  {root} eod_greeks 1day", lambda: TS.fetch("bulk_hist/option/eod_greeks", root=root, exp=pick, start_date=20260609, end_date=20260609))
    except Exception as e:
        print(f"  {root}: expirations FAIL {type(e).__name__} {str(e)[:50]}")

print("\n=== 3. INTRADAY INDEX OPTIONS (NDX 5-min greeks) — confirm + size ===")
try:
    exps = sorted(int(x) for x in TS.expirations("NDXP"))
    ne = [e for e in exps if e >= 20260609]
    pick = ne[0] if ne else exps[-1]
    r = try_(f"NDXP bulk greeks ivl=5m exp{pick} 1day", lambda: TS.fetch("bulk_hist/option/greeks", root="NDXP", exp=pick, start_date=20260609, end_date=20260609, ivl=300000))
    if r is not None and len(r):
        print(f"  -> ~{len(r):,} rows for ONE expiration ONE day at 5-min. (full chain = sum over expirations/days)")
except Exception as e:
    print(f"  NDXP intraday FAIL {type(e).__name__} {str(e)[:50]}")
