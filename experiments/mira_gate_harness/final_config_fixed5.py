"""FINAL CONFIG on the REAL exit: fixed-5R (+0.22R, the validated-optimal exit) instead of the
conservative trail_2R (+0.13). Replays fixed-5R per op trade keeping symbol/day/regime, then runs the
same block-bootstrap speed/safety DIAL + walk-forward pilot. Shows the CEILING, not the floor."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "backend"))
import legal_reclaim_bars as LB  # noqa: E402
import app.data.reader as R  # noqa: E402
import exit_sweep_op as EX  # noqa: E402  (replay)

RUNS = HERE / "runs"
LIQ = ["ES.c.0", "NQ.c.0", "YM.c.0"]
TARGET, DD, LOCK = 4000.0, 2000.0, 2100.0
MIN_SZ, MAX_SZ, MAX_DAYS, N_MC, FRAC = 14.0, 600.0, 450, 12000, 0.10
SYMW = {"YM.c.0": 1.6, "NQ.c.0": 1.1, "ES.c.0": 0.7}
REG_WITH, REG_CTR = 1.4, 0.7


def load(f, fams=None):
    d = pd.read_parquet(RUNS / f); d = d[d["symbol"].isin(LIQ)].copy()
    return d[d["level_family"].isin(fams)] if fams is not None else d


std = load("mbp1_stack_features.parquet"); std = std[std["level_family"] != "opening_range"]
fc = pd.concat([std, load("mbp1_stack_ndog_levels_full.parquet"),
                load("mbp1_stack_stacked_failure_full.parquet", ["eqhigh_stack"])], ignore_index=True)
fc["decision_ts_utc"] = pd.to_datetime(fc["decision_ts_utc"], utc=True)
fc = fc.drop_duplicates(EX.KEY)
fc["drift"] = pd.to_numeric(fc["w90_drift_dir_ticks"], errors="coerce")
fc = fc[(fc["zone_5m_has"] == 1) & fc["drift"].notna()].copy()
fc["yr"] = pd.to_datetime(fc["session_date"]).dt.year
fc["mo"] = pd.to_datetime(fc["session_date"]).dt.to_period("M")
# merge entry/stop/risk
src = pd.concat([pd.read_parquet(RUNS / f) for f in
                 ["legal_bars_full.parquet", "ndog_levels_full.parquet", "stacked_failure_full.parquet"]],
                ignore_index=True)
src["decision_ts_utc"] = pd.to_datetime(src["decision_ts_utc"], utc=True)
src["entry_ts_utc"] = pd.to_datetime(src["entry_ts_utc"], utc=True)
fc = fc.merge(src[EX.KEY + ["entry_ts_utc", "entry_px", "stop_px", "risk_pts"]].drop_duplicates(EX.KEY),
              on=EX.KEY, how="left").dropna(subset=["entry_ts_utc", "entry_px", "stop_px", "risk_pts"])

# replay fixed-5R + RTH open (regime) per symbol
print("replaying fixed-5R...", flush=True)
rows = []
for sym, g in fc.groupby("symbol"):
    df = R.read_bars(symbol=sym, timeframe="1m", start="2025-04-25", end="2026-06-12",
                     columns=["ts_event", "open", "high", "low", "close"])
    b = LB.Bars(df)
    et = pd.to_datetime(df["ts_event"], utc=True).dt.tz_convert(LB.ET)
    rth = df.assign(d=et.dt.date, tm=et.dt.time)
    rth = rth[rth["tm"] == LB.RTH_START].groupby("d")["open"].first().to_dict()
    for r in g.itertuples():
        i_ent = int(np.searchsorted(b.ts, int(pd.Timestamp(r.entry_ts_utc).value), "left"))
        if i_ent >= len(b.ts):
            continue
        d = 1 if r.side == "low" else -1
        out = EX.replay(d, i_ent, float(r.entry_px), float(r.stop_px), float(r.risk_pts), b, sym,
                        5.0, None, 1.0, None, 60)
        if out is None:
            continue
        o = rth.get(pd.Timestamp(r.session_date).date(), np.nan)
        trend = d * (float(r.level_price) - o)
        rows.append((sym, r.session_date, r.drift, r.yr, r.mo, out[0], trend))
z = pd.DataFrame(rows, columns=["symbol", "session_date", "drift", "yr", "mo", "R", "trend"]).dropna(subset=["trend"])
z["regw"] = np.where(z["trend"] > 0, REG_WITH, REG_CTR)
z["w"] = z["symbol"].map(SYMW) * z["regw"]; z["dt"] = pd.to_datetime(z["session_date"])
thr = {s: np.percentile(z[(z.symbol == s) & (z.yr == 2026)]["drift"], 60) for s in LIQ}
op = z[z.drift >= z.symbol.map(thr)].copy(); op["w"] /= op["w"].mean()
print(f"FIXED-5R op: {len(op)} trades, meanR {op['R'].mean():+.3f} (vs trail_2R +0.13), win {100*(op['R']>0).mean():.0f}%")

bdays = pd.date_range(op["dt"].min(), op["dt"].max(), freq="B")
by_day = {d: list(zip(g["w"], g["R"])) for d, g in op.groupby("dt")}
blocks = [np.array(by_day.get(d, []), dtype=float).reshape(-1, 2) for d in bdays]
all_tr = op[["w", "R"]].to_numpy(); daycounts = np.array([len(b) for b in blocks])


def run_path(get_day, rng, use_w, frac):
    bal = peak = 0.0
    for di in range(MAX_DAYS):
        block = get_day(rng)
        for k in range(len(block)):
            floor = 0.0 if peak >= LOCK else peak - DD
            w = block[k, 0] if use_w else 1.0
            size = min(MAX_SZ, max(MIN_SZ, frac * (bal - floor) * w))
            bal += block[k, 1] * size; peak = max(peak, bal)
            floor = 0.0 if peak >= LOCK else peak - DD
            if bal <= floor:
                return None, True
            if bal >= TARGET:
                return di + 1, False
    return None, False


def block_day(rng):
    return blocks[rng.integers(0, len(blocks))]


def iid_day(rng):
    n = daycounts[rng.integers(0, len(daycounts))]
    return all_tr[rng.integers(0, len(all_tr), n)] if n else np.empty((0, 2))


def mc(get_day, use_w, frac, label):
    rng = np.random.default_rng(7); hit, blew, tt = 0, 0, []
    for _ in range(N_MC):
        t, bl = run_path(get_day, rng, use_w, frac)
        if t is not None:
            hit += 1; tt.append(t)
        elif bl:
            blew += 1
    med = np.median(tt) if tt else np.nan
    print(f"  {label:36s} P(hit)={100*hit/N_MC:>4.0f}%  P(blow)={100*blew/N_MC:>4.0f}%  "
          f"median {med:>4.0f} bdays (~{med/21.7:.1f}mo)")


print(f"\n=== BLOCK-BOOTSTRAP DIAL on REAL fixed-5R exit (combined symbol x regime, honest clustering) ===")
for f in (0.08, 0.10, 0.15, 0.20, 0.25):
    mc(block_day, True, f, f"BLOCK combined @ {int(f*100)}%")
print("  ---")
mc(block_day, False, FRAC, "BLOCK flat @10% (ref)")
