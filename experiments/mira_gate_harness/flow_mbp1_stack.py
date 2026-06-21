"""13-MONTH drift x zone stack from BARS + MBP-1 (no MBO needed).

The deployable edge = zone_5m_has(==1) AND w90_drift_dir_ticks(>=29.33). Neither needs the MBO book:
  - zone_5m_has  : detected from 1m/5m BARS (reuse flow_at_zone._detect_zone_tf + _retraced).
  - drift        : trade-price momentum [decision-90s, decision) from MBP-1 trades (VALIDATED ==MBO,
                   corr 1.0000, mbp1_drift_validate.py).
MBP-1 covers ES/NQ/YM/RTY 2025-05-01..2026-06-09 (~342 days) vs MBO's 6mo -> ~2.5x data + a FRESH
8-month OOS (May-Dec 2025) the MBO never saw. Universe = legal_bars_full entered reclaims, |R|<=5.

Crash-safe: cached per (symbol, trading_day) to runs/mbp1_stack_features.parquet.
Run: backend/.venv/Scripts/python.exe experiments/mira_gate_harness/flow_mbp1_stack.py
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as pds

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, r"C:\Users\benbr\BacktestStation\experiments\smt_ltf_bench")
import flow_at_zone as FZ  # noqa: E402  (zone detection: _resample_for_day, _detect_zone_tf, _retraced)
import legal_reclaim_bars as LB  # noqa: E402  (comprehensive TICK map incl cross-asset)

RUNS = HERE / "runs"
UNIVERSE = RUNS / "legal_bars_full.parquet"
CACHE = RUNS / "mbp1_stack_features.parquet"
DISP = False  # --displacement: break-direction dir_sign (side=high -> long) instead of reclaim's fade
MBP1 = Path(r"D:\data\raw\databento\mbp-1")
SYMBOLS = ["ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0"]  # widened to the universe's symbols when --universe
TICK = LB.TICK  # comprehensive: indices + cross-asset (metals/energy/FX/rates/crypto)
RISK_CAP = 5.0
WIN_NS = 90 * 1_000_000_000  # drift window
ONE_NS = 1_000_000_000
START_DATE = "2025-05-01"  # MBP-1 coverage start


def covered_days() -> dict:
    cov = {}
    for s in SYMBOLS:
        sd = MBP1 / f"symbol={s}"
        cov[s] = {p.name.split("=", 1)[1] for p in sd.glob("date=*")
                  if (p / "part-000.parquet").exists()} if sd.exists() else set()
    return cov


def load_universe() -> pd.DataFrame:
    df = pd.read_parquet(UNIVERSE)
    df = df[df["status"] == "entered"].copy()
    df["decision_ts_utc"] = pd.to_datetime(df["decision_ts_utc"], utc=True)
    df["touch_ts_utc"] = pd.to_datetime(df["touch_ts_utc"], utc=True)
    m = df["symbol"].isin(SYMBOLS)
    m &= df["session_date"] >= START_DATE
    m &= df["trail_2R"].abs() <= RISK_CAP
    m &= df["fixed_3R"].abs() <= RISK_CAP
    m &= df["touch_ts_utc"].notna() & (df["touch_ts_utc"] <= df["decision_ts_utc"])
    df = df[m].copy()
    df["trading_day"] = df["session_date"]
    cov = covered_days()
    df = df[df.apply(lambda r: r["trading_day"] in cov.get(r["symbol"], set()), axis=1)].copy()
    df = df.drop_duplicates(subset=["symbol", "decision_ts_utc", "level_price", "side"])
    return df.sort_values(["symbol", "trading_day", "decision_ts_utc"]).reset_index(drop=True)


def read_mbp1_trades(sym: str, td: str, lo_ns: int, hi_ns: int):
    p = MBP1 / f"symbol={sym}" / f"date={td}" / "part-000.parquet"
    lo, hi = pd.Timestamp(lo_ns, tz="UTC"), pd.Timestamp(hi_ns, tz="UTC")
    t = pds.dataset(p).to_table(
        columns=["ts_event", "action", "side", "price", "size"],
        filter=(pds.field("action") == "T") & (pds.field("ts_event") >= lo) & (pds.field("ts_event") < hi),
    ).to_pandas()
    return (t["ts_event"].astype("int64").to_numpy(), t["price"].to_numpy(float),
            t["side"].to_numpy(), t["size"].to_numpy(float))


def anchor_features(sym, row, tf_frames, ts, px, side, sz) -> dict:
    tick = TICK[sym]
    # reclaim: low swept -> long. displacement: high broken UP -> long (WITH the break).
    dir_sign = (1 if row["side"] == "high" else -1) if DISP else (1 if row["side"] == "low" else -1)
    dec = int(row["decision_ts_utc"].value)
    touch = int(row["touch_ts_utc"].value)
    out = {"symbol": sym, "session_date": row["session_date"], "trading_day": row["trading_day"],
           "level_family": row["level_family"], "side": row["side"],
           "level_price": float(row["level_price"]), "decision_ts_utc": row["decision_ts_utc"],
           "trail_2R": float(row["trail_2R"]), "fixed_3R": float(row["fixed_3R"]),
           "depth_tk": float(row.get("depth_tk", np.nan)), "wait_s": float(row.get("wait_s", np.nan))}
    # ---- DECISION-window orderflow PANEL [dec-90s, dec) (all dir-signed, from MBP-1 trades) ----
    w = (ts >= dec - WIN_NS) & (ts < dec)
    out["w90_trade_count"] = int(w.sum())
    if w.sum() >= 2:
        wp, ws, wz = px[w], side[w], sz[w]
        out["w90_drift_dir_ticks"] = dir_sign * (wp[-1] - wp[0]) / tick   # momentum into level
        buy = wz[ws == "B"].sum(); sell = wz[ws == "A"].sum(); tot = buy + sell
        out["w90_aggr_imb_dir"] = dir_sign * (buy - sell) / tot if tot > 0 else 0.0  # aggressor balance
        out["w90_delta_dir"] = float(dir_sign * (buy - sell))            # signed volume (raw)
        out["w90_vol"] = float(tot)                                       # participation
        span = (wp.max() - wp.min()) / tick
        out["w90_absorption"] = float(tot / (1.0 + span))                # vol per tick = absorption/defense
    else:
        for k in ("w90_drift_dir_ticks", "w90_aggr_imb_dir", "w90_delta_dir", "w90_vol", "w90_absorption"):
            out[k] = np.nan
    # late 30s acceleration (is the move ACCELERATING into the decision?)
    wl = (ts >= dec - 30 * ONE_NS) & (ts < dec)
    out["w30_late_drift_dir"] = dir_sign * (px[wl][-1] - px[wl][0]) / tick if wl.sum() >= 2 else np.nan
    # ---- APPROACH-window orderflow [touch-90s, touch) : flow as price APPROACHES the level ----
    wa = (ts >= touch - WIN_NS) & (ts < touch)
    if wa.sum() >= 2:
        ap, aps, apz = px[wa], side[wa], sz[wa]
        out["app_drift_dir"] = dir_sign * (ap[-1] - ap[0]) / tick
        ab = apz[aps == "B"].sum(); asl = apz[aps == "A"].sum(); at = ab + asl
        out["app_aggr_imb_dir"] = dir_sign * (ab - asl) / at if at > 0 else 0.0
        out["app_absorption"] = float(at / (1.0 + (ap.max() - ap.min()) / tick))
    else:
        for k in ("app_drift_dir", "app_aggr_imb_dir", "app_absorption"):
            out[k] = np.nan
    # zone_5m_has from BARS (reuse flow_at_zone)
    has = 0
    tf_b = tf_frames.get("5m")
    bars1m = tf_frames.get("1m")
    if tf_b is not None and len(tf_b):
        close_ns = tf_b.index.asi8 + 5 * 60 * ONE_NS
        sub = tf_b.iloc[(close_ns >= touch - 6 * 3600 * ONE_NS) & (close_ns <= dec)]
        zone = FZ._detect_zone_tf(sub, row["side"], float(row["level_price"]), touch, dec, "5m", tick)
        if zone is not None and FZ._retraced(bars1m, zone[0], zone[1], zone[3], dec, tick):
            has = 1
    out["zone_5m_has"] = has
    return out


def main() -> int:
    global UNIVERSE, CACHE, DISP, SYMBOLS
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--universe", default=None, help="alternate universe parquet (e.g. displacement)")
    ap.add_argument("--displacement", action="store_true", help="break-direction dir_sign")
    args = ap.parse_args()
    if args.universe:
        UNIVERSE = Path(args.universe)
        CACHE = RUNS / f"mbp1_stack_{UNIVERSE.stem}.parquet"
        SYMBOLS = sorted(pd.read_parquet(UNIVERSE, columns=["symbol"])["symbol"].unique())  # cross-asset
    DISP = args.displacement
    uni = load_universe()
    yr = pd.to_datetime(uni["session_date"]).dt.to_period("M")
    print(f"[universe] {len(uni)} reclaims over {uni['trading_day'].nunique()} days "
          f"({uni['session_date'].min()}..{uni['session_date'].max()}); "
          f"2025={int((pd.to_datetime(uni['session_date']).dt.year==2025).sum())} "
          f"2026={int((pd.to_datetime(uni['session_date']).dt.year==2026).sum())}", flush=True)
    if args.smoke:
        days = sorted(uni[uni["symbol"] == "ES.c.0"]["trading_day"].unique())[:3]
        uni = uni[(uni["symbol"] == "ES.c.0") & uni["trading_day"].isin(days)]
        print(f"[smoke] {days} -> {len(uni)} trades")

    cached = pd.read_parquet(CACHE) if CACHE.exists() else pd.DataFrame()
    done = set(map(tuple, cached[["symbol", "trading_day"]].drop_duplicates().to_numpy())) if len(cached) else set()
    groups = uni.groupby(["symbol", "trading_day"], sort=True)
    todo = [k for k in groups.groups if k not in done]
    print(f"[build] {groups.ngroups} symbol-days ({len(done)} cached, {len(todo)} to compute)", flush=True)
    for n, (sym, td) in enumerate(todo, 1):
        g = groups.get_group((sym, td))
        try:
            tf_frames = FZ._resample_for_day(sym, td)
            decs = g["decision_ts_utc"].astype("int64")
            tchs = g["touch_ts_utc"].astype("int64")  # widen read to cover approach window [touch-90s,touch)
            lo_ns = int(min(decs.min(), tchs.min())) - 100 * ONE_NS
            ts, px, side, sz = read_mbp1_trades(sym, td, lo_ns, int(decs.max()))
            rows = [anchor_features(sym, r, tf_frames, ts, px, side, sz) for _, r in g.iterrows()]
        except Exception as e:
            print(f"  SKIP {sym} {td}: {type(e).__name__}: {e}", flush=True)
            continue
        cached = pd.concat([cached, pd.DataFrame(rows)], ignore_index=True)
        tmp = CACHE.with_suffix(".tmp.parquet")
        cached.to_parquet(tmp, index=False); tmp.replace(CACHE)
        if n % 25 == 0 or n == len(todo):
            print(f"  [{n}/{len(todo)}] {sym} {td}: {len(rows)} anchors", flush=True)
    print(f"\nwrote {CACHE}: {len(cached)} rows", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
