"""EXIT SWEEP on the validated operating point (reclaim + drift x zone, working liquidity levels).
Replays a grid of SL/TP policies honestly (conservative: stop wins ties, gap-through fills at the
worse price, trail arms off PREVIOUS bars' hwm) on the operating-point trades' forward bars, and
reports each policy pooled + 2025-OOS. Stop (risk = 1R) is the structure swing stop; we vary the
TARGET, TRAIL, BREAKEVEN, and TIME. Best policy -> feeds prop-sizing.
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

LIQ = ["ES.c.0", "NQ.c.0", "YM.c.0"]
KEY = ["symbol", "session_date", "decision_ts_utc", "level_price", "side"]
_NS = 1_000_000_000

# policy grid: (name, target_R or None, arm_R or None=no trail, trail_R, be_R or None, hold_min)
POLICIES = [
    ("fixed_1.5R", 1.5, None, 1.0, None, 60), ("fixed_2R", 2.0, None, 1.0, None, 60),
    ("fixed_2.5R", 2.5, None, 1.0, None, 60), ("fixed_3R", 3.0, None, 1.0, None, 60),
    ("fixed_4R", 4.0, None, 1.0, None, 60),
    ("trail_1R", None, 1.0, 1.0, None, 60), ("trail_2R", None, 2.0, 1.0, None, 60),
    ("trail_3R", None, 3.0, 1.0, None, 60),
    ("BE1+3R", 3.0, None, 1.0, 1.0, 60), ("BE1+4R", 4.0, None, 1.0, 1.0, 60),
    ("fixed_3R+trail2", 3.0, 2.0, 1.0, None, 60),
    ("fixed_3R_120m", 3.0, None, 1.0, None, 120), ("fixed_3R_30m", 3.0, None, 1.0, None, 30),
    ("trail_2R_120m", None, 2.0, 1.0, None, 120),
]


def replay(d, i_ent, e_px, s_px, risk, b, sym, target_R, arm_R, trail_R, be_R, hold_min):
    end = min(len(b.ts), i_ent + hold_min + 10)
    sl = slice(i_ent, end)
    hi_f = (b.h[sl] if d == 1 else -b.l[sl]); lo_f = (b.l[sl] if d == 1 else -b.h[sl])
    op_f = d * b.o[sl]; cl_f = d * b.c[sl]; tns = b.ts[sl]
    if not len(hi_f):
        return None
    e_f, s_f = d * e_px, d * s_px
    i_time = LB.first_true(tns >= tns[0] + hold_min * 60 * _NS)
    hwm = np.empty(len(hi_f)); hwm[0] = e_f
    if len(hi_f) > 1:
        np.maximum(np.maximum.accumulate(hi_f)[:-1], e_f, out=hwm[1:])
    eff = np.full(len(hi_f), s_f)
    if arm_R is not None:  # trailing stop arms off previous-bar hwm
        armed = hwm >= e_f + arm_R * risk
        eff = np.where(armed, np.maximum(s_f, hwm - trail_R * risk), s_f)
    if be_R is not None:  # breakeven: once +be_R reached, stop -> entry
        be_armed = hwm >= e_f + be_R * risk
        eff = np.where(be_armed, np.maximum(eff, e_f), eff)
    i_stop = LB.first_true(lo_f <= eff)
    i_tgt = LB.first_true(hi_f >= e_f + target_R * risk) if target_R is not None else -1
    cand = [(i_time, "time"), (i_stop, "stop"), (i_tgt, "target"), (len(hi_f) - 1, "data_end")]
    prio = {"time": 0, "data_end": 0, "stop": 1, "target": 2}
    i, reason = min(((i, rs) for i, rs in cand if i >= 0), key=lambda t: (t[0], prio[t[1]]))
    if reason == "stop":
        ex = min(float(eff[i]), float(op_f[i]) if i > 0 else float(eff[i]))
        gross = (ex - e_f) / risk; cost = "trail" if eff[i] > s_f else "stop"
    elif reason == "target":
        gross = float(target_R); cost = "target"
    elif reason == "time":
        gross = (float(op_f[i]) - e_f) / risk; cost = "time"
    else:
        gross = (float(cl_f[i]) - e_f) / risk; cost = "stop"
    return LB.net_r(gross, cost, sym, risk), reason


def main() -> int:
    def load(f, fams=None):
        d = pd.read_parquet(HERE / "runs" / f); d = d[d["symbol"].isin(LIQ)].copy()
        if fams is not None:
            d = d[d["level_family"].isin(fams)]
        return d
    std = load("mbp1_stack_features.parquet"); std = std[std["level_family"] != "opening_range"]
    fc = pd.concat([std, load("mbp1_stack_ndog_levels_full.parquet"),
                    load("mbp1_stack_stacked_failure_full.parquet", ["eqhigh_stack"])], ignore_index=True)
    fc["decision_ts_utc"] = pd.to_datetime(fc["decision_ts_utc"], utc=True)
    fc = fc.drop_duplicates(KEY)
    fc["drift"] = pd.to_numeric(fc["w90_drift_dir_ticks"], errors="coerce"); fc["zf"] = fc["zone_5m_has"] == 1
    fc["yr"] = pd.to_datetime(fc["session_date"]).dt.year
    thr = {s: float(np.percentile(fc[(fc.symbol == s) & fc.zf & (fc.yr == 2026)]["drift"].dropna(), 70)) for s in LIQ}
    op = fc[fc.zf & (fc.drift >= fc.symbol.map(thr))][KEY + ["yr"]].copy()
    # merge entry/stop/risk from the source universes
    src = pd.concat([pd.read_parquet(HERE / "runs" / f) for f in
                     ["legal_bars_full.parquet", "ndog_levels_full.parquet", "stacked_failure_full.parquet"]], ignore_index=True)
    src["decision_ts_utc"] = pd.to_datetime(src["decision_ts_utc"], utc=True)
    src["entry_ts_utc"] = pd.to_datetime(src["entry_ts_utc"], utc=True)
    op = op.merge(src[KEY + ["entry_ts_utc", "entry_px", "stop_px", "risk_pts"]].drop_duplicates(KEY), on=KEY, how="left")
    op = op.dropna(subset=["entry_ts_utc", "entry_px", "stop_px", "risk_pts"])
    print(f"operating-point trades for exit sweep: {len(op)}")

    rows = {p[0]: [] for p in POLICIES}
    for sym, g in op.groupby("symbol"):
        df = R.read_bars(symbol=sym, timeframe="1m",
                         start=(pd.to_datetime(g["session_date"]).min()).strftime("%Y-%m-%d"),
                         end=(pd.to_datetime(g["session_date"]).max() + pd.Timedelta(days=3)).strftime("%Y-%m-%d"),
                         columns=["ts_event", "open", "high", "low", "close"])
        b = LB.Bars(df)
        for r in g.itertuples():
            i_ent = int(np.searchsorted(b.ts, int(pd.Timestamp(r.entry_ts_utc).value), "left"))
            if i_ent >= len(b.ts):
                continue
            d = 1 if r.side == "low" else -1
            for name, tR, aR, trR, beR, hold in POLICIES:
                out = replay(d, i_ent, float(r.entry_px), float(r.stop_px), float(r.risk_pts), b, sym, tR, aR, trR, beR, hold)
                if out is not None:
                    rows[name].append((out[0], r.yr))

    print(f"\n{'policy':16s} {'pooled':>22s} {'2025-OOS':>22s}")
    res = []
    for name, _, _, _, _, _ in POLICIES:
        x = pd.DataFrame(rows[name], columns=["R", "yr"])
        a, o = x["R"], x[x.yr == 2025]["R"]
        res.append((name, a.mean(), o.mean(), len(a)))
        print(f"{name:16s} n={len(a):4d} R={a.mean():+.3f} win={100*(a>0).mean():4.1f}% | "
              f"n={len(o):4d} R={o.mean():+.3f} win={100*(o>0).mean():4.1f}%")
    best = max(res, key=lambda t: t[2])
    print(f"\nBEST by 2025-OOS: {best[0]} (OOS R={best[2]:+.3f}, pooled {best[1]:+.3f}) "
          f"vs current trail_2R OOS +0.143")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
