"""ThetaData GEX puller -> daily dealer-gamma levels (zero-gamma flip, call/put walls, total GEX) per index.

For each trading day: pull EOD per-strike GAMMA (bulk_hist/option/eod_greeks) + OPEN INTEREST, compute dealer GEX
by strike, derive the zero-gamma flip + the call/put walls. Output: out/gex_levels_<index>.parquet -> feeds the
cross-asset GEX-divergence test and the gamma-regime conditioner.

REQUIRES: ThetaData sub + Theta Terminal running on 127.0.0.1:25510. The v2 endpoints are confirmed from the docs;
a couple FIELD NAMES (gamma / underlying_price / open_interest / strike / right / date) may need a tweak on first
run -- they print on the first call so we can fix in 1 line. The GEX math itself is standard and solid.

Run: backend/.venv/Scripts/python.exe experiments/options_signals_v0/gex_pull.py SPX 2020-01-01 2026-06-01
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import requests
except ImportError:
    requests = None

BASE = "http://127.0.0.1:25510/v2"
ROOT = {"SPX": "SPXW", "NDX": "NDXP", "RUT": "RUTW", "DJX": "DJX"}   # weekly/0DTE index-option roots
MULT = 100                                                          # index option contract multiplier
OUT = Path(__file__).resolve().parent / "out"


def _raw(path: str, **params) -> dict:
    r = requests.get(f"{BASE}/{path}", params=params, timeout=120)
    r.raise_for_status()
    return r.json()


def _parse_bulk(j: dict) -> pd.DataFrame:
    """Theta bulk response -> flat rows. Each item = {contract:{strike,right,expiration}, ticks:[[...]]};
    header.format names the tick columns; strike is in 1/1000 dollars."""
    fmt = j["header"]["format"]
    rows = []
    for item in j.get("response", []):
        c = item.get("contract", {})
        strike, right, exp = c.get("strike", 0) / 1000.0, c.get("right"), c.get("expiration")
        for tick in item.get("ticks", []):
            d = dict(zip(fmt, tick))
            d["strike"], d["right"], d["expiration"] = strike, right, exp
            rows.append(d)
    return pd.DataFrame(rows)


def _ymd(d) -> int:
    return int(pd.Timestamp(d).strftime("%Y%m%d"))


def pull_chain(index: str, start, end, max_dte_days: int = 400) -> pd.DataFrame:
    """All EOD greeks + OI for `index` over [start, end], expirations from start out to start+max_dte (skip far LEAPS)."""
    root = ROOT[index]
    s, e = _ymd(start), _ymd(end)
    all_exps = [int(x) for x in _raw("list/expirations", root=root)["response"]]
    exps = [x for x in all_exps if x >= s and x <= _ymd(pd.Timestamp(end) + pd.Timedelta(days=max_dte_days))]
    print(f"  {index}: {len(exps)} expirations in window (max_dte {max_dte_days}d)")
    parts = []
    for k, exp in enumerate(exps):
        try:
            g = _parse_bulk(_raw("bulk_hist/option/eod_greeks", root=root, exp=exp, start_date=s, end_date=e))
            oi = _parse_bulk(_raw("bulk_hist/option/open_interest", root=root, exp=exp, start_date=s, end_date=e))
        except Exception:
            continue
        if g.empty or oi.empty:
            continue
        m = g.merge(oi[["date", "strike", "right", "expiration", "open_interest"]],
                    on=["date", "strike", "right", "expiration"], how="inner")
        keep = [c for c in ("date", "strike", "right", "expiration", "gamma", "underlying_price", "open_interest")
                if c in m.columns]
        parts.append(m[keep])
        if k % 40 == 0 and k:
            time.sleep(0.05)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def gex_levels(chain: pd.DataFrame) -> pd.DataFrame:
    """Dealer GEX per option (calls +, puts -): OI * gamma * spot^2 * 0.01 * 100. Per day -> total / zero-gamma / walls."""
    right = chain["right"].astype(str).str.upper().str[0]
    spot = chain["underlying_price"].to_numpy(float)
    gex = (chain["open_interest"].to_numpy(float) * chain["gamma"].to_numpy(float)
           * spot * spot * 0.01 * MULT * np.where(right == "C", 1.0, -1.0))
    chain = chain.assign(gex=gex)
    rows = []
    for d, day in chain.groupby("date"):
        bs = day.groupby("strike")["gex"].sum().sort_index()
        if bs.empty:
            continue
        st, cum = bs.index.to_numpy(float), bs.cumsum().to_numpy(float)
        flip = np.nan
        x = np.where(np.diff(np.sign(cum)) != 0)[0]                                  # zero-gamma = cumulative-GEX flip
        if len(x):
            i = x[0]
            flip = float(np.interp(0, [cum[i], cum[i + 1]], [st[i], st[i + 1]])) if cum[i] != cum[i + 1] else st[i]
        rows.append({"date": int(d), "total_gex": float(bs.sum()), "zero_gamma": flip,
                     "call_wall": float(bs.idxmax()), "put_wall": float(bs.idxmin()),
                     "spot": float(day["underlying_price"].iloc[0])})
    return pd.DataFrame(rows).sort_values("date")


def main() -> int:
    if requests is None:
        print("pip install requests")
        return 1
    index = sys.argv[1] if len(sys.argv) > 1 else "SPX"
    start = sys.argv[2] if len(sys.argv) > 2 else "2020-01-01"
    end = sys.argv[3] if len(sys.argv) > 3 else "2026-06-01"
    max_dte = int(sys.argv[4]) if len(sys.argv) > 4 else 400
    print(f"pulling {index} ({ROOT[index]}) {start}..{end} from Theta Terminal ({BASE}) ...")
    chain = pull_chain(index, start, end, max_dte_days=max_dte)
    if chain.empty:
        print("no data -- is Theta Terminal running + subscribed? check the printed field names vs the code.")
        return 1
    lv = gex_levels(chain)
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"gex_levels_{index.lower()}.parquet"
    lv.to_parquet(p)
    print(f"\n{len(lv)} days of GEX levels -> {p}")
    print(lv.tail(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
