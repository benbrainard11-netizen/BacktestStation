"""Is the recent direction edge a real REGIME SHIFT (momentum->reversion) or overfit?

The decisive, low-overfitting test: NQ's intraday AUTOCORRELATION over time, market-wide
(NOT the SMT signal). corr(prior 30-min return, forward 15-min return) per half-year:
  > 0  = momentum (moves continue)  -> shorting an over-extension LOSES (the 2018-24 regime)
  < 0  = mean-reversion (moves fade) -> shorting an over-extension WINS (the recent edge)
If this flips from + to - around 2023-2025, the recent cross-asset-SMT short edge has a real
structural story (0DTE-driven intraday reversion). If it's flat/noisy, the edge is idiosyncratic.

Skips 2025-H1 (reserved) and 2026-04+ (sealed holdout). Bars only.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\investigate_regime.py
"""
from __future__ import annotations

import sys
from datetime import date as Date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
import data_io as D
from build_events import GRID_MS, SESSION_END_MS

RTH_OPEN_MS = 9 * 3600_000 + 30 * 60_000


def halfyear(dstr):
    y, m = int(dstr[:4]), int(dstr[5:7])
    return f"{y}H{1 if m <= 6 else 2}"


def main() -> int:
    days = sorted(p.name.split("=")[1] for p in C.BARS_1M_NQ.glob("date=*"))
    days = [d for d in days if "2018-01-01" <= d <= "2026-03-31"
            and not ("2025-01-01" <= d <= "2025-08-31")]   # reserve 2025-H1, sacred holdout already >Mar26
    rows = []
    for dstr in days:
        day = Date.fromisoformat(dstr)
        df = D.load_bars_sym(C.BARS_1M_NQ, day)
        if df is None:
            continue
        lo, hi = D.et_ts(day, RTH_OPEN_MS), D.et_ts(day, SESSION_END_MS)
        r = df[(df["et"] >= lo) & (df["et"] < hi)]
        if len(r) < 120:
            continue
        c = r.set_index("et")["close"]
        for ms in GRID_MS:
            if ms > C.TRIG_LAST_ENTRY_MS:
                break
            t = D.et_ts(day, ms)
            p0 = c[c.index <= t - pd.Timedelta(minutes=30)]
            pnow = c[c.index <= t]
            pfwd = c[c.index <= t + pd.Timedelta(minutes=15)]
            if len(p0) and len(pnow) and len(pfwd) and pnow.index[-1] < pfwd.index[-1]:
                prior = pnow.iloc[-1] / p0.iloc[-1] - 1.0
                fwd = pfwd.iloc[-1] / pnow.iloc[-1] - 1.0
                if np.isfinite(prior) and np.isfinite(fwd):
                    rows.append({"hy": halfyear(dstr), "yr": dstr[:4], "prior": prior, "fwd": fwd})

    f = pd.DataFrame(rows)
    print(f"{len(f)} decisions over {f.hy.nunique()} half-years\n")
    print("### intraday autocorrelation corr(prior-30m, fwd-15m) per half-year")
    print("    (>0 momentum/continuation,  <0 mean-reversion/fade)")
    for hy, g in f.groupby("hy"):
        cc = np.corrcoef(g["prior"], g["fwd"])[0, 1] if len(g) > 30 else np.nan
        fade = (-np.sign(g["prior"]) * g["fwd"]).mean() * 1e4   # bps from fading the prior move
        bar = "#" * int(abs(cc) * 200) if np.isfinite(cc) else ""
        sign = "REVERT" if cc < 0 else "moment"
        print(f"  {hy:7s} n={len(g):5d} corr={cc:+.4f} {sign:7s} fade_bps={fade:+.2f}  {bar}")
    print("\n### by era")
    for lab, m in [("2018-2024", f.yr <= "2024"), ("2025H2-2026Q1 (recent)", f.yr >= "2025")]:
        g = f[m]
        cc = np.corrcoef(g["prior"], g["fwd"])[0, 1]
        fade = (-np.sign(g["prior"]) * g["fwd"]).mean() * 1e4
        print(f"  {lab:24s} n={len(g):6d} corr={cc:+.4f} fade_bps={fade:+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
