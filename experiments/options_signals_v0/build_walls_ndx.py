"""Compute NDX gamma walls from RAW prices (NDX has no vendor greeks).

Reads the cached raw NDX option prices (bulk_hist/option/eod) + open interest per
expiration, then for each trading day:
  1. derive the underlying via put-call parity:  F = median(K + Cmid - Pmid) near the money
  2. invert implied vol from each near-money option mid (Black-Scholes, vectorized bisection)
  3. Black-Scholes gamma from that IV
  4. net dealer gamma per strike (calls +, puts -, weighted by OI) -> call_wall (argmax) /
     put_wall (argmin) / zero_gamma (cumsum crossing) / pin (argmax|net|) -- SAME definition
     as build_walls_v2 so NDX slots straight into the model.
Cache-only (no Terminal) once the raw pull is done. Run AFTER robust_keeper_ndx finishes.

Run: backend\\.venv\\Scripts\\python.exe experiments\\options_signals_v0\\build_walls_ndx.py
Artifact: experiments/fuhhhhh/out/walls_ndx.parquet  [date,spot,call_wall,put_wall,zero_gamma,pin,gex_proxy]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theta_store as TS  # noqa: E402
from gex_pull import _ymd  # noqa: E402

ROOT = "NDXP"
MULT = 100
WINDOW = 14            # must match the pull's window so TS.fetch hits the cache
DTE_MAX = 30           # walls use <=30 DTE (near-spot gamma dominates)
NEAR_FRAC = 0.15       # only invert IV / weight strikes within +-15% of the forward
OUT = Path(__file__).resolve().parents[1] / "fuhhhhh" / "out" / "walls_ndx.parquet"


def bs_price(S, K, T, sig, is_call):
    """Black-Scholes price, r=q=0. Arrays broadcastable."""
    T = np.maximum(T, 1e-6)
    sig = np.maximum(sig, 1e-6)
    sqT = np.sqrt(T)
    d1 = (np.log(S / K) + 0.5 * sig * sig * T) / (sig * sqT)
    d2 = d1 - sig * sqT
    call = S * norm.cdf(d1) - K * norm.cdf(d2)
    return np.where(is_call, call, call - S + K)   # put via parity (r=0)


def implied_vol(price, S, K, T, is_call):
    """Vectorized bisection IV in [1e-3, 5]. NaN where price is below intrinsic / no solution."""
    lo = np.full_like(price, 1e-3, dtype=float)
    hi = np.full_like(price, 5.0, dtype=float)
    intrinsic = np.where(is_call, np.maximum(S - K, 0.0), np.maximum(K - S, 0.0))
    bad = (price <= intrinsic + 1e-6) | ~np.isfinite(price)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        pm = bs_price(S, K, T, mid, is_call)
        up = pm < price
        lo = np.where(up, mid, lo)
        hi = np.where(up, hi, mid)
    iv = 0.5 * (lo + hi)
    return np.where(bad, np.nan, iv)


def bs_gamma(S, K, T, sig):
    T = np.maximum(T, 1e-6)
    sig = np.maximum(sig, 1e-4)
    with np.errstate(all="ignore"):
        d1 = (np.log(S / K) + 0.5 * sig * sig * T) / (sig * np.sqrt(T))
        g = np.exp(-0.5 * d1 * d1) / np.sqrt(2 * np.pi) / (S * sig * np.sqrt(T))
    return np.where(np.isfinite(g), g, 0.0)


def load_chain(start: str, end: str) -> pd.DataFrame:
    s, e = _ymd(start), _ymd(end)
    exps = [x for x in TS.expirations(ROOT) if s <= x <= _ymd(pd.Timestamp(end) + pd.Timedelta(days=90))]
    print(f"{ROOT}: {len(exps)} expirations; reading cached prices+OI...", flush=True)
    parts, miss = [], 0
    for k, exp in enumerate(exps):
        e_ts = pd.Timestamp(str(exp))
        s_k = max(s, _ymd(e_ts - pd.Timedelta(days=WINDOW)))
        try:
            px = TS.fetch("bulk_hist/option/eod", root=ROOT, exp=exp, start_date=s_k, end_date=exp)
            oi = TS.fetch("bulk_hist/option/open_interest", root=ROOT, exp=exp, start_date=s_k, end_date=exp)
        except Exception:
            miss += 1
            continue
        if px.empty or oi.empty:
            continue
        m = px.merge(oi[["date", "strike", "right", "expiration", "open_interest"]],
                     on=["date", "strike", "right", "expiration"], how="inner")
        if m.empty:
            continue
        bid, ask, close = m["bid"].to_numpy(float), m["ask"].to_numpy(float), m["close"].to_numpy(float)
        mid = np.where((bid > 0) & (ask > 0), 0.5 * (bid + ask), close)
        m = m.assign(mid=mid)
        parts.append(m[["date", "expiration", "strike", "right", "mid", "open_interest"]])
        if k and k % 100 == 0:
            print(f"  ...{k}/{len(exps)}", flush=True)
    df = pd.concat(parts, ignore_index=True)
    df = df[df["expiration"].astype(int) >= df["date"].astype(int)].copy()
    df["right"] = df["right"].astype(str).str.upper().str[0]
    print(f"chain rows: {len(df)} (missing-fetch {miss})", flush=True)
    return df


def parity_forward(g: pd.DataFrame) -> float:
    """F = K + (Cmid - Pmid), median over strikes with both a call and put (near the money)."""
    c = g[g["right"] == "C"][["strike", "mid"]].rename(columns={"mid": "c"})
    p = g[g["right"] == "P"][["strike", "mid"]].rename(columns={"mid": "p"})
    j = c.merge(p, on="strike")
    if j.empty:
        return float("nan")
    fwd = j["strike"].to_numpy(float) + (j["c"].to_numpy(float) - j["p"].to_numpy(float))
    # near-money: strikes whose |C-P| is small (closest to ATM) are most reliable
    order = (j["c"] - j["p"]).abs().to_numpy().argsort()
    return float(np.median(fwd[order[: max(5, len(fwd) // 5)]]))


def _zero_gamma(strikes, prof):
    cum = np.cumsum(prof)
    x = np.where(np.diff(np.sign(cum)) != 0)[0]
    if not len(x):
        return float("nan")
    i = x[0]
    return float(strikes[i]) if cum[i] == cum[i + 1] else float(np.interp(0, [cum[i], cum[i + 1]], [strikes[i], strikes[i + 1]]))


def main(start: str | None = None, end: str | None = None) -> int:
    # callable (start, end) so other roots can reuse this self-compute engine by monkeypatching
    # module ROOT/OUT (see build_walls_selfcompute.py); falls back to argv for the NDX CLI.
    start = start or (sys.argv[1] if len(sys.argv) > 1 else "2018-01-01")
    end = end or (sys.argv[2] if len(sys.argv) > 2 else "2026-12-31")
    chain = load_chain(start, end)
    rows = []
    for D, g in chain.groupby("date"):
        F = parity_forward(g)
        if not (F > 0):
            continue
        g = g[(g["strike"] >= F * (1 - NEAR_FRAC)) & (g["strike"] <= F * (1 + NEAR_FRAC))].copy()
        dte = (pd.to_datetime(g["expiration"].astype(int).astype(str), format="%Y%m%d")
               - pd.to_datetime(str(int(D)), format="%Y%m%d")).dt.days.clip(lower=0)
        g = g[dte <= DTE_MAX].copy()
        if len(g) < 8:
            continue
        T = ((pd.to_datetime(g["expiration"].astype(int).astype(str), format="%Y%m%d")
              - pd.to_datetime(str(int(D)), format="%Y%m%d")).dt.days.clip(lower=0).to_numpy(float)) / 365.0
        K = g["strike"].to_numpy(float)
        is_call = (g["right"].to_numpy() == "C")
        iv = implied_vol(g["mid"].to_numpy(float), F, K, T, is_call)
        gam = bs_gamma(F, K, T, iv)
        sign = np.where(is_call, 1.0, -1.0)
        gex = np.where(np.isfinite(gam), gam, 0.0) * g["open_interest"].to_numpy(float) * sign
        per = pd.Series(gex * F * F * 0.01 * MULT, index=K).groupby(level=0).sum().sort_index()
        if len(per) < 5:
            continue
        strikes, prof = per.index.to_numpy(float), per.to_numpy(float)
        aprof = pd.Series(np.abs(gex) * F * F * 0.01 * MULT, index=K).groupby(level=0).sum().reindex(per.index).to_numpy(float)
        rows.append({"date": int(D), "spot": F,
                     "call_wall": float(strikes[np.argmax(prof)]),
                     "put_wall": float(strikes[np.argmin(prof)]),
                     "zero_gamma": _zero_gamma(strikes, prof),
                     "pin": float(strikes[np.argmax(aprof)]),
                     "gex_proxy": float(prof.sum())})
    w = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp.parquet")          # atomic write: never a half file / race a stale run
    w.to_parquet(tmp)
    tmp.replace(OUT)
    yrs = pd.Series(pd.to_datetime(w["date"].astype(str), format="%Y%m%d").dt.year).value_counts().sort_index()
    print(f"\nwalls[{ROOT}]: {len(w)} days {w['date'].min()} -> {w['date'].max()}; days/yr {yrs.to_dict()} -> {OUT}")
    print(w.tail(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
