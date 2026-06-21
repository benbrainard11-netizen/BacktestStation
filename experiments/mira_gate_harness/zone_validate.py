"""Validate that flow_mbp1_stack's reused zone detection reproduces flow_at_zone's zone_5m_has on
the 2026 overlap. Recompute zone_5m_has for sample 2026 ES anchors via the SAME FZ functions and
compare to the cached flow_at_zone_all zone_5m_has. Must match (same bars, same detector)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "backend"))
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\experiments\smt_ltf_bench")
import flow_at_zone as FZ  # noqa: E402

ONE_NS = 1_000_000_000
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10}

ref = pd.read_parquet(HERE / "runs" / "flow_at_zone_all.parquet")
ref["decision_ts_utc"] = pd.to_datetime(ref["decision_ts_utc"], utc=True)
ref["touch_ts_utc"] = pd.to_datetime(ref["touch_ts_utc"], utc=True)
ref = ref[ref["symbol"] == "ES.c.0"].copy()
days = sorted(ref["trading_day"].unique())[:6]
sub = ref[ref["trading_day"].isin(days)].copy()


def recompute_has(sym, row, tf_frames):
    tick = TICK[sym]
    dec = int(row["decision_ts_utc"].value)
    touch = int(row["touch_ts_utc"].value)
    tf_b = tf_frames.get("5m"); bars1m = tf_frames.get("1m")
    if tf_b is None or not len(tf_b):
        return 0
    close_ns = tf_b.index.asi8 + 5 * 60 * ONE_NS
    s = tf_b.iloc[(close_ns >= touch - 6 * 3600 * ONE_NS) & (close_ns <= dec)]
    zone = FZ._detect_zone_tf(s, row["side"], float(row["level_price"]), touch, dec, "5m", tick)
    if zone is not None and FZ._retraced(bars1m, zone[0], zone[1], zone[3], dec, tick):
        return 1
    return 0


rows = []
for td in days:
    tf = FZ._resample_for_day("ES.c.0", td)
    for _, r in sub[sub["trading_day"] == td].iterrows():
        rows.append({"ref": int(r["zone_5m_has"]), "mine": recompute_has("ES.c.0", r, tf)})
d = pd.DataFrame(rows)
print(f"compared {len(d)} ES 2026 anchors over {len(days)} days")
print(f"  ref zone rate {d['ref'].mean():.3f}  mine {d['mine'].mean():.3f}")
print(f"  agreement: {100*(d['ref']==d['mine']).mean():.1f}%")
print(f"  confusion: both1={int(((d.ref==1)&(d.mine==1)).sum())} both0={int(((d.ref==0)&(d.mine==0)).sum())} "
      f"ref1_mine0={int(((d.ref==1)&(d.mine==0)).sum())} ref0_mine1={int(((d.ref==0)&(d.mine==1)).sum())}")
