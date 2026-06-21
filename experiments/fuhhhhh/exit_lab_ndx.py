"""Exit lab: does letting winners RUN beat the fixed +-0.10ATR bracket? (the multiplier)

The signal predicts SUSTAINED moves; a fixed 1R target throws the tail away. Tick-simulate
several exits on NQ MBP-1 for the SHORT carriers (union + intersection), risk unit = initial
stop = 0.10*ATR, window = entry..16:00 ET. Honest: entry crosses spread, stops slip through
the print, targets/trails fill at the level, commission netted.

Schemes: fixed 1R | asymmetric (stop .10 / target .30=3R, .50=5R) | trailing (.10/.20 ATR) |
hold-with-stop to EOD.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\exit_lab_ndx.py
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
INIT_ATR = 0.10
COMM_PTS = C.COMMISSION_RT / C.POINT_VALUE_NQ
EOD_MS = 16 * 3600_000
RNG = np.random.default_rng(29)

o = pd.read_parquet(OUT / "dataset_ndx.parquet").merge(
    pd.read_parquet(OUT / "xasset_dir_ndx.parquet"), on=["date", "ms"], how="left")
q80 = o["rs_div_30m"].quantile(0.8)
bear_single = (o.xsmt_5m == -1) | (o.rs_div_30m >= q80)
bear_inter = (o.xsmt_5m == -1) & (o.rs_div_30m >= q80)
sig = o[bear_single].copy()
sig["tier"] = np.where(bear_inter[bear_single], "inter", "union")


def load_mbp(day):
    p = C.MBP1_NQ / f"date={day.isoformat()}" / "part-000.parquet"
    if not p.exists():
        return None
    t = pq.ParquetFile(p).read(columns=["ts_event", "action", "price", "bid_px", "sequence"])
    ts = t["ts_event"].to_numpy().astype("datetime64[ns]").astype(np.int64)
    order = np.lexsort((t["sequence"].to_numpy().astype(np.int64), ts))
    ts = ts[order]; act = t["action"].to_numpy(zero_copy_only=False)[order]
    bid = t["bid_px"].to_numpy().astype(np.float64)[order]
    px = t["price"].to_numpy().astype(np.float64)[order]
    istr = act == "T"
    return ts, bid, ts[istr], px[istr]


def short_exits(arr, t_ns, eod_ns, atr):
    ts, bid, tr_ts, tr_px = arr
    i = int(np.searchsorted(ts, t_ns, side="left"))
    if i >= len(ts) or not (bid[i] > 0):
        return None
    entry = bid[i]                                       # short fills at bid (cross spread)
    risk = INIT_ATR * atr
    lo = int(np.searchsorted(tr_ts, t_ns, side="left"))
    hi = int(np.searchsorted(tr_ts, eod_ns, side="right"))
    w = tr_px[lo:hi]
    if len(w) < 2:
        return None
    init_stop = entry + risk
    cmin_prev = np.concatenate([[entry], np.minimum.accumulate(w)[:-1]])   # min of prior prints

    def fixed(tgt_atr):                                  # stop init_stop, target entry-tgt
        tgt = entry - tgt_atr * atr
        hs = np.argmax(w >= init_stop) if (w >= init_stop).any() else None
        ht = np.argmax(w <= tgt) if (w <= tgt).any() else None
        if hs is None and ht is None:
            ex = w[-1]
        elif ht is None:
            ex = w[hs]                                   # stop slips
        elif hs is None:
            ex = tgt
        else:
            ex = (w[hs] if hs <= ht else tgt)
        return (entry - ex) / risk - COMM_PTS / risk

    def trail(tr_atr):                                   # trailing stop ratchets down
        stop_lvl = np.minimum(init_stop, cmin_prev + tr_atr * atr)
        hit = w >= stop_lvl
        if not hit.any():
            return (entry - w[-1]) / risk - COMM_PTS / risk
        k = int(np.argmax(hit))
        return (entry - w[k]) / risk - COMM_PTS / risk  # exit at the print (slip)

    return {"fix1R": fixed(INIT_ATR), "tgt3R": fixed(0.30), "tgt5R": fixed(0.50),
            "trail.10": trail(0.10), "trail.20": trail(0.20),
            "holdEOD": (entry - w[-1]) / risk - COMM_PTS / risk if not (w >= init_stop).any()
            else (entry - w[int(np.argmax(w >= init_stop))]) / risk - COMM_PTS / risk}


rows = []
for dstr, g in sig.groupby("date"):
    arr = load_mbp(Date.fromisoformat(dstr))
    if arr is None:
        continue
    day = Date.fromisoformat(dstr)
    eod = D.et_ts(day, EOD_MS).value
    for _, s in g.iterrows():
        r = short_exits(arr, D.et_ts(day, int(s.ms)).value, eod, float(s.geo_atr))
        if r is not None:
            rows.append({"date": dstr, "tier": s.tier, **r})

f = pd.DataFrame(rows)
schemes = ["fix1R", "tgt3R", "tgt5R", "trail.10", "trail.20", "holdEOD"]


def line(df, lab):
    print(f"\n{lab} (n={len(df)})")
    print(f"  {'scheme':10s} {'meanR':>8s} {'totalR':>8s} {'win%':>5s} {'avgWin':>7s} {'avgLoss':>7s} {'p':>6s}")
    for sc in schemes:
        r = df[sc].to_numpy()
        days = df["date"].to_numpy()
        by = {d: r[days == d] for d in np.unique(days)}
        bm = np.array([np.concatenate([by[d] for d in RNG.choice(list(by), len(by), True)]).mean() for _ in range(2000)])
        aw = r[r > 0].mean() if (r > 0).any() else 0
        al = r[r < 0].mean() if (r < 0).any() else 0
        print(f"  {sc:10s} {r.mean():>+8.4f} {r.sum():>8.1f} {(r>0).mean()*100:>4.0f}% {aw:>+7.3f} {al:>+7.3f} {(bm<=0).mean():>6.3f}")


line(f, "ALL union short")
line(f[f.tier == "inter"], "intersection short")
