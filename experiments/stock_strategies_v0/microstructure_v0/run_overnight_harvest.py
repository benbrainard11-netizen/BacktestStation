"""Is the overnight premium HARVESTABLE? Two forms: (A) pure daily overnight-capture (close->open every
day) net of a realistic cost sweep -- likely turnover-killed; (B) a LOW-TURNOVER monthly tilt: hold the
high-overnight-persistence names (capture their overnight-heavy TOTAL return), rebalance monthly. Compare
to equal-weight universe + SPY. The real question: can a low-turnover tilt beat buy-hold net of costs?
Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
MIN_PRICE, MIN_DVOL = 5.0, 5e6


def stats(r, label, bench=None, ppy=252):
    r = r.dropna()
    ann = (1 + r).prod() ** (ppy / len(r)) - 1
    vol = r.std() * np.sqrt(ppy); shp = r.mean() / r.std() * np.sqrt(ppy) if r.std() else 0
    eq = (1 + r).cumprod(); dd = (eq / eq.cummax() - 1).min()
    ex = f"  alpha {((r - bench.reindex(r.index)).mean()*ppy)*100:+.1f}%" if bench is not None else ""
    print(f"  {label:30s} CAGR {ann*100:+6.1f}%  vol {vol*100:3.0f}%  Sharpe {shp:+.2f}  maxDD {dd*100:5.0f}%{ex}")


def main():
    df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
    cs = set(pd.read_parquet(POLY / "meta.parquet")["ticker"])
    df["dt"] = pd.to_datetime(df["date"].astype(int).astype(str), format="%Y%m%d")
    spy = df[df["ticker"] == "SPY"].set_index("dt")["close"].sort_index()
    spy_ret = spy.pct_change()
    u = df[df["ticker"].isin(cs)].sort_values(["ticker", "date"]).copy()

    # per stock-day overnight + total, with liquidity flag
    on, tot, liq, dts_all, tick = [], [], [], [], []
    for t, g in u.groupby("ticker", sort=False):
        o = g["open"].to_numpy(); c = g["close"].to_numpy(); v = g["volume"].to_numpy()
        if len(c) < 60:
            continue
        pc = np.roll(c, 1)
        dvol = pd.Series(c * v).rolling(20).mean().shift(1).to_numpy()
        lq = (c >= MIN_PRICE) & (dvol >= MIN_DVOL)
        ov = o / pc - 1
        ok = np.isfinite(ov) & (np.abs(ov) < 0.5)
        on.append(np.where(ok, ov, np.nan)); tot.append(c / pc - 1)
        liq.append(lq); dts_all.append(g["dt"].to_numpy()); tick.append(np.repeat(t, len(c)))
    R = pd.DataFrame({"dt": np.concatenate(dts_all), "ticker": np.concatenate(tick),
                      "on": np.concatenate(on), "tot": np.concatenate(tot), "liq": np.concatenate(liq)})
    R = R[R["liq"]].dropna(subset=["on"])

    # (A) pure daily overnight capture, equal-weight liquid universe, cost sweep
    dayon = R.groupby("dt")["on"].mean()
    print("=== (A) pure overnight capture (long liquid universe close->open every day) ===")
    stats(dayon, "gross (0 cost)")
    for bps in (2, 5, 10):
        stats(dayon - bps / 1e4, f"net @ {bps}bps round-trip/day")
    print("  (~252 trades/yr -> cost = bps*252; the broad capture needs <~5bps to survive)")

    # (B) low-turnover monthly tilt: hold high trailing-overnight names, capture TOTAL return
    print("\n=== (B) low-turnover monthly tilt: hold high-overnight names, monthly rebalance ===")
    close = u.pivot_table(index="dt", columns="ticker", values="close")
    o_ = u.pivot_table(index="dt", columns="ticker", values="open")
    overnight = o_ / close.shift(1) - 1
    dvol = (close * u.pivot_table(index="dt", columns="ticker", values="volume")).rolling(20).mean()
    liqm = (close >= MIN_PRICE) & (dvol >= MIN_DVOL)
    me = close.resample("ME").last()
    on_trail = overnight.rolling(63).mean().resample("ME").last()      # trailing 3mo overnight (causal signal)
    fwd = me.shift(-1) / me - 1                                        # next-month TOTAL return
    liq_me = liqm.resample("ME").last()
    rows = []
    for t in me.index:
        sig, fr, lq = on_trail.loc[t], fwd.loc[t], liq_me.loc[t]
        ok = sig.notna() & fr.notna() & lq
        if ok.sum() < 50:
            continue
        q = sig[ok].rank(pct=True)
        top = fr[ok][q >= 0.8].mean(); ew = fr[ok].mean()
        rows.append((t, top, ew))
    P = pd.DataFrame(rows, columns=["dt", "top", "ew"]).set_index("dt")
    spm = spy_ret.resample("ME").apply(lambda x: (1 + x).prod() - 1).reindex(P.index)
    stats(P["top"] - 0.001, "overnight-tilt top-20% (10bps)", bench=spm, ppy=12)   # ~monthly turnover cost
    stats(P["ew"], "equal-weight universe", bench=spm, ppy=12)
    stats(spm, "SPY", ppy=12)
    print("\nREAD: (A) net>0 at realistic bps => pure overnight tradeable (rare). (B) tilt Sharpe/alpha > SPY")
    print("=> a low-turnover way to harvest the overnight premium. Neither => real but unharvestable (textbook).")


if __name__ == "__main__":
    main()
