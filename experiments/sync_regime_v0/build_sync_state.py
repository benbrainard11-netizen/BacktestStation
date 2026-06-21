"""Cross-asset synchronization state (v0) — the 'correlation expand/contract' signal.

Builds the daily sync-state triplet across the 28-future macro universe:
  - ar_top1   : share of variance in the 1st PC of the rolling correlation matrix
                (single common factor = how 'synced' everything is; Kritzman-style)
  - ar_topN5  : absorption ratio over the top N/5 eigenvectors (Kritzman 2010)
  - avg_corr  : mean off-diagonal pairwise correlation
  - dispersion: cross-sectional std of that day's returns

Then characterizes it: persistence (is it forecastable?), crisis sanity check, and
whether the sync state CONDITIONS forward equity vol. Decides if the target has a
there-there before we point a TSFM at it. Daily, full history, CPU-only.

Run:
  backend/.venv/Scripts/python.exe experiments/sync_regime_v0/build_sync_state.py
"""
from __future__ import annotations

import sys
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "backend")
from app.data.reader import read_bars  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

SYMS = [f"{s}.c.0" for s in [
    "ES", "NQ", "YM", "RTY",                  # equity index
    "6A", "6B", "6C", "6E", "6J", "6N", "6S",  # FX
    "CL", "BZ", "HO", "NG", "RB",             # energy
    "GC", "SI", "HG", "PA", "PL",             # metals
    "ZB", "ZN", "ZF", "ZT",                   # rates
    "ZC", "ZS", "ZW",                          # grains
]]
START, END = dt.date(2018, 1, 1), dt.date(2026, 5, 22)
WIN = 60  # rolling window (trading days) for the correlation matrix


def daily_returns(min_days: int = 1200) -> pd.DataFrame:
    """Robust daily log-return panel: uniform daily grid, weekdays only, drop
    sparse symbols, align on the common window, small ffill to bridge holidays."""
    prices = {}
    for s in SYMS:
        df = read_bars(symbol=s, timeframe="1m", start=START, end=END)
        if len(df) == 0:
            print(f"  {s}: NO DATA"); continue
        ts = pd.to_datetime(df["ts_event"], utc=True)
        px = df.assign(_ts=ts).set_index("_ts")["close"].resample("1D").last()
        px = px[px.index.weekday < 5]  # weekdays only (drop spurious weekend rows)
        prices[s] = px

    P = pd.DataFrame(prices)
    print("\n  -- per-symbol daily coverage --")
    for s in sorted(P.columns, key=lambda c: P[c].notna().sum()):
        fv, lv = P[s].first_valid_index(), P[s].last_valid_index()
        print(f"     {s:9} n={int(P[s].notna().sum()):5}  {fv.date()} -> {lv.date()}")

    good = [s for s in P.columns if P[s].notna().sum() >= min_days]
    dropped = [s for s in P.columns if s not in good]
    if dropped:
        print(f"  DROPPED (< {min_days} days): {dropped}")
    P = P[good]
    lo = max(P[c].first_valid_index() for c in P.columns)
    hi = min(P[c].last_valid_index() for c in P.columns)
    P = P.loc[lo:hi].ffill(limit=2).dropna(how="any")
    R = np.log(P).diff().dropna(how="any")
    print(f"  aligned panel: {R.shape[0]} days x {R.shape[1]} assets  "
          f"{R.index.min().date()} -> {R.index.max().date()}")
    return R


def sync_state(R: pd.DataFrame) -> pd.DataFrame:
    arr = R.to_numpy()
    dates = R.index.to_numpy()
    n = arr.shape[1]
    n5 = max(1, n // 5)
    recs = []
    for i in range(WIN, len(arr)):
        win = arr[i - WIN:i]
        c = np.corrcoef(win, rowvar=False)
        c = np.nan_to_num(c, nan=0.0)
        np.fill_diagonal(c, 1.0)
        eig = np.linalg.eigvalsh(c)[::-1]
        tot = eig.sum()
        ar1 = eig[0] / tot
        ar5 = eig[:n5].sum() / tot
        offdiag = (c.sum() - n) / (n * (n - 1))
        disp = float(np.std(arr[i]))
        recs.append((dates[i], ar1, ar5, offdiag, disp))
    S = pd.DataFrame(recs, columns=["date", "ar_top1", "ar_topN5", "avg_corr", "dispersion"]).set_index("date")
    return S


def characterize(S: pd.DataFrame, R: pd.DataFrame) -> None:
    print("\n================ SYNC STATE CHARACTERIZATION ================")
    print(S.describe().round(4).to_string())

    print("\n-- persistence of ar_top1 (is it forecastable?) --")
    for h in (1, 5, 20, 60):
        x = S["ar_top1"]
        y = S["ar_top1"].shift(-h)
        v = (~x.isna()) & (~y.isna())
        r = np.corrcoef(x[v], y[v])[0, 1]
        print(f"   corr( ar_top1[t], ar_top1[t+{h:>2}] ) = {r:+.3f}   R^2={r**2:.3f}")

    print("\n-- naive-persistence vs change: std of h-day change in ar_top1 --")
    for h in (1, 5, 20):
        print(f"   h={h:>2}: std(d_ar_top1) = {S['ar_top1'].diff(h).std():.4f}  "
              f"(level std = {S['ar_top1'].std():.4f})")

    print("\n-- crisis sanity: 8 highest ar_top1 days (should be stress periods) --")
    print(S["ar_top1"].sort_values(ascending=False).head(8).round(3).to_string())

    # Does sync state condition FORWARD equity vol? (ES realized vol next 20d)
    es = R["ES.c.0"]
    fwd_vol20 = es.shift(-1).rolling(20).std().reindex(S.index)
    for col in ("ar_top1", "avg_corr", "dispersion"):
        v = (~S[col].isna()) & (~fwd_vol20.isna())
        r = np.corrcoef(S[col][v], fwd_vol20[v])[0, 1]
        print(f"\n   corr( {col}[t], ES fwd-20d realized vol ) = {r:+.3f}")

    # High vs low absorption regime: forward ES vol and |return|
    hi = S["ar_top1"] > S["ar_top1"].median()
    fwd_absret5 = es.shift(-1).rolling(5).apply(lambda w: np.abs(np.sum(w)), raw=True).reindex(S.index)
    print("\n-- regime split (ar_top1 high vs low) on forward ES move --")
    for name, mask in (("HIGH absorption", hi), ("LOW absorption", ~hi)):
        m = mask & (~fwd_vol20.isna())
        print(f"   {name:>16}: fwd-20d vol={fwd_vol20[m].mean():.4f}  "
              f"fwd-5d |Σret|={fwd_absret5[m].mean():.4f}  n={int(m.sum())}")


def main() -> int:
    print("Loading daily returns for 28 futures...")
    R = daily_returns()
    R.to_parquet(OUT / "daily_returns.parquet")
    S = sync_state(R)
    S.to_parquet(OUT / "sync_state.parquet")
    print(f"\nWrote {OUT/'sync_state.parquet'}  ({len(S)} days)")
    characterize(S, R)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
