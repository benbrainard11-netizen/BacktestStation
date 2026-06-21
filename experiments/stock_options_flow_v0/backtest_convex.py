"""Honest convex straddle backtest — the v2 expression engine (the 'huge wins' test).

Thesis: when dealers are SHORT gamma (gex_proxy < 0), moves get amplified → vol expands → owning
convexity (a long ATM straddle) pays. Long options bleed to the vol-risk-premium, so the gamma gate
must BEAT unconditional straddle-buying, not merely be positive.

HONEST RULES (CLAUDE.md rule 8 spirit, options edition):
  - Decide on day D from walls[D] (EOD chain). Enter ATM straddle paying the ASK on both legs at D close.
  - Exit H trading days later selling the BID on both legs (theta paid automatically; no cherry-pick).
  - Causal: only data <= D for the decision; fills cross the spread; no post-hoc strike/expiry choice
    (nearest-ATM, nearest monthly with DTE in [DTE_LO, DTE_HI]).
  - Report regime-gated vs UNCONDITIONAL vs RANDOM, plus fragility (top-5-trade share). Holdout-sealed.

Run: THETA_CACHE_ONLY=1 backend\\.venv\\Scripts\\python.exe -u backtest_convex.py [NAMES...]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "options_signals_v0"))
os.environ.setdefault("THETA_CACHE_ONLY", "1")
import theta_store as TS  # noqa: E402
from gex_pull import _ymd  # noqa: E402

WALLS = ROOT / "experiments" / "options_signals_v0" / "out"
START, END, WINDOW = "2023-01-01", "2026-06-30", 35
HOLDOUT_START = 20250701       # SEALED boundary
HOLDOUT_READ = os.environ.get("HOLDOUT_READ") == "1"  # =1 reads >= boundary (the ONE registered verdict)
H = 5                          # holding period, trading days
DTE_LO, DTE_HI = 15, 45        # so D+H stays inside the chosen expiration's life
ATM_TOL = 0.06                 # strike within 6% of spot counts as ATM-candidate


def monthly_exps(s_int: int, e_int: int) -> list[int]:
    """3rd-Friday monthly expirations over [start, end+90d], generated LOCALLY (no terminal call —
    so cache-only analysis stays fully offline while a pull holds the terminal)."""
    start = pd.Timestamp(str(s_int))
    end = pd.Timestamp(str(e_int)) + pd.Timedelta(days=90)
    out, m = [], pd.Timestamp(year=start.year, month=start.month, day=1)
    while m <= end:
        fris = [d for d in pd.date_range(m, m + pd.offsets.MonthEnd(0)) if d.weekday() == 4]
        if len(fris) >= 3:
            xi = int(fris[2].strftime("%Y%m%d"))
            if s_int <= xi <= int(end.strftime("%Y%m%d")):
                out.append(xi)
        m = m + pd.offsets.MonthBegin(1)
    return out


def load_chain(t: str) -> pd.DataFrame:
    s, e = _ymd(START), _ymd(END)
    exps = monthly_exps(s, e)
    parts = []
    for exp in exps:
        e_ts = pd.Timestamp(str(exp))
        s_k, e_k = max(s, _ymd(e_ts - pd.Timedelta(days=WINDOW))), min(e, exp)
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


def straddle_trades(t: str) -> pd.DataFrame:
    chain = load_chain(t)
    if chain.empty:
        return pd.DataFrame()
    wf = WALLS / f"walls_{t.lower()}.parquet"
    if not wf.exists():
        return pd.DataFrame()
    walls = pd.read_parquet(wf)[["date", "gex_proxy"]]
    # index for fast lookup: (date, exp, strike, right) -> bid/ask
    chain = chain.set_index(["date", "exp", "strike", "right"]).sort_index()
    dates = np.array(sorted(chain.index.get_level_values("date").unique()))
    gex = dict(zip(walls["date"].astype(int), walls["gex_proxy"].astype(float)))
    spot_by_date = (chain["underlying_price"].groupby(level="date").median())

    rows = []
    for i, D in enumerate(dates):
        in_window = (D >= HOLDOUT_START) if HOLDOUT_READ else (D < HOLDOUT_START)
        if not in_window or D not in gex:
            continue
        # exit date = H trading positions later, within the cached date grid
        if i + H >= len(dates):
            continue
        Dx = dates[i + H]
        spot = float(spot_by_date.get(D, np.nan))
        if not np.isfinite(spot):
            continue
        # pick nearest monthly expiration with DTE in window on D
        d_ts = pd.Timestamp(str(D))
        cand = sorted({e for e in chain.index.get_level_values("exp").unique()
                       if DTE_LO <= (pd.Timestamp(str(e)) - d_ts).days <= DTE_HI
                       and pd.Timestamp(str(e)) > pd.Timestamp(str(Dx))})
        if not cand:
            continue
        exp = cand[0]
        # ATM strike present as BOTH call & put on D and Dx, with valid quotes
        try:
            sub = chain.xs((D, exp), level=("date", "exp"))
        except KeyError:
            continue
        ks = sub.index.get_level_values("strike").unique()
        ks = [k for k in ks if abs(k - spot) / spot <= ATM_TOL]
        best = None
        for k in sorted(ks, key=lambda k: abs(k - spot)):
            try:
                ca, pa = chain.loc[(D, exp, k, "C"), "ask"], chain.loc[(D, exp, k, "P"), "ask"]
                cb2, pb2 = chain.loc[(Dx, exp, k, "C"), "bid"], chain.loc[(Dx, exp, k, "P"), "bid"]
            except KeyError:
                continue
            ca, pa = float(np.atleast_1d(ca)[0]), float(np.atleast_1d(pa)[0])
            cb2, pb2 = float(np.atleast_1d(cb2)[0]), float(np.atleast_1d(pb2)[0])
            if ca > 0 and pa > 0:
                best = (k, ca + pa, max(cb2, 0) + max(pb2, 0))
                break
        if best is None:
            continue
        k, entry, exit_ = best
        rows.append({"date": int(D), "exit_date": int(Dx), "strike": k, "exp": int(exp),
                     "entry": entry, "exit": exit_, "ret": exit_ / entry - 1.0,
                     "gex": gex[D], "short_gamma": gex[D] < 0})
    df = pd.DataFrame(rows)
    df["ticker"] = t
    return df


def stats(label, r):
    r = np.asarray(r, float)
    r = r[np.isfinite(r)]
    if len(r) < 10:
        return f"  {label:22} n={len(r)} (too few)"
    top5 = np.sort(r)[-5:].sum()
    frag = top5 / r.sum() if r.sum() != 0 else np.nan
    return (f"  {label:22} n={len(r):>4}  mean={r.mean():+.3f}  median={np.median(r):+.3f}  "
            f"win={np.mean(r>0):.0%}  sharpe={r.mean()/(r.std()+1e-9):+.2f}  top5share={frag:+.2f}")


def main() -> int:
    names = [a.upper() for a in sys.argv[1:]] or ["SOFI"]
    all_t = [straddle_trades(t) for t in names]
    all_t = [d for d in all_t if not d.empty]
    if not all_t:
        print("no trades — chain/walls not cached yet for", names)
        return 1
    big = pd.concat(all_t, ignore_index=True)
    print(f"straddle trades: {len(big)}  names={sorted(big['ticker'].unique())} "
          f"dates {big['date'].min()}..{big['date'].max()} (train<{HOLDOUT_START})\n")
    print("return = straddle P&L as fraction of premium paid (honest ask-in / bid-out, hold "
          f"{H}d):")
    print(stats("ALL (unconditional)", big["ret"]))
    print(stats("SHORT-gamma gated", big[big["short_gamma"]]["ret"]))
    print(stats("LONG-gamma (control)", big[~big["short_gamma"]]["ret"]))
    # magnitude: most-negative-GEX quartile
    q = big["gex"].quantile(0.25)
    print(stats("deep short-gamma (Q1)", big[big["gex"] <= q]["ret"]))
    lift = big[big["short_gamma"]]["ret"].mean() - big["ret"].mean()
    print(f"\nGATE LIFT (short-gamma mean - unconditional mean) = {lift:+.3f}  "
          f"<- must be clearly >0 for the convex expression to add value")
    print("EXPLORATORY sanity run (train only, overlapping holds -> autocorrelated; full verdict "
          "uses non-overlapping entries + adversarial verification once all names are pulled).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
