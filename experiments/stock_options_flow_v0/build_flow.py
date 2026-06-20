"""Build per-(ticker, date) OPTIONS-FLOW features from the cached monthly chains (cache-only).

The flow family (the 'smart money positioning' angle): call vs put VOLUME, dollar flow, volume/OI
(new-positioning turnover), delta-weighted flow, ATM-band concentration. All from eod_greeks (volume,
close, delta, underlying) + OI. Keyed by date, causal (day-D flow predicts D+1). Companion to the
gamma walls (the vol angle). Writes out/flow_<ticker>.parquet.

Run: THETA_CACHE_ONLY=1 python build_flow.py PLTR SOFI ...    (default: all in universe_pilot.txt)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "options_signals_v0"))
import theta_store as TS  # noqa: E402
from gex_pull import _ymd  # noqa: E402

os.environ.setdefault("THETA_CACHE_ONLY", "1")  # read cache, never hit the feed here
START, END, WINDOW, ATM_BAND = "2023-01-01", "2026-06-30", 35, 0.10
OUT = HERE / "out"


def is_monthly(x: int) -> bool:
    d = pd.Timestamp(str(x))
    return d.weekday() == 4 and 15 <= d.day <= 21


def load_chain(t: str) -> pd.DataFrame:
    s, e = _ymd(START), _ymd(END)
    hi = _ymd(pd.Timestamp(END) + pd.Timedelta(days=90))
    exps = [x for x in sorted(TS.expirations(t)) if s <= x <= hi and is_monthly(x)]
    parts = []
    for exp in exps:
        e_ts = pd.Timestamp(str(exp))
        s_k, e_k = max(s, _ymd(e_ts - pd.Timedelta(days=WINDOW))), min(e, exp)
        if s_k > e_k:
            continue
        gk = TS.fetch("bulk_hist/option/eod_greeks", root=t, exp=exp, start_date=s_k, end_date=e_k)
        oi = TS.fetch("bulk_hist/option/open_interest", root=t, exp=exp, start_date=s_k, end_date=e_k)
        if gk is None or gk.empty:
            continue
        if oi is not None and not oi.empty:
            gk = gk.merge(oi[["date", "strike", "right", "expiration", "open_interest"]],
                          on=["date", "strike", "right", "expiration"], how="left")
        else:
            gk["open_interest"] = np.nan
        gk["right"] = gk["right"].astype(str).str.upper().str[0]
        de, dd = pd.Timestamp(str(exp)), pd.to_datetime(gk["date"].astype(int).astype(str), format="%Y%m%d")
        gk = gk[((de - dd).dt.days >= 0) & ((de - dd).dt.days <= 60)]
        parts.append(gk[["date", "strike", "right", "close", "volume", "open_interest",
                         "delta", "implied_vol", "underlying_price"]])
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True).drop_duplicates(["date", "strike", "right"])


def features(t: str) -> pd.DataFrame:
    df = load_chain(t)
    if df.empty:
        print(f"[{t}] no cached chain", flush=True)
        return df
    df["dollar"] = df["volume"].astype(float) * df["close"].astype(float) * 100.0
    rows = []
    for D, g in df.groupby("date"):
        spot = float(np.nanmedian(g["underlying_price"]))
        c, p = g[g["right"] == "C"], g[g["right"] == "P"]
        atm = g[(g["strike"] - spot).abs() / max(spot, 1e-9) <= ATM_BAND]
        cv, pv = float(c["volume"].sum()), float(p["volume"].sum())
        cd, pd_ = float(c["dollar"].sum()), float(p["dollar"].sum())
        coi, poi = float(c["open_interest"].sum()), float(p["open_interest"].sum())
        tv = cv + pv
        # per-stock ATM implied vol (the proper 'beyond IV' control) — near-ATM, valid IVs only
        iv = atm["implied_vol"]
        iv = iv[(iv > 0.05) & (iv < 5.0)]
        atm_iv = float(iv.median()) if len(iv) else np.nan
        rows.append({
            "date": int(D), "spot": spot, "atm_iv": atm_iv,
            "cp_vol_ratio": cv / (pv + 1.0),                       # >1 = call-heavy flow
            "cp_dollar_ratio": cd / (pd_ + 1.0),
            "cp_oi_ratio": coi / (poi + 1.0),
            "vol_oi": tv / (coi + poi + 1.0),                       # turnover vs standing positioning
            "net_call_share": (cv - pv) / (tv + 1.0),              # [-1,1] directional flow tilt
            "atm_cp_vol": float(atm[atm["right"] == "C"]["volume"].sum()) /
                          (float(atm[atm["right"] == "P"]["volume"].sum()) + 1.0),
            "delta_flow": float((g["volume"] * g["delta"]).sum()),  # delta-weighted volume (signed)
            "tot_vol": tv,
        })
    out = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    out["ticker"] = t
    return out


def main() -> int:
    names = [a.upper() for a in sys.argv[1:]] or [
        ln.strip() for ln in (HERE / "universe_pilot.txt").read_text().splitlines()
        if ln.strip() and not ln.startswith("#")]
    OUT.mkdir(parents=True, exist_ok=True)
    for t in names:
        f = features(t)
        if f.empty:
            continue
        f.to_parquet(OUT / f"flow_{t.lower()}.parquet")
        print(f"[{t}] flow days={len(f)} {int(f['date'].min())}..{int(f['date'].max())}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
