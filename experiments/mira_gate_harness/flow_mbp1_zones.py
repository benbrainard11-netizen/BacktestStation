"""TIMEFRAME SWEEP (Ben's idea): compute zone_has at 1m / 3m / 5m / 15m for the SAME 13-month
universe as flow_mbp1_stack, BAR-ONLY (no MBP-1). Merges with the drift cache so we can test which
zone TF best captures the drift x zone edge, and whether the best TF differs by level type (esp.
precise levels like gamma walls wanting a finer 1m/3m zone). Output: runs/mbp1_zones_multi.parquet.

Run AFTER flow_mbp1_stack.py (reuses its universe + the validated FZ zone detector at each TF).
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\experiments\smt_ltf_bench")
import flow_at_zone as FZ  # noqa: E402
from smt_bench import resample_tf  # noqa: E402
import flow_mbp1_stack as MS  # noqa: E402  (load_universe, TICK, ONE_NS)

RUNS = HERE / "runs"
CACHE = RUNS / "mbp1_zones_multi.parquet"
TFS = {"1m": 1, "3m": 3, "5m": 5, "15m": 15}
ONE_NS = 1_000_000_000
FZ.TF_MIN.update({"1m": 1, "3m": 3})  # FZ only ships 5m/15m; _detect_zone_tf needs the label->min map


def zone_has_tf(bars1m, tf_b, row, tick, tf_label) -> int:
    if tf_b is None or not len(tf_b):
        return 0
    dec = int(row["decision_ts_utc"].value)
    touch = int(row["touch_ts_utc"].value)
    tf_min = TFS[tf_label]  # known TF minutes (do NOT infer from bar spacing — session gaps round to 0)
    close_ns = tf_b.index.asi8 + tf_min * 60 * ONE_NS
    sub = tf_b.iloc[(close_ns >= touch - 6 * 3600 * ONE_NS) & (close_ns <= dec)]
    z = FZ._detect_zone_tf(sub, row["side"], float(row["level_price"]), touch, dec, tf_label, tick)
    return 1 if (z is not None and FZ._retraced(bars1m, z[0], z[1], z[3], dec, tick)) else 0


def main() -> int:
    uni = MS.load_universe()
    print(f"[universe] {len(uni)} reclaims; computing zone_has at {list(TFS)}", flush=True)
    cached = pd.read_parquet(CACHE) if CACHE.exists() else pd.DataFrame()
    done = set(map(tuple, cached[["symbol", "trading_day"]].drop_duplicates().to_numpy())) if len(cached) else set()
    groups = uni.groupby(["symbol", "trading_day"], sort=True)
    todo = [k for k in groups.groups if k not in done]
    print(f"[build] {groups.ngroups} symdays ({len(done)} cached, {len(todo)} to compute)", flush=True)
    for n, (sym, td) in enumerate(todo, 1):
        g = groups.get_group((sym, td))
        tick = MS.TICK[sym]
        try:
            base = FZ._resample_for_day(sym, td)  # has '1m','5m','15m'
            bars1m = base.get("1m")
            frames = {"1m": bars1m, "5m": base.get("5m"), "15m": base.get("15m"),
                      "3m": resample_tf(bars1m, 3) if bars1m is not None and len(bars1m) else None}
        except Exception as e:
            print(f"  SKIP {sym} {td}: {type(e).__name__}: {e}", flush=True)
            continue
        rows = []
        for _, r in g.iterrows():
            rec = {"symbol": sym, "decision_ts_utc": r["decision_ts_utc"],
                   "level_price": float(r["level_price"]), "side": r["side"]}
            for tf in TFS:
                rec[f"zone_{tf}_has"] = zone_has_tf(bars1m, frames.get(tf), r, tick, tf)
            rows.append(rec)
        cached = pd.concat([cached, pd.DataFrame(rows)], ignore_index=True)
        tmp = CACHE.with_suffix(".tmp.parquet"); cached.to_parquet(tmp, index=False); tmp.replace(CACHE)
        if n % 50 == 0 or n == len(todo):
            print(f"  [{n}/{len(todo)}] {sym} {td}", flush=True)
    print(f"\nwrote {CACHE}: {len(cached)} rows; zone rates "
          + ", ".join(f"{tf}={cached[f'zone_{tf}_has'].mean():.2f}" for tf in TFS), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
