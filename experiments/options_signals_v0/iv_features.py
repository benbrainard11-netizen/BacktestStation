"""Intraday vol-SURFACE features (IV level + skew) -- the last untested options flavor, distinct from the
gamma/vanna/charm FLOW. Reads the cached 0DTE chains (per-strike implied_vol per minute) straight from the local
store (cache hits, no re-pull, no Terminal). Per minute: ATM IV (robust median within +-0.5% of spot),
risk-reversal SKEW (OTM-put IV minus OTM-call IV, the fear gauge), and call/put wing IVs.
Output: out/iv_intraday_<index>.parquet (date, ms_of_day, atm_iv, skew, put_iv, call_iv).
Run: backend/.venv/Scripts/python.exe experiments/options_signals_v0/iv_features.py SPX 2025-05-01 2026-06-06
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from theta_store import expirations as _exps, fetch as _fetch  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
ROOT = {"SPX": "SPXW", "NDX": "NDXP", "RUT": "RUTW"}


def _ymd(d) -> int:
    return int(pd.Timestamp(d).strftime("%Y%m%d"))


def day_iv(ch: pd.DataFrame) -> pd.DataFrame:
    """Per-minute ATM IV + risk-reversal skew from one day's 0DTE chain."""
    c = ch[(ch["implied_vol"] > 0.01) & (ch["implied_vol"] < 5.0)].copy()       # drop junk IV
    if c.empty:
        return pd.DataFrame()
    rt = c["right"].astype(str).str.upper().str[0]
    rows = []
    for ms, g in c.groupby("ms_of_day"):
        S = float(g["underlying_price"].iloc[0])
        if not (S > 0):
            continue
        m = g["strike"].to_numpy(float) / S - 1.0                               # moneyness
        iv = g["implied_vol"].to_numpy(float)
        rg = rt.loc[g.index].to_numpy()
        atm = iv[np.abs(m) <= 0.005]
        put = iv[(rg == "P") & (m <= -0.005) & (m >= -0.02)]
        call = iv[(rg == "C") & (m >= 0.005) & (m <= 0.02)]
        if len(atm) < 1:
            continue
        pv, cv = (np.median(put) if len(put) else np.nan), (np.median(call) if len(call) else np.nan)
        rows.append({"ms_of_day": int(ms), "atm_iv": float(np.median(atm)),
                     "put_iv": pv, "call_iv": cv, "skew": (pv - cv) if (len(put) and len(call)) else np.nan})
    return pd.DataFrame(rows)


def main() -> int:
    index = sys.argv[1] if len(sys.argv) > 1 else "SPX"
    start = sys.argv[2] if len(sys.argv) > 2 else "2025-05-01"
    end = sys.argv[3] if len(sys.argv) > 3 else "2026-06-06"
    root = ROOT[index]
    s, e = _ymd(start), _ymd(end)
    days = [x for x in _exps(root) if s <= x <= e]
    print(f"{index}: {len(days)} 0DTE days -- reading IV from local cache")
    parts = []
    for k, day in enumerate(days):
        try:
            ch = _fetch("bulk_hist/option/greeks", root=root, exp=day, start_date=day, end_date=day, ivl=300000)
        except Exception:
            continue
        if ch.empty or "implied_vol" not in ch.columns:
            continue
        d = day_iv(ch)
        if len(d):
            d["date"] = int(day)
            parts.append(d)
        if k and k % 50 == 0:
            print(f"  ...{k}/{len(days)}")
    if not parts:
        print("no IV data")
        return 1
    out = pd.concat(parts, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"iv_intraday_{index.lower()}.parquet"
    out.to_parquet(p)
    print(f"\n{len(out)} minute-rows over {out['date'].nunique()} days -> {p}")
    print(out[["atm_iv", "skew", "put_iv", "call_iv"]].describe().loc[["mean", "50%", "min", "max"]].to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
