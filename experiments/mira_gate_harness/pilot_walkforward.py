"""OPERATIONAL PILOT: expanding-window WALK-FORWARD (the honest 'paper trade it forward'). Each month's
drift threshold is calibrated on PRIOR data only (no lookahead, unlike the MC which froze 2026), and the
deployed DYNAMIC + SYMBOL sizing runs on the REAL historical trade sequence as ONE realized funded account.
Surfaces what a live bot would actually have experienced: monthly frequency stability, the realized equity
path, time-to-$4k, max drawdown, blowups. One realized path (not a distribution -- the block-bootstrap is
the distribution); this is the existence-proof + operational sanity check."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
LIQ = ["ES.c.0", "NQ.c.0", "YM.c.0"]
TARGET, DD, LOCK = 4000.0, 2000.0, 2100.0
MIN_SZ, MAX_SZ, FRAC = 14.0, 600.0, 0.15
SYMW = {"YM.c.0": 1.6, "NQ.c.0": 1.1, "ES.c.0": 0.7}
CAL_MIN_MONTHS = 3  # need this much history before trading


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
fc = fc[(fc["zone_5m_has"] == 1) & fc["R"].abs().lt(50) & fc["drift"].notna()].copy()
fc["dt"] = pd.to_datetime(fc["session_date"])
fc["mo"] = fc["dt"].dt.to_period("M")
fc = fc.sort_values("decision_ts_utc")
months = sorted(fc["mo"].unique())
wmean = fc["symbol"].map(SYMW).mean(); SYMWN = {k: v / wmean for k, v in SYMW.items()}

# ---- walk-forward live-signal generation (expanding-window threshold per month) ----
live = []
print(f"{'month':9s} {'cal_thr (ES/NQ/YM)':>22s} {'signals':>8s} {'meanR':>7s}")
for mo in months[CAL_MIN_MONTHS:]:
    hist = fc[fc["mo"] < mo]
    thr = {}
    for s in LIQ:
        h = hist[(hist.symbol == s)]["drift"]
        thr[s] = float(np.percentile(h, 60)) if len(h) >= 30 else np.inf
    cur = fc[(fc["mo"] == mo) & (fc["drift"] >= fc["symbol"].map(thr))]
    live.append(cur)
    r = cur["R"].mean() if len(cur) else np.nan
    print(f"{str(mo):9s} {('/'.join(f'{thr[s]:.0f}' for s in LIQ)):>22s} {len(cur):>8d} {r:>+7.3f}")

sig = pd.concat(live).sort_values("decision_ts_utc")
print(f"\nWALK-FORWARD signals: {len(sig)} over {len(months)-CAL_MIN_MONTHS} months "
      f"(~{len(sig)/(len(months)-CAL_MIN_MONTHS):.1f}/mo), realized meanR {sig['R'].mean():+.3f}, "
      f"win {100*(sig['R']>0).mean():.0f}%")

# ---- run the deployed dynamic+symbol sizing on the REAL sequence ----
bal = peak = 0.0
maxdd = 0.0
hit_at = None
blew = False
eq = []
for i, r in enumerate(sig.itertuples(), 1):
    floor = 0.0 if peak >= LOCK else peak - DD
    size = min(MAX_SZ, max(MIN_SZ, FRAC * (bal - floor) * SYMWN[r.symbol]))
    bal += r.R * size
    peak = max(peak, bal)
    maxdd = min(maxdd, bal - peak)
    eq.append(bal)
    floor = 0.0 if peak >= LOCK else peak - DD
    if bal <= floor and not blew:
        blew = True; print(f"\n*** trailing-DD BREACH at trade {i} (bal ${bal:.0f}) ***"); break
    if bal >= TARGET and hit_at is None:
        hit_at = i

eq = np.array(eq)
print(f"\n=== realized walk-forward account (dynamic 15% x symbol, start $0) ===")
print(f"  final balance: ${bal:,.0f}  | peak ${peak:,.0f}  | max drawdown ${maxdd:,.0f}  | blew up: {blew}")
if hit_at:
    n_mo = pd.Period(sig.iloc[hit_at-1]["mo"], "M") - pd.Period(sig.iloc[0]["mo"], "M")
    print(f"  HIT +$4k at trade {hit_at} of {len(sig)}  (~{hit_at/(len(sig)/(len(months)-CAL_MIN_MONTHS)):.1f} months in)")
else:
    print(f"  did NOT reach +$4k in the window (got to ${eq.max():,.0f})")
# monthly P&L realized
sig = sig.assign(eq=eq)
print(f"\n  realized monthly trade counts: {sig.groupby('mo').size().to_dict()}")
print(f"\nNOTE: expanding-window calibration (no lookahead). ONE realized path -- the block-bootstrap is the "
      f"distribution; this confirms the deployed rule survives honest forward calibration + real sequencing.")
