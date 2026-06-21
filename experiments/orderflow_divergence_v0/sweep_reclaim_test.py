"""Confirmed-sweep RECLAIM test — the faithful PO3 trade, tested honestly.

The user's correction to the strawman exhaustion test: don't enter at a fixed time after a RAW penetration
with a SYMMETRIC stop. Instead --
  1. CONFIRM the sweep: price wicks below a prior swing-low then CLOSES BACK ABOVE it (rejection / judas
     reversal) within K minutes. Only confirmed reclaims are traded (raw breakdowns that never reclaim = no
     trade -- that's the strategy, not a bias).
  2. Enter at the RECLAIM bar close (a real price near the low). Stop = just below the wick low (TIGHT).
     Target = ASYMMETRIC expansion (M x risk). Even a sub-50% win rate pays if M is big enough.
  3. Confirm EARLY (small K) so most of the expansion is still ahead of the entry.
Then: does ORDER FLOW at the reclaim FILTER to the better trades?

Honest-fill discipline: reclaim/entry/stop known at the reclaim bar; forward sim starts the NEXT bar; within
a bar STOP WINS ties (conservative, repo rule #8). Costs charged in R per trade (cost_ticks / risk_ticks).

Run: backend/.venv/Scripts/python.exe experiments/orderflow_divergence_v0/sweep_reclaim_test.py --symbol ZN.c.0
"""
from __future__ import annotations

import argparse
import glob
from pathlib import Path

import numpy as np
import pandas as pd

OFI = Path(__file__).resolve().parent / "out" / "event_ofi"
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10,
        "ZN.c.0": 1 / 64, "ZB.c.0": 1 / 32, "CL.c.0": 0.01}
CUT = pd.Timestamp("2026-02-15", tz="UTC")
LB, K, N = 60, 15, 120          # prior-low lookback (min), max bars to reclaim (confirm early), max holding (min)
M_LIST = (1.0, 2.0, 3.0)        # asymmetric target multiples of risk
TRAIL = 1.0                     # trailing-stop distance in R (let winners run -> capture the fat tail)


def minute_bars(sym: str) -> pd.DataFrame:
    fs = sorted(glob.glob(str(OFI / sym / "*.parquet")))
    df = pd.concat([pd.read_parquet(f, columns=["ts", "mid", "signed", "volume"]) for f in fs], ignore_index=True)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.set_index("ts").sort_index().dropna(subset=["mid"])
    df = df[~df.index.duplicated(keep="first")]
    g = df.resample("1min", label="right", closed="right")
    return pd.DataFrame({"o": g["mid"].first(), "h": g["mid"].max(), "l": g["mid"].min(), "c": g["mid"].last(),
                         "net": g["signed"].sum(), "vol": g["volume"].sum()}).dropna(subset=["c"])


