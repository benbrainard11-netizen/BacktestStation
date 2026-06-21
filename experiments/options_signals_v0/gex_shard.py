"""Sharded GEX pull: split an index's expiration list across N processes; each writes RAW
per-(date,strike) dealer-GEX sums to out/_shards/. merge_gex_shards.py derives the levels.
Usage: gex_shard.py INDEX START END SHARD_IDX N_SHARDS"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gex_pull import ROOT, MULT, _ymd  # noqa: E402
from theta_store import expirations as _exps, fetch as _fetch  # noqa: E402

index, start, end, si, ns = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
# optional 6th arg = request window in days (default 100). Smaller = lighter requests that
# the flaky Terminal can serve without freezing; >=35d still covers the <=30 DTE the walls need.
WINDOW_DAYS = int(sys.argv[6]) if len(sys.argv) > 6 else 100
root = ROOT[index]
s, e = _ymd(start), _ymd(end)
# NEWEST-FIRST: recent years are research-usable immediately; deep history backfills behind.
# Startup list fetch retries: it times out when sibling shards are mid-burst (60s proxy limit).
all_exps = None
for _attempt in range(5):
    try:
        all_exps = _exps(root)
        break
    except Exception as _e:
        print(f"expirations fetch failed ({_e}); retry in 45s", flush=True)
        time.sleep(45)
if all_exps is None:
    raise SystemExit("could not fetch expirations after 5 attempts")
exps = sorted((x for x in all_exps if s <= x <= _ymd(pd.Timestamp(end) + pd.Timedelta(days=90))),
              reverse=True)[si::ns]
OUT = Path(__file__).resolve().parent / "out" / "_shards"
OUT.mkdir(parents=True, exist_ok=True)
print(f"shard {si}/{ns}: {len(exps)} expirations", flush=True)

accum = None
spot = {}
failed = []
for k, exp in enumerate(exps):
    # Bound each request to the expiration's LIFE (max_dte 90 + buffer) — full-range requests
    # made the server scan 11 years per expiration (~6 min/exp; this fix: seconds/exp).
    exp_ts = pd.Timestamp(str(exp))
    s_k = max(s, _ymd(exp_ts - pd.Timedelta(days=WINDOW_DAYS)))
    e_k = min(e, exp)
    if s_k > e_k:
        continue
    g = oi = None
    for attempt in range(3):
        try:
            g = _fetch("bulk_hist/option/eod_greeks", root=root, exp=exp, start_date=s_k, end_date=e_k)
            oi = _fetch("bulk_hist/option/open_interest", root=root, exp=exp, start_date=s_k, end_date=e_k)
            break
        except Exception:
            time.sleep(5 * (attempt + 1))
    if g is None or oi is None:
        failed.append(exp)
        continue
    if g.empty or oi.empty:
        continue
    m = g.merge(oi[["date", "strike", "right", "expiration", "open_interest"]],
                on=["date", "strike", "right", "expiration"], how="inner")
    if m.empty:
        continue
    sp = m["underlying_price"].to_numpy(float)
    sign = np.where(m["right"].astype(str).str.upper().str[0] == "C", 1.0, -1.0)
    m = m.assign(gex=m["open_interest"].to_numpy(float) * m["gamma"].to_numpy(float) * sp * sp * 0.01 * MULT * sign)
    g2 = m.groupby(["date", "strike"])["gex"].sum()
    accum = g2 if accum is None else accum.add(g2, fill_value=0.0)
    for dt_, spv in zip(m["date"].to_numpy(), sp):
        spot[int(dt_)] = float(spv)
    if k and k % 40 == 0:
        print(f"  shard {si}: {k}/{len(exps)}", flush=True)

if accum is not None:
    accum.rename("gex").reset_index().to_parquet(OUT / f"{index.lower()}_s{si}.parquet", index=False)
    pd.DataFrame({"date": list(spot), "spot": list(spot.values())}).to_parquet(
        OUT / f"{index.lower()}_spot_s{si}.parquet", index=False)
(OUT / f"{index.lower()}_failed_s{si}.txt").write_text("\n".join(map(str, failed)))
print(f"shard {si} DONE: failed={len(failed)}", flush=True)
