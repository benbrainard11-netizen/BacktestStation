"""Honest tick-fill check for the cross-asset direction book (the make-or-break gate).

For each signal trade, re-fill on NQ MBP-1:
  - ENTRY crosses the spread: long fills at the prevailing ASK, short at the BID (at the
    first quote >= decision time t).
  - BARRIERS (+-MOVE_ATR*ATR) resolve by TRADE PRINTS in time order: whichever price prints
    first wins (CLAUDE.md rule 8). Both in the same print / ambiguous -> STOP wins (conservative).
  - Timeout at t+HORIZON (or 16:00): exit at last print.
  - Cost = commission only (spread is now modeled explicitly via bid/ask entry).
Compares tick-fill R to the bar-level R (dataset r_short/r_long) per tier.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\tickfill_ndx.py
"""
import sys
from datetime import date as Date
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
import data_io as D

OUT = Path(__file__).resolve().parent / "out"
HORIZON_MIN = 15
MOVE_ATR = 0.10
COMM_PTS = C.COMMISSION_RT / C.POINT_VALUE_NQ        # 0.19 pts round-trip (spread modeled separately)
RNG = np.random.default_rng(23)

o = pd.read_parquet(OUT / "dataset_ndx.parquet").merge(
    pd.read_parquet(OUT / "xasset_dir_ndx.parquet"), on=["date", "ms"], how="left")
q80, q20 = o["rs_div_30m"].quantile(0.8), o["rs_div_30m"].quantile(0.2)
bear_single = (o.xsmt_5m == -1) | (o.rs_div_30m >= q80)
bear_inter = (o.xsmt_5m == -1) & (o.rs_div_30m >= q80)
bull_inter = (o.xsmt_5m == 1) & (o.rs_div_30m <= q20)
o["dir"] = np.where(bear_single, -1, np.where(bull_inter, 1, 0))
o["tier"] = np.where(bear_inter | bull_inter, "inter", np.where(bear_single, "union", ""))
sig = o[o["dir"] != 0].copy()


def load_mbp(day: Date):
    p = C.MBP1_NQ / f"date={day.isoformat()}" / "part-000.parquet"
    if not p.exists():
        return None
    t = pq.ParquetFile(p).read(columns=["ts_event", "action", "price", "bid_px", "ask_px", "sequence"])
    ts = t["ts_event"].to_numpy().astype("datetime64[ns]").astype(np.int64)
    seq = t["sequence"].to_numpy().astype(np.int64)
    order = np.lexsort((seq, ts))
    ts = ts[order]
    act = t["action"].to_numpy(zero_copy_only=False)[order]
    px = t["price"].to_numpy().astype(np.float64)[order]
    bid = t["bid_px"].to_numpy().astype(np.float64)[order]
    ask = t["ask_px"].to_numpy().astype(np.float64)[order]
    istr = act == "T"
    return ts, bid, ask, ts[istr], px[istr]


def fill_one(arr, t_ns, direction, atr):
    ts, bid, ask, tr_ts, tr_px = arr
    i = int(np.searchsorted(ts, t_ns, side="left"))
    if i >= len(ts):
        return None
    entry = ask[i] if direction > 0 else bid[i]           # cross the spread
    if not (entry > 0):
        return None
    move = MOVE_ATR * atr
    tgt = entry + move if direction > 0 else entry - move
    stp = entry - move if direction > 0 else entry + move
    end = t_ns + HORIZON_MIN * 60 * 10**9
    lo = int(np.searchsorted(tr_ts, t_ns, side="left"))
    hi = int(np.searchsorted(tr_ts, end, side="right"))
    if hi <= lo:
        return None
    w = tr_px[lo:hi]
    if direction > 0:
        hit_t = np.argmax(w >= tgt) if (w >= tgt).any() else None
        hit_s = np.argmax(w <= stp) if (w <= stp).any() else None
    else:
        hit_t = np.argmax(w <= tgt) if (w <= tgt).any() else None
        hit_s = np.argmax(w >= stp) if (w >= stp).any() else None
    if hit_t is None and hit_s is None:
        exitp = w[-1]                                     # timeout: exit at last print
    elif hit_s is None:
        exitp = tgt                                       # target only: limit fills at the level
    elif hit_t is None:
        exitp = w[hit_s]                                  # stop only: fills at actual print (slips through)
    else:
        exitp = w[hit_s] if hit_s <= hit_t else tgt       # stop-first -> actual print (slip); tie -> stop
    pnl = (exitp - entry) if direction > 0 else (entry - exitp)
    return pnl / move - COMM_PTS / move                  # R, commission netted


def boot(r, dates):
    df = pd.DataFrame({"r": r, "d": dates})
    days = df.d.unique(); by = {d: df[df.d == d]["r"].to_numpy() for d in days}
    m = np.array([np.concatenate([by[d] for d in RNG.choice(days, len(days), True)]).mean() for _ in range(3000)])
    return float(np.mean(r)), float((m <= 0).mean())


rows = []
for dstr, g in sig.groupby("date"):
    arr = load_mbp(Date.fromisoformat(dstr))
    if arr is None:
        continue
    for _, s in g.iterrows():
        t_ns = D.et_ts(Date.fromisoformat(dstr), int(s.ms)).value
        r = fill_one(arr, t_ns, int(s.dir), float(s.geo_atr))
        if r is not None:
            rows.append({"date": dstr, "tier": s.tier, "dir": int(s.dir),
                         "r_tick": r, "r_bar": (s.r_short if s.dir < 0 else s.r_long)})

f = pd.DataFrame(rows)
f["mo"] = f["date"].str.slice(0, 7)
print(f"tick-filled {len(f)} trades over {f.date.nunique()} days\n")
print(f"{'cell':22s} {'n':>5s} {'R_bar':>8s} {'R_tick':>8s} {'erosion':>8s} {'p_tick':>7s} {'win%':>5s} {'mo+':>5s}")
for lab, m in [("UNION short", f.dir < 0), ("  intersection short", (f.tier == 'inter') & (f.dir < 0)),
               ("  union-only short", (f.tier == 'union') & (f.dir < 0)),
               ("intersection long", (f.tier == 'inter') & (f.dir > 0))]:
    s = f[m]
    if len(s) < 20:
        print(f"{lab:22s} {len(s):>5d}  thin"); continue
    rb, rt = s.r_bar.mean(), s.r_tick.mean()
    _, p = boot(s.r_tick.to_numpy(), s.date.to_numpy())
    bymo = s.groupby("mo")["r_tick"].mean()
    print(f"{lab:22s} {len(s):>5d} {rb:>+8.4f} {rt:>+8.4f} {rt-rb:>+8.4f} {p:>7.3f} {(s.r_tick>0).mean()*100:>4.0f}% {int((bymo>0).sum())}/{len(bymo)}")
