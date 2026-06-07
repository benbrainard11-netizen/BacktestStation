"""Local raw store for ThetaData -- the pull-once layer.

fetch() pulls a bulk endpoint from the local Theta Terminal ONCE, caches the parsed chain to
D:\\data\\raw\\thetadata\\ (append-only, keyed by the request params), and serves it from local disk on every
repeat. Turns the slow API into a permanent local options DB: re-running any computation never re-pulls.
Used by gex_pull / pull_0dte / the full-intraday builder.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

try:
    import requests
except ImportError:
    requests = None

BASE = "http://127.0.0.1:25510/v2"
RAW = Path("D:/data/raw/thetadata")          # append-only local raw store (matches the Databento raw convention)


def _parse_bulk(j: dict) -> pd.DataFrame:
    fmt = j["header"]["format"]
    rows = []
    for it in j.get("response", []):
        c = it.get("contract", {})
        k, rt, ex = c.get("strike", 0) / 1000.0, c.get("right"), c.get("expiration")
        for t in it.get("ticks", []):
            d = dict(zip(fmt, t))
            d["strike"], d["right"], d["expiration"] = k, rt, ex
            rows.append(d)
    return pd.DataFrame(rows)


def fetch(endpoint: str, **params) -> pd.DataFrame:
    """Cached bulk fetch: local on hit, pull+cache on miss. Parsed flat chain (all greek cols + contract meta)."""
    sub = RAW / endpoint.replace("/", "_")
    sub.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5((endpoint + "|" + json.dumps(params, sort_keys=True)).encode()).hexdigest()
    fn = sub / f"{key}.parquet"
    if fn.exists():
        return pd.read_parquet(fn)
    r = requests.get(f"{BASE}/{endpoint}", params=params, timeout=180)
    r.raise_for_status()
    df = _parse_bulk(r.json())
    tmp = fn.with_suffix(".tmp.parquet")               # atomic write (append-only: never a half file)
    df.to_parquet(tmp)
    tmp.replace(fn)
    return df


def expirations(root: str) -> list[int]:
    r = requests.get(f"{BASE}/list/expirations", params={"root": root}, timeout=60)
    r.raise_for_status()
    return [int(x) for x in r.json()["response"]]


def cache_stats() -> str:
    if not RAW.exists():
        return "empty"
    files = list(RAW.rglob("*.parquet"))
    mb = sum(f.stat().st_size for f in files) / 1e6
    return f"{len(files)} cached chains, {mb:.0f} MB in {RAW}"
