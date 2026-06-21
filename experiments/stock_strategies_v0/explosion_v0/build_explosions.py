"""EXPLOSION setup table: the 'capture the breakout MOVE' reframe. Candidates = upside thrusts
(20d-high breakout OR gap-up) on the clean 2016-2026 Polygon universe (delisted incl, incl the
2020-21 explosion era). The TARGET is the TAIL, not the mean: did the stock run big (max-favorable
-excursion >= 30/40/50/100%) within 60 trading days? Plus the TRADEABLE outcome (enter next open,
1xATR stop, 3xATR chandelier let-run, costs) so we can test real economics, not just potential.
Causal features only. Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
OUT = Path(__file__).resolve().parent / "out"; OUT.mkdir(parents=True, exist_ok=True)
MIN_PRICE, MIN_DVOL = 3.0, 2e6          # tradeable-ish but keeps the explosive small-cap zone
HOLD, FRIC, K_ATR, CHAND = 60, 0.0015, 1.0, 3.0


def tradeable(o, h, l, c, i, atr):
    """Enter open[i+1], 1xATR stop, chandelier let-run, max HOLD days. Returns (R, mfe_pct)."""
    entry = o[i + 1] * (1 + FRIC)
    risk = K_ATR * atr
    if risk <= 0:
        return np.nan, np.nan
    stop = entry - risk
    cur, run_hi = stop, entry
    cost_R = 2 * FRIC * entry / risk
    n = len(c)
    end = min(i + 1 + HOLD, n)
    mfe_pct = 0.0
    for j in range(i + 1, end):
        mfe_pct = max(mfe_pct, h[j] / c[i] - 1)
        if o[j] <= cur:
            return (o[j] - entry) / risk - cost_R, mfe_pct
        if l[j] <= cur:
            return (cur - entry) / risk - cost_R, mfe_pct
        run_hi = max(run_hi, h[j])
        cur = max(cur, run_hi - CHAND * atr)
    return (c[end - 1] - entry) / risk - cost_R, mfe_pct


def main():
    df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
    df = df.sort_values(["ticker", "date"])
    meta = pd.read_parquet(POLY / "meta.parquet")
    cs = set(meta["ticker"]); active = dict(zip(meta["ticker"], meta["active"]))
    spy = df[df["ticker"] == "SPY"].sort_values("date").set_index("date")["close"]
    spy_ret60 = (spy / spy.shift(60) - 1).to_dict(); spy_c = spy.to_dict()
    spy_ma = (spy > spy.rolling(50).mean()).to_dict()

    rows = []
    g = df[df["ticker"].isin(cs)]
    for t, d in g.groupby("ticker", sort=False):
        if len(d) < 300:
            continue
        o = d["open"].to_numpy(); h = d["high"].to_numpy(); l = d["low"].to_numpy()
        c = d["close"].to_numpy(); v = d["volume"].to_numpy(); dts = d["date"].to_numpy()
        n = len(c); pc = np.roll(c, 1)
        tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
        atr = pd.Series(tr).rolling(14).mean().to_numpy()
        atr50 = pd.Series(tr).rolling(50).mean().to_numpy()
        ma50 = pd.Series(c).rolling(50).mean().to_numpy()
        hi20 = pd.Series(h).rolling(20).max().shift(1).to_numpy()
        lo20 = pd.Series(l).rolling(20).min().shift(1).to_numpy()
        hi252 = pd.Series(h).rolling(252).max().to_numpy()
        avgv = pd.Series(v).rolling(20).mean().shift(1).to_numpy()
        dvol = pd.Series(c * v).rolling(20).mean().shift(1).to_numpy()
        act = bool(active.get(t, False))
        for i in range(252, n - HOLD - 1):
            gap = o[i] / c[i - 1] - 1
            is_brk = c[i] > hi20[i] if not np.isnan(hi20[i]) else False
            if not (is_brk or gap >= 0.05):
                continue
            if c[i] < MIN_PRICE or np.isnan(dvol[i]) or dvol[i] < MIN_DVOL or np.isnan(atr[i - 1]) or atr[i - 1] <= 0:
                continue
            di = int(dts[i])
            R, mfe = tradeable(o, h, l, c, i, atr[i - 1])
            if np.isnan(R):
                continue
            rows.append({
                "ticker": t, "date": di, "active": act,
                "gap": gap, "is_brk": int(is_brk),
                "vol_spike": v[i] / avgv[i] if avgv[i] else np.nan,
                "ret_1m": c[i] / c[i - 21] - 1, "ret_3m": c[i] / c[i - 63] - 1,
                "ret_6m": c[i] / c[i - 126] - 1, "ret_12_1": c[i - 21] / c[i - 252] - 1,
                "rs_6m": (c[i] / c[i - 126] - 1) - (spy_ret60.get(di) or 0),
                "high52_prox": c[i] / hi252[i] if hi252[i] else np.nan,
                "atr_pct": atr[i - 1] / c[i] if c[i] else np.nan,
                "vol_contract": atr[i - 1] / atr50[i - 1] if atr50[i - 1] else np.nan,
                "base_width": (hi20[i] - lo20[i]) / c[i] if c[i] and not np.isnan(hi20[i]) else np.nan,
                "dist_ma50": c[i] / ma50[i] - 1 if ma50[i] else np.nan,
                "regime_up": int(bool(spy_ma.get(di))), "spy_ret60": spy_ret60.get(di) or 0,
                "log_price": np.log(c[i]), "log_dvol": np.log(dvol[i] + 1),
                # TARGETS
                "mfe": mfe, "trade_R": R,
                "expl30": int(mfe >= 0.30), "expl40": int(mfe >= 0.40),
                "expl50": int(mfe >= 0.50), "expl100": int(mfe >= 1.00),
            })
    S = pd.DataFrame(rows)
    S.to_parquet(OUT / "explosion_setups.parquet")
    print(f"thrust setups: {len(S):,} | tickers {S['ticker'].nunique():,} | {S['date'].min()}..{S['date'].max()} "
          f"| active {S['active'].mean()*100:.0f}%")
    print(f"  base explosion rates: >=30% {S['expl30'].mean()*100:.1f}%  >=40% {S['expl40'].mean()*100:.1f}%  "
          f">=50% {S['expl50'].mean()*100:.1f}%  >=100% {S['expl100'].mean()*100:.1f}%")
    print(f"  mean trade_R {S['trade_R'].mean():+.3f}  median mfe {S['mfe'].median()*100:.1f}%  "
          f"mean mfe {S['mfe'].mean()*100:.1f}%")
    by = S.groupby(S['date'] // 10000)['expl40'].mean() * 100
    print("  expl40 by year: " + " ".join(f"{y}:{v:.0f}%" for y, v in by.items()))


if __name__ == "__main__":
    main()
