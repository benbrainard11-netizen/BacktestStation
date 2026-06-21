"""EDGE-PROPORTIONAL sizing: risk more on high-quality setups, less on low-quality (Ben's idea).
Quality signal = drift magnitude (validated monotonic edge predictor). Calibrate weight(drift) on
2026 DESIGN (drift quintile -> relative edge), apply to 2025 OOS, run funded MC. Compare FLAT vs
QUALITY-WEIGHTED vs SHUFFLE control (drift<->R link broken -> must lose the advantage). Weights
normalized to mean 1 on OOS so it's a fair ALLOCATION test (same average risk), not just "risk more".
Also tests SYMBOL weighting (YM-led) and drift+symbol combined."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
LIQ = ["ES.c.0", "NQ.c.0", "YM.c.0"]
TARGET, DD, LOCK = 4000.0, 2000.0, 2100.0
MIN_SZ, MAX_SZ, MAX_TRADES, N_MC = 14.0, 600.0, 1500, 12000
FRAC = 0.15  # buffer-fraction (the balanced dynamic rule)
MONTHS_OOS = 8.0  # 2025-05..2025-12 ~ fresh OOS span


def load(f, fams=None):
    d = pd.read_parquet(RUNS / f); d = d[d["symbol"].isin(LIQ)].copy()
    return d[d["level_family"].isin(fams)] if fams is not None else d


std = load("mbp1_stack_features.parquet"); std = std[std["level_family"] != "opening_range"]
fc = pd.concat([std, load("mbp1_stack_ndog_levels_full.parquet"),
                load("mbp1_stack_stacked_failure_full.parquet", ["eqhigh_stack"])], ignore_index=True)
fc = fc.drop_duplicates(["symbol", "session_date", "decision_ts_utc", "level_price", "side"])
fc["drift"] = pd.to_numeric(fc["w90_drift_dir_ticks"], errors="coerce")
fc["zf"] = fc["zone_5m_has"] == 1
fc["R"] = pd.to_numeric(fc["trail_2R"], errors="coerce")
fc["yr"] = pd.to_datetime(fc["session_date"]).dt.year
fc = fc[fc.zf & fc["R"].abs().lt(50) & fc["drift"].notna()].copy()
# operating point = drift >= 60th pctile (per symbol, design)
thr = {s: np.percentile(fc[(fc.symbol == s) & (fc.yr == 2026)]["drift"], 60) for s in LIQ}
op = fc[fc.drift >= fc.symbol.map(thr)].copy()
des, oos = op[op.yr == 2026], op[op.yr == 2025]
print(f"operating point: design(2026) {len(des)}, OOS(2025) {len(oos)}; meanR oos {oos['R'].mean():+.3f}")

# calibrate weight(drift) on DESIGN: quintile -> relative edge (clamped), boundaries frozen
qb = des["drift"].quantile([.2, .4, .6, .8]).values
des_q = np.digitize(des["drift"], qb)
qmean = des.groupby(des_q)["R"].mean()
base = des["R"].mean()
wmap = {q: float(np.clip(qmean.get(q, base) / base if base > 0 else 1.0, 0.3, 2.5)) for q in range(5)}
print(f"DESIGN drift-quintile meanR: {dict((q, round(qmean.get(q, np.nan),3)) for q in range(5))}")
print(f"-> weight map (clamped): {dict((q, round(w,2)) for q,w in wmap.items())}")

oos_q = np.digitize(oos["drift"].values, qb)
w_drift = np.array([wmap[q] for q in oos_q])
w_sym = oos["symbol"].map({"YM.c.0": 1.6, "NQ.c.0": 1.1, "ES.c.0": 0.7}).values  # YM-led, frozen direction
R = oos["R"].values


def norm(w):  # mean-1 so average risk matches FLAT (fair allocation comparison)
    return w / w.mean()


def sim(R, w, f, rng):
    n = len(R); ri = rng.integers(0, n, MAX_TRADES)
    bal = peak = 0.0
    for t in range(MAX_TRADES):
        floor = 0.0 if peak >= LOCK else peak - DD
        size = min(MAX_SZ, max(MIN_SZ, f * (bal - floor) * w[ri[t]]))
        bal += R[ri[t]] * size
        peak = max(peak, bal); floor = 0.0 if peak >= LOCK else peak - DD
        if bal <= floor:
            return None, True
        if bal >= TARGET:
            return t + 1, False
    return None, False


def stats(R, w, label):
    rng = np.random.default_rng(7)
    hit, blew, tt = 0, 0, []
    for _ in range(N_MC):
        t, b = sim(R, w, FRAC, rng)
        if t is not None:
            hit += 1; tt.append(t)
        elif b:
            blew += 1
    med = np.median(tt) if tt else np.nan
    print(f"  {label:34s} P(hit)={100*hit/N_MC:>4.0f}%  P(blow)={100*blew/N_MC:>4.0f}%  "
          f"median {med:>4.0f}tr (~{med/(len(oos)/MONTHS_OOS):.1f}mo)")


print(f"\n=== funded MC to +$4k, buffer-frac {int(FRAC*100)}%, OOS 2025 (weights mean-1 = fair) ===")
stats(R, np.ones(len(R)), "FLAT (size by buffer only)")
stats(R, norm(w_drift), "QUALITY: drift-weighted")
stats(R, norm(w_sym), "QUALITY: symbol-weighted (YM-led)")
stats(R, norm(w_drift * w_sym), "QUALITY: drift x symbol")
rng = np.random.default_rng(1)
stats(R, norm(rng.permutation(w_drift)), "SHUFFLE control (drift<->R broken)")
print(f"\nVERDICT: quality sizing is REAL only if drift/symbol BEAT flat AND shuffle ~= flat.")
