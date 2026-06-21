"""FEASIBILITY (free, thin): express the VALIDATED earnings up-gap PEAD continuation as a long CALL,
on the 9 names whose options we already pulled. Reuses earnings_gap_v0's resolved events (no gap-detection
rebuild) + the offline option loaders from backtest_convex. Cache-only, no feed.

Mechanism check, NOT a verdict (n is small): does entering a call AFTER the gap (IV crush already done)
capture the +1.5%/20d drift net of premium/spread/theta? Compares call-return-on-premium vs the stock's
own move over the SAME window, with fat-tail + 'beats premium' stats. ATM and +5% OTM (more convex).

Run: THETA_CACHE_ONLY=1 backend\\.venv\\Scripts\\python.exe -u backtest_earnings_calls.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "options_signals_v0"))
os.environ.setdefault("THETA_CACHE_ONLY", "1")
import theta_store as TS  # noqa: E402
from gex_pull import _ymd  # noqa: E402

WINDOW = 49                       # MUST match pull_events.py so cache keys align
START_I, END_I = 20230101, 20260630


def monthly_exps(s_int, e_int):
    start = pd.Timestamp(str(s_int)); end = pd.Timestamp(str(e_int)) + pd.Timedelta(days=90)
    out, m = [], pd.Timestamp(year=start.year, month=start.month, day=1)
    while m <= end:
        fris = [d for d in pd.date_range(m, m + pd.offsets.MonthEnd(0)) if d.weekday() == 4]
        if len(fris) >= 3:
            xi = int(fris[2].strftime("%Y%m%d"))
            if s_int <= xi <= int(end.strftime("%Y%m%d")):
                out.append(xi)
        m = m + pd.offsets.MonthBegin(1)
    return out


def load_chain(t):
    """Offline (cache-only) monthly chain; per-exp window == pull_events.py so keys hit cache."""
    parts = []
    for exp in monthly_exps(START_I, END_I):
        s_k = max(START_I, _ymd(pd.Timestamp(str(exp)) - pd.Timedelta(days=WINDOW)))
        e_k = min(END_I, exp)
        if s_k > e_k:
            continue
        g = TS.fetch("bulk_hist/option/eod_greeks", root=t, exp=exp, start_date=s_k, end_date=e_k)
        if g is None or g.empty:
            continue
        g = g[["date", "strike", "right", "bid", "ask", "close", "underlying_price"]].copy()
        g["right"] = g["right"].astype(str).str.upper().str[0]
        g["exp"] = exp
        parts.append(g)
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True).drop_duplicates(["date", "exp", "strike", "right"])

NINE = ["SOFI", "AFRM", "RIOT", "ROKU", "DKNG", "PLTR", "MARA", "SIVB", "MSTR"]
FEAT = ROOT / "experiments" / "stock_strategies_v0" / "earnings_gap_v0" / "out" / "features.parquet"
WIN_LO, WIN_HI = 20230101, 20260301      # options-cache window
H_MAX = 10                               # shorter hold -> far less coverage bias on monthlies-only data
DTE_LO, DTE_HI = 16, 45                  # wider entry-day DTE band (must clear the hold before expiry)


def call_trade(chain_idx, dates, D, exitD, spot, otm):
    """Buy nearest-(1+otm)-strike call at D (ask), sell at exitD (bid). Returns (ret_on_premium, strike)."""
    exps = sorted({e for e in chain_idx.index.get_level_values("exp").unique()
                   if DTE_LO <= (pd.Timestamp(str(e)) - pd.Timestamp(str(D))).days <= DTE_HI
                   and pd.Timestamp(str(e)) > pd.Timestamp(str(exitD))})
    target = spot * (1 + otm)
    for exp in exps:
        try:
            sub = chain_idx.xs((D, exp), level=("date", "exp"))
        except KeyError:
            continue
        ks = sorted(sub.index.get_level_values("strike").unique(), key=lambda k: abs(k - target))
        for k in ks:
            try:
                ask = float(np.atleast_1d(chain_idx.loc[(D, exp, k, "C"), "ask"])[0])
                bid_x = float(np.atleast_1d(chain_idx.loc[(exitD, exp, k, "C"), "bid"])[0])
            except KeyError:
                continue
            if ask > 0.02:                                   # tradeable premium
                return (max(bid_x, 0.0) / ask - 1.0, k)
    return (None, None)


def run(otm):
    ev = pd.read_parquet(FEAT)
    ev = ev[ev["ticker"].isin(NINE)].copy()
    ev["entry_i"] = pd.to_datetime(ev["entry_dt"]).dt.strftime("%Y%m%d").astype(int)
    ev["exit_i"] = pd.to_datetime(ev["exit_dt"]).dt.strftime("%Y%m%d").astype(int)
    ev = ev[(ev["entry_i"] >= WIN_LO) & (ev["entry_i"] <= WIN_HI)].reset_index(drop=True)
    rows = []
    for t in sorted(ev["ticker"].unique()):
        chain = load_chain(t)
        if chain.empty:
            continue
        idx = chain.set_index(["date", "exp", "strike", "right"]).sort_index()
        dates = np.array(sorted(chain["date"].unique()))
        spot_by = chain.groupby("date")["underlying_price"].median()
        for _, e in ev[ev["ticker"] == t].iterrows():
            # snap entry to first cached trading date >= the event entry
            cand = dates[dates >= e["entry_i"]]
            if not len(cand):
                continue
            D = int(cand[0])
            i = int(np.where(dates == D)[0][0])
            exitD = int(dates[min(i + H_MAX, len(dates) - 1)])
            if int(e["exit_i"]) < exitD:                      # respect the strategy's own exit if sooner
                c2 = dates[dates >= e["exit_i"]]
                if len(c2):
                    exitD = int(min(exitD, c2[0]))
            spot = float(spot_by.get(D, np.nan))
            if not np.isfinite(spot) or exitD <= D:
                continue
            ret, k = call_trade(idx, dates, D, exitD, spot, otm)
            if ret is None:
                continue
            sret = float(spot_by.get(exitD, np.nan)) / spot - 1.0   # stock move over the SAME window
            rows.append({"ticker": t, "D": D, "exitD": exitD, "strike": k, "spot": spot,
                         "call_ret": ret, "stock_ret": sret, "x20": e.get("x20", np.nan),
                         "realized_r": e.get("realized_r", np.nan)})
    return pd.DataFrame(rows)


def stats(label, r):
    r = np.asarray(r, float); r = r[np.isfinite(r)]
    if len(r) < 3:
        return f"  {label:16} n={len(r)} (too few)"
    return (f"  {label:16} n={len(r):>3}  mean={r.mean():+.2f}  median={np.median(r):+.2f}  "
            f"win={np.mean(r>0):.0%}  max={r.max():+.2f}  >+1.0R={np.mean(r>1.0):.0%}  total={r.sum():+.1f}")


def main():
    for otm in (0.0, 0.05):
        df = run(otm)
        tag = "ATM call" if otm == 0 else "+5% OTM call"
        print(f"\n################ EARNINGS up-gap PEAD as a {tag} ({len(df)} events, 8 names, 2023-26) ################")
        if df.empty:
            print("  no usable events (option coverage gap)"); continue
        print(stats("CALL ret/premium", df["call_ret"]))
        print(stats("(stock move ref)", df["stock_ret"]))
        beat = df["call_ret"].mean() - 0.0
        print(f"  -> long calls {'MAKE' if df['call_ret'].mean()>0 else 'LOSE'} money on average "
              f"(mean {df['call_ret'].mean():+.1%} on premium); avg stock move {df['stock_ret'].mean():+.1%}")
        # per-ticker so we see if it's one name
        for t, g in df.groupby("ticker"):
            print(f"     {t:6} n={len(g):>2} call mean={g['call_ret'].mean():+.2f} stock mean={g['stock_ret'].mean():+.2%}")
    print("\nSNIFF TEST — thin n, in-sample, no holdout. Tells us: do post-gap calls dodge IV crush and "
          "capture the drift net of premium? A clear yes justifies the broad pull + Sharadar clean build.")


if __name__ == "__main__":
    main()
