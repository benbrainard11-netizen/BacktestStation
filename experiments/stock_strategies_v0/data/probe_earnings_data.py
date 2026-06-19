"""Earnings data-completeness probe. We have clean 9yr delisted-incl PRICE now; the one open gap was
DELISTED earnings DATES (yfinance has survivors only). Does the upgraded Polygon sub give earnings/
filing dates incl delisted? Test financials (filing_date/period) + any earnings endpoint, on a
survivor AND delisted names. Reads env POLYGON_API_KEY. Run w/ backend\\.venv\\Scripts\\python.exe.
"""

from __future__ import annotations

import os

import requests

K = os.environ["POLYGON_API_KEY"]
H = "https://api.polygon.io"


def get(path, **p):
    p["apiKey"] = K
    r = requests.get(f"{H}{path}", params=p, timeout=30)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {}


def fin(tkr, n=6):
    sc, j = get("/vX/reference/financials", ticker=tkr, limit=n, sort="filing_date", order="desc")
    res = j.get("results", []) or []
    print(
        f"  financials {tkr}: HTTP{sc} status={j.get('status')} rows={len(res)} {j.get('error','') or ''}".rstrip()
    )
    for r in res[:n]:
        print(
            f"    filed={r.get('filing_date')} period={r.get('fiscal_period')} {r.get('fiscal_year')} "
            f"start={r.get('start_date')} end={r.get('end_date')}"
        )


print("=== POLYGON financials (filing dates -> earnings-day proxy) ===")
fin("AAPL")  # survivor, recent
print()
fin("SIVB")  # delisted (SVB)
print()
fin("FRC")  # delisted (First Republic)
print()
fin("ATVI")  # delisted (Activision, acquired)

print("\n=== how far back do financials go? (AAPL, oldest) ===")
sc, j = get("/vX/reference/financials", ticker="AAPL", limit=100, sort="filing_date", order="asc")
res = j.get("results", []) or []
if res:
    print(f"  AAPL oldest filing: {res[0].get('filing_date')} | total returned {len(res)}")

print("\n=== any dedicated earnings endpoint (BMO/AMC + surprise)? ===")
for path in ("/benzinga/v1/earnings", "/v3/reference/earnings", "/vX/reference/earnings"):
    sc, j = get(path, ticker="AAPL", limit=3)
    print(f"  {path}: HTTP{sc} status={j.get('status')} {str(j.get('error',''))[:60]}")

print("\n=== dividends/splits (corp-action dates, incl delisted) ===")
for t in ("AAPL", "SIVB"):
    sc, j = get("/v3/reference/dividends", ticker=t, limit=3)
    print(f"  dividends {t}: HTTP{sc} rows={len(j.get('results',[]) or [])}")
