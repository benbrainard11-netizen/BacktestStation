"""Analyze the Jan-2026 OOS short revalidation output (from mira_short_revalidation.py --full).

Produces, for the live exit logic (fixed signal.py, trail_2R, net costs):
  * per-direction summary: N, win%, mean/median R, profit factor, bootstrap 95% CI, P(R>0), P(R>0.2)
  * head-to-head longs vs shorts (+ bootstrap CI on the difference)
  * per-symbol and no-YM (live universe) breakdowns
  * exit-reason mix + R-distribution by direction
  * BUG CONTRAST: R the hwm-sign bug destroyed on shorts
  * REGIME: short expectancy on down-trend vs up-trend days (descriptive, full-day classification)

No retuning, no look-ahead in the trades themselves (regime label is descriptive only, stated as such).

Run: backend/.venv/Scripts/python.exe experiments/sizing_v1/mira_short_analysis.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TRAIL = HERE / "out" / "mira_short_revalidation" / "jan2026_trail_2R.parquet"
BARS_ROOT = Path(r"D:\data\processed\bars\timeframe=1m")
RNG = np.random.default_rng(20260605)


def boot_ci(r: np.ndarray, B: int = 20000):
    if len(r) == 0:
        return (np.nan, np.nan, np.nan, np.nan, np.nan)
    idx = RNG.integers(0, len(r), size=(B, len(r)))
    means = r[idx].mean(axis=1)
    return (float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)),
            float((means > 0).mean()), float((means > 0.2).mean()), float(means.std()))


def summarize(label: str, r: pd.Series) -> dict:
    r = r.dropna().to_numpy()
    n = len(r)
    if n == 0:
        return {"seg": label, "n": 0}
    wins, losses = r[r > 0], r[r < 0]
    pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else float("inf")
    lo, hi, p0, p20, se = boot_ci(r)
    return {"seg": label, "n": n, "win%": round(100 * (r > 0).mean(), 1),
            "meanR": round(float(r.mean()), 3), "medR": round(float(np.median(r)), 3),
            "sumR": round(float(r.sum()), 1), "pf": round(float(pf), 2),
            "CI95": f"[{lo:+.3f},{hi:+.3f}]", "P(>0)": round(p0, 3), "P(>.2R)": round(p20, 3),
            "SE": round(se, 3)}


def ptab(rows: list[dict]) -> None:
    rows = [r for r in rows if r.get("n", 0) > 0]
    if not rows:
        print("   (no rows)"); return
    cols = ["seg", "n", "win%", "meanR", "medR", "sumR", "pf", "CI95", "P(>0)", "P(>.2R)"]
    w = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    print("   " + "  ".join(c.rjust(w[c]) for c in cols))
    for r in rows:
        print("   " + "  ".join(str(r.get(c, "")).rjust(w[c]) for c in cols))


def day_return(symbol: str, day) -> float:
    """Descriptive full-day 1m open->close return (regime label only, not a trade signal)."""
    p = BARS_ROOT / f"symbol={symbol}" / f"date={pd.Timestamp(day).date().isoformat()}"
    try:
        b = pd.read_parquet(p, columns=["ts_event", "open", "close"])
    except Exception:
        return np.nan
    if b.empty:
        return np.nan
    b = b.sort_values("ts_event")
    o, c = float(b["open"].iloc[0]), float(b["close"].iloc[-1])
    return (c - o) / o if o else np.nan


def main() -> int:
    df = pd.read_parquet(TRAIL)
    df["entry_ts"] = pd.to_datetime(df["entry_ts"], utc=True)
    df["entry_date"] = df["entry_ts"].dt.date
    df["dir"] = np.where(df["direction"] == 1, "long", "short")
    R = "r_signal_net"

    print("=" * 80)
    print(f"MIRA SHORT RE-VALIDATION — Jan-2026 OOS  (fixed signal.py, trail_2R, net costs)")
    print(f"N={len(df)}  longs={int((df.direction==1).sum())}  shorts={int((df.direction==-1).sum())}"
          f"  days={df['entry_date'].nunique()}")
    print("=" * 80)

    print("\n### 1) HEAD-TO-HEAD (live exit logic) ###")
    ptab([summarize("ALL", df[R]),
          summarize("LONGS", df[df.direction == 1][R]),
          summarize("SHORTS", df[df.direction == -1][R])])

    # bootstrap the long-short gap
    lr = df[df.direction == 1][R].dropna().to_numpy()
    sr = df[df.direction == -1][R].dropna().to_numpy()
    B = 20000
    d = (sr[RNG.integers(0, len(sr), (B, len(sr)))].mean(1)
         - lr[RNG.integers(0, len(lr), (B, len(lr)))].mean(1))
    print(f"\n   short-minus-long meanR diff = {sr.mean()-lr.mean():+.3f}R  "
          f"95% CI [{np.percentile(d,2.5):+.3f},{np.percentile(d,97.5):+.3f}]  "
          f"P(short>long)={ (d>0).mean():.3f}")

    print("\n### 2) SHORTS by SYMBOL ###")
    ptab([summarize(s, g[g.direction == -1][R]) for s, g in df.groupby("symbol")])

    print("\n### 3) no-YM (live universe ES/NQ/RTY) ###")
    noym = df[~df.symbol.astype(str).str.startswith("YM")]
    ptab([summarize("noYM ALL", noym[R]),
          summarize("noYM LONGS", noym[noym.direction == 1][R]),
          summarize("noYM SHORTS", noym[noym.direction == -1][R])])

    print("\n### 4) EXIT-REASON MIX ###")
    for nm, sub in [("LONGS", df[df.direction == 1]), ("SHORTS", df[df.direction == -1])]:
        mix = sub["reason_signal"].value_counts().to_dict()
        meanby = {k: round(float(sub[sub.reason_signal == k][R].mean()), 3) for k in mix}
        print(f"   {nm}: counts={mix}  meanR_by_reason={meanby}")

    print("\n### 5) SHORT R-DISTRIBUTION ###")
    s = df[df.direction == -1][R].dropna()
    qs = [0, 5, 10, 25, 50, 75, 90, 95, 100]
    print("   percentiles: " + "  ".join(f"p{q}={np.percentile(s,q):+.2f}" for q in qs))
    bins = [-np.inf, -1.0, -0.5, 0, 0.5, 1.0, 2.0, np.inf]
    lbls = ["<-1", "-1..-.5", "-.5..0", "0..0.5", "0.5..1", "1..2", ">2"]
    print("   histogram: " + dict(zip(lbls, pd.cut(s, bins, labels=lbls).value_counts().reindex(lbls).fillna(0).astype(int))).__str__())

    print("\n### 6) BUG CONTRAST (what the live bot would have done to shorts) ###")
    ptab([summarize("SHORTS fixed", df[df.direction == -1]["r_signal_net"]),
          summarize("SHORTS bugged", df[df.direction == -1]["r_bugged_net"])])
    sf = df[df.direction == -1]["r_signal_net"].sum()
    sb = df[df.direction == -1]["r_bugged_net"].sum()
    print(f"   bug destroyed {sf - sb:+.1f}R of short edge over the window "
          f"(fixed {sf:+.1f}R vs bugged {sb:+.1f}R)")

    print("\n### 7) REGIME — shorts on down vs up days (descriptive full-day classification) ###")
    df["day_ret"] = [day_return(sym, d) for sym, d in zip(df.symbol, df.entry_date)]
    sdf = df[df.direction == -1].copy()
    sdf["regime"] = np.where(sdf["day_ret"] < 0, "down_day", "up_day")
    ptab([summarize(f"shorts {rg}", g[R]) for rg, g in sdf.groupby("regime")])
    print(f"   (day_ret available for {sdf['day_ret'].notna().sum()}/{len(sdf)} shorts)")
    # longs too, for symmetry
    ldf = df[df.direction == 1].copy()
    ldf["regime"] = np.where(ldf["day_ret"] < 0, "down_day", "up_day")
    print("   longs for symmetry:")
    ptab([summarize(f"longs {rg}", g[R]) for rg, g in ldf.groupby("regime")])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
