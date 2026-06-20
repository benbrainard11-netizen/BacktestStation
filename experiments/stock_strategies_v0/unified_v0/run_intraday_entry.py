"""Survivorship-CLEAN intraday breakout test. The daily-bar verdict was: breakout CONTINUATION
reverts (top decile market-relative negative). But that used a wide daily-low stop. The open
question is R-GEOMETRY: a 1-min entry AT the breakout-level cross + a TIGHT (ATR) stop +
let-it-run gives small losses when wrong and big wins when it runs. Does that asymmetry turn
the negative drift into positive R? Tested on the clean Polygon minute pull (delisted INCLUDED).

Entry  = stop-buy at the prior-20d-high level (intraday cross), honest fill (gap-over -> open).
Stop   = entry - k*ATR14 (ATR-based => no tiny-risk inflation trap). Same-day stop checked on
         the minute bars; thereafter tracked on DAILY bars (stop wins ties, gap-through at open).
Exit   = chandelier trail (let runners run) OR fixed R target, max_hold cap. Costs both sides.
Run with backend\\.venv\\Scripts\\python.exe.
"""

from __future__ import annotations

from datetime import time as T
from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
MIN = POLY / "minute"
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

# --- economics / mechanic knobs ---
BUF_ENTRY = 0.001  # stop-buy 10bps above the breakout level
FRICTION = 0.0015  # commission+slippage per side (small caps, dvol>1e6)
K_ATR = 1.0  # initial stop distance in ATR14
CHAND = 3.0  # chandelier trail = run_high - CHAND*ATR
MAX_HOLD = 40
RTH0, RTH1 = T(9, 30), T(16, 0)


def load_daily():
    # Scope to the setup tickers before building per-ticker arrays: the daily now spans 2016-2026 /
    # ~25k tickers (incl ETFs/warrants), and building arrays + an idx dict for ALL of them OOMs. The
    # backtest only touches setup tickers (run_setup returns None otherwise), so this is a pure memory
    # optimization -- no behavior change.
    keep = set(pd.read_parquet(POLY / "minute_sample_manifest.parquet")["ticker"])
    df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
    df = df[df["ticker"].isin(keep)].sort_values(["ticker", "date"])
    d = {}
    for t, g in df.groupby("ticker", sort=False):
        c = g["close"].to_numpy()
        h = g["high"].to_numpy()
        lo = g["low"].to_numpy()
        o = g["open"].to_numpy()
        dts = g["date"].to_numpy()
        pc = np.roll(c, 1)
        tr = np.maximum(h - lo, np.maximum(np.abs(h - pc), np.abs(lo - pc)))
        atr = pd.Series(tr).rolling(14).mean().to_numpy()
        hi20 = pd.Series(h).rolling(20).max().shift(1).to_numpy()
        d[t] = dict(
            o=o, h=h, l=lo, c=c, dt=dts, atr=atr, hi20=hi20, idx={int(x): i for i, x in enumerate(dts)}
        )
    return d


