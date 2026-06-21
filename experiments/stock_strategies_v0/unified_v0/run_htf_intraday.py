"""Strict-HTF intraday test (the one breakout stone unturned). Our prior intraday test used the
BROAD 20d-high break (mostly noise). This runs the REAL PDF high-tight-flag setup at intraday
resolution across a broad->mid->strict ladder, with the SAME honest mechanic AND the decisive
null control: does an HTF day beat a RANDOM non-HTF day for the same names? If even the strictest
tier can't beat the random-day baseline, breakouts are dead at every strictness.
Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import run_intraday_entry as rie   # minute_rth, forward_daily, BUF_ENTRY, FRICTION, K_ATR, MAX_HOLD

POLY = Path(r"D:\data\processed\stocks\polygon")
HERE = Path(__file__).resolve().parent
CAND = pd.read_parquet(HERE / "out" / "htf_candidates.parquet")
RNG = np.random.default_rng(0)


def load_daily(tickers):
    df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
    df = df[df["ticker"].isin(tickers)].sort_values(["ticker", "date"])
    D = {}
    for t, g in df.groupby("ticker", sort=False):
        o, h, l, c = (g[x].to_numpy() for x in ("open", "high", "low", "close"))
        dts = g["date"].to_numpy(); pc = np.roll(c, 1)
        tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
        atr = pd.Series(tr).rolling(14).mean().to_numpy()
        D[t] = dict(o=o, h=h, l=l, c=c, atr=atr, idx={int(x): i for i, x in enumerate(dts)})
    return D


def run_intraday(D, row, target_R=None):
    """Intraday: enter at the stored breakout LEVEL cross, stop = entry - 1*ATR_prev."""
    t, date = row.ticker, int(row.date)
    d = D.get(t)
    if d is None:
        return None
    i = d["idx"].get(date)
    if i is None or i < 1 or i >= len(d["c"]) - 1:
        return None
    atr = row.atr_prev
    bars = rie.minute_rth(t, date, d["o"][i])
    if bars is None:
        return None
    trig = row.level * (1 + rie.BUF_ENTRY)
    cr = np.where(bars[:, 1] >= trig)[0]
    if not len(cr):
        return None
    k = cr[0]
    entry = max(trig, bars[k, 0]) * (1 + rie.FRICTION)
    stop = entry - rie.K_ATR * atr
    risk = entry - stop
    cost_R = 2 * rie.FRICTION * entry / risk
    for r in range(k + 1, len(bars)):
        if bars[r, 2] <= stop:
            return (min(stop, bars[r, 0]) - entry) / risk - cost_R
    R, *_ = rie.forward_daily(d, i, entry, stop, atr, target_R)
    return R - cost_R


def daily_mech(D, t, i):
    """Apples-to-apples daily mechanic (for the null control): enter day i+1 open, stop=1*ATR[i]."""
    d = D.get(t)
    if d is None or i < 0 or i + 1 >= len(d["c"]):
        return None
    atr = d["atr"][i]
    if np.isnan(atr) or atr <= 0:
        return None
    entry = d["o"][i + 1] * (1 + rie.FRICTION)
    stop = entry - rie.K_ATR * atr
    risk = entry - stop
    if risk <= 0:
        return None
    cost_R = 2 * rie.FRICTION * entry / risk
    R, *_ = rie.forward_daily(d, i, entry, stop, atr)
    return R - cost_R


def boot_mean(x, n=2000):
    x = np.asarray(x); idx = RNG.integers(0, len(x), (n, len(x)))
    m = x[idx].mean(1)
    return np.percentile(m, [2.5, 97.5])


def name_block_delta(cand_by_t, rand_by_t, n=2000):
    """Bootstrap 95% CI on (cand meanR - rand meanR), resampling TICKERS."""
    ts = list(cand_by_t)
    deltas = []
    for _ in range(n):
        pick = RNG.choice(len(ts), len(ts))
        cv = np.concatenate([cand_by_t[ts[j]] for j in pick])
        rv = np.concatenate([rand_by_t[ts[j]] for j in pick])
        deltas.append(cv.mean() - rv.mean())
    return np.percentile(deltas, [2.5, 97.5])


def main():
    D = load_daily(set(CAND["ticker"]) | {"SPY"})
    print(f"HTF candidates {len(CAND):,} | tickers {CAND['ticker'].nunique():,}\n")

    # --- intraday R by tier ---
    CAND["Ri"] = [run_intraday(D, r) for r in CAND.itertuples(index=False)]
    CAND["Ri5"] = [run_intraday(D, r, target_R=5) for r in CAND.itertuples(index=False)]
    R = CAND.dropna(subset=["Ri"]).copy()
    print("=== INTRADAY R (level-cross entry + 1xATR stop + chandelier let-run), by strictness ===")
    for name, sub in [("LOOSE (all)", R), ("MID", R[R.is_mid]), ("STRICT", R[R.is_strict])]:
        if len(sub) < 5:
            print(f"  {name:14s} n={len(sub)} (too few)"); continue
        ci = boot_mean(sub["Ri"].to_numpy())
        de = sub[~sub.active]
        print(f"  {name:14s} n={len(sub):5d}  meanR {sub.Ri.mean():+.3f}  95%CI [{ci[0]:+.3f},{ci[1]:+.3f}]  "
              f"win {(sub.Ri>0).mean()*100:4.1f}%  5R-tgt {sub.Ri5.mean():+.3f}  "
              f"delisted {de.Ri.mean():+.3f}(n{len(de)})")

    # --- NULL CONTROL: HTF day vs random non-HTF day, identical DAILY mechanic ---
    print("\n=== NULL CONTROL: HTF days vs RANDOM non-HTF days (same ticker, same daily mechanic) ===")
    cand_days = {t: set(g["date"].astype(int)) for t, g in CAND.groupby("ticker")}
    for name, sub in [("LOOSE", CAND), ("MID", CAND[CAND.is_mid]), ("STRICT", CAND[CAND.is_strict])]:
        cand_by_t, rand_by_t = {}, {}
        for t, g in sub.groupby("ticker"):
            d = D.get(t)
            if d is None:
                continue
            cR = [daily_mech(D, t, d["idx"][int(dt)]) for dt in g["date"] if int(dt) in d["idx"]]
            cR = [x for x in cR if x is not None]
            n = len(d["c"])
            avail = [j for j in range(60, n - 41) if int(d_date(d, j)) not in cand_days[t]]
            if not cR or len(avail) < 3:
                continue
            rsel = RNG.choice(avail, min(3 * len(cR), len(avail)), replace=False)
            rR = [daily_mech(D, t, j) for j in rsel]
            rR = [x for x in rR if x is not None]
            if rR:
                cand_by_t[t] = np.array(cR); rand_by_t[t] = np.array(rR)
        cv = np.concatenate(list(cand_by_t.values())); rv = np.concatenate(list(rand_by_t.values()))
        ci = name_block_delta(cand_by_t, rand_by_t)
        print(f"  {name:7s} HTF(daily) {cv.mean():+.3f} (n{len(cv)})  vs random {rv.mean():+.3f} (n{len(rv)})  "
              f"DELTA {cv.mean()-rv.mean():+.3f}  95%CI [{ci[0]:+.3f},{ci[1]:+.3f}]")
    print("\nREAD: STRICT meanR CI above 0 AND null DELTA CI above 0 => HTF selection adds real edge.")
    print("CI spans 0 / negative => breakouts dead even as the strict PDF setup.")


def d_date(d, j):
    # reverse the idx map cheaply: store once
    if "_rev" not in d:
        d["_rev"] = {v: k for k, v in d["idx"].items()}
    return d["_rev"][j]


if __name__ == "__main__":
    main()
