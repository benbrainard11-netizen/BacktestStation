"""Full near-term INTRADAY GEX via EOD-OI re-price.

Open interest (real dealer positioning) updates once per day at settlement -- intraday only SPOT moves. So
intraday GEX = the EOD chain (OI + IV per strike, every expiration <= DTE) re-priced by Black-Scholes gamma at
each intraday spot. This captures the same information as pulling 78 separate 1-min chains/day for ~1% of the
data (the OI isn't changing intraday -- only re-downloading it would be). Uses OPTION.PRO only: intraday index
data needs a separate indices sub we skip, so intraday spot is reused from the cached 0DTE chain's
underlying_price. Unlike 0DTE (OI~0, volume-proxied) this uses REAL open interest across the near-term complex.

Approximation: EOD IV is held flat intraday (the IV surface drifts within the day); the spot-driven gamma move
dominates the regime signal (squeeze vs pin, zero-gamma location). Output: out/intraday_gex_<index>.parquet.
Run: backend/.venv/Scripts/python.exe experiments/options_signals_v0/intraday_gex.py SPX 2025-05-01 2026-06-06 [dte]
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
MULT = 100
CLOSE_MS = 16 * 3600 * 1000          # 16:00 ET settle
DAY_MS = 24 * 3600 * 1000


def _ymd(d) -> int:
    return int(pd.Timestamp(d).strftime("%Y%m%d"))


def bs_gamma(S, K, T, sig):
    """Black-Scholes gamma (r=q=0). S,K,T,sig broadcastable."""
    T = np.maximum(T, 5 / 525600.0)
    sig = np.maximum(sig, 1e-4)
    with np.errstate(all="ignore"):
        d1 = (np.log(S / K) + 0.5 * sig * sig * T) / (sig * np.sqrt(T))
        g = np.exp(-0.5 * d1 * d1) / np.sqrt(2 * np.pi) / (S * sig * np.sqrt(T))
    return np.where(np.isfinite(g), g, 0.0)


def load_eod_chain(index: str, start, end, dte: int) -> pd.DataFrame:
    """Per trade-date EOD snapshot of every alive contract <= dte days out: date, expiration, strike, sign, oi, iv."""
    root = ROOT[index]
    s, e = _ymd(start), _ymd(end)
    emax = _ymd(pd.Timestamp(end) + pd.Timedelta(days=dte))
    exps = [x for x in _exps(root) if s <= x <= emax]
    print(f"  {index} ({root}): {len(exps)} expirations span the window (<= {dte}d out)")
    parts = []
    fails = 0
    for k, exp in enumerate(exps):
        try:
            g = _fetch("bulk_hist/option/eod_greeks", root=root, exp=exp, start_date=s, end_date=e)
            oi = _fetch("bulk_hist/option/open_interest", root=root, exp=exp, start_date=s, end_date=e)
        except Exception as ex:                                          # loud breaker -- no silent 200-day skips
            fails += 1
            if fails >= 8:
                raise RuntimeError(f"aborting: {fails} consecutive fetch failures near exp {exp} (feed down?): {ex}")
            continue
        fails = 0
        if g.empty or oi.empty:
            continue
        m = g.merge(oi[["date", "strike", "right", "expiration", "open_interest"]],
                    on=["date", "strike", "right", "expiration"], how="inner")
        if not m.empty:
            parts.append(m[["date", "expiration", "strike", "right", "implied_vol", "open_interest"]])
        if k and k % 25 == 0:
            print(f"   ...eod {k}/{len(exps)} expirations")
    if not parts:
        return pd.DataFrame()
    df = pd.concat(parts, ignore_index=True)
    df = df[df["expiration"].astype(int) >= df["date"].astype(int)].copy()          # drop expired
    df["sign"] = np.where(df["right"].astype(str).str.upper().str[0] == "C", 1.0, -1.0)
    de = pd.to_datetime(df["expiration"].astype(int).astype(str), format="%Y%m%d")
    dd = pd.to_datetime(df["date"].astype(int).astype(str), format="%Y%m%d")
    df["cal_days"] = (de - dd).dt.days.clip(lower=0).to_numpy(float)
    return df


def _zero_gamma(strikes: np.ndarray, prof: np.ndarray) -> np.ndarray:
    """Per-minute zero-gamma strike: where cumulative gamma-by-strike crosses 0. prof shape (n_strike, n_min)."""
    cum = np.cumsum(prof, axis=0)
    out = np.full(prof.shape[1], np.nan)
    for j in range(prof.shape[1]):
        c = cum[:, j]
        x = np.where(np.diff(np.sign(c)) != 0)[0]
        if len(x):
            i = x[0]
            out[j] = strikes[i] if c[i] == c[i + 1] else float(np.interp(0, [c[i], c[i + 1]], [strikes[i], strikes[i + 1]]))
    return out


def intraday_gex(index: str, start, end, dte: int) -> pd.DataFrame:
    chain = load_eod_chain(index, start, end, dte)
    if chain.empty:
        return pd.DataFrame()
    spf = OUT / f"spot_intraday_{index.lower()}.parquet"           # lean one-contract spot (preferred)
    if not spf.exists():
        spf = OUT / f"dte0_intraday_{index.lower()}.parquet"       # fallback: 0DTE-chain-derived spot
    sp = pd.read_parquet(spf)[["date", "ms_of_day", "spot"]]
    rows = []
    for D, cg in chain.groupby("date"):
        sd = sp[sp["date"].astype(int) == int(D)]
        if sd.empty:
            continue
        K = cg["strike"].to_numpy(float)[:, None]
        OI = cg["open_interest"].to_numpy(float)[:, None]
        iv = cg["implied_vol"].to_numpy(float)[:, None]
        sgn = cg["sign"].to_numpy(float)[:, None]
        cal = cg["cal_days"].to_numpy(float)[:, None]
        S = sd["spot"].to_numpy(float)[None, :]                                     # (1, n_min)
        ms = sd["ms_of_day"].to_numpy(float)[None, :]
        T = (cal + np.clip((CLOSE_MS - ms) / DAY_MS, 0, 1)) / 365.0                 # (n_contract, n_min)
        gex = OI * bs_gamma(S, K, T, iv) * S * S * 0.01 * MULT * sgn                # signed dealer GEX
        net = gex.sum(axis=0)
        su = np.unique(K[:, 0])
        prof = np.zeros((len(su), gex.shape[1]))
        np.add.at(prof, np.searchsorted(su, K[:, 0]), gex)                          # collapse to strike profile
        zg = _zero_gamma(su, prof)
        for j in range(gex.shape[1]):
            rows.append({"date": int(D), "ms_of_day": int(sd["ms_of_day"].to_numpy()[j]),
                         "net_gex": float(net[j]), "zero_gamma": float(zg[j]), "spot": float(S[0, j])})
    return pd.DataFrame(rows)


def main() -> int:
    index = sys.argv[1] if len(sys.argv) > 1 else "SPX"
    start = sys.argv[2] if len(sys.argv) > 2 else "2025-05-01"
    end = sys.argv[3] if len(sys.argv) > 3 else "2026-06-06"
    dte = int(sys.argv[4]) if len(sys.argv) > 4 else 30
    print(f"intraday GEX {index} {start}..{end}  (EOD-OI re-price, <= {dte}d) ...")
    out = intraday_gex(index, start, end, dte)
    if out.empty:
        print("no data -- need cached 0DTE spot (dte0_intraday) + Terminal up for the EOD chains")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"intraday_gex_{index.lower()}.parquet"
    out.to_parquet(p)
    print(f"\n{len(out)} minute-rows over {out['date'].nunique()} days -> {p}")
    print(out.tail(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
