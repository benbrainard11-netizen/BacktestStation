"""ThetaData GEX puller -> daily dealer-gamma levels (zero-gamma, call/put walls, total GEX) per index.

STREAMS expirations and accumulates per-(date,strike) dealer GEX so it stays memory-safe over many years.
Dealer GEX per option = OI * gamma * spot^2 * 0.01 * 100, calls +, puts - (customers long, dealers short).
Output: out/gex_levels_<index>.parquet -> feeds the cross-asset GEX-divergence test + the regime conditioner.

REQUIRES: Theta Terminal running on 127.0.0.1:25510 (v2 API) with an active OPTION.PRO subscription.
NOTE: zero_gamma is a cumulative-crossing proxy (TODO: proper IV re-pricing); total_gex + walls are exact.

Run: backend/.venv/Scripts/python.exe experiments/options_signals_v0/gex_pull.py SPX 2025-05-01 2026-06-06 [max_dte_days]
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from theta_store import expirations as _exps, fetch as _fetch  # noqa: E402  (local raw-cache layer on D:)

BASE = "http://127.0.0.1:25510/v2"
ROOT = {"SPX": "SPXW", "NDX": "NDXP", "RUT": "RUTW", "DJX": "DJX",   # active weekly/0DTE index-option roots
        "GLD": "GLD", "SLV": "SLV"}                                   # metal ETF proxies (gold/silver walls)
MULT = 100
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


def pull_gex_levels(index: str, start, end, max_dte_days: int = 90) -> pd.DataFrame:
    """Stream all expirations active in the window; accumulate dealer GEX by (date, strike); derive daily levels."""
    root = ROOT[index]
    s, e = _ymd(start), _ymd(end)
    all_exps = _exps(root)
    exps = [x for x in all_exps if x >= s and x <= _ymd(pd.Timestamp(end) + pd.Timedelta(days=max_dte_days))]
    print(f"  {index} ({root}): {len(exps)} expirations in window, max_dte {max_dte_days}d")
    accum = None                              # Series, MultiIndex (date, strike) -> summed dealer GEX
    spot_d: dict[int, float] = {}
    for k, exp in enumerate(exps):
        try:
            g = _fetch("bulk_hist/option/eod_greeks", root=root, exp=exp, start_date=s, end_date=e)
            oi = _fetch("bulk_hist/option/open_interest", root=root, exp=exp, start_date=s, end_date=e)
        except Exception:
            continue
        if g.empty or oi.empty:
            continue
        m = g.merge(oi[["date", "strike", "right", "expiration", "open_interest"]],
                    on=["date", "strike", "right", "expiration"], how="inner")
        if m.empty:
            continue
        sp = m["underlying_price"].to_numpy(float)
        sign = np.where(m["right"].astype(str).str.upper().str[0] == "C", 1.0, -1.0)
        m = m.assign(gex=m["open_interest"].to_numpy(float) * m["gamma"].to_numpy(float) * sp * sp * 0.01 * MULT * sign)
        g2 = m.groupby(["date", "strike"])["gex"].sum()
        accum = g2 if accum is None else accum.add(g2, fill_value=0.0)
        for dt, spv in zip(m["date"].to_numpy(), sp):
            spot_d[int(dt)] = float(spv)
        if k and k % 50 == 0:
            print(f"   ...{k}/{len(exps)} expirations")
            time.sleep(0.05)
    if accum is None or accum.empty:
        return pd.DataFrame()

    rows = []
    for dt, grp in accum.groupby(level=0):
        bs = grp.droplevel(0).sort_index()
        st, cum = bs.index.to_numpy(float), bs.cumsum().to_numpy(float)
        flip = np.nan
        x = np.where(np.diff(np.sign(cum)) != 0)[0]
        if len(x):
            i = x[0]
            flip = float(np.interp(0, [cum[i], cum[i + 1]], [st[i], st[i + 1]])) if cum[i] != cum[i + 1] else st[i]
        rows.append({"date": int(dt), "total_gex": float(bs.sum()), "zero_gamma": flip,
                     "call_wall": float(bs.idxmax()), "put_wall": float(bs.idxmin()), "spot": spot_d.get(int(dt), np.nan)})
    return pd.DataFrame(rows).sort_values("date")


def main() -> int:
    if requests is None:
        print("pip install requests")
        return 1
    index = sys.argv[1] if len(sys.argv) > 1 else "SPX"
    start = sys.argv[2] if len(sys.argv) > 2 else "2025-05-01"
    end = sys.argv[3] if len(sys.argv) > 3 else "2026-06-06"
    max_dte = int(sys.argv[4]) if len(sys.argv) > 4 else 90
    print(f"pulling {index} {start}..{end} from Theta Terminal ({BASE}) ...")
    lv = pull_gex_levels(index, start, end, max_dte)
    if lv.empty:
        print("no data -- is the Terminal running + subscribed?")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"gex_levels_{index.lower()}.parquet"
    lv.to_parquet(p)
    print(f"\n{len(lv)} days of GEX levels -> {p}")
    print(lv.tail(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