def minute_rth(tkr, date, daily_open):
    fp = MIN / f"{tkr}__{int(date)}.parquet"
    if not fp.exists():
        return None
    m = pd.read_parquet(fp)
    if not len(m):
        return None
    et = pd.to_datetime(m["t"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    rth = m[(et.dt.time >= RTH0) & (et.dt.time < RTH1)].reset_index(drop=True)
    if not len(rth):
        return None
    fac = daily_open / rth["o"].iloc[0] if rth["o"].iloc[0] else 1.0  # reconcile at the OPEN (causal)
    if not (0.5 < fac < 2.0):
        fac = 1.0
    return rth[["o", "h", "l", "c"]].to_numpy() * fac


def forward_daily(D, i, entry, stop, atr, target_R=None):
    """Track from day i+1 on daily bars. Returns (R, reason, days, mfe_R)."""
    risk = entry - stop
    o, h, l, c = D["o"], D["h"], D["l"], D["c"]
    cur, run_hi, mfe = stop, entry, 0.0
    n = len(c)
    for j in range(i + 1, min(i + 1 + MAX_HOLD, n)):
        mfe = max(mfe, (h[j] - entry) / risk)
        if o[j] <= cur:  # gap through stop at open
            return (o[j] - entry) / risk, "gap_stop", j - i, mfe
        if l[j] <= cur:
            return (cur - entry) / risk, "stop", j - i, mfe
        if target_R is not None:
            tgt = entry + target_R * risk
            if h[j] >= tgt:
                fill = o[j] if o[j] >= tgt else tgt  # gap through target -> open
                return (fill - entry) / risk, "target", j - i, mfe
        run_hi = max(run_hi, h[j])
        cur = max(cur, run_hi - CHAND * atr)  # chandelier ratchet
    return (c[min(i + MAX_HOLD, n - 1)] - entry) / risk, "maxhold", min(MAX_HOLD, n - 1 - i), mfe


def run_setup(D, tkr, date, target_R=None):
    if tkr not in D:
        return None
    i = D[tkr]["idx"].get(int(date))
    if i is None or i < 21 or i >= len(D[tkr]["c"]) - 1:
        return None
    L = D[tkr]["hi20"][i]
    atr = D[tkr]["atr"][i - 1]  # causal: ATR through the PRIOR day only (day i range unknown at entry)
    do = D[tkr]["o"][i]
    if np.isnan(L) or np.isnan(atr) or atr <= 0:
        return None
    bars = minute_rth(tkr, date, do)
    if bars is None:
        return None
    trig = L * (1 + BUF_ENTRY)
    cross = np.where(bars[:, 1] >= trig)[0]  # high >= trigger
    if not len(cross):
        return None
    k = cross[0]
    entry = max(trig, bars[k, 0]) * (1 + FRICTION)  # gap-over -> bar open; +slip
    stop = entry - K_ATR * atr
    risk = entry - stop
    cost_R = FRICTION * entry / risk  # exit side only; the entry side is already in the (1+FRICTION) fill
    # same-day stop on the minute bars AFTER entry
    for r in range(k + 1, len(bars)):
        if bars[r, 2] <= stop:  # low <= stop
            fill = min(stop, bars[r, 0])
            return dict(
                tkr=tkr, date=int(date), R=(fill - entry) / risk - cost_R, reason="stop_d0", days=0, mfe=0.0
            )
    R, reason, days, mfe = forward_daily(D[tkr], i, entry, stop, atr, target_R)
    return dict(tkr=tkr, date=int(date), R=R - cost_R, reason=reason, days=days, mfe=mfe)


def summarize(df, label):
    R = df["R"].to_numpy()
    win = (R > 0).mean() * 100
    stopd0 = (df["reason"] == "stop_d0").mean() * 100
    p = np.percentile(R, [5, 50, 95])
    print(
        f"  {label:22s} n={len(df):6d}  meanR {R.mean():+.3f}  medR {p[1]:+.2f}  "
        f"win {win:4.1f}%  d0-stop {stopd0:4.1f}%  p95 {p[2]:+.1f}  maxR {R.max():+.1f}  totR {R.sum():+.0f}"
    )


def main():
    print("loading daily...")
    D = load_daily()
    samp = pd.read_parquet(POLY / "minute_sample_manifest.parquet")
    print(f"setups in sample: {len(samp):,}\n")

    # primary: chandelier let-run
    res = [run_setup(D, t, d) for t, d in zip(samp["ticker"], samp["date"])]
    res = [r for r in res if r is not None]
    R = pd.DataFrame(res)
    act = set(samp[samp["active"]]["ticker"])
    R["active"] = R["tkr"].isin(act)
    R["yr"] = R["date"] // 10000
    R.to_parquet(OUT / "intraday_entry_results.parquet")

    print(f"=== INTRADAY breakout entry (1m level-cross) + {K_ATR}xATR stop + chandelier let-run ===")
    print(f"   ({len(R):,} of {len(samp):,} setups had usable minute+daily)\n")
    summarize(R, "ALL")
    summarize(R[R.active], "active only")
    summarize(R[~R.active], "DELISTED only")
    print()
    for y in sorted(R["yr"].unique()):
        summarize(R[R.yr == y], f"year {y}")

    print("\n=== exit-rule grid (ALL setups) ===")
    summarize(R, "chandelier(3xATR)")
    for tr in (3, 5, 10):
        rr = [run_setup(D, t, d, target_R=tr) for t, d in zip(samp["ticker"], samp["date"])]
        rr = pd.DataFrame([x for x in rr if x is not None])
        summarize(rr, f"fixed target {tr}R")

    print("\n=== cost sensitivity (chandelier, meanR) ===")
    base = R["R"]
    print(f"  as-run friction {FRICTION*100:.2f}%/side -> meanR {base.mean():+.3f}")

    print("\n=== runner check (MFE = max favorable R before exit) ===")
    mfe = R["mfe"]
    print(
        f"  median MFE {mfe.median():+.1f}R | p90 {mfe.quantile(.9):+.1f}R | p99 {mfe.quantile(.99):+.1f}R "
        f"| >=10R {(mfe>=10).mean()*100:.1f}% | >=20R {(mfe>=20).mean()*100:.1f}%"
    )
    print("\nREAD: meanR>0 (esp. DELISTED-included) => tight-stop intraday geometry rescues breakouts;")
    print(
        "meanR<=0 across exits => the breakout edge is dead even with ideal entry/stop. d0-stop% = chop rate."
    )


if __name__ == "__main__":
    main()
