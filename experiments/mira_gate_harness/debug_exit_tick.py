"""Tick-level divergence finder for idx=16: live machine exit ts vs vectorized exit ts,
plus the fav/hwm series around both points."""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import realized_r as RR  # noqa: E402
import feed as feed_mod  # noqa: E402
import exit_sweep as XS  # noqa: E402

SIG = RR.SIG
_NS = 1_000_000_000

ds = pd.read_parquet(HERE / "data" / "train.parquet")
ds["trigger_ts_utc"] = pd.to_datetime(ds["trigger_ts_utc"], utc=True)
row = ds.loc[16]
sym, direction, trig, tts = str(row["symbol"]), -1, float(row["trigger_price"]), row["trigger_ts_utc"]
arr = RR.load_mbp1(sym, tts - pd.Timedelta(seconds=200), tts + pd.Timedelta(minutes=255))
ts_ns, bid, ask = arr

# live machine, instrumented
root = sym.split(".")[0]
trade = SIG.ReclaimTrade(symbol=root, direction=direction, trigger_price=trig,
                         stop_ref_price=trig + 1000.0, decision_ts=tts.to_pydatetime(), exit_mode="trail_2R")
buf = feed_mod.MBP1Buffer(sym, retain_sec=100_000)
trig_n = int(tts.value)
start = int(np.searchsorted(ts_ns, trig_n - 185 * _NS, "left"))
entry_pos = None
for pos in range(start, len(ts_ns)):
    tn = int(ts_ns[pos]); b = bid[pos]; a = ask[pos]
    if not (np.isfinite(b) and np.isfinite(a)):
        continue
    buf.append_raw(tn, b, a)
    if tn < trig_n:
        continue
    act = trade.on_quote(pd.Timestamp(tn, tz="UTC").to_pydatetime(), b, a)
    if act.kind == "enter":
        trade.reset_stop(buf.local_extreme(tn, direction, 180))
        entry_pos = pos
    elif act.kind == "exit":
        print(f"LIVE exit: pos={pos} ts={pd.Timestamp(tn, tz='UTC')} px={act.price} gross={act.realized_R:+.4f} "
              f"({act.reason}) hwm={trade.hwm} risk={trade.risk} entry_pos={entry_pos} entry_px={trade.entry_px}")
        break

# vectorized
ent = XS.entry_for(sym, direction, trig, tts, arr)
e_idx, e_px, e_ns, stop_px, risk = ent
b2, a2 = bid[e_idx + 1:], ask[e_idx + 1:]
tns = ts_ns[e_idx + 1:]
ok = np.isfinite(b2) & np.isfinite(a2)
px = a2[ok]; tns2 = tns[ok]
fav_r = (e_px - px) / risk
hwm = np.maximum.accumulate(fav_r)
armed = hwm >= 2.0
mask = armed & (fav_r <= hwm - 1.0)
i = int(np.argmax(mask))
print(f"VECT exit: ts={pd.Timestamp(int(tns2[i]), tz='UTC')} px={px[i]} fav_r={fav_r[i]:+.4f} hwm={hwm[i]:.4f} "
      f"entry_idx={e_idx} entry_px={e_px}")
arm_i = int(np.argmax(armed))
print(f"VECT armed at ts={pd.Timestamp(int(tns2[arm_i]), tz='UTC')} hwm={hwm[arm_i]:.4f}")
