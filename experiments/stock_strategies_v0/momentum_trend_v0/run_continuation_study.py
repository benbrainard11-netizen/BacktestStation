"""RETHINK momentum: a model-free continuation study. No entries/exits/shell — just:
after a breakout, does the stock beat the MARKET over the next H days, and does that signal
concentrate where the doc says (explosive prior thrust, high volatility/ADR, small price)?

Market-relative (minus SPY over the same window) kills the survivorship/beta confound: if the
'edge' is just survivors riding the market up, excess return -> 0.

Breakouts = close > 10-day high + liquidity (loose, to get N for slicing). Records prior
thrust %, ADR %, price. Dev window only. Run with backend\\.venv\\Scripts\\python.exe.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import common as C  # noqa: E402
import loaders as L  # noqa: E402

HZ = [1, 2, 3, 5, 10, 20]             # forward horizons (incl. short, for fast follow-through)
MIN_PRICE, MIN_DV = 5.0, 3e6
qfile = Path(__file__).resolve().parents[1] / "data" / "quarantine_tickers.txt"
BAD = set(qfile.read_text().split()) if qfile.exists() else set()
DEV_END = pd.Timestamp(C.DEV_END)


def spy_forward() -> dict:
    spy = L.load_etf("SPY").set_index("dt")
    out = {}
    for h in HZ:
        out[h] = (spy["close"].shift(-h) / spy["open"].shift(-1) - 1).rename(f"spy{h}")
    return {h: out[h] for h in HZ}, spy.index


def scan_one(t: str, spy_fwd: dict) -> pd.DataFrame | None:
    try:
        d = L.load_daily(t)
    except Exception:
        return None
    if len(d) < 130:
        return None
    cl, hi, lo, vol = d["close"], d["high"], d["low"], d["volume"]
    prior_hi = hi.rolling(10).max().shift(1)
    dv = (cl * vol).rolling(20).mean().shift(1)
    thrust = cl.shift(11) / cl.shift(70) - 1                  # 60d runup ending before a 10d base
    adr = ((hi - lo) / cl).rolling(20).mean().shift(1)
    entry = d["open"].shift(-1)
    m = (cl > prior_hi) & (cl >= MIN_PRICE) & (dv >= MIN_DV) & (d["dt"] <= DEV_END)
    rows = pd.DataFrame({"dt": d["dt"], "thrust": thrust, "adr": adr, "price": cl})
    for h in HZ:
        rows[f"r{h}"] = cl.shift(-h) / entry - 1
    rows = rows[m.fillna(False)].dropna(subset=["thrust", "adr"] + [f"r{h}" for h in HZ])
    if not len(rows):
        return None
    rows["ticker"] = t
    for h in HZ:                                              # market-relative excess
        rows[f"x{h}"] = rows[f"r{h}"] - rows["dt"].map(spy_fwd[h])
    return rows.dropna(subset=[f"x{h}" for h in HZ])


spy_fwd, _ = spy_forward()
tickers = [t for t in L.list_universe("daily") if t not in BAD]
print(f"scanning {len(tickers)} names for 10d-high breakouts...", flush=True)
parts = []
for i, t in enumerate(tickers):
    r = scan_one(t, spy_fwd)
    if r is not None:
        parts.append(r)
    if (i + 1) % 1000 == 0:
        print(f"  ...{i+1}/{len(tickers)}  rows={sum(len(p) for p in parts)}", flush=True)
df = pd.concat(parts, ignore_index=True)
df.to_parquet(Path(__file__).resolve().parent / "out" / "continuation_study.parquet")
print(f"\n{len(df):,} breakouts.  Market-relative forward return (excess vs SPY), mean %:\n")


def tbl(df, col, label):
    g = df.groupby(col)
    out = pd.DataFrame({"n": g.size()})
    for h in HZ:
        out[f"x{h}d_%"] = (g[f"x{h}"].mean() * 100).round(2)
    out[f"win{HZ[2]}d_%"] = (g[f"x{HZ[2]}"].apply(lambda s: (s > 0).mean()) * 100).round(0)
    print(f"--- by {label} ---"); print(out.to_string()); print()


df["thrust_b"] = pd.cut(df["thrust"], [-1, 0, .15, .30, .60, 1.0, 99],
                        labels=["<0", "0-15%", "15-30%", "30-60%", "60-100%", ">100%"])
df["adr_b"] = pd.cut(df["adr"], [0, .02, .035, .05, .08, 1], labels=["<2%", "2-3.5%", "3.5-5%", "5-8%", ">8%"])
df["px_b"] = pd.cut(df["price"], [0, 10, 25, 75, 200, 1e9], labels=["<$10", "$10-25", "$25-75", "$75-200", ">$200"])

print(f"ALL breakouts: " + " ".join(f"x{h}d={df[f'x{h}'].mean()*100:+.2f}%" for h in HZ) + "\n")
tbl(df, "thrust_b", "PRIOR THRUST (the explosive-mover thesis)")
tbl(df, "adr_b", "ADR / volatility")
tbl(df, "px_b", "PRICE (size proxy)")
print("READ: positive market-relative excess = real continuation alpha beyond the market.")
print("If it concentrates in high-thrust / high-ADR / low-price -> the doc's turf is where to model.")
print("If ~0 everywhere -> momentum continuation isn't on this universe; models won't save it.")
