"""Strict High-Tight-Flag candidates on the CLEAN Polygon universe (delisted INCLUDED). Ports
momentum_trend_v0/detector.py's full filter stack (prior thrust + tight low-volume base + breakout
volume + MA alignment + not-extended + closes-near-HOD + narrow-range run-in + liquidity + thrust
linearity R^2) onto Polygon daily, so we can test the REAL PDF setup (not the broad 20d-high break)
at intraday resolution against a random-day baseline. Output = out/htf_candidates.parquet with the
breakout LEVEL (base high) and causal prior-day ATR for the stop.
Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
OUT = Path(__file__).resolve().parent / "out"; OUT.mkdir(exist_ok=True)

# --- DetectorConfig defaults (mirror momentum_trend_v0/detector.py) ---
THRUST_PCT, THRUST_WIN = 0.30, 60
BASE_LEN, BASE_WIDTH = 10, 0.25
VOL_DRY, BO_VOL_MULT = 0.7, 1.5
EXTEND_MAX, HOD_FRAC, NR_DAYS = 0.10, 0.25, 3
LINEARITY_MIN = 0.80
MIN_PRICE, MIN_DVOL = 5.0, 3e6


def candidate_mask(d: pd.DataFrame):
    """Returns (loose_mask, is_mid, is_strict, base_hi, dollar_vol). LOOSE = the candidate set;
    is_mid / is_strict are progressively-stricter flags so we can test the broad->strict ladder."""
    hi, lo, cl, vol = d["high"], d["low"], d["close"], d["volume"]
    ma10 = cl.rolling(10).mean(); ma20 = cl.rolling(20).mean()
    rng = hi - lo
    base_hi = hi.rolling(BASE_LEN).max().shift(1)
    base_lo = lo.rolling(BASE_LEN).min().shift(1)
    base_mid = (base_hi + base_lo) / 2
    base_vol = vol.rolling(BASE_LEN).mean().shift(1)
    base_med_rng = rng.rolling(BASE_LEN).median().shift(1)
    thrust_vol = vol.rolling(THRUST_WIN).mean().shift(1 + BASE_LEN)
    thrust_runup = cl.shift(BASE_LEN + 1) / cl.shift(BASE_LEN + THRUST_WIN) - 1
    recent_rng = rng.rolling(NR_DAYS).mean().shift(1)
    dollar_vol = (cl * vol).rolling(20).mean().shift(1)

    # LOOSE: prior thrust + breakout above base + MA alignment + breakout volume + liquidity
    loose = (
        (cl > base_hi)
        & (thrust_runup >= THRUST_PCT)
        & (cl > ma10) & (ma10 > ma20)
        & (vol > vol.shift(1)) & (vol >= base_vol * BO_VOL_MULT)
        & (cl >= MIN_PRICE) & (dollar_vol >= MIN_DVOL)
    ).fillna(False)
    # MID: + tight base + volume dry-up + not-extended
    mid = loose & (
        ((base_hi - base_lo) / base_mid <= BASE_WIDTH)
        & (base_vol < thrust_vol * VOL_DRY)
        & ((cl - ma10) / ma10 <= EXTEND_MAX)
    ).fillna(False)
    # STRICT: + closes near HOD + narrow-range run-in  (+ linearity applied later, per-candidate)
    strict = mid & (
        (rng > 0) & ((hi - cl) / rng <= HOD_FRAC)
        & (recent_rng < base_med_rng)
    ).fillna(False)
    return loose, mid, strict, base_hi, dollar_vol


def linearity_ok(cl: np.ndarray, i: int) -> bool:
    a, b = i - BASE_LEN - THRUST_WIN, i - BASE_LEN
    if a < 0:
        return False
    y = np.log(cl[a:b])
    if len(y) < 5 or not np.all(np.isfinite(y)):
        return False
    x = np.arange(len(y))
    r = np.corrcoef(x, y)[0, 1]
    return r * r >= LINEARITY_MIN


def main():
    print("loading polygon daily...")
    df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
    df = df.sort_values(["ticker", "date"])
    meta = pd.read_parquet(POLY / "meta.parquet")
    active = dict(zip(meta["ticker"], meta["active"]))
    cs = set(meta["ticker"])

    rows = []
    for t, d in df[df["ticker"].isin(cs)].groupby("ticker", sort=False):
        if len(d) < THRUST_WIN + BASE_LEN + 25:
            continue
        d = d.reset_index(drop=True)
        loose, mid, strict, base_hi, dvol = candidate_mask(d)
        cl = d["close"].to_numpy(); hi = d["high"].to_numpy(); lo = d["low"].to_numpy()
        pc = np.roll(cl, 1)
        tr = np.maximum(hi - lo, np.maximum(np.abs(hi - pc), np.abs(lo - pc)))
        atr = pd.Series(tr).rolling(14).mean().to_numpy()
        lo_a, mid_a, st_a = loose.to_numpy(), mid.to_numpy(), strict.to_numpy()
        for i in np.flatnonzero(lo_a):
            if i < 1 or np.isnan(atr[i - 1]) or atr[i - 1] <= 0:
                continue
            rows.append({
                "ticker": t, "date": int(d["date"].iloc[i]), "active": active.get(t, False),
                "level": float(base_hi.iloc[i]), "atr_prev": float(atr[i - 1]),
                "close": float(cl[i]), "dvol": float(dvol.iloc[i]),
                "is_mid": bool(mid_a[i]),
                "is_strict": bool(st_a[i] and linearity_ok(cl, i)),
            })

    S = pd.DataFrame(rows)
    S.to_parquet(OUT / "htf_candidates.parquet")
    print(f"HTF ladder: LOOSE {len(S):,} | MID {S['is_mid'].sum():,} | STRICT {S['is_strict'].sum():,}")
    print(f"  active {S['active'].sum():,} / delisted {(~S['active']).sum():,} | "
          f"{S['date'].min()}..{S['date'].max()} | tickers {S['ticker'].nunique()} | "
          f"median dvol ${S['dvol'].median()/1e6:.1f}M | median price ${S['close'].median():.0f}")


if __name__ == "__main__":
    main()
