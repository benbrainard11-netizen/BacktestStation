"""Compute daily dealer Gamma Exposure (GEX) for SPX from the OPRA chains we pulled.

For each trading day in 2025:
  - instrument map (definition): instrument_id -> strike, call/put, expiry, multiplier
  - open interest (statistics, stat_type==9 -> quantity) per instrument that day
  - Black-Scholes gamma(spot, strike, IV, T); spot = ES.c.0 ET close (SPX proxy)
  - GEX = sum over near-money strikes of  sign * gamma * OI * mult * spot^2 * 0.01
    (sign = +call / -put: standard dealer-long-calls / short-puts convention).
    Positive = dealers suppress vol (pin/revert); negative = dealers amplify (trend).

v0 uses VIX/100 as a FLAT implied vol (the standard GEX-lite) -- robust, and the OI structure drives the
sign/flip regime far more than the exact per-strike IV. (Per-strike IV from the ohlcv-1d prices is the
refinement, but Newton inversion on illiquid strikes produces spurious gamma -> v0 keeps it simple.)
HONEST: dealer-sign is an ASSUMPTION; VIX-flat ignores skew/term-structure. Good enough to test whether
the REGIME (sign/level) conditions ES, which is the whole point.

Output: out/spx_gex_daily.parquet (date, gex[$B/1%], spot, n_strikes, put_share)
Run: backend/.venv/Scripts/python.exe experiments/options_signals_v0/gex_compute.py
"""
from __future__ import annotations

from pathlib import Path

import databento as db
import numpy as np
import pandas as pd
from scipy.stats import norm

RAW = Path("D:/data/raw/opra")
OUT = Path("experiments/options_signals_v0/out")
MONEY = 0.15
MONTHS = [f"2025-{m:02d}" for m in range(1, 13)]


def bs_gamma(S, K, sigma, T):
    sq = sigma * np.sqrt(T)
    d1 = (np.log(S / K) + 0.5 * sigma ** 2 * T) / sq
    return norm.pdf(d1) / (S * sq)


def daily_close(path: Path, col: str) -> pd.Series:
    s = pd.read_parquet(path)
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
    return s[col]


def main() -> int:
    spot = daily_close(Path(__file__).resolve().parents[1] / "tgif_v0" / "out" / "ES_dailyET.parquet", "close")
    vix = daily_close(OUT / "vix_history.parquet", "VIX") / 100.0
    rows = []
    for mo in MONTHS:
        dfd = db.DBNStore.from_file(RAW / "definition" / f"SPX_OPT_{mo}.dbn.zst").to_df()
        imap = (dfd.dropna(subset=["strike_price", "expiration"]).groupby("instrument_id")
                .agg(K=("strike_price", "last"), cls=("instrument_class", "last"),
                     exp=("expiration", "last"), mult=("contract_multiplier", "last")))
        imap["mult"] = imap["mult"].fillna(100).replace(0, 100)
        imap["expN"] = pd.to_datetime(imap["exp"]).dt.tz_localize(None)
        st = db.DBNStore.from_file(RAW / "statistics" / f"SPX_OPT_{mo}.dbn.zst").to_df()
        st = st[st["stat_type"] == 9].copy()
        st["date"] = pd.to_datetime(st["ts_event"]).dt.tz_localize(None).dt.normalize()

        for d, g in st.groupby("date"):
            if d not in spot.index or d not in vix.index or not np.isfinite(vix.loc[d]):
                continue
            S, sig = float(spot.loc[d]), float(vix.loc[d])
            oi = g.groupby("instrument_id")["quantity"].last()
            j = imap.join(oi.rename("oi"), how="inner")
            j = j[j["oi"] > 0]
            j["T"] = (j["expN"] - d).dt.total_seconds() / (365.25 * 86400)
            j = j[(j["T"] > 1 / 365) & (np.abs(j["K"] / S - 1) < MONEY)]
            if len(j) < 20:
                continue
            iscall = (j["cls"] == "C").to_numpy()
            gam = bs_gamma(S, j["K"].to_numpy(), sig, j["T"].to_numpy())
            dollar = gam * j["oi"].to_numpy() * j["mult"].to_numpy() * S ** 2 * 0.01
            gex = float(np.sum(np.where(iscall, 1.0, -1.0) * dollar))
            put_share = float(np.sum(dollar[~iscall]) / np.sum(dollar)) if np.sum(dollar) else np.nan
            rows.append({"date": d, "gex": gex / 1e9, "spot": S, "n_strikes": len(j), "put_share": put_share})
        print(f"{mo} done", flush=True)

    out = pd.DataFrame(rows).set_index("date").sort_index()
    out.to_parquet(OUT / "spx_gex_daily.parquet")
    print(f"\nwrote spx_gex_daily.parquet  ({len(out)} days)")
    print(f"GEX ($B per 1% move): mean {out['gex'].mean():+.2f}  median {out['gex'].median():+.2f}  "
          f"min {out['gex'].min():+.2f}  max {out['gex'].max():+.2f}  std {out['gex'].std():.2f}")
    print(f"positive (pin/suppress) {100*(out['gex']>0).mean():.0f}%  |  "
          f"negative (trend/amplify) {100*(out['gex']<0).mean():.0f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
