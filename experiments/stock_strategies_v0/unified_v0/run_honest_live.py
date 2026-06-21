"""HONEST same-day-live / day-late re-test of the breakout edge on DAILY bars (no new minute pull).

Three independent corrections to the +0.676R headline, each measured:
  (1) SELECTION-ON-CLOSE: the validated sample = days that CLOSED above the 20d high (is_breakout). A real
      stop-buy fills on the intraday CROSS regardless of the close -> include the ~46% that crossed then faded.
  (2) DAY OFFSET: the backtest fills intraday on day i; the live bot detects the close>20dH then arms for the
      NEXT session (i+1). Measure i+1-open and i+1-stop-buy (the exact live mechanic).
  (3) FILTER LOOKAHEAD: the ML features use day-i CLOSE, but the day-i intraday entry precedes that close.
      The causally-honest use of those features is to score at the close and enter i+1. So for the ACTUAL
      OOS-selected names (ml_selected_results, the +0.676 set), recompute their i+1 R = the honest deployable R.

Mechanic mirrors run_intraday_entry exactly (entry=max(trig,open)*(1+FRIC); stop=entry-1*ATR; ATR causal;
chandelier 3xATR let-run; max-hold 40; cost = FRIC*entry/risk exit side; R capped +/-10). Same-day stop on
daily bars is resolved CONSERVATIVELY (low<=stop => stopped, stop-wins) per the honest-fills rule.
Run with backend\\.venv\\Scripts\\python.exe -u.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

POLY = Path(r"D:\data\processed\stocks\polygon")
OUT = Path(__file__).resolve().parent / "out"
BUF, FRIC, K_ATR, CHAND, HOLD, RCAP = 0.001, 0.0015, 1.0, 3.0, 40, 10.0
YEAR0 = 20190101


def letrun(o, h, l, c, start, entry, stop, atr):
    """Chandelier let-run from index `start` (the fill bar). Same-day stop checked by caller.
    Tracks j=start+1.. exactly like run_intraday_entry.forward_daily. Returns capped R (cost applied)."""
    risk = entry - stop
    if risk <= 0:
        return None
    cost_R = FRIC * entry / risk
    n = len(c)
    cur, run_hi = stop, entry
    R = (c[min(start + HOLD, n - 1)] - entry) / risk
    for j in range(start + 1, min(start + 1 + HOLD, n)):
        if o[j] <= cur:
            R = (o[j] - entry) / risk
            break
        if l[j] <= cur:
            R = (cur - entry) / risk
            break
        run_hi = max(run_hi, h[j])
        cur = max(cur, run_hi - CHAND * atr)
    return float(np.clip(R - cost_R, -RCAP, RCAP))


def entry_at(o, h, l, c, idx, trig, atr):
    """Stop-buy at `trig` on bar `idx`: fills iff high>=trig. Returns capped R or None (no fill)."""
    if atr <= 0 or np.isnan(atr) or np.isnan(trig):
        return None
    if h[idx] < trig:
        return None  # never crossed -> no fill
    entry = max(trig, o[idx]) * (1 + FRIC)
    stop = entry - K_ATR * atr
    if entry - stop <= 0:
        return None
    if l[idx] <= stop:  # conservative same-day stop (stop wins; intraday order unknown on daily bars)
        risk = entry - stop
        return float(np.clip((stop - entry) / risk - FRIC * entry / risk, -RCAP, RCAP))
    return letrun(o, h, l, c, idx, entry, stop, atr)


def build():
    df = pd.concat([pd.read_parquet(f) for f in sorted(POLY.glob("daily_*.parquet"))], ignore_index=True)
    cs = set(pd.read_parquet(POLY / "meta.parquet")["ticker"])
    df = df[(df["ticker"].isin(cs)) & (df["date"] >= 20180101)].sort_values(["ticker", "date"])
    D = {}
    for t, g in df.groupby("ticker", sort=False):
        o = g["open"].to_numpy(float); h = g["high"].to_numpy(float)
        l = g["low"].to_numpy(float); c = g["close"].to_numpy(float); v = g["volume"].to_numpy(float)
        dts = g["date"].to_numpy().astype(int); n = len(c)
        if n < 60:
            continue
        pc = np.roll(c, 1)
        tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
        atr = pd.Series(tr).rolling(14).mean().to_numpy()          # NO shift; index [i-1] for causal
        hi20 = pd.Series(h).rolling(20).max().shift(1).to_numpy()
        dvol = pd.Series(c * v).rolling(20).mean().shift(1).to_numpy()
        D[t] = dict(o=o, h=h, l=l, c=c, dt=dts, atr=atr, hi20=hi20, dvol=dvol,
                    idx={int(x): k for k, x in enumerate(dts)})
    return D


def main():
    print("loading daily...")
    D = build()

    # ---------- (1)+(2) UNFILTERED population scan ----------
    rows = []
    for t, d in D.items():
        o, h, l, c, atr, hi20, dvol, dts = (d[k] for k in ("o", "h", "l", "c", "atr", "hi20", "dvol", "dt"))
        n = len(c)
        for i in range(21, n - 1):
            if dts[i] < YEAR0:
                continue
            if c[i] < 5 or np.isnan(dvol[i]) or dvol[i] < 1e6 or np.isnan(hi20[i]) or np.isnan(atr[i - 1]):
                continue
            trig = hi20[i] * (1 + BUF)
            if h[i] < trig:
                continue                                            # stop-buy never filled day i
            is_brk = int(c[i] > hi20[i])
            r_dayi = entry_at(o, h, l, c, i, trig, atr[i - 1])      # the architecturally-fixed same-day bot
            r_i1o = entry_at(o, h, l, c, i + 1, o[i + 1], atr[i]) if i + 1 < n else None  # trig=open => MOO fill
            trig2 = (d["hi20"][i + 1] * (1 + BUF)) if i + 1 < n and not np.isnan(d["hi20"][i + 1]) else np.nan
            r_i1sb = entry_at(o, h, l, c, i + 1, trig2, atr[i]) if i + 1 < n else None
            rows.append((dts[i] // 10000, is_brk, r_dayi, r_i1o, r_i1sb))
    A = pd.DataFrame(rows, columns=["yr", "is_brk", "r_dayi", "r_i1o", "r_i1sb"])

    def mr(s):
        s = s.dropna()
        return f"{s.mean():+.3f} (n={len(s):,})" if len(s) else "n/a"

    print(f"\nfilled stop-buys (high>=trig, liquid, 2019+): {len(A):,}  | close-confirmed {A['is_brk'].mean()*100:.0f}%\n")
    print("=== UNFILTERED (no ML) — daily-bar proxy of the mechanic ===")
    print(f"  day-i intraday  | is_breakout only : {mr(A[A.is_brk==1].r_dayi)}   <- calibrate vs minute ~+0.185")
    print(f"  day-i intraday  | FULL pop (incl faders): {mr(A.r_dayi)}   <- honest same-day, no close-cond")
    print(f"  day-i intraday  | faders only (closed<=20dH): {mr(A[A.is_brk==0].r_dayi)}   <- the dropped 46%")
    print(f"  i+1 OPEN entry  | is_breakout (detect close>20dH, enter next open): {mr(A[A.is_brk==1].r_i1o)}")
    print(f"  i+1 STOP-BUY    | is_breakout (THE current live bot mechanic): {mr(A[A.is_brk==1].r_i1sb)}")

    print("\n  by year (is_breakout): day-i / i+1-open / i+1-stopbuy")
    for y in sorted(A.yr.unique()):
        s = A[(A.yr == y) & (A.is_brk == 1)]
        print(f"    {y}: {s.r_dayi.mean():+.3f} / {s.r_i1o.mean():+.3f} / {s.r_i1sb.mean():+.3f}  n={len(s):,}")

    # ---------- (3) ML-SELECTED (OOS wf) names: their honest i+1 R ----------
    sel = pd.read_parquet(OUT / "ml_selected_results.parquet")[["tkr", "date", "R"]].copy()
    sel["R"] = sel["R"].clip(-RCAP, RCAP)
    out = []
    miss = 0
    for t, dd, r0 in zip(sel["tkr"], sel["date"], sel["R"]):
        d = D.get(t)
        if d is None:
            miss += 1; continue
        i = d["idx"].get(int(dd))
        if i is None or i + 1 >= len(d["c"]):
            miss += 1; continue
        o, h, l, c, atr, hi20 = d["o"], d["h"], d["l"], d["c"], d["atr"], d["hi20"]
        r_i1o = entry_at(o, h, l, c, i + 1, o[i + 1], atr[i])
        trig2 = hi20[i + 1] * (1 + BUF) if not np.isnan(hi20[i + 1]) else np.nan
        r_i1sb = entry_at(o, h, l, c, i + 1, trig2, atr[i])
        atr_pct = atr[i - 1] / c[i] if c[i] and not np.isnan(atr[i - 1]) else np.nan
        out.append((int(dd) // 10000, r0, r_i1o, r_i1sb, atr_pct))
    M = pd.DataFrame(out, columns=["yr", "r_dayi", "r_i1o", "r_i1sb", "atr_pct"])
    print(f"\n=== ML-SELECTED (OOS) names — honest entry timing  (matched {len(M):,}/{len(sel):,}; {miss:,} unmatched) ===")
    print(f"  day-i intraday (the +0.676 headline)        : {M.r_dayi.mean():+.3f}")
    print(f"  i+1 OPEN entry (causally honest, day late)   : {mr(M.r_i1o)}")
    print(f"  i+1 STOP-BUY  (EXACT current live bot)       : {mr(M.r_i1sb)}")
    print("\n  by year: day-i / i+1-open / i+1-stopbuy")
    for y in sorted(M.yr.unique()):
        s = M[M.yr == y]
        print(f"    {y}: {s.r_dayi.mean():+.3f} / {s.r_i1o.mean():+.3f} / {s.r_i1sb.mean():+.3f}  n={len(s):,}")

    # costs on the honest i+1 numbers (cost-in-R = 2*(f-FRIC)/atr_pct on top of the baked-in FRIC)
    mm = M.dropna(subset=["r_i1sb", "atr_pct"]).copy()
    mm["atr_pct"] = mm["atr_pct"].clip(lower=0.005)
    print("\n  i+1 STOP-BUY net meanR by extra cost/side:")
    for f in (0.0015, 0.003, 0.005):
        net = (mm["r_i1sb"] - 2 * (f - FRIC) / mm["atr_pct"]).mean()
        print(f"    {f*100:.2f}%/side: {net:+.3f}")

    print("\nREAD: if i+1 (esp. STOP-BUY) stays clearly >0 across years AND survives cost => the live bot trades a")
    print("real (if smaller) edge. If it collapses toward/below 0 => the +0.676 lived on the day-i intraday timing")
    print("(lookahead-coupled to close[i] features) and the deployable strategy has no honest edge as built.")


if __name__ == "__main__":
    main()
