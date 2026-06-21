"""BLOCK-BOOTSTRAP harden (the make-or-break test). IID bootstrap assumes trades arrive independently;
they don't -- losses CLUSTER on bad regime days (up to 9/day, 18% of days 3+). This resamples whole
DAYS (preserving the real within-day trade set + correlation), runs the funded account to +$4k under the
deployed DYNAMIC + SYMBOL sizing, and adds the firm rules (trailing DD $2000 lock@+$2100 = hard fail;
optional DAILY-LOSS STOP). Compares IID vs BLOCK to isolate the cost of clustering, and shows whether
the daily-stop + dynamic sizing contain it. Outcome col = trail_2R (conservative; fixed-5R is rosier)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
LIQ = ["ES.c.0", "NQ.c.0", "YM.c.0"]
TARGET, DD, LOCK = 4000.0, 2000.0, 2100.0
MIN_SZ, MAX_SZ, MAX_DAYS, N_MC = 14.0, 600.0, 450, 12000
FRAC = 0.15
SYMW = {"YM.c.0": 1.6, "NQ.c.0": 1.1, "ES.c.0": 0.7}


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
op = fc[fc.drift >= fc.symbol.map(thr)].copy().sort_values(["session_date", "decision_ts_utc"])
# freq-weighted symbol-weight normalization so avg risk matches FLAT (fair)
wmean = op["symbol"].map(SYMW).mean()
SYMWN = {k: v / wmean for k, v in SYMW.items()}

# day-blocks: per business day, the ordered list of (symbol, R); include BLANK business days
days = pd.date_range(op["session_date"].min(), op["session_date"].max(), freq="B")
op["d"] = pd.to_datetime(op["session_date"])
by_day = {d: list(zip(g["symbol"], g["R"])) for d, g in op.groupby("d")}
blocks = [np.array([(SYMWN[s], r) for s, r in by_day.get(d, [])], dtype=float).reshape(-1, 2) for d in days]
all_trades = np.array([(SYMWN[s], r) for s, r in zip(op["symbol"], op["R"])])  # for IID
daycounts = np.array([len(b) for b in blocks])  # empirical daily-count distribution (incl 0s)
print(f"op: {len(op)} trades over {len(days)} business days ({(daycounts>0).mean()*100:.0f}% active, "
      f"max {daycounts.max()}/day); meanR {op['R'].mean():+.3f}")
ACT_PER_MO = (daycounts > 0).sum() / ((op['d'].max() - op['d'].min()).days / 30.4)


def run_path(get_day, rng, use_symw, daily_stop):
    bal = peak = 0.0
    for di in range(MAX_DAYS):
        block = get_day(rng)  # array of (symw, R)
        daypnl = 0.0
        for k in range(len(block)):
            if daily_stop and daypnl <= -daily_stop:
                break
            floor = 0.0 if peak >= LOCK else peak - DD
            w = block[k, 0] if use_symw else 1.0
            size = min(MAX_SZ, max(MIN_SZ, FRAC * (bal - floor) * w))
            pnl = block[k, 1] * size
            bal += pnl; daypnl += pnl
            peak = max(peak, bal)
            floor = 0.0 if peak >= LOCK else peak - DD
            if bal <= floor:
                return None, True
            if bal >= TARGET:
                return di + 1, False
    return None, False


def iid_day(rng):  # same daily-count distribution, but trades are independent draws (no clustering)
    n = daycounts[rng.integers(0, len(daycounts))]
    if n == 0:
        return np.empty((0, 2))
    return all_trades[rng.integers(0, len(all_trades), n)]


def block_day(rng):
    return blocks[rng.integers(0, len(blocks))]


def sim(get_day, use_symw, daily_stop, seed=7):
    rng = np.random.default_rng(seed)
    hit, blew, tt = 0, 0, []
    for _ in range(N_MC):
        t, b = run_path(get_day, rng, use_symw, daily_stop)
        if t is not None:
            hit += 1; tt.append(t)
        elif b:
            blew += 1
    med = np.median(tt) if tt else np.nan
    return hit / N_MC, blew / N_MC, med


def row(label, get_day, use_symw, ds):
    p, pb, med = sim(get_day, use_symw, ds)
    mo = med / ACT_PER_MO * (daycounts > 0).mean() if med == med else np.nan  # business-days -> months
    moc = (med / 21.7) if med == med else np.nan  # business days / ~21.7 per mo
    print(f"  {label:42s} P(hit)={100*p:>4.0f}%  P(blow)={100*pb:>4.0f}%  "
          f"median {med:>4.0f} bdays (~{moc:.1f}mo)")


print(f"\n=== IID vs BLOCK (dynamic 15% buffer x symbol-weight, NO daily stop) ===")
row("IID (independent trades)", iid_day, True, None)
row("BLOCK (real day clusters)  <-- honest", block_day, True, None)
print(f"\n=== under BLOCK clustering: does the dynamic+symbol model still beat flat? ===")
row("BLOCK flat (buffer only, no symw)", block_day, False, None)
row("BLOCK dynamic x symbol", block_day, True, None)
print(f"\n=== BLOCK + DAILY-LOSS STOP (cap a bad cluster day) -- the clustering defense ===")
for ds in (2000, 1500, 1000, 750):
    row(f"BLOCK dyn x symw, daily-stop ${ds}", block_day, True, ds)
print(f"\nNOTE: trail_2R exit (conservative). BLOCK preserves within-day loss correlation; the gap from "
      f"IID = the real cost of clustering. Daily-stop caps a bad day before it breaches the trailing DD.")
