"""Build the causal feature matrix for the gap-selection model. One row per doc-setup gap
(gap>=7.5% & above prior high). All features known at the gap-day open / prior close. Targets:
x20 (20d market-relative drift, the clean signal) + realized_r (tradeable). Keeps entry/exit
dates for the portfolio eval. Writes out/features.parquet.
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
from shell import ShellConfig, Signal, run_signals  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
study = pd.read_parquet(OUT / "earnings_study.parquet")
setup = study[(study["gap"] >= 0.075) & (study["above_high"])].copy()

# tradeable target + dates from the shell
sigs = [Signal(r.ticker, r.dt, tag="earnings_gap") for r in setup.itertuples()]
tr = run_signals(sigs, ShellConfig(entry_mode="signal_open", stop_mode="pct", stop_pct=0.08,
                                   do_partial=False, move_to_be=False, trail_ma="ma20"))
tr["entry_dt"] = pd.to_datetime(tr["entry_date"]); tr["exit_dt"] = pd.to_datetime(tr["exit_date"])

# clean target + dormancy from the study
m = setup[["ticker", "dt", "gap", "dormant", "x20"]].rename(columns={"dt": "entry_dt"})
df = tr.merge(m, on=["ticker", "entry_dt"], how="left")

# earnings surprise from the calendar
cal = L.load_earnings()[["ticker", "date", "surprise_pct"]].copy()
cal["entry_dt"] = pd.to_datetime(cal["date"])
df = df.merge(cal[["ticker", "entry_dt", "surprise_pct"]], on=["ticker", "entry_dt"], how="left")

# market regime (SPY/QQQ MA10>MA20) at the prior day
def idx_state(t):
    d = L.with_mas(L.load_etf(t)).set_index("dt")
    return (d["ma10"] > d["ma20"]).astype(float)
reg = (idx_state("SPY") + idx_state("QQQ")).shift(1)   # 0/1/2 risk-on count, prior day
spy = L.load_etf("SPY").set_index("dt")
spy_ret20 = (spy["close"] / spy["close"].shift(20) - 1).shift(1)

# per-ticker daily features (causal: prior close / gap-day open)
rows = []
for t, g in df.groupby("ticker"):
    try:
        d = L.with_mas(L.load_daily(t)).reset_index(drop=True)
    except Exception:
        continue
    pos = {dt: i for i, dt in enumerate(d["dt"])}
    for r in g.itertuples():
        i = pos.get(r.entry_dt)
        if i is None or i < 61:
            continue
        o, c, hi, lo = d["open"], d["close"], d["high"], d["low"]
        feat = {
            "ticker": t, "entry_dt": r.entry_dt, "exit_dt": r.exit_dt,
            "realized_r": r.realized_r, "x20": r.x20,
            "gap": r.gap, "dormant": float(r.dormant),
            "above_high_dist": o[i] / hi[i - 1] - 1,
            "ret20_prior": c[i - 1] / c[i - 21] - 1,
            "ret60_prior": c[i - 1] / c[i - 61] - 1,
            "adr20": ((hi - lo) / c).iloc[i - 20:i].mean(),
            "log_price": np.log(c[i - 1]),
            "log_dvol": np.log((c * d["volume"]).iloc[i - 20:i].mean() + 1),
            "c_ma10": c[i - 1] / d["ma10"][i - 1] - 1,
            "c_ma50": c[i - 1] / d["ma50"][i - 1] - 1,
            "surprise": r.surprise_pct,
            "regime": reg.asof(r.entry_dt),
            "spy_ret20": spy_ret20.asof(r.entry_dt),
            "month": r.entry_dt.month,
        }
        rows.append(feat)

feat = pd.DataFrame(rows).dropna(subset=["x20", "realized_r"]).reset_index(drop=True)
feat.to_parquet(OUT / "features.parquet")
print(f"features: {len(feat)} rows x {feat.shape[1]} cols, "
      f"{feat['entry_dt'].min().date()}..{feat['entry_dt'].max().date()}")
print("cols:", [c for c in feat.columns if c not in ('ticker','entry_dt','exit_dt')])
print(f"surprise non-null: {feat['surprise'].notna().mean()*100:.0f}%")
