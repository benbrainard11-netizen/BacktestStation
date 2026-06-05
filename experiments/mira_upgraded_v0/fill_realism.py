"""Fill realism (honest): re-fill gate-selected reclaim trades TICK-BY-TICK on MBP-1 prints, with NO look-ahead
and a stop-placement sweep. Entry = the ACTUAL reclaim crossing (first print back through the level after the
sweep extreme), filled at the level. STOP swept from 0..16 ticks past the extreme; TARGET = 3R from entry (limit).
First touch in real trade order decides; stop fills at the crossing print (slippage). Does ANY honest stop survive?

Run: backend/.venv/Scripts/python.exe fill_realism.py [EVENTS_TF_PARQUET] [SYMBOL] [SAMPLE_LIMIT]
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

TARGET, MAXH, BUFS = 3.0, 120, [0, 2, 4, 8, 16]   # R target, horizon min, stop buffers (ticks past extreme)


def tick_all(e, ts, px, sym):
    ptv, cost, tick = SPEC.get(sym, DEF)
    level, extreme = float(e["level_price"]), float(e["sweep.5m.sweep_extreme_price"])
    long = e["smt_anchor_side"] == "low"
    ext_ts = pd.Timestamp(e["sweep.5m.sweep_extreme_ts_utc"]).to_datetime64()
    i0 = int(np.searchsorted(ts, ext_ts))
    i1 = int(np.searchsorted(ts, ext_ts + np.timedelta64(MAXH, "m")))
    w = px[i0:i1]
    if len(w) == 0:
        return None
    cross = np.where(w >= level)[0] if long else np.where(w <= level)[0]   # reclaim back through the level
    if len(cross) == 0:
        return None
    wa = w[cross[0]:]                                                       # from the reclaim entry forward
    depth = max(abs(level - extreme), 8 * tick)
    res = {}
    for buf in BUFS:
        risk = depth + buf * tick
        if long:
            stop, target = extreme - buf * tick, level + TARGET * risk
            s, t = np.where(wa <= stop)[0], np.where(wa >= target)[0]
        else:
            stop, target = extreme + buf * tick, level - TARGET * risk
            s, t = np.where(wa >= stop)[0], np.where(wa <= target)[0]
        si = s[0] if len(s) else 10**9
        ti = t[0] if len(t) else 10**9
        if si <= ti and si < 10**9:
            fill, o = float(wa[si]), "stop"
        elif ti < si:
            fill, o = target, "target"
        else:
            fill, o = float(wa[-1]), "timeout"
        pnl = (fill - level) if long else (level - fill)
        res[buf] = (pnl / risk - cost / (risk * ptv), o)
    return res


def main() -> int:
    ev = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out" / "events_es_tf.parquet"
    sym = sys.argv[2] if len(sys.argv) > 2 else "ES.c.0"
    lim = int(sys.argv[3]) if len(sys.argv) > 3 else None
    df = pd.read_parquet(ev)
    df["day"] = pd.to_datetime(df["session_date"]).dt.date
    df = df[df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0].reset_index(drop=True)
    df["fam"] = pd.factorize(df["level_family"])[0]
    feats = [c for c in df.columns if c.startswith("smt_tf.")] + ["fam"]
    sel, _, r_bucket, _ = wf_gate(df, feats, TARGET)
    sub = df[sel].copy()
    sub["r_bucket"] = r_bucket[sel]
    print(f"{sym}: gate-selected {len(sub)} trades, honest tick-fill (entry=reclaim crossing){f' sample {lim}' if lim else ''}...")

    per_buf = {b: ([], []) for b in BUFS}     # (r, outcome)
    days, rb = [], []
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
            res = tick_all(e, ts, pxv, sym)
            if res is None:
                continue
            days.append(d); rb.append(e["r_bucket"])
            for b in BUFS:
                per_buf[b][0].append(res[b][0]); per_buf[b][1].append(res[b][1])
        if lim and len(days) >= lim:
            break

    days = np.array(days, dtype=object)
    bm, bl, bh = boot(np.array(rb), days)
    print(f"\n  bucket-R reference: {bm:+.2f} [{bl:+.2f},{bh:+.2f}]   n{len(days)}\n")
    print("  honest tick-R by stop buffer (ticks past extreme):")
    for b in BUFS:
        r = np.array(per_buf[b][0])
        o = np.array(per_buf[b][1])
        m, lo, hi = boot(r, days)
        wr = (o == "target").mean()
        flag = "  <== survives" if lo > 0 else ""
        print(f"    +{b:>2}tk: {m:+.2f} [{lo:+.2f},{hi:+.2f}]  win{wr:.2f}  stop%{(o == 'stop').mean():.2f}{flag}")
    print("\nREAD: if every honest buffer is <= 0, the tight-stop edge does NOT survive real fills (bucket-R was optimistic).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
