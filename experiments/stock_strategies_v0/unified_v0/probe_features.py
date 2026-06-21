"""Probe what NEW breakout-selector features the existing Polygon sub already serves (free) before
buying anything: ticker details (shares outstanding/float, market cap, SIC sector), news (catalyst
proxy), short interest, short volume. Tests a survivor AND a delisted name (our universe needs both).
Reads env POLYGON_API_KEY. Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import os
import json

import requests

KEY = os.environ["POLYGON_API_KEY"]
HOST = "https://api.polygon.io"


def get(path, **params):
    params["apiKey"] = KEY
    r = requests.get(f"{HOST}{path}", params=params, timeout=30)
    try:
        j = r.json()
    except Exception:
        j = {}
    return r.status_code, j


def probe_details(tkr, date=None):
    p = {}
    if date:
        p["date"] = date
    sc, j = get(f"/v3/reference/tickers/{tkr}", **p)
    res = j.get("results", {}) if isinstance(j.get("results"), dict) else {}
    fields = {k: res.get(k) for k in ("name", "market_cap", "share_class_shares_outstanding",
              "weighted_shares_outstanding", "sic_code", "sic_description", "total_employees",
              "list_date", "delisted_utc", "primary_exchange")}
    print(f"  details {tkr} (date={date}): HTTP {sc} status={j.get('status')}")
    print(f"    {json.dumps(fields, default=str)}")


def probe_news(tkr, gte, lte):
    sc, j = get("/v2/reference/news", ticker=tkr, **{"published_utc.gte": gte, "published_utc.lte": lte},
                limit=50, order="asc")
    n = len(j.get("results", []) or [])
    print(f"  news {tkr} [{gte}..{lte}]: HTTP {sc} status={j.get('status')} count={n}")
    if n:
        r0 = j["results"][0]
        print(f"    e.g. {r0.get('published_utc')} | {str(r0.get('title'))[:70]} | insights={'insights' in r0}")


def probe_short_interest(tkr):
    for path in ("/stocks/v1/short-interest", f"/v1/reference/short-interest/{tkr}"):
        sc, j = get(path, ticker=tkr, limit=5)
        n = len(j.get("results", []) or []) if isinstance(j.get("results"), list) else 0
        print(f"  short-interest {tkr} [{path}]: HTTP {sc} status={j.get('status')} rows={n}"
              f"{' err='+str(j.get('error'))[:60] if sc!=200 else ''}")
        if n:
            print(f"    e.g. {json.dumps(j['results'][0], default=str)[:160]}")
            return


def probe_short_volume(tkr):
    sc, j = get("/stocks/v1/short-volume", ticker=tkr, limit=5)
    n = len(j.get("results", []) or []) if isinstance(j.get("results"), list) else 0
    print(f"  short-volume {tkr}: HTTP {sc} status={j.get('status')} rows={n}"
          f"{' err='+str(j.get('error'))[:60] if sc!=200 else ''}")
    if n:
        print(f"    e.g. {json.dumps(j['results'][0], default=str)[:160]}")


print("=== TICKER DETAILS (float / market cap / SIC sector) ===")
probe_details("AAPL")
probe_details("AAPL", date="2023-01-15")          # point-in-time shares?
probe_details("SIVB")                              # delisted name
print("\n=== NEWS (catalyst proxy) ===")
probe_news("AAPL", "2024-05-01", "2024-05-10")
probe_news("SIVB", "2023-03-01", "2023-03-10")     # delisted, around its blowup
print("\n=== SHORT INTEREST (squeeze fuel) ===")
probe_short_interest("AAPL")
print("\n=== SHORT VOLUME ===")
probe_short_volume("AAPL")
