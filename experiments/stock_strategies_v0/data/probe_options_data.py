"""Find the fastest route to per-STOCK daily options flow (call/put volume + OI) for the options-flow
breakout test. Probe ThetaData bulk option endpoints (latency + structure) AND Polygon options access.
Determines scope (how many names feasible). Reads env POLYGON_API_KEY. Run w/ backend\\.venv\\Scripts\\python.exe.
"""

from __future__ import annotations

import os
import time

import requests

PKEY = os.environ.get("POLYGON_API_KEY", "")
TH = "http://127.0.0.1:25510"


def th(path, **p):
    t0 = time.time()
    try:
        r = requests.get(f"{TH}{path}", params=p, timeout=60)
        dt = time.time() - t0
        txt = r.text
        return r.status_code, round(dt, 1), txt[:240]
    except Exception as e:
        return None, round(time.time() - t0, 1), str(e)[:120]


print("=== THETADATA option roots + bulk EOD (1 day, all contracts for a root) ===")
sc, dt, t = th("/v2/list/roots/option")
print(f"  list option roots: HTTP{sc} {dt}s  {t[:80]}")
# bulk EOD for one underlying, one day -> all contracts that day
sc, dt, t = th("/v2/bulk_hist/option/eod", root="AAPL", start_date="20230103", end_date="20230103")
print(f"  bulk eod AAPL 1day: HTTP{sc} {dt}s  bytes~{len(t)}  {t[:180]}")
# bulk EOD over a small range
sc, dt, t = th("/v2/bulk_hist/option/eod", root="AAPL", start_date="20230103", end_date="20230110")
print(f"  bulk eod AAPL 1wk : HTTP{sc} {dt}s  {t[:120]}")
# open interest bulk
sc, dt, t = th("/v2/bulk_hist/option/open_interest", root="AAPL", start_date="20230103", end_date="20230103")
print(f"  bulk OI AAPL 1day : HTTP{sc} {dt}s  {t[:140]}")
# delisted underlying options?
sc, dt, t = th("/v2/bulk_hist/option/eod", root="SIVB", start_date="20230301", end_date="20230301")
print(f"  bulk eod SIVB(del): HTTP{sc} {dt}s  {t[:120]}")

print("\n=== POLYGON options access on current sub ===")


def pg(path, **p):
    p["apiKey"] = PKEY
    t0 = time.time()
    try:
        r = requests.get(f"https://api.polygon.io{path}", params=p, timeout=30)
        return r.status_code, round(time.time() - t0, 1), r.json()
    except Exception as e:
        return None, 0, {"_e": str(e)[:100]}


sc, dt, j = pg("/v3/reference/options/contracts", underlying_ticker="AAPL", limit=3)
print(
    f"  options contracts ref: HTTP{sc} {dt}s status={j.get('status')} rows={len(j.get('results',[]) or [])}"
)
# a per-contract daily agg (need a real contract id)
res = j.get("results", []) or []
if res:
    cid = res[0].get("ticker")
    sc, dt, j2 = pg(f"/v2/aggs/ticker/{cid}/range/1/day/2024-01-01/2024-03-01")
    print(
        f"  options aggs {cid}: HTTP{sc} status={j2.get('status')} rows={j2.get('resultsCount', len(j2.get('results',[]) or []))}"
    )
# grouped/snapshot for options volume by underlying?
sc, dt, j = pg("/v3/snapshot/options/AAPL", limit=3)
print(f"  options snapshot AAPL: HTTP{sc} status={j.get('status')} {str(j.get('error',''))[:60]}")
print("\nREAD: pick the route with lowest latency that yields per-underlying daily call/put VOLUME + OI.")
