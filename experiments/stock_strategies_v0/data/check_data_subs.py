"""Inventory what the CURRENT subs actually serve (history depth), before deciding on any upgrade.
Polygon: how far back does grouped-daily go on the current plan? ThetaData: is the terminal up, and
how deep is stock EOD / 1m, incl delisted? Reads env POLYGON_API_KEY. Run w/ backend\\.venv\\Scripts\\python.exe.
"""

from __future__ import annotations

import os

import requests

PKEY = os.environ.get("POLYGON_API_KEY", "")


def poly_grouped(date):
    try:
        r = requests.get(
            f"https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/{date}",
            params={"adjusted": "true", "apiKey": PKEY},
            timeout=30,
        )
        j = r.json()
        n = j.get("resultsCount", len(j.get("results", []) or []))
        return f"HTTP{r.status_code} status={j.get('status')} rows={n} {j.get('error','') or ''}".strip()
    except Exception as e:
        return f"ERR {str(e)[:80]}"


def theta(path, port=25510, **params):
    try:
        r = requests.get(f"http://127.0.0.1:{port}{path}", params=params, timeout=25)
        t = r.text.strip().replace("\n", " ")
        return f"HTTP{r.status_code} {t[:150]}"
    except Exception as e:
        return f"DOWN {str(e)[:90]}"


print("=== POLYGON grouped-daily history floor (current sub) ===")
for d in [
    "2010-06-01",
    "2014-06-02",
    "2016-06-01",
    "2018-06-01",
    "2019-06-03",
    "2020-03-16",
    "2021-01-04",
    "2021-06-01",
    "2022-06-01",
]:
    print(f"  {d}: {poly_grouped(d)}")

print("\n=== THETADATA terminal liveness ===")
live_port = None
for port in (25510, 25511):
    for probe in ("/v2/system/mdds/status", "/v2/list/roots/stock"):
        res = theta(probe, port)
        print(f"  port {port} {probe}: {res}")
        if res.startswith("HTTP200") and live_port is None:
            live_port = port

if live_port:
    p = live_port
    print(f"\n=== THETADATA stock EOD history depth (port {p}) ===")
    for yr in (2010, 2012, 2014, 2016, 2018, 2020):
        print(
            f"  AAPL EOD {yr}: {theta('/v2/hist/stock/eod', p, root='AAPL', start_date=f'{yr}0104', end_date=f'{yr}0111')}"
        )
    print("\n=== THETADATA delisted + 1m ===")
    print(
        f"  SIVB EOD 2023: {theta('/v2/hist/stock/eod', p, root='SIVB', start_date='20230101', end_date='20230310')}"
    )
    print(
        f"  AAPL 1m 2016 : {theta('/v2/hist/stock/ohlc', p, root='AAPL', start_date='20160104', end_date='20160104', ivl='60000')}"
    )
    print(
        f"  AAPL 1m 2018 : {theta('/v2/hist/stock/ohlc', p, root='AAPL', start_date='20180104', end_date='20180104', ivl='60000')}"
    )
    print(f"  roots count  : {theta('/v2/list/roots/stock', p)[:80]}")
else:
    print("\n  ThetaData terminal not responding on 25510/25511 — start ThetaTerminal to probe it live.")
