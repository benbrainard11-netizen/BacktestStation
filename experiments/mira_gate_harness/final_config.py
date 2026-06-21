"""FINAL CONFIG end-to-end: combined SYMBOL x REGIME sizing at 10% buffer (round-trip protection),
through BOTH the block-bootstrap (honest clustered distribution) AND the walk-forward pilot (realized
path, expanding-window calibration). Combined weight = symbol_w[sym] * regime_w(trend) normalized to
freq-weighted mean 1; both axes shuffle-gated earlier (drift cut). Robust BINARY regime weight (with-
trend vs counter) not the fitted quartile map. Conservative trail_2R exit. FRAC=10% (MC said ~as fast,
far safer than 15%; the realized round-trip is why)."""
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
MIN_SZ, MAX_SZ, MAX_DAYS, MAX_TR, N_MC, FRAC = 14.0, 600.0, 450, 1500, 12000, 0.10
SYMW = {"YM.c.0": 1.6, "NQ.c.0": 1.1, "ES.c.0": 0.7}
REG_WITH, REG_CTR = 1.4, 0.7  # with-trend vs counter-trend (robust binary)


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
fc["mo"] = pd.to_datetime(fc["session_date"]).dt.to_period("M")  # for walk-forward recalibration
thr = {s: np.percentile(fc[(fc.symbol == s) & (fc.yr == 2026)]["drift"], 60) for s in LIQ}
op = fc[fc.drift >= fc.symbol.map(thr)].copy()

# regime (trend-align) per trade from RTH opens
rth = {}
for sym in LIQ:
    b = R.read_bars(symbol=sym, timeframe="1m", start="2025-04-25", end="2026-06-12", columns=["ts_event", "open"])
    t = pd.to_datetime(b["ts_event"], utc=True).dt.tz_convert(LB.ET)
    o = b.assign(d=t.dt.date, tm=t.dt.time)
    o = o[o["tm"] == LB.RTH_START].groupby("d")["open"].first()
    for d, px in o.items():
        rth[(sym, d)] = float(px)
op["d"] = pd.to_datetime(op["session_date"]).dt.date
op["dir"] = np.where(op["side"] == "low", 1, -1)
op["trend"] = op["dir"] * (op["level_price"].astype(float) - [rth.get((s, d), np.nan) for s, d in zip(op["symbol"], op["d"])])
op = op.dropna(subset=["trend"]).sort_values("decision_ts_utc")
op["regw"] = np.where(op["trend"] > 0, REG_WITH, REG_CTR)
op["w"] = op["symbol"].map(SYMW) * op["regw"]
op["w"] /= op["w"].mean()  # freq-weighted mean 1
op["dt"] = pd.to_datetime(op["session_date"]); op["mo"] = op["dt"].dt.to_period("M")
print(f"FINAL CONFIG: {len(op)} op trades, meanR {op['R'].mean():+.3f}, FRAC {int(FRAC*100)}%, "
      f"combined symbol x regime weight (mean {op['w'].mean():.2f}, range {op['w'].min():.2f}-{op['w'].max():.2f})")

# ---------- block-bootstrap ----------
bdays = pd.date_range(op["dt"].min(), op["dt"].max(), freq="B")
by_day = {d: list(zip(g["w"], g["R"])) for d, g in op.groupby("dt")}
blocks = [np.array(by_day.get(d, []), dtype=float).reshape(-1, 2) for d in bdays]
all_tr = op[["w", "R"]].to_numpy()
daycounts = np.array([len(b) for b in blocks])


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


def iid_day(rng):
    n = daycounts[rng.integers(0, len(daycounts))]
    return all_tr[rng.integers(0, len(all_tr), n)] if n else np.empty((0, 2))


def block_day(rng):
    return blocks[rng.integers(0, len(blocks))]


def mc(get_day, use_w, frac, label):
    rng = np.random.default_rng(7); hit, blew, tt = 0, 0, []
    for _ in range(N_MC):
        t, b = run_path(get_day, rng, use_w, frac)
        if t is not None:
            hit += 1; tt.append(t)
        elif b:
            blew += 1
    med = np.median(tt) if tt else np.nan
    print(f"  {label:40s} P(hit)={100*hit/N_MC:>4.0f}%  P(blow)={100*blew/N_MC:>4.0f}%  "
          f"median {med:>4.0f} bdays (~{med/21.7:.1f}mo)")


print(f"\n=== BLOCK-BOOTSTRAP speed/safety DIAL (combined symbol x regime, honest clustering) ===")
for f in (0.08, 0.10, 0.15, 0.20, 0.25):
    mc(block_day, True, f, f"BLOCK combined @ {int(f*100)}% buffer")
print("  ---")
mc(iid_day, True, FRAC, "IID combined @10% (optimistic ref)")
mc(block_day, False, FRAC, "BLOCK flat @10% (no quality axes, ref)")

# ---------- walk-forward pilot ----------
months = sorted(op["mo"].unique())
wmean_sym = fc["symbol"].map(SYMW).mean()
live = []
for moi in months[3:]:
    hist = op[op["mo"] < moi]  # (threshold already applied to op; recalibrate per month for honesty)
    base = fc[fc["mo"] < moi]
    th = {s: (np.percentile(base[base.symbol == s]["drift"], 60) if (base.symbol == s).sum() >= 30 else np.inf) for s in LIQ}
    cur = fc[(fc["mo"] == moi) & (fc["drift"] >= fc["symbol"].map(th))].copy()
    live.append(cur)
sig = pd.concat(live).sort_values("decision_ts_utc")
# attach regime + weight to the walk-forward signals
sig["d"] = pd.to_datetime(sig["session_date"]).dt.date
sig["dir"] = np.where(sig["side"] == "low", 1, -1)
sig["trend"] = sig["dir"] * (sig["level_price"].astype(float) - [rth.get((s, d), np.nan) for s, d in zip(sig["symbol"], sig["d"])])
sig = sig.dropna(subset=["trend"])
sig["w"] = sig["symbol"].map(SYMW) * np.where(sig["trend"] > 0, REG_WITH, REG_CTR)
sig["w"] /= sig["w"].mean()
bal = peak = 0.0; maxdd = 0.0; hit_at = None; blew = False; n = 0
for r in sig.itertuples():
    n += 1
    floor = 0.0 if peak >= LOCK else peak - DD
    size = min(MAX_SZ, max(MIN_SZ, FRAC * (bal - floor) * r.w))
    bal += r.R * size; peak = max(peak, bal); maxdd = min(maxdd, bal - peak)
    floor = 0.0 if peak >= LOCK else peak - DD
    if bal <= floor:
        blew = True; break
    if bal >= TARGET and hit_at is None:
        hit_at = n
print(f"\n=== WALK-FORWARD PILOT, final config @10% ({len(sig)} signals ~{len(sig)/(len(months)-3):.0f}/mo, "
      f"meanR {sig['R'].mean():+.3f}) ===")
print(f"  final ${bal:,.0f} | peak ${peak:,.0f} | max DD ${maxdd:,.0f} | blew {blew} | "
      f"hit +$4k: {'trade '+str(hit_at) if hit_at else 'NO (max $'+format(peak,',.0f')+')'}")
