"""Consolidation-breakout test (Ben's pattern): pressure UP -> tight CONSOLIDATION -> break of the
base on volume, stop UNDER the base.

This is the faithful version of the idea the raw "close > 20d-high + 1-ATR stop" test could not
express. Differences that matter:
  * the level is the CONSOLIDATION HIGH (top of a real tightening base), not the 20-day high;
  * the stop is the CONSOLIDATION LOW (structure), not entry - 1*ATR;
  * the break must come on above-average VOLUME (the one filter that clearly helped: +0.30 vs +0.12).

Daily-bar test on the full survivorship-clean Polygon universe (delisted incl). Entry day uses the
daily bar (honest: gap over the level -> fill at open; if the same day also trades the base low, the
OHLC order is unknown so the STOP wins -- CLAUDE.md rule 8, counted as ambiguous/conservative). The
multi-day hold + chandelier trail / fixed-R exits reuse run_intraday_entry.forward_daily unchanged.

Run with backend\\.venv\\Scripts\\python.exe -u.
"""

from __future__ import annotations

import importlib.util
import time

import numpy as np
import pandas as pd

RIE = r"C:\Users\benbr\BacktestStation\experiments\stock_strategies_v0\unified_v0\run_intraday_entry.py"
_spec = importlib.util.spec_from_file_location("rie", RIE)
rie = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rie)

# --- pattern params (first pass; tune after we see the shape) ---
K = 10  # consolidation length (trading days)
TIGHT = 0.12  # base height (high-low)/low must be <= 12%  (a real tight base)
RUNUP_DAYS = 25  # window of the prior advance INTO the base
RUNUP_MIN = 0.20  # price must have risen >= 20% over that window  (pressure up)
VOL_MULT = 1.2  # breakout-day volume >= 1.2x the prior 20d avg  (the banked volume win)
MIN_RISK = 0.02  # require base depth >= 2% of entry, else the structure stop is a tiny-risk trap


def run():
    t0 = time.time()
    print("loading full daily universe...", flush=True)
    files = sorted(rie.POLY.glob("daily_*.parquet"))
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    meta = pd.read_parquet(rie.POLY / "meta.parquet")
    active_set = set(meta[meta["active"]]["ticker"])
    print(f"  {len(df):,} rows, {df['ticker'].nunique():,} tickers ({time.time()-t0:.0f}s)", flush=True)

    rows = []
    ambiguous = 0
    for tkr, g in df.sort_values(["ticker", "date"]).groupby("ticker", sort=False):
        n = len(g)
        if n < RUNUP_DAYS + K + 30:
            continue
        o = g["open"].to_numpy(float)
        h = g["high"].to_numpy(float)
        lo = g["low"].to_numpy(float)
        c = g["close"].to_numpy(float)
        v = g["volume"].to_numpy(float)
        dts = g["date"].to_numpy()

        pc = np.roll(c, 1)
        tr = np.maximum(h - lo, np.maximum(np.abs(h - pc), np.abs(lo - pc)))
        atr = pd.Series(tr).rolling(14).mean().to_numpy()
        ma50 = pd.Series(c).rolling(50).mean().to_numpy()
        avgv = pd.Series(v).rolling(20).mean().shift(1).to_numpy()
        dvol = pd.Series(c * v).rolling(20).mean().shift(1).to_numpy()
        base_hi = pd.Series(h).rolling(K).max().shift(1).to_numpy()  # base = prior K days (excl today)
        base_lo = pd.Series(lo).rolling(K).min().shift(1).to_numpy()

        for i in range(RUNUP_DAYS + K + 1, n - 1):
            bh, bl = base_hi[i], base_lo[i]
            if np.isnan(bh) or np.isnan(bl) or bl <= 0 or np.isnan(atr[i]) or np.isnan(ma50[i - 1]):
                continue
            # tradeable (prior day, causal)
            if c[i - 1] < 5 or np.isnan(dvol[i]) or dvol[i] < 1e6:
                continue
            # consolidation: tight base
            if (bh - bl) / bl > TIGHT:
                continue
            # pressure up: ran into the base, and base sits above the 50-MA
            base_start = i - K
            if c[base_start - 1] <= 0 or c[base_start - 1 - RUNUP_DAYS] <= 0:
                continue
            runup = c[base_start - 1] / c[base_start - 1 - RUNUP_DAYS] - 1.0
            if runup < RUNUP_MIN or c[i - 1] <= ma50[i - 1]:
                continue
            # breakout of the base high, on volume
            trig = bh * (1 + rie.BUF_ENTRY)
            if h[i] < trig or np.isnan(avgv[i]) or v[i] < VOL_MULT * avgv[i]:
                continue

            entry = max(trig, o[i]) * (1 + rie.FRICTION)  # gap over -> open; +slippage
            stop = bl
            risk = entry - stop
            if risk <= 0 or risk / entry < MIN_RISK:
                continue
            cost_R = (
                rie.FRICTION * entry / risk
            )  # exit side only; entry side already in the (1+FRICTION) fill

            if lo[i] <= stop:  # same-day base-low touch: OHLC order unknown -> stop wins (rule 8)
                ambiguous += 1
                R, reason, days, mfe = (stop - entry) / risk - cost_R, "stop_d0", 0, 0.0
            else:
                D = {"o": o, "h": h, "l": lo, "c": c}
                R, reason, days, mfe = rie.forward_daily(D, i, entry, stop, atr[i], None)
                R -= cost_R
            rows.append(
                dict(
                    tkr=tkr,
                    date=int(dts[i]),
                    R=R,
                    reason=reason,
                    days=days,
                    mfe=mfe,
                    risk_pct=risk / entry,
                )
            )

    R = pd.DataFrame(rows)
    R["active"] = R["tkr"].isin(active_set)
    R["yr"] = R["date"] // 10000
    R.to_parquet(rie.OUT / "consolidation_breakout_results.parquet")
    print(f"\n=== CONSOLIDATION breakout (base-high entry, base-low stop, vol>= {VOL_MULT}x) ===")
    print(
        f"   K={K} tight<={TIGHT} runup>={RUNUP_MIN} over {RUNUP_DAYS}d | {len(R):,} setups | "
        f"ambiguous(stop-wins) {ambiguous:,} | [{time.time()-t0:.0f}s]\n"
    )
    rie.summarize(R, "ALL")
    rie.summarize(R[R.active], "active only")
    rie.summarize(R[~R.active], "DELISTED only")
    # winsorized mean (kill the freak-R tail seen in the 20d-high test)
    w = R["R"].clip(upper=R["R"].quantile(0.99))
    print(
        f"  winsorized@99pct meanR {w.mean():+.3f}  | median risk {R['risk_pct'].median()*100:.1f}% of price"
    )
    print()
    for y in sorted(R["yr"].unique()):
        rie.summarize(R[R.yr == y], f"year {y}")
    print("\n=== exit grid ===")
    rie.summarize(R, "chandelier(3xATR)")
    print("READ: done", flush=True)


if __name__ == "__main__":
    run()
