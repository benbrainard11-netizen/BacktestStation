"""REGIME LAYER v1 -- route REVERSE (sweep_reclaim, fade) vs TREND (sweep_continue, trade the break) by VOL regime.

Cut 1 found vol/structure is the one family that adds; the user's thesis: "sometimes it reverses, sometimes it
takes it and goes -- we have to know the difference." Test: per sweep compute BOTH reclaim R (fade) and continue R
(trend). Split by prior-day-range VOL regime. Do they CROSS OVER (reclaim wins in low-vol/range, continue wins in
high-vol/expansion)? Then ROUTE by regime (high-vol->continue, low-vol->reclaim) and compare to always-one, overall
+ per period. Honest seq_r / seq_r_continue, day-block CI. Reads events_<asset>_tf.parquet.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reclaim_entry import boot, seq_r  # noqa: E402
from setups import seq_r_continue  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
TARGET = 3.0
ASSETS = [("ES", "events_es_tf.parquet"), ("NQ", "events_nq_tf.parquet"),
          ("YM", "events_ym_tf.parquet"), ("RTY", "events_rty_tf.parquet")]
PERIODS = [("25Q4", 20251001, 20260101), ("26Q1", 20260101, 20260401), ("26Q2", 20260401, 20260701)]


def load(fn: str) -> pd.DataFrame:
    df = pd.read_parquet(OUT / fn).reset_index(drop=True)
    df["recl"] = df["sweep.5m.ever_reclaimed"].fillna(0).to_numpy() > 0
    df["r_recl"] = seq_r(df, TARGET)              # fade-the-sweep (valid where it reclaimed)
    df["r_cont"] = seq_r_continue(df, TARGET)     # trade-the-break (all sweeps)
    t = pd.to_datetime(df["touch_ts_utc"], utc=True).dt.tz_convert("America/New_York")
    df["day"] = t.dt.date
    df["ymd"] = t.dt.strftime("%Y%m%d").astype(int)
    df["vol"] = df.get("prior_rth_range_pts", np.nan)
    return df


def _m(r, day):
    return boot(np.asarray(r), np.asarray(day)) if len(r) >= 15 else (np.nan, np.nan, np.nan)


def main() -> int:
    print(f"REGIME LAYER v1 @ {TARGET}R -- reverse vs trend by VOL regime (prior-day range tertiles):\n")
    for asset, fn in ASSETS:
        if not (OUT / fn).exists():
            print(f"{asset}: missing")
            continue
        df = load(fn)
        v = df["vol"].to_numpy(float)
        lo, hi = np.nanquantile(v, [0.34, 0.67])
        df["volreg"] = np.where(v <= lo, "low", np.where(v >= hi, "high", "mid"))
        print(f"{asset} (n={len(df)} sweeps, {df['recl'].sum()} reclaimed):")
        print("   crossover -- reclaim(fade) R  vs  continue(trend) R, by vol regime:")
        for reg in ["low", "mid", "high"]:
            s = df[df["volreg"] == reg]
            rc = s[s["recl"]]
            rm, rl, rh = _m(rc["r_recl"].to_numpy(), rc["day"].to_numpy())
            cm, cl, ch = _m(s["r_cont"].to_numpy(), s["day"].to_numpy())
            print(f"      {reg:4} vol:  reclaim {rm:+.2f}[{rl:+.2f},{rh:+.2f}] n{len(rc)}   "
                  f"continue {cm:+.2f}[{cl:+.2f},{ch:+.2f}] n{len(s)}")

        # route: high-vol -> continue (any sweep); low/mid -> reclaim (only if it reclaimed)
        take_cont = (df["volreg"] == "high").to_numpy()
        take_recl = (df["volreg"] != "high").to_numpy() & df["recl"].to_numpy()
        rr = np.where(take_cont, df["r_cont"].to_numpy(), df["r_recl"].to_numpy())
        routed = take_cont | take_recl
        am, al, ah = _m(df.loc[df["recl"], "r_recl"].to_numpy(), df.loc[df["recl"], "day"].to_numpy())
        bm, bl, bh = _m(df["r_cont"].to_numpy(), df["day"].to_numpy())
        gm, gl, gh = _m(rr[routed], df["day"].to_numpy()[routed])
        print(f"   ROUTED {gm:+.2f}[{gl:+.2f},{gh:+.2f}] n{int(routed.sum())}   "
              f"vs always-reclaim {am:+.2f}[{al:+.2f},{ah:+.2f}]   always-continue {bm:+.2f}[{bl:+.2f},{bh:+.2f}]")
        cells = []
        for plab, ps, pe in PERIODS:
            pm = (df["ymd"].to_numpy() >= ps) & (df["ymd"].to_numpy() < pe) & routed
            if pm.sum() < 15:
                cells.append(f"{plab} n<15")
                continue
            cells.append(f"{plab} {rr[pm].mean():+.2f}(n{int(pm.sum())})")
        print(f"      routed by period: {'  |  '.join(cells)}\n")
    print("READ: crossover (reclaim wins low-vol, continue wins high-vol) = regime separates the two trades. "
          "ROUTED clearly > both always-one + positive each period = the regime layer adds. Flat = vol regime doesn't route.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
