"""Validate the MBP-1 premise: does drift computed from MBP-1 trades == drift from MBO (the cached
w90_drift_dir_ticks in flow_at_scale_all)? Trades are the SAME prints in both feeds, so they should
match. If yes, MBP-1 unlocks drift over the full 13-month window (2025-05..2026-06) vs MBO's 6mo.
Sample: a few ES Jan-2026 overlap days."""
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as pds

HERE = Path(__file__).resolve().parent
R = HERE / "runs"
MBP1 = Path(r"D:\data\raw\databento\mbp-1")
TICK = {"ES.c.0": 0.25, "NQ.c.0": 0.25, "YM.c.0": 1.0, "RTY.c.0": 0.10}
WIN_S = 90  # the drift window [decision-90s, decision), matching flow_at_scale

feats = pd.read_parquet(R / "flow_at_scale_all.parquet")
feats["decision_ts_utc"] = pd.to_datetime(feats["decision_ts_utc"], utc=True)
feats["td"] = feats["decision_ts_utc"].dt.tz_convert("America/New_York").dt.date.astype(str)
# sample: ES, first 4 Jan-2026 trading days present in the cache
es = feats[feats["symbol"] == "ES.c.0"].copy()
days = sorted(es[es["td"].str[:7] == "2026-01"]["td"].unique())[:4]
print(f"validating MBP-1 drift vs MBO drift on ES days: {days}")


def mbp1_trades(sym, td):
    p = MBP1 / f"symbol={sym}" / f"date={td}" / "part-000.parquet"
    t = pds.dataset(p).to_table(columns=["ts_event", "action", "price"],
                                filter=pds.field("action") == "T").to_pandas()
    return t["ts_event"].astype("int64").to_numpy(), t["price"].to_numpy(float)


rows = []
for td in days:
    ts, px = mbp1_trades("ES.c.0", td)
    sub = es[es["td"] == td]
    for _, r in sub.iterrows():
        dec = int(pd.Timestamp(r["decision_ts_utc"]).value)  # ns
        lo = dec - WIN_S * 1_000_000_000
        m = (ts >= lo) & (ts < dec)
        if m.sum() < 2:
            continue
        wp = px[m]
        dir_sign = 1.0 if r["side"] == "low" else -1.0
        mbp1_drift = dir_sign * (wp[-1] - wp[0]) / TICK["ES.c.0"]
        rows.append({"mbo_drift": float(r["w90_drift_dir_ticks"]), "mbp1_drift": mbp1_drift,
                     "n_tr_mbp1": int(m.sum())})

d = pd.DataFrame(rows)
d["diff"] = d["mbp1_drift"] - d["mbo_drift"]
print(f"\nmatched {len(d)} anchors")
print(f"  corr(mbp1, mbo) = {d['mbp1_drift'].corr(d['mbo_drift']):.4f}")
print(f"  mean abs diff   = {d['diff'].abs().mean():.3f} ticks   (exact match => ~0)")
print(f"  median |diff|   = {d['diff'].abs().median():.3f} ticks")
print(f"  exact (|diff|<0.01): {100*(d['diff'].abs()<0.01).mean():.0f}%")
print(d.head(8).to_string(index=False))
