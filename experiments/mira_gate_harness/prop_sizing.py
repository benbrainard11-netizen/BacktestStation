"""PROP-EVAL Monte Carlo on the operating point (reclaim + drift x zone + fixed-5R, ~25/mo, +0.20R).
Risk-normalized: each trade risks $X (size contracts so the structure stop = $X) -> P&L = R * $X.
Models the real 50k trailing-DD eval: start $50k, +R*$X per trade, trailing DD $2000 (floor = peak -
2000 until peak >= lock, then floor locks at $50k); PASS = reach the profit target before the floor is
breached. Bootstraps the operating-point R-series to estimate pass rate vs $X, then per-firm EV.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "backend"))
import legal_reclaim_bars as LB  # noqa: E402
import app.data.reader as R  # noqa: E402
import exit_sweep_op as EX  # noqa: E402  (reuse replay + the operating-point loader)

# 50k firms: (name, target_profit, trailing_dd, lock_threshold_profit, eval_fee, funded_value_or_proxy)
FIRMS = [
    ("apex", 3000, 2000, 2100, 90, 13000), ("topstep", 3000, 2000, 2000, 149, 8000),
    ("mffu", 3000, 2000, 2100, 157, 8000), ("tpt", 3000, 2000, 2000, 130, 8000),
    ("tradeify", 3000, 2000, 3000, 145, 8000), ("lucid", 3000, 2000, 2100, 90, 8000),
]
TARGET_PROFIT = 3000.0  # typical 50k eval target
N_MC = 4000
MAX_TRADES = 120        # ~5 months at 25/mo before giving up


def build_r_series(pct: float = 70) -> np.ndarray:
    """Operating-point trades' fixed-5R outcomes, time-ordered. pct = per-symbol drift threshold
    percentile (70 = deployed/conservative, 60 = the higher-frequency operating point)."""
    def load(f, fams=None):
        d = pd.read_parquet(HERE / "runs" / f); d = d[d["symbol"].isin(EX.LIQ)].copy()
        return d[d["level_family"].isin(fams)] if fams is not None else d
    std = load("mbp1_stack_features.parquet"); std = std[std["level_family"] != "opening_range"]
    fc = pd.concat([std, load("mbp1_stack_ndog_levels_full.parquet"),
                    load("mbp1_stack_stacked_failure_full.parquet", ["eqhigh_stack"])], ignore_index=True)
    fc["decision_ts_utc"] = pd.to_datetime(fc["decision_ts_utc"], utc=True); fc = fc.drop_duplicates(EX.KEY)
    fc["drift"] = pd.to_numeric(fc["w90_drift_dir_ticks"], errors="coerce"); fc["zf"] = fc["zone_5m_has"] == 1
    fc["yr"] = pd.to_datetime(fc["session_date"]).dt.year
    thr = {s: float(np.percentile(fc[(fc.symbol == s) & fc.zf & (fc.yr == 2026)]["drift"].dropna(), pct)) for s in EX.LIQ}
    op = fc[fc.zf & (fc.drift >= fc.symbol.map(thr))][EX.KEY].copy()
    src = pd.concat([pd.read_parquet(HERE / "runs" / f) for f in
                     ["legal_bars_full.parquet", "ndog_levels_full.parquet", "stacked_failure_full.parquet"]], ignore_index=True)
    src["decision_ts_utc"] = pd.to_datetime(src["decision_ts_utc"], utc=True); src["entry_ts_utc"] = pd.to_datetime(src["entry_ts_utc"], utc=True)
    op = op.merge(src[EX.KEY + ["entry_ts_utc", "entry_px", "stop_px", "risk_pts"]].drop_duplicates(EX.KEY), on=EX.KEY, how="left")
    op = op.dropna(subset=["entry_ts_utc", "entry_px", "stop_px", "risk_pts"]).sort_values("entry_ts_utc")
    rs = []
    for sym, g in op.groupby("symbol"):
        df = R.read_bars(symbol=sym, timeframe="1m", start=pd.to_datetime(g["session_date"]).min().strftime("%Y-%m-%d") if "session_date" in g else "2025-05-01",
                         end="2026-06-12", columns=["ts_event", "open", "high", "low", "close"])
        b = LB.Bars(df)
        for r in g.itertuples():
            i_ent = int(np.searchsorted(b.ts, int(pd.Timestamp(r.entry_ts_utc).value), "left"))
            if i_ent >= len(b.ts):
                continue
            d = 1 if r.side == "low" else -1
            out = EX.replay(d, i_ent, float(r.entry_px), float(r.stop_px), float(r.risk_pts), b, sym, 5.0, None, 1.0, None, 60)
            if out is not None:
                rs.append(out[0])
    return np.array(rs, float)


TRADES_PER_WEEK = 6.25  # ~27/mo on the operating point


def sim_path(R_series, risk_usd, dd, lock, milestones, max_trades=MAX_TRADES):
    """One bootstrapped account path. Returns ({milestone: #trades_to_reach or None}, blew_up)."""
    seq = R_series[np.random.randint(0, len(R_series), max_trades)]
    bal = peak = 0.0
    reached = {m: None for m in milestones}
    for t, r in enumerate(seq, 1):
        bal += r * risk_usd
        peak = max(peak, bal)
        floor = 0.0 if peak >= lock else (peak - dd)
        if bal <= floor:
            return reached, True
        for m in milestones:
            if reached[m] is None and bal >= m:
                reached[m] = t
    return reached, False


def eval_stats(R_series, risk_usd, target, dd, lock):
    """pass rate + time-to-pass (#trades + weeks) for the passing runs."""
    times = []
    for _ in range(N_MC):
        reached, _ = sim_path(R_series, risk_usd, dd, lock, [target])
        if reached[target] is not None:
            times.append(reached[target])
    pr = len(times) / N_MC
    t = np.array(times) if times else np.array([np.nan])
    return pr, np.median(t), np.percentile(t, 25), np.percentile(t, 75)


def funded_stats(R_series, risk_usd, dd, lock, targets):
    """For a funded account: P(reach target before blowup) + median #trades to it, per target."""
    out = {}
    for tgt in targets:
        hit, times = 0, []
        for _ in range(N_MC):
            reached, blew = sim_path(R_series, risk_usd, dd, lock, [tgt], max_trades=400)
            if reached[tgt] is not None:
                hit += 1; times.append(reached[tgt])
        out[tgt] = (hit / N_MC, np.median(times) if times else np.nan)
    return out


def wk(n):
    return n / TRADES_PER_WEEK


def main() -> int:
    Rs = build_r_series()
    print(f"operating-point fixed-5R series: n={len(Rs)} meanR={Rs.mean():+.3f} std={Rs.std():.2f} "
          f"win={100*(Rs>0).mean():.0f}% (max +{Rs.max():.1f}R / min {Rs.min():.1f}R); ~{TRADES_PER_WEEK}/wk")
    print(f"\n=== EVAL: pass rate + SPEED-to-pass vs $risk/trade (+$3000 target, $2k trailing DD) ===")
    best = {}
    for risk in (100, 150, 200, 250, 300):
        pr, med, p25, p75 = eval_stats(Rs, risk, TARGET_PROFIT, 2000, 2100)
        best[risk] = pr
        print(f"  ${risk:4d}/trade: pass {100*pr:4.1f}% | time-to-pass median {med:.0f} trades (~{wk(med):.1f} wk), "
              f"p25-p75 {p25:.0f}-{p75:.0f} trades ({wk(p25):.1f}-{wk(p75):.1f} wk)")
    bsz = max(best, key=best.get)
    print(f"\n=== FUNDED (after passing, ${bsz}/trade): how fast to a $4k / $10k balance? ===")
    print(f"  (funded acct, $2k trailing DD locks at +$2.1k; P(reach before blowup) + median speed)")
    fs = funded_stats(Rs, bsz, 2000, 2100, [4000, 10000])
    for tgt, (p, med) in fs.items():
        print(f"  +${tgt:5d}: reached {100*p:4.1f}% of funded accts | median {med:.0f} trades (~{wk(med):.1f} wk / ~{wk(med)/4.3:.1f} mo)")
    # sizing UP once funded (locked floor -> can risk more for faster extraction)
    print(f"\n  funded, sized UP to $350/trade (locked floor allows more risk):")
    fs2 = funded_stats(Rs, 350, 2000, 2100, [4000, 10000])
    for tgt, (p, med) in fs2.items():
        print(f"  +${tgt:5d}: reached {100*p:4.1f}% | median {med:.0f} trades (~{wk(med):.1f} wk)")
    print(f"\n  NOTE: bootstrap IID n={N_MC} (real streaks worse); rules simplified (no daily/consistency).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
