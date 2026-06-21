"""Tune the stop: ATR-multiple vs structural (opening-range edge), on honest-ish bar fills.

Test bed = the opening-drive trades (NQ 2018-2026, follow the 09:45 drive), run-it to EOD with
only the stop as risk control. For each stop variant measure expectancy E[R], win%, median stop
distance -> $-risk/contract (NQ mini & MNQ micro), and whether one contract fits a prop drawdown
budget. Picks the stop that maximizes E[R] subject to fitting the budget.
"""
import sys
from datetime import date as Date
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "sizing_v1"))
import common as C
import data_io as D
from stops import compute_stop

OUT = HERE / "out"
OPEN_MS, DEC_MS, EOD_MS = 9 * 3600_000 + 30 * 60_000, 9 * 3600_000 + 45 * 60_000, 16 * 3600_000
COST_PTS = 0.5                       # ~2 ticks slip+comm (conservative); cost in R = COST/stop
DD_BUDGET = 200.0                    # $ risk allowed per trade (10% of a $2k trailing DD)
PV = {"NQ": 20.0, "MNQ": 2.0}

VARIANTS = [
    ("atr_0.10", dict(struct=False, k_fallback=0.10)),
    ("atr_0.15", dict(struct=False, k_fallback=0.15)),
    ("atr_0.20", dict(struct=False, k_fallback=0.20)),
    ("atr_0.30", dict(struct=False, k_fallback=0.30)),
    ("struct_OR", dict(struct=True, k_fallback=0.20)),
]

od = pd.read_parquet(OUT / "open_dataset.parquet").dropna(subset=["or_drive_atr", "atr", "entry"]).copy()
od = od[od.or_drive_atr.abs() > 1e-9]


def rth(day):
    df = D.load_bars_sym(C.BARS_1M_NQ, day)
    if df is None:
        return None
    f = df[(df["et"] >= D.et_ts(day, OPEN_MS)) & (df["et"] < D.et_ts(day, EOD_MS))]
    return f if len(f) else None


def refill(fwd_h, fwd_l, fwd_c, entry, direction, stop_dist):
    """Hold to EOD; exit at stop (first touch) else EOD close. Returns R (net cost)."""
    stop_px = entry - direction * stop_dist
    if direction > 0:
        hit = np.argmax(fwd_l <= stop_px) if (fwd_l <= stop_px).any() else None
    else:
        hit = np.argmax(fwd_h >= stop_px) if (fwd_h >= stop_px).any() else None
    exitp = stop_px if hit is not None else fwd_c[-1]
    raw = (exitp - entry) * direction / stop_dist
    return raw - COST_PTS / stop_dist


rows = []
for _, s in od.iterrows():
    day = Date.fromisoformat(s.date)
    f = rth(day)
    if f is None:
        continue
    orb = f[(f["et"] >= D.et_ts(day, OPEN_MS)) & (f["et"] < D.et_ts(day, DEC_MS))]
    fwd = f[f["et"] >= D.et_ts(day, DEC_MS)]
    if len(orb) < 5 or len(fwd) < 5:
        continue
    entry, atr, direction = float(s.entry), float(s.atr), int(np.sign(s.or_drive_atr))
    or_lo, or_hi = float(orb["low"].min()), float(orb["high"].max())
    level = or_lo if direction > 0 else or_hi
    fh, fl, fc = fwd["high"].to_numpy(float), fwd["low"].to_numpy(float), fwd["close"].to_numpy(float)
    rec = {"date": s.date, "yr": s.yr}
    for name, cfg in VARIANTS:
        sd = compute_stop(entry, direction, atr, level=(level if cfg["struct"] else None), k_fallback=cfg["k_fallback"])
        rec[name] = refill(fh, fl, fc, entry, direction, sd)
        rec[name + "_sd"] = sd
    rows.append(rec)

f = pd.DataFrame(rows)
print(f"{len(f)} opening-drive trades, {f.yr.nunique()} years\n")
print(f"{'variant':10s} {'E[R]':>7s} {'win%':>5s} {'medStop':>8s} {'NQ$risk':>8s} {'MNQ$risk':>9s} {'MNQ fits $200?':>14s} {'yrs+':>6s}")
for name, _ in VARIANTS:
    r = f[name].to_numpy()
    med_sd = float(np.median(f[name + "_sd"]))
    nq_risk, mnq_risk = med_sd * PV["NQ"], med_sd * PV["MNQ"]
    fits = "yes (%d lot)" % int(DD_BUDGET / mnq_risk) if mnq_risk <= DD_BUDGET else "NO"
    byyr = f.groupby("yr")[name].mean()
    print(f"{name:10s} {r.mean():>+7.4f} {(r>0).mean()*100:>4.0f}% {med_sd:>8.1f} {nq_risk:>8.0f} {mnq_risk:>9.0f} {fits:>14s} {int((byyr>0).sum())}/{len(byyr)}")
print("\n(E[R] = expectancy in risk units, net cost; pick max E[R] among variants where MNQ fits the budget)")
