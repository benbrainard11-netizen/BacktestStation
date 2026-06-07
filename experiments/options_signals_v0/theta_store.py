"""Local raw store for ThetaData -- the pull-once layer.

Pulls an endpoint from the local Theta Terminal ONCE, caches the parsed result to D:\\data\\raw\\thetadata\\
(append-only, keyed by request params), and serves it from local disk on every repeat. Turns the slow API into
a permanent local options DB: re-running any computation never re-pulls. Retries transient feed drops (FPSS
reconnect storms) and RAISES on persistent failure -- never silently returns empty on a dead feed (CLAUDE.md
rule 6). fetch() = bulk endpoints (nested {contract,ticks}); fetch_flat() = single-contract endpoints (flat rows).
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import pandas as pd

try:
    import requests
except ImportError:
    requests = None

BASE = "http://127.0.0.1:25510/v2"
RAW = Path("D:/data/raw/thetadata")          # append-only local raw store (matches the Databento raw convention)


def _parse_bulk(j: dict) -> pd.DataFrame:
    """Bulk response: each item = {contract:{strike,right,expiration}, ticks:[[...]]}; strike in 1/1000 dollars."""
    fmt = j["header"]["format"]
    rows = []
    for it in j.get("response", []) or []:
        c = it.get("contract", {})
        k, rt, ex = c.get("strike", 0) / 1000.0, c.get("right"), c.get("expiration")
        for t in it.get("ticks", []):
            d = dict(zip(fmt, t))
            d["strike"], d["right"], d["expiration"] = k, rt, ex
            rows.append(d)
    return pd.DataFrame(rows)


def _parse_flat(j: dict) -> pd.DataFrame:
    """Single-contract response: response = [[tick],...] matching header.format (no contract meta)."""
    fmt = j["header"]["format"]
    return pd.DataFrame([dict(zip(fmt, t)) for t in (j.get("response", []) or [])])


def _get(endpoint: str, params: dict) -> dict | None:
    """One network pull with retry. Returns parsed json, None on legit-empty (472/no-data), raises on persistent fail."""
    last = None
    for attempt in range(4):
        try:
            r = requests.get(f"{BASE}/{endpoint}", params=params, timeout=180)
            if r.status_code == 200:
                return r.json()
            body = r.text[:100]
            if r.status_code == 472 or "No data" in body:      # legit empty -- not a failure
                return None
            if r.status_code == 471:                            # permissions -- retrying won't help
                raise RuntimeError(f"{endpoint}: permissions/{body}")
            last = f"HTTP {r.status_code}: {body}"              # transient feed/server -- retry
        except requests.RequestException as e:
            last = type(e).__name__
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"{endpoint} failed after 4 tries (feed down?): {last}")


def _cached(endpoint: str, params: dict, parser) -> pd.DataFrame:
    sub = RAW / endpoint.replace("/", "_")
    sub.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5((endpoint + "|" + json.dumps(params, sort_keys=True)).encode()).hexdigest()
    fn = sub / f"{key}.parquet"
    if fn.exists():
        return pd.read_parquet(fn)
    j = _get(endpoint, params)
    if j is None:                                              # legit-empty: don't cache, re-check next run
        return pd.DataFrame()
    df = parser(j)
    tmp = fn.with_suffix(".tmp.parquet")                       # atomic write (append-only: never a half file)
    df.to_parquet(tmp)
    tmp.replace(fn)
    time.sleep(0.05)                                           # gentle on the feed under sustained pulls
    return df


def fetch(endpoint: str, **params) -> pd.DataFrame:
    """Cached BULK fetch (all-strikes chains)."""
    return _cached(endpoint, params, _parse_bulk)


def fetch_flat(endpoint: str, **params) -> pd.DataFrame:
    """Cached SINGLE-CONTRACT fetch (flat rows, e.g. one ATM contract's intraday greeks)."""
    return _cached(endpoint, params, _parse_flat)


def expirations(root: str) -> list[int]:
    r = requests.get(f"{BASE}/list/expirations", params={"root": root}, timeout=60)
    r.raise_for_status()
    return [int(x) for x in r.json()["response"]]


def index_eod_close(root: str, start: int, end: int) -> dict:
    """Daily index close over a range in ONE ungated call -> {yyyymmdd: close}. For picking ATM strikes."""
    j = _get("hist/index/eod", {"root": root, "start_date": start, "end_date": end})
    if j is None:
        return {}
    df = _parse_flat(j)
    return dict(zip(df["date"].astype(int), df["close"].astype(float)))


def cache_stats() -> str:
    if not RAW.exists():
        return "empty"
    files = list(RAW.rglob("*.parquet"))
    mb = sum(f.stat().st_size for f in files) / 1e6
    return f"{len(files)} cached chains, {mb:.0f} MB in {RAW}"