def simulate(sym: str, entry_mode: str = "reclaim", wr: int = 30, lb: int = LB, k: int = K, hold: int = N):
    tick = TICK[sym]
    b = minute_bars(sym)
    lvl = b["l"].rolling(lb, min_periods=lb // 2).min().shift(1).to_numpy()
    h, l, c = b["h"].to_numpy(), b["l"].to_numpy(), b["c"].to_numpy()
    net, vol = b["net"].to_numpy(), b["vol"].to_numpy()
    ts = b.index.to_numpy()
    n = len(b)
    pen = l < lvl
    fresh = pen & ~np.r_[False, pen[:-1]]
    starts = np.where(fresh & ~np.isnan(lvl))[0]

    trades = []
    for t0 in starts:
        L = lvl[t0]
        t_end = min(t0 + k, n - 1)
        t_r = next((t for t in range(t0, t_end + 1) if c[t] > L), -1)   # first close back above the level
        if t_r < 0:
            continue                                                    # never reclaimed -> real breakdown, no trade
        wick_low = l[t0:t_r + 1].min()
        stop = wick_low - tick                                          # tight, 1 tick below the wick
        if entry_mode == "retrace":                                    # limit BACK at the reclaimed level (better price, no cross)
            e_idx = next((t for t in range(t_r + 1, min(t_r + wr, n - 1) + 1) if l[t] <= L), -1)
            if e_idx < 0:
                continue                                               # never retraced -> missed fill (the tradeoff)
            entry = L
        else:                                                          # market at the reclaim close
            e_idx, entry = t_r, c[t_r]
        risk = entry - stop
        if risk <= 0:
            continue
        end = min(e_idx + hold, n - 1)
        res, unresolved, mfe = {}, set(M_LIST), 0.0
        peak, tstop, r_trail = entry, stop, None
        if entry_mode == "retrace" and l[e_idx] <= stop:               # filled then stopped same bar (conservative)
            res = {M: -1.0 for M in M_LIST}
            unresolved, r_trail = set(), -1.0
        for t in range(e_idx + 1, end + 1):
            mfe = max(mfe, (h[t] - entry) / risk)
            if r_trail is None and l[t] <= tstop:                      # trailing-stop exit (stop-first, conservative)
                r_trail = (tstop - entry) / risk
            if unresolved:                                             # fixed-target exits (parallel bookkeeping)
                if l[t] <= stop:
                    for M in unresolved:
                        res[M] = -1.0
                    unresolved = set()
                else:
                    hit = {M for M in unresolved if h[t] >= entry + M * risk}
                    for M in hit:
                        res[M] = M
                    unresolved -= hit
            peak = max(peak, h[t])                                     # ratchet the trail AFTER exit checks
            tstop = max(tstop, peak - TRAIL * risk)
            if r_trail is not None and not unresolved:
                break
        if r_trail is None:
            r_trail = (c[end] - entry) / risk                          # time exit
        for M in unresolved:
            res[M] = (c[end] - entry) / risk
        trades.append({"date": pd.Timestamp(ts[t_r]), "risk_tk": risk / tick, "risk_pts": risk, "lag": e_idx - t0,
                       "recl_flow": net[t_r], "wick_absorp": vol[t0:t_r + 1].sum() / ((h[t0:t_r + 1].max() - wick_low) / tick + 1),
                       "mfe": mfe, "Rtrail": r_trail, **{f"R{M}": res[M] for M in M_LIST}})
    return pd.DataFrame(trades), len(starts)


def expectancy(tdf, M, cost_ticks):
    r = tdf[f"R{M}"].to_numpy() - cost_ticks / tdf["risk_tk"].to_numpy()   # net R after cost
    win = (tdf[f"R{M}"].to_numpy() > 0).mean()
    return r.mean(), win, len(tdf)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--cost-ticks", type=float, default=2.0)
    ap.add_argument("--entry", choices=["reclaim", "retrace"], default="reclaim")
    ap.add_argument("--retrace-window", type=int, default=30)
    ap.add_argument("--lb", type=int, default=LB, help="prior-low lookback in min (level size: 60=intraday, 1440=~day)")
    ap.add_argument("--k", type=int, default=K, help="max min to reclaim")
    ap.add_argument("--hold", type=int, default=N, help="max holding min (capture the whole move)")
    a = ap.parse_args(argv)
    tdf, n_starts = simulate(a.symbol, a.entry, a.retrace_window, a.lb, a.k, a.hold)
    if tdf.empty:
        print(f"{a.symbol}: no trades"); return 0
    te = tdf[tdf["date"] >= CUT]
    print(f"{a.symbol} [{a.entry} lb{a.lb}/k{a.k}/hold{a.hold}]: penetrations {n_starts:,} -> filled {len(tdf):,} "
          f"(fill rate {len(tdf)/max(n_starts,1):.2f}); OOS trades {len(te):,}  median reclaim lag {te['lag'].median():.0f}min")
    mfe_pts = te["mfe"] * te["risk_pts"]
    print(f"  SCALE (points): median stop {te['risk_pts'].median():.1f}  |  MFE-pts median {mfe_pts.median():.1f}  "
          f"75th {mfe_pts.quantile(.75):.1f}  90th {mfe_pts.quantile(.90):.1f}  max {mfe_pts.max():.0f}")
    print(f"  MFE (R, uncapped over hold): median {te['mfe'].median():.2f}  75th {te['mfe'].quantile(.75):.2f}  "
          f"90th {te['mfe'].quantile(.90):.2f}  -> how big do expansions get vs the tight stop")
    print(f"  -- OOS expectancy per target (net of {a.cost_ticks}tk cost) --")
    for M in M_LIST:
        er, win, n = expectancy(te, M, a.cost_ticks)
        print(f"    target {M:.0f}R: win={win:.3f}  E[R/trade]={er:+.3f}  total={er*n:+.1f}R  (n={n})")
    rt = te["Rtrail"].to_numpy() - a.cost_ticks / te["risk_tk"].to_numpy()
    wins = te.loc[te["Rtrail"] > 0, "Rtrail"]
    print(f"    TRAIL {TRAIL:.0f}R: win={(te['Rtrail'].to_numpy()>0).mean():.3f}  E[R/trade]={rt.mean():+.3f}  "
          f"total={rt.sum():+.1f}R  avgWin={wins.mean():.2f}R  maxWin={wins.max():.1f}R  (let winners run)")
    # STABILITY: trailing-1R expectancy by month over the FULL history (rule-based, nothing trained ->
    # every month is a valid OOS check; consistent sign = real, one-month spike = noise/overfit-by-search).
    full = tdf.copy()
    full["ym"] = full["date"].dt.tz_localize(None).dt.to_period("M").astype(str)
    print(f"  -- TRAIL {TRAIL:.0f}R expectancy BY MONTH (full history, stability check) --")
    pos = 0
    months = sorted(full["ym"].unique())
    for ym in months:
        g = full[full["ym"] == ym]
        rr = g["Rtrail"].to_numpy() - a.cost_ticks / g["risk_tk"].to_numpy()
        if len(g) >= 15:
            pos += rr.mean() > 0
            print(f"    {ym}: n={len(g):4d}  E[R]={rr.mean():+.3f}")
    print(f"  -> {pos}/{len([m for m in months if len(full[full['ym']==m])>=15])} months positive")
    # does order flow at the reclaim FILTER to better trades? (buy-flow reclaim vs sell-flow)
    print(f"  -- flow filter (reclaim-bar net signed > 0 = buyers confirm) @ target 2R --")
    for lab, sub in [("buy-flow reclaim", te[te["recl_flow"] > 0]), ("sell-flow reclaim", te[te["recl_flow"] <= 0])]:
        if len(sub) > 40:
            er, win, n = expectancy(sub, 2.0, a.cost_ticks)
            print(f"    {lab:18} win={win:.3f}  E[R/trade]={er:+.3f}  (n={n})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
