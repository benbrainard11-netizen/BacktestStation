"""Test the 'gap -> retrace into the gap -> continue' idea: is entering on a PULLBACK better
than buying the gap immediately? A limit at a % gap-retracement; filled if price dips there
within K days; you MISS the runaways that never pull back. Compares market-relative 20d return:
immediate (all gaps, from open) vs pullback (filled subset, from the limit). Also: do the
runaways (no pullback) continue best? Daily, doc-setup up-gaps, dev window.
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

K = 10          # days to wait for the pullback
H = 20          # forward horizon
DEV_END = pd.Timestamp(C.DEV_END)
LEVELS = [0.3, 0.5, 0.7, 1.0]   # fraction of the gap retraced (1.0 = back to prior close)

spy = L.load_etf("SPY").set_index("dt")["close"]
study = pd.read_parquet(Path(__file__).resolve().parent / "out" / "earnings_study.parquet")
setup = study[(study["gap"] >= 0.075) & (study["above_high"])].copy()

rows = []
for t, g in setup.groupby("ticker"):
    try:
        d = L.load_daily(t)
    except Exception:
        continue
    dt = d["dt"].to_numpy(); o = d["open"].to_numpy(); c = d["close"].to_numpy(); lo = d["low"].to_numpy()
    pos = {x: i for i, x in enumerate(dt)}
    for r in g.itertuples():
        i = pos.get(np.datetime64(pd.Timestamp(r.dt)))
        if i is None or i + H >= len(d):
            continue
        pc, op = c[i - 1], o[i]
        minlK = lo[i:i + K + 1].min()
        c_fwd = c[i + H]
        sp = spy.get(pd.Timestamp(dt[i])); spf = spy.get(pd.Timestamp(dt[i + H]))
        if not sp or not spf:
            continue
        spy_ret = spf / sp - 1
        rec = {"ticker": t, "imm": c_fwd / op - 1 - spy_ret, "minlK": minlK, "pc": pc, "op": op, "c_fwd": c_fwd, "spy_ret": spy_ret}
        rows.append(rec)

df = pd.DataFrame(rows)
print(f"{len(df)} up-gaps. Forward {H}d market-relative return.\n")
print(f"IMMEDIATE entry (all, buy the open): mean {df['imm'].mean()*100:+.2f}%  win {(df['imm']>0).mean()*100:.0f}%\n")
print(f"{'pullback level':16s} {'fill%':>6} {'pullback ret':>13} {'immed(filled)':>14} {'runaway ret':>12}")
for f in LEVELS:
    lvl = df["op"] - f * (df["op"] - df["pc"])      # entry limit (lower = deeper retrace)
    filled = df["minlK"] <= lvl
    pb = (df["c_fwd"] / lvl - 1 - df["spy_ret"])[filled]
    imm_filled = df["imm"][filled]
    runaway = df["imm"][~filled]
    print(f"{int(f*100)}% gap retrace  {filled.mean()*100:5.0f}% {pb.mean()*100:+12.2f}% "
          f"{imm_filled.mean()*100:+13.2f}% {runaway.mean()*100:+11.2f}%")
print("\nREAD: 'pullback ret' = enter at the limit on the dip (filled subset). 'immed(filled)' =")
print("buying those SAME gaps at the open. 'runaway ret' = the gaps that never pulled back (skipped).")
print("Pullback wins only if pullback-ret > immediate-all AND runaways aren't where the edge is.")
