"""EXIT LAB -- in-depth trade management, tick-honest. We've only ever tested ONE exit (fixed 3R, all-or-nothing).
Here we re-walk each gate-selected trade's ACTUAL MBP-1 tick path from the honest entry and simulate real exit
policies, in R-space (stop = -1R by construction), then compare honest tick-R per policy:
  fixed 1.5/2/3/4/5R   -- is 3R even the right target?
  trail1               -- activate at +1R, trail 1R behind the high-water-mark (let winners run)
  be1t3                -- breakeven stop after +1R, target 3R (kill the give-backs)
  part15               -- book half at +1.5R, runner on BE + 1R-trail
Same no-lookahead entry/stop as fill_realism (stop = 4 ticks past extreme). Day-block CI.
Run: backend/.venv/Scripts/python.exe exit_lab.py [EVENTS_TF] [SYMBOL] [SAMPLE_LIMIT]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(RT / "backend"))
from app.data.reader import read_mbp1_trading_day  # noqa: E402
from reclaim_entry import DEF, SPEC, boot  # noqa: E402
from smt_economics import wf_gate  # noqa: E402

TARGET, MAXH, BUF = 3.0, 120, 4            # gate target (for selection), horizon min, stop buffer (ticks past extreme)


def _first(mask):
    idx = np.where(mask)[0]
    return int(idx[0]) if len(idx) else None


def _trail(Rp, act, d):
    stop, hwm, on = -1.0, -1e9, False
    for r in Rp:
        if r <= stop:
            return stop
        hwm = max(hwm, r)
        if not on and hwm >= act:
            on = True
        if on:
            stop = max(stop, hwm - d)
    return float(Rp[-1])


def _be(Rp, act, k):
    stop, hwm = -1.0, -1e9
    for r in Rp:
        if r <= stop:
            return stop
        if r >= k:
            return k
        hwm = max(hwm, r)
        if hwm >= act:
            stop = max(stop, 0.0)
    return float(Rp[-1])


def _runner_be_trail(Rp, d):
    stop, hwm = 0.0, -1e9
    for r in Rp:
        if r <= stop:
            return stop
        hwm = max(hwm, r)
        stop = max(stop, hwm - d)
    return float(Rp[-1])


def _partial(Rp, p_at, frac, d):
    hi, si = _first(Rp >= p_at), _first(Rp <= -1.0)
    if hi is None:
        return -1.0 if si is not None else float(Rp[-1])
    if si is not None and si < hi:
        return -1.0
    return frac * p_at + (1.0 - frac) * _runner_be_trail(Rp[hi:], d)


def run_policies(Rp, cost_r):
    si = _first(Rp <= -1.0)
    out = {}
    for k in (1.5, 2.0, 3.0, 4.0, 5.0):
        ti = _first(Rp >= k)
        if si is not None and (ti is None or si < ti):
            out[f"fix{k:g}"] = -1.0
        elif ti is not None:
            out[f"fix{k:g}"] = k
        else:
            out[f"fix{k:g}"] = float(Rp[-1])
    out["trail1"] = _trail(Rp, 1.0, 1.0)
    out["be1t3"] = _be(Rp, 1.0, 3.0)
    out["part15"] = _partial(Rp, 1.5, 0.5, 1.0)
    return {k: v - cost_r for k, v in out.items()}


def path_R(e, ts, px, sym):
    ptv, cost, tick = SPEC.get(sym, DEF)
    level, extreme = float(e["level_price"]), float(e["sweep.5m.sweep_extreme_price"])
    long = e["smt_anchor_side"] == "low"
    ext_ts = pd.Timestamp(e["sweep.5m.sweep_extreme_ts_utc"]).to_datetime64()
    i0 = int(np.searchsorted(ts, ext_ts))
    i1 = int(np.searchsorted(ts, ext_ts + np.timedelta64(MAXH, "m")))
    w = px[i0:i1]
    if len(w) == 0:
        return None
    cross = np.where(w >= level)[0] if long else np.where(w <= level)[0]
    if len(cross) == 0:
        return None
    wa = w[cross[0]:]
    entry = float(wa[0]) + (tick if long else -tick)
    stop = extreme - BUF * tick if long else extreme + BUF * tick
    risk = (entry - stop) if long else (stop - entry)
    if risk <= 0:
        return None
    Rp = ((wa - entry) / risk) if long else ((entry - wa) / risk)
    return run_policies(Rp, cost / (risk * ptv))


def main() -> int:
    ev = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out" / "events_es_tf.parquet"
    sym = sys.argv[2] if len(sys.argv) > 2 else "ES.c.0"
    lim = int(sys.argv[3]) if len(sys.argv) > 3 else None
    df = pd.read_parquet(ev)
    df["day"] = pd.to_datetime(df["session_date"]).dt.date
    df = df[df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].reset_index(drop=True)
    df["fam"] = pd.factorize(df["level_family"])[0]
    feats = [c for c in df.columns if c.startswith("smt_tf.")] + ["fam"]
    sel, _, _, _ = wf_gate(df, feats, TARGET)
    sub = df[sel].copy()
    print(f"{sym}: {len(sub)} gate-selected trades, tick-honest exit policies (stop +{BUF}tk)...\n")

    pol_r: dict = {}
    days = []
    for d, g in sub.groupby("day"):
        try:
            mbp = read_mbp1_trading_day(symbol=sym, trading_day=d, columns=["ts_event", "action", "price"])
        except Exception:
            continue
        tr = mbp[(mbp["action"] == "T") & (mbp["price"] > 0)]
        if tr.empty:
            continue
        ts = pd.to_datetime(tr["ts_event"], utc=True).dt.tz_localize(None).to_numpy()
        pxv = tr["price"].to_numpy(float)
        for _, e in g.iterrows():
            res = path_R(e, ts, pxv, sym)
            if res is None:
                continue
            days.append(d)
            for k, v in res.items():
                pol_r.setdefault(k, []).append(v)
        if lim and len(days) >= lim:
            break

    days = np.array(days, dtype=object)
    print(f"  {len(days)} trades filled. honest tick-R by exit policy [day-block CI], avg trade R:")
    rows = [(k, *boot(np.array(v), days)) for k, v in pol_r.items()]
    for k, m, lo, hi in sorted(rows, key=lambda x: -x[1]):
        flag = "  <==" if lo > 0 else ""
        print(f"    {k:8} {m:+.2f} [{lo:+.2f},{hi:+.2f}]{flag}")
    print("\nREAD: the top policy with CI>0 is the better exit. If fixed3 is mid-pack, we've been leaving R on the "
          "table; if it's on top, the simple target was right. Then confirm the winner on the other 3 markets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
