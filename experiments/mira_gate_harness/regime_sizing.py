"""REGIME-weighted sizing (Ben's last quality axis): risk more when the day's REGIME favors the setup.
Regime = intraday TREND ALIGNMENT at the trade -- trend_align = dir_sign * (level_price - RTH_open)/tick
(>0 = with-trend continuation, <0 = counter-trend fade). Prior: regime-aligned reclaims pay better
(memory: down-days favor shorts). Calibrate weight(trend) on 2026 DESIGN, apply to 2025 OOS, funded MC,
GATE with shuffle control (trend<->R broken must lose the edge). Same discipline as quality_sizing.py."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "backend"))
import legal_reclaim_bars as LB  # noqa: E402
import app.data.reader as R  # noqa: E402

RUNS = HERE / "runs"
LIQ = ["ES.c.0", "NQ.c.0", "YM.c.0"]
TARGET, DD, LOCK = 4000.0, 2000.0, 2100.0
MIN_SZ, MAX_SZ, MAX_TRADES, N_MC, FRAC = 14.0, 600.0, 1500, 12000, 0.15


def load(f, fams=None):
    d = pd.read_parquet(RUNS / f); d = d[d["symbol"].isin(LIQ)].copy()
    return d[d["level_family"].isin(fams)] if fams is not None else d


std = load("mbp1_stack_features.parquet"); std = std[std["level_family"] != "opening_range"]
fc = pd.concat([std, load("mbp1_stack_ndog_levels_full.parquet"),
                load("mbp1_stack_stacked_failure_full.parquet", ["eqhigh_stack"])], ignore_index=True)
fc["decision_ts_utc"] = pd.to_datetime(fc["decision_ts_utc"], utc=True)
fc = fc.drop_duplicates(["symbol", "session_date", "decision_ts_utc", "level_price", "side"])
fc["drift"] = pd.to_numeric(fc["w90_drift_dir_ticks"], errors="coerce")
fc["R"] = pd.to_numeric(fc["trail_2R"], errors="coerce")
fc["yr"] = pd.to_datetime(fc["session_date"]).dt.year
fc = fc[(fc["zone_5m_has"] == 1) & fc["R"].abs().lt(50) & fc["drift"].notna()].copy()
thr = {s: np.percentile(fc[(fc.symbol == s) & (fc.yr == 2026)]["drift"], 60) for s in LIQ}
op = fc[fc.drift >= fc.symbol.map(thr)].copy()

# RTH open per (symbol, date) from 1m bars
print("reading RTH opens...", flush=True)
rth_open = {}
for sym in LIQ:
    b = R.read_bars(symbol=sym, timeframe="1m", start="2025-04-25", end="2026-06-12",
                    columns=["ts_event", "open"])
    t = pd.to_datetime(b["ts_event"], utc=True).dt.tz_convert(LB.ET)
    b = b.assign(d=t.dt.date, tm=t.dt.time)
    o = b[b["tm"] == LB.RTH_START].groupby("d")["open"].first()
    for d, px in o.items():
        rth_open[(sym, d)] = float(px)
op["d"] = pd.to_datetime(op["session_date"]).dt.date
op["rth_open"] = [rth_open.get((s, d), np.nan) for s, d in zip(op["symbol"], op["d"])]
op["dir"] = np.where(op["side"] == "low", 1, -1)
op["tick"] = op["symbol"].map(LB.TICK)
op["trend"] = op["dir"] * (op["level_price"].astype(float) - op["rth_open"]) / op["tick"]
op = op.dropna(subset=["trend"])
des, oos = op[op.yr == 2026], op[op.yr == 2025]
print(f"op with regime: design {len(des)}, OOS {len(oos)}; trend>0 (with-trend) {100*(op['trend']>0).mean():.0f}%")

# calibrate weight(trend) on DESIGN: with-trend vs counter-trend edge
for lab, m in [("with-trend (>0)", des["trend"] > 0), ("counter-trend (<=0)", des["trend"] <= 0)]:
    print(f"  DESIGN {lab}: meanR {des[m]['R'].mean():+.3f} (n{m.sum()})")
qb = des["trend"].quantile([.25, .5, .75]).values
des_q = np.digitize(des["trend"], qb)
qmean = des.groupby(des_q)["R"].mean(); base = des["R"].mean()
wmap = {q: float(np.clip(qmean.get(q, base) / base if base > 0 else 1, 0.3, 2.5)) for q in range(4)}
print(f"  DESIGN trend-quartile meanR: {dict((q, round(qmean.get(q, np.nan),3)) for q in range(4))} "
      f"-> weights {dict((q, round(w,2)) for q,w in wmap.items())}")

oos_q = np.digitize(oos["trend"].values, qb)
w_reg = np.array([wmap[q] for q in oos_q]); R_oos = oos["R"].values


def norm(w):
    return w / w.mean()


def sim(R, w, rng):
    n = len(R); ri = rng.integers(0, n, MAX_TRADES); bal = peak = 0.0
    for t in range(MAX_TRADES):
        floor = 0.0 if peak >= LOCK else peak - DD
        size = min(MAX_SZ, max(MIN_SZ, FRAC * (bal - floor) * w[ri[t]]))
        bal += R[ri[t]] * size; peak = max(peak, bal); floor = 0.0 if peak >= LOCK else peak - DD
        if bal <= floor:
            return None, True
        if bal >= TARGET:
            return t + 1, False
    return None, False


def stats(R, w, label):
    rng = np.random.default_rng(7); hit, blew, tt = 0, 0, []
    for _ in range(N_MC):
        t, b = sim(R, w, rng)
        if t is not None:
            hit += 1; tt.append(t)
        elif b:
            blew += 1
    med = np.median(tt) if tt else np.nan
    print(f"  {label:36s} P(hit)={100*hit/N_MC:>4.0f}%  P(blow)={100*blew/N_MC:>4.0f}%  "
          f"median {med:>4.0f}tr (~{med/(len(oos)/8):.1f}mo)")


print(f"\n=== funded MC to +$4k, buffer-frac 15%, OOS 2025 (IID; regime weights mean-1) ===")
stats(R_oos, np.ones(len(R_oos)), "FLAT")
stats(R_oos, norm(w_reg), "REGIME-weighted (trend-align)")
rng = np.random.default_rng(1)
stats(R_oos, norm(rng.permutation(w_reg)), "SHUFFLE control")
print(f"\nVERDICT: regime sizing REAL only if it beats FLAT AND shuffle ~= FLAT.")
