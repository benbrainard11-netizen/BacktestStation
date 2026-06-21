"""Three-way isolation for the 2 exit-sweep validation mismatches (idx 16, 625):
cache (RR.compute's original run)  vs  live state machine re-run on the sweep's arrays
vs  the vectorized engine. Whichever pair agrees localizes the bug."""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\live_engine\engine")
import realized_r as RR  # noqa: E402
import exit_sweep as XS  # noqa: E402

ds = pd.read_parquet(HERE / "data" / "train.parquet")
ds["trigger_ts_utc"] = pd.to_datetime(ds["trigger_ts_utc"], utc=True)

for idx in (16, 625):
    row = ds.loc[idx]
    sym = str(row["symbol"])
    direction = 1 if str(row["smt_anchor_side"]) == "low" else -1
    trig = float(row["trigger_price"])
    tts = row["trigger_ts_utc"]
    print(f"\n=== idx={idx} {sym} dir={direction} trig={trig} @ {tts} cache_rr={row['realized_r']:+.4f} ({row['r_reason']})")

    # arrays as the SWEEP loads them (wide window)
    lo = tts - pd.Timedelta(seconds=200)
    hi = tts + pd.Timedelta(minutes=XS.MAX_TIMEOUT + 15)
    arr_wide = RR.load_mbp1(sym, lo, hi)
    # arrays as RR.compute loaded them (+72m window)
    arr_rr = RR.load_mbp1(sym, lo, tts + pd.Timedelta(minutes=72))

    for tag, arr in (("wide", arr_wide), ("rr72", arr_rr)):
        res = RR.drive(sym, direction, trig, tts, arr)
        if res is None:
            print(f"  live-machine[{tag}]: None")
            continue
        gross, reason, risk = res
        net = RR.net_r(gross, reason, sym, risk)
        print(f"  live-machine[{tag}]: net={net:+.4f} ({reason}) risk={risk:.2f}")

    ent = XS.entry_for(sym, direction, trig, tts, arr_wide)
    if ent is None:
        print("  vector entry: None")
        continue
    res = XS.eval_policies(direction, ent[0], ent[1], ent[2], ent[3], ent[4], arr_wide, sym)
    print(f"  vector[wide] trail_2R: {res['trail_2R'][0]:+.4f} ({res['trail_2R'][1]})  "
          f"entry_px={ent[1]} stop={ent[3]:.2f} risk={ent[4]:.2f}")
