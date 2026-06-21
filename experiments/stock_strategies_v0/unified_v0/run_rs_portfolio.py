"""Relative-strength long book — the momentum SURVIVOR built as a real strategy. Rank the clean
Polygon universe (delisted INCLUDED) by 12-1mo momentum each month-end, hold the strongest names
equal-weight, rebalance monthly, honest costs + turnover. Delisting is captured honestly: a held
name that craters/dies earns its final return then drops out (no survivorship lift). Benchmarked
vs SPY buy-and-hold. Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
COST_SIDE = 0.001          # 0.1% per side (liquid names)
MIN_PRICE, MIN_DVOL = 5.0, 5e6


def load_panels():
    df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
    df["dt"] = pd.to_datetime(df["date"].astype(int).astype(str), format="%Y%m%d")
    df["dvol"] = df["close"] * df["volume"]
    cs = set(pd.read_parquet(POLY / "meta.parquet")["ticker"])
    spy = (df[df["ticker"] == "SPY"].set_index("dt").resample("ME")["close"].last())
    me = df[df["ticker"].isin(cs)].groupby("ticker").resample("ME", on="dt").agg(
        close=("close", "last"), dvol=("dvol", "mean"))
    close = me["close"].unstack(0)
    dvol = me["dvol"].unstack(0)
    return close, dvol, spy


def metrics(rets: pd.Series, label: str, bench: pd.Series | None = None):
    rets = rets.dropna()
    if len(rets) < 12:
        print(f"  {label}: too few months"); return
    eq = (1 + rets).cumprod()
    yrs = len(rets) / 12
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    vol = rets.std() * np.sqrt(12)
    sharpe = rets.mean() / rets.std() * np.sqrt(12) if rets.std() else 0
    dd = (eq / eq.cummax() - 1).min()
    calmar = cagr / abs(dd) if dd else 0
    extra = ""
    if bench is not None:
        b = bench.reindex(rets.index).dropna()
        al = (rets.reindex(b.index) - b).mean() * 12
        extra = f"  alpha/yr {al*100:+5.1f}%"
    print(f"  {label:30s} CAGR {cagr*100:+6.1f}%  vol {vol*100:4.0f}%  Sharpe {sharpe:+.2f}  "
          f"maxDD {dd*100:5.0f}%  Calmar {calmar:+.2f}{extra}")


def backtest(close, dvol, trail, fwd, liq, n_hold=None, decile=False, spy_trend=None, label=""):
    months = close.index
    held_prev, rets, turn = set(), [], []
    idx = []
    for k, t in enumerate(months):
        tr, fr, lq = trail.loc[t], fwd.loc[t], liq.loc[t]
        ok = tr.notna() & fr.notna() & lq
        if ok.sum() < 20 or pd.isna(fr).all():
            continue
        cash = spy_trend is not None and not bool(spy_trend.get(t, True))
        if cash:
            held = set()
        else:
            ranked = tr[ok].sort_values(ascending=False)
            k_n = max(10, int(ok.sum() * 0.1)) if decile else min(n_hold, len(ranked))
            held = set(ranked.index[:k_n])
        r = fwd.loc[t, list(held)].mean() if held else 0.0
        changed = len(held ^ held_prev)
        denom = max(len(held), len(held_prev), 1)
        to = changed / denom
        rets.append(r - to * COST_SIDE)
        turn.append(to); idx.append(t); held_prev = held
    s = pd.Series(rets, index=pd.DatetimeIndex(idx))
    s.attrs["turnover"] = np.mean(turn) * 12
    return s


def main():
    close, dvol, spy = load_panels()
    print(f"universe {close.shape[1]:,} names x {close.shape[0]} months "
          f"({close.index[0].date()}..{close.index[-1].date()})")
    trail = close.shift(1) / close.shift(12) - 1
    fwd = close.shift(-1) / close - 1
    liq = (close >= MIN_PRICE) & (dvol >= MIN_DVOL)
    spy_ret = spy / spy.shift(1) - 1
    spy_above = (spy > spy.rolling(10).mean())

    print(f"\navg eligible names/mo: {int(liq.sum(1).mean()):,} | cost {COST_SIDE*100:.1f}%/side\n")
    print("=== relative-strength long book (12-1mo momentum, monthly rebalance) ===")
    configs = [
        ("top decile (ew)", dict(decile=True)),
        ("top 50 names (ew)", dict(n_hold=50)),
        ("top 30 names (ew)", dict(n_hold=30)),
        ("top 50 + SPY-trend filter", dict(n_hold=50, spy_trend=spy_above.to_dict())),
    ]
    series = {}
    for name, kw in configs:
        s = backtest(close, dvol, trail, fwd, liq, label=name, **kw)
        series[name] = s
        metrics(s, name + f" [turn {s.attrs['turnover']*100:.0f}%/yr]", bench=spy_ret)
    print()
    metrics(spy_ret.reindex(series["top 50 names (ew)"].index), "SPY buy & hold (benchmark)")

    print("\n=== by-year total return (top 50 ew vs SPY) ===")
    t50, sp = series["top 50 names (ew)"], spy_ret
    for y in range(t50.index[0].year, t50.index[-1].year + 1):
        a = (1 + t50[t50.index.year == y]).prod() - 1
        b = (1 + sp[sp.index.year == y]).prod() - 1
        print(f"  {y}: RS {a*100:+6.1f}%   SPY {b*100:+6.1f}%   excess {(a-b)*100:+5.1f}%")
    print("\nREAD: alpha/yr>0 and Calmar>SPY => the RS book adds over just owning the index.")


if __name__ == "__main__":
    main()
