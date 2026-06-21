"""Earnings strategy FIRST read — model-free, daily, market-relative (no shell/intraday yet).
Question: after an earnings GAP UP, does the stock drift up vs the market over the next days,
and does it concentrate in the doc's setup (gap >7.5%, opens above the prior high, off a
dormant base)? This tests post-earnings drift (PEAD) directly.

AMC earnings (after close on day E) -> the gap is E+1; BMO (before open) -> the gap is E.
Market-relative = minus SPY over the same window (kills survivorship/beta). Dev window only.
Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import common as C  # noqa: E402
import loaders as L  # noqa: E402

HZ = [5, 10, 20, 40]
DEV_END = pd.Timestamp(C.DEV_END)

spy = L.load_etf("SPY").set_index("dt")
spy_open, spy_close = spy["open"], spy["close"]

earn = L.load_earnings()
rows = []
for t, ev in earn.groupby("ticker"):
    try:
        d = L.load_daily(t)
    except Exception:
        continue
    if len(d) < 130:
        continue
    dt = d["dt"].to_numpy()
    o, h, c = d["open"].to_numpy(), d["high"].to_numpy(), d["close"].to_numpy()
    for _, e in ev.iterrows():
        E = np.datetime64(pd.Timestamp(e["earnings_dt_et"]).tz_localize(None).normalize())
        side = "right" if e["when"] == "AMC" else "left"   # AMC -> session after E; BMO -> E
        gp = int(np.searchsorted(dt, E, side=side))
        if gp < 61 or gp + max(HZ) >= len(d):
            continue
        gday = pd.Timestamp(dt[gp])
        if gday > DEV_END:
            continue
        gap = o[gp] / c[gp - 1] - 1
        rec = {
            "ticker": t, "dt": gday, "gap": gap,
            "above_high": o[gp] > h[gp - 1],
            "dormant": abs(c[gp - 1] / c[gp - 61] - 1) < 0.10,   # ~flat prior 3 months
        }
        for H in HZ:                                            # market-relative, from the gap-day OPEN
            sp = spy_close.get(pd.Timestamp(dt[gp + H]))
            so = spy_open.get(gday)
            if sp is None or so is None:
                rec[f"x{H}"] = np.nan
            else:
                rec[f"x{H}"] = (c[gp + H] / o[gp] - 1) - (sp / so - 1)
        rows.append(rec)

df = pd.DataFrame(rows).dropna(subset=[f"x{H}" for H in HZ])
(Path(__file__).resolve().parent / "out").mkdir(exist_ok=True)
df.to_parquet(Path(__file__).resolve().parent / "out" / "earnings_study.parquet")
print(f"{len(df):,} earnings events (dev, w/ forward data). Market-relative drift from gap-day OPEN, mean %:\n")


def tbl(sub, col, label):
    g = sub.groupby(col)
    out = pd.DataFrame({"n": g.size()})
    for H in HZ:
        out[f"x{H}d_%"] = (g[f"x{H}"].mean() * 100).round(2)
    out["win20d_%"] = (g["x20"].apply(lambda s: (s > 0).mean()) * 100).round(0)
    print(f"--- by {label} ---"); print(out.to_string()); print()


df["gap_b"] = pd.cut(df["gap"], [-1, -.075, 0, .03, .075, .15, 9],
                     labels=["<-7.5%", "-7.5..0", "0-3%", "3-7.5%", "7.5-15%", ">15%"])
print("ALL events: " + " ".join(f"x{H}d={df[f'x{H}'].mean()*100:+.2f}%" for H in HZ) + "\n")
tbl(df, "gap_b", "GAP SIZE (PEAD: bigger up-gap -> more drift?)")

# the doc's actual setup: gap > 7.5% AND opens above prior high
setup = df[(df["gap"] >= 0.075) & (df["above_high"])]
base = df[df["gap"] < 0.075]
print(f"=== DOC SETUP (gap>=7.5% & above prior high), n={len(setup)} ===")
print("  " + " ".join(f"x{H}d={setup[f'x{H}'].mean()*100:+.2f}%" for H in HZ)
      + f"  win20d={ (setup['x20']>0).mean()*100:.0f}%")
print(f"  + dormant base only, n={len(setup[setup.dormant])}: "
      + " ".join(f"x{H}d={setup[setup.dormant][f'x{H}'].mean()*100:+.2f}%" for H in HZ))
print(f"  (baseline gap<7.5%, n={len(base)}: x20d={base['x20'].mean()*100:+.2f}%)")
print("\nREAD: positive market-relative drift = real PEAD edge. Want it to GROW with gap size")
print("and be strongest in the doc setup. ~0 => no edge here either.")
