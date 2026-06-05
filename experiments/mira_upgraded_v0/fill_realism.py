"""Fill realism: re-fill the gate-selected reclaim trades TICK-BY-TICK on MBP-1 trade prints, and compare to the
bucket-sequenced honest-R. Conservative fills: enter 1 tick past the level; STOP fills at the actual trade price
that crosses it (slippage if it gaps through); TARGET is a limit (fills at target). First touch in real trade
order decides. Mark-to-market if neither hits by the horizon. How much of the edge survives real fills?

Run: backend/.venv/Scripts/python.exe fill_realism.py [EVENTS_TF_PARQUET] [SYMBOL]
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

TARGET, MAXH = 3.0, 120  # R target, max horizon minutes


def tick_r(e, ts, px, sym):
    ptv, cost, tick = SPEC.get(sym, DEF)
    level, extreme = float(e["level_price"]), float(e["sweep.5m.sweep_extreme_price"])
    depth = max(abs(level - extreme), 8 * tick)
    risk = depth + 2 * tick
    long = e["smt_anchor_side"] == "low"
    if long:
        entry, stop, target = level + tick, extreme - 2 * tick, level + tick + TARGET * risk
    else:
        entry, stop, target = level - tick, extreme + 2 * tick, level - tick - TARGET * risk
    entry_ts = pd.Timestamp(e["entry_ts"]).to_datetime64()
    i0 = int(np.searchsorted(ts, entry_ts))
    i1 = int(np.searchsorted(ts, entry_ts + np.timedelta64(MAXH, "m")))
    w = px[i0:i1]
    if len(w) == 0:
        return np.nan, "nodata"
    if long:
        s = np.where(w <= stop)[0]
        t = np.where(w >= target)[0]
    else:
        s = np.where(w >= stop)[0]
        t = np.where(w <= target)[0]
    si = s[0] if len(s) else 10**9
    ti = t[0] if len(t) else 10**9
    if si <= ti and si < 10**9:
        fill, out = float(w[si]), "stop"          # stop fills at the actual print (slippage past stop)
    elif ti < si:
        fill, out = target, "target"              # limit at target
    else:
        fill, out = float(w[-1]), "timeout"       # mark-to-market
    pnl = (fill - entry) if long else (entry - fill)
    return pnl / risk - cost / (risk * ptv), out


def main() -> int:
    ev = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out" / "events_es_tf.parquet"
    sym = sys.argv[2] if len(sys.argv) > 2 else "ES.c.0"
    df = pd.read_parquet(ev)
    df["day"] = pd.to_datetime(df["session_date"]).dt.date
    df = df[df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].reset_index(drop=True)
    df["fam"] = pd.factorize(df["level_family"])[0]
    feats = [c for c in df.columns if c.startswith("smt_tf.")] + ["fam"]
    sel, _, r_bucket, day = wf_gate(df, feats, TARGET)
    sub = df[sel].copy()
    sub["r_bucket"] = r_bucket[sel]
    sub["entry_ts"] = pd.to_datetime(sub["touch_ts_utc"]) + pd.to_timedelta(
        sub["sweep.5m.time_to_reclaim_min"].fillna(0), unit="m")
    print(f"{sym}: gate-selected {len(sub)} trades -- tick-filling on MBP-1 prints...")
    rs, outs, days = [], [], []
    for d, g in sub.groupby("day"):
        try:
            mbp = read_mbp1_trading_day(symbol=sym, trading_day=d, columns=["ts_event", "action", "price"])
        except Exception:
            continue
        tr = mbp[mbp["action"] == "T"]
        if tr.empty:
            continue
        ts = pd.to_datetime(tr["ts_event"], utc=True).tz_convert("UTC").tz_localize(None).values
        pxv = tr["price"].to_numpy(float)
        for _, e in g.iterrows():
            r, out = tick_r(e, ts, pxv, sym)
            if np.isfinite(r):
                rs.append(r); outs.append(out); days.append(d)
    rs, days = np.array(rs), np.array(days, dtype=object)
    bm, bl, bh = boot(sub["r_bucket"].to_numpy(), sub["day"].to_numpy())
    tm, tl, th = boot(rs, days)
    oc = pd.Series(outs).value_counts().to_dict()
    print(f"\n  bucket-R (15m sequencing): {bm:+.2f} [{bl:+.2f},{bh:+.2f}] n{len(sub)}")
    print(f"  TICK-R (real fills):       {tm:+.2f} [{tl:+.2f},{th:+.2f}] n{len(rs)}")
    print(f"  survival {tm / bm * 100 if bm else 0:.0f}%   outcomes {oc}")
    print("\nREAD: TICK-R CI still clearly > 0 = the edge survives real fills. Big drop from bucket-R = stop-fill optimism.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
