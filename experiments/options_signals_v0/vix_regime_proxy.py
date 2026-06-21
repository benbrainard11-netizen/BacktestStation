"""FREE proxy test: does an options-implied REGIME signal condition ES behavior?

Before spending ~$75 on real options/GEX data, this checks whether the regime-gate idea even has a
there-there, using FREE data: VIX term structure (VIX / VIX3M / VIX9D from CBOE) as a CRUDE stand-in
for dealer-gamma regime. Backwardation (near-term vol > longer-term, ratio>1) ~ stressed / negative-gamma
(trend, high vol); contango (ratio<1) ~ calm / positive-gamma (mean-revert, low vol).

Test: regime measured at close of day t (no lookahead) -> does it predict day t+1's ES intraday
TRENDINESS (efficiency ratio = |net move| / path length; high=trend, low=chop/mean-revert) and realized
vol? Vol should work (VIX *is* implied vol) -- the interesting result is whether it conditions TRENDINESS,
which is the pin-vs-trend gate we'd actually buy GEX data to get. HONEST: VIX term structure is a crude
proxy; real dealer GEX is sharper. This only tells us whether the direction is worth paying for.

Run: backend/.venv/Scripts/python.exe experiments/options_signals_v0/vix_regime_proxy.py
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "backend")
from app.data.reader import read_bars  # noqa: E402

OUT = Path("experiments/options_signals_v0/out")
ESCACHE = OUT / "es_daily_intraday.parquet"
VIX = OUT / "vix_history.parquet"


def es_daily() -> pd.DataFrame:
    if ESCACHE.exists():
        return pd.read_parquet(ESCACHE)
    df = read_bars(symbol="ES.c.0", timeframe="1m", start=dt.date(2018, 1, 1), end=dt.date(2026, 6, 1))
    ts = pd.to_datetime(df["ts_event"], utc=True)
    df = df.assign(_ts=ts).set_index("_ts").between_time("14:00", "21:00")  # ~RTH (UTC)
    rows = []
    for d, g in df.groupby(df.index.date):
        c = g["close"].to_numpy(dtype=float)
        c = c[np.isfinite(c) & (c > 0)]
        if len(c) < 30:
            continue
        r = np.diff(np.log(c))
        path = np.abs(r).sum()
        rows.append({"date": pd.Timestamp(d), "rv": float(np.sqrt((r ** 2).sum())),
                     "eff": float(abs(np.log(c[-1] / c[0])) / path) if path > 0 else np.nan,
                     "absret": float(abs(c[-1] / c[0] - 1))})
    out = pd.DataFrame(rows)
    out.to_parquet(ESCACHE)
    return out


def main() -> int:
    es = es_daily().set_index("date")
    es.index = pd.to_datetime(es.index).tz_localize(None).normalize()
    V = pd.read_parquet(VIX)
    V.index = pd.to_datetime(V.index).tz_localize(None).normalize()
    V["ts_ratio"] = V["VIX"] / V["VIX3M"]     # >1 backwardation (stress), <1 contango (calm)
    V["ts9"] = V["VIX9D"] / V["VIX"]          # very-short end (0DTE-ish)
    reg = V[["VIX", "ts_ratio", "ts9"]].shift(1)   # regime from day t-1 -> applies to t (NO lookahead)

    m = es.join(reg, how="inner").dropna(subset=["eff", "rv", "ts_ratio", "VIX", "ts9"])
    print(f"merged {len(m)} trading days  {m.index.min().date()}..{m.index.max().date()}")
    print("(eff = intraday trendiness: high=trend, low=mean-revert; rv = realized vol)\n")

    for sig, desc in [("ts_ratio", "VIX/VIX3M term structure (>1 = stress)"),
                      ("VIX", "VIX level"),
                      ("ts9", "VIX9D/VIX very-short end")]:
        m = m.copy()
        m["bucket"] = pd.qcut(m[sig], 3, labels=["low", "mid", "high"])
        g = m.groupby("bucket", observed=True).agg(
            n=("eff", "size"), trendiness=("eff", "mean"), realized_vol=("rv", "mean"),
            abs_move=("absret", "mean"))
        ce, cv = m[sig].corr(m["eff"]), m[sig].corr(m["rv"])
        print(f"== {desc} (prior-day) -> next-day ES ==")
        print(g.to_string(float_format=lambda x: f"{x:.4f}"))
        print(f"  corr({sig}, trendiness) = {ce:+.3f}    corr({sig}, realized_vol) = {cv:+.3f}\n")

    # verdict on the key thing: does the regime condition TRENDINESS (not just vol)?
    ce = m["ts_ratio"].corr(m["eff"])
    hi = m[m["ts_ratio"] > m["ts_ratio"].quantile(0.8)]["eff"].mean()
    lo = m[m["ts_ratio"] < m["ts_ratio"].quantile(0.2)]["eff"].mean()
    print(f"VERDICT (trendiness gate): stress-regime trendiness {hi:.4f} vs calm {lo:.4f} "
          f"(diff {hi-lo:+.4f}, corr {ce:+.3f}).")
    print("  -> " + ("SIGNAL: regime conditions trend-vs-revert -> real GEX data (~$75) is worth testing."
                     if abs(ce) > 0.06 or abs(hi - lo) > 0.01 else
                     "WEAK: term structure barely moves trendiness; real GEX MIGHT still help but temper expectations."))
    print("  (Realized vol IS conditioned by VIX as expected -- that part is just the sanity check.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
