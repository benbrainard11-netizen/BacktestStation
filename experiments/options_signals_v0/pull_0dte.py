"""ThetaData 0DTE intraday GEX puller. Same-day-expiry options at 1-min: pull IV (greeks) + volume (ohlc),
compute Black-Scholes gamma from IV (the intraday greeks endpoint omits gamma), weight by CUMULATIVE intraday
volume (0DTE open interest is ~0 -- positioning builds via the day's flow) -> per-minute 0DTE GEX (net gamma
sign) + pin strike + spot. The fast pin/squeeze signal to condition reclaim trades on.

REQUIRES Theta Terminal on 127.0.0.1:25510 + OPTION.PRO. Output: out/dte0_intraday_<index>.parquet.
Run: backend/.venv/Scripts/python.exe experiments/options_signals_v0/pull_0dte.py SPX 2025-05-01 2026-06-06
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

B = "http://127.0.0.1:25510/v2"
ROOT = {"SPX": "SPXW", "NDX": "NDXP", "RUT": "RUTW"}
MULT = 100
OUT = Path(__file__).resolve().parent / "out"
CLOSE_MS = 16 * 3600 * 1000          # SPXW PM settle ~16:00 ET
YEAR_MS = 365 * 24 * 3600 * 1000


def _raw(path: str, **p) -> dict:
    r = requests.get(f"{B}/{path}", params=p, timeout=120)
    r.raise_for_status()
    return r.json()


def _parse(j: dict) -> pd.DataFrame:
    fmt = j["header"]["format"]
    rows = []
    for it in j.get("response", []):
        c = it.get("contract", {})
        k, rt = c.get("strike", 0) / 1000.0, c.get("right")
        for t in it.get("ticks", []):
            d = dict(zip(fmt, t))
            d["strike"], d["right"] = k, rt
            rows.append(d)
    return pd.DataFrame(rows)


def bs_greeks(S, K, T, sig):
    """Black-Scholes gamma, vanna (dDelta/dVol), charm (dDelta/dTime) from IV. r=q=0."""
    T = np.maximum(T, 5 / 525600.0)
    sig = np.maximum(sig, 1e-4)
    sqT = np.sqrt(T)
    with np.errstate(all="ignore"):
        d1 = (np.log(S / K) + 0.5 * sig * sig * T) / (sig * sqT)
        d2 = d1 - sig * sqT
        phi = np.exp(-0.5 * d1 * d1) / np.sqrt(2 * np.pi)
        gamma = phi / (S * sig * sqT)
        vanna = -phi * d2 / sig
        charm = phi * d2 / (2.0 * T)
    fin = lambda x: np.where(np.isfinite(x), x, 0.0)  # noqa: E731
    return fin(gamma), fin(vanna), fin(charm)


def pull_day(root: str, day: int, ivl: int = 60000):
    try:
        g = _fetch("bulk_hist/option/greeks", root=root, exp=day, start_date=day, end_date=day, ivl=ivl)
        v = _fetch("bulk_hist/option/ohlc", root=root, exp=day, start_date=day, end_date=day, ivl=ivl)
    except Exception:
        return None
    if g.empty or v.empty:
        return None
    m = g.merge(v[["ms_of_day", "strike", "right", "volume"]], on=["ms_of_day", "strike", "right"], how="inner")
    if m.empty:
        return None
    S, K, iv = (m["underlying_price"].to_numpy(float), m["strike"].to_numpy(float), m["implied_vol"].to_numpy(float))
    T = np.maximum(CLOSE_MS - m["ms_of_day"].to_numpy(float), 60000) / YEAR_MS
    gam, van, cha = bs_greeks(S, K, T, iv)
    m["gamma"], m["vanna"], m["charm"] = gam, van, cha
    m = m.sort_values("ms_of_day")
    m["cumvol"] = m.groupby(["strike", "right"])["volume"].cumsum()
    sign = np.where(m["right"].astype(str).str.upper().str[0] == "C", 1.0, -1.0)
    pos = m["cumvol"].to_numpy(float) * sign * MULT                  # signed dealer position proxy
    m["gex"] = m["gamma"].to_numpy(float) * pos * S * S * 0.01       # dealer GEX
    m["vex"] = m["vanna"].to_numpy(float) * pos                      # net dealer vanna exposure
    m["cex"] = m["charm"].to_numpy(float) * pos                      # net dealer charm exposure
    m["gw"] = m["gamma"].to_numpy(float) * m["cumvol"].to_numpy(float)
    rows = []
    for ms, grp in m.groupby("ms_of_day"):
        gw = grp.groupby("strike")["gw"].sum()
        rows.append({"date": int(day), "ms_of_day": int(ms), "net_gex": float(grp["gex"].sum()),
                     "net_vanna": float(grp["vex"].sum()), "net_charm": float(grp["cex"].sum()),
                     "pin": float(gw.idxmax()) if gw.max() > 0 else np.nan,
                     "spot": float(grp["underlying_price"].iloc[0])})
    return pd.DataFrame(rows)


def main() -> int:
    if requests is None:
        print("pip install requests")
        return 1
    index = sys.argv[1] if len(sys.argv) > 1 else "SPX"
    start = sys.argv[2] if len(sys.argv) > 2 else "2025-05-01"
    end = sys.argv[3] if len(sys.argv) > 3 else "2026-06-06"
    root = ROOT[index]
    ivl = int(sys.argv[4]) if len(sys.argv) > 4 else 60000
    s, e = int(pd.Timestamp(start).strftime("%Y%m%d")), int(pd.Timestamp(end).strftime("%Y%m%d"))
    days = [x for x in _exps(root) if s <= x <= e]
    print(f"{index} ({root}): {len(days)} 0DTE days {start}..{end}  (ivl={ivl}ms)")
    parts, t0 = [], time.time()
    for k, day in enumerate(days):
        d = pull_day(root, day, ivl)
        if d is not None:
            parts.append(d)
        if k and k % 20 == 0:
            print(f"  ...{k}/{len(days)} ({round(time.time() - t0)}s)")
    if not parts:
        print("no data")
        return 1
    out = pd.concat(parts, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"dte0_intraday_{index.lower()}.parquet"
    out.to_parquet(p)
    print(f"\n{len(out)} minute-rows over {out['date'].nunique()} days -> {p}")
    print(out.tail(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
