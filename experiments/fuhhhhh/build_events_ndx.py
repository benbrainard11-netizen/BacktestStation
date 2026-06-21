"""NASDAQ port of Iteration 3: NQ trigger -> seek prior-day NDX gamma wall -> stop=ATR, EOD.

Faithful twin of build_events.py, with the asset roles swapped:
  primary instrument = NQ (sweep + pivots)        (was ES)
  SMT confirm index  = ES                          (was NQ)
  target walls       = PRIOR-DAY NDX daily walls   (was SPX intraday GEX panel)
  basis              = NDX -> NQ                    (was SPX -> ES)
  economics          = NQ ($20/pt, COST_PTS_NQ)    (was ES $50/pt)

Causality (rule 1): triggers use NQ bars closed by t (et <= t-1m); the target wall is
PRIOR-DAY (D-1) NDX EOD walls (OI is fixed at the prior close, so D-1 walls are known
at D's open); basis from D-1; ATR from days < D; entry = first post-decision NQ print.

LIMITATION (honest): NDX walls are DAILY static prior-EOD levels, not intraday-repriced
like the SPX panel the ES model used. So the wall here is a fixed daily level the price
seeks intraday. Flow trigger deferred (NQ MBP features not built yet) -> sweep + SMT only.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\build_events_ndx.py
Output: out/events_ndx.parquet + out/events_ndx.manifest.json
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date as Date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
import data_io as D
import objectives_labels as OL
import triggers as T
from build_events import GRID_MS, SESSION_END_MS

OUTDIR = Path(__file__).resolve().parent / "out"
RTH_OPEN_MS = 9 * 3600_000 + 30 * 60_000
WALL_COLS = ("call_wall", "put_wall", "zero_gamma", "pin")


def _tick(x: float) -> float:
    return round(x / C.TICK) * C.TICK


def load_walls_ndx() -> dict[Date, dict]:
    """walls_ndx.parquet -> {python date: {spot, call_wall, put_wall, zero_gamma, pin, gex_proxy}}."""
    df = pd.read_parquet(C.WALLS_NDX)
    df["d"] = pd.to_datetime(df["date"].astype(int).astype(str), format="%Y%m%d").dt.date
    extra = ["gex_proxy"] if "gex_proxy" in df.columns else []
    out = {}
    for _, r in df.iterrows():
        out[r["d"]] = {"spot": float(r["spot"]), **{c: float(r[c]) for c in WALL_COLS + tuple(extra)}}
    return out


def load_intraday_walls() -> dict[tuple[str, int], list[float]]:
    """walls_ndx_intraday.parquet -> {(date_iso, ms): [walls in NQ space]} (basis pre-applied)."""
    p = C.WALLS_NDX.parent / "walls_ndx_intraday.parquet"
    df = pd.read_parquet(p)
    lut: dict[tuple[str, int], list[float]] = {}
    for date_iso, ms, cw, pw, zg, pin in zip(df["date"], df["ms"], df["call_wall"],
                                             df["put_wall"], df["zero_gamma"], df["pin"]):
        ws = [_tick(v) for v in (cw, pw, zg, pin) if np.isfinite(v)]
        if ws:
            lut[(date_iso, int(ms))] = ws
    return lut


def sym_rth(root, day: Date) -> pd.DataFrame | None:
    """RTH [09:30,16:00) bars for a symbol's bar dir, ET-stamped."""
    df = D.load_bars_sym(root, day)
    if df is None:
        return None
    lo, hi = D.et_ts(day, RTH_OPEN_MS), D.et_ts(day, SESSION_END_MS)
    out = df[(df["et"] >= lo) & (df["et"] < hi)]
    return out if len(out) else None


def ndx_nq_basis(prev_day: Date, walls_prev: dict) -> float | None:
    """NQ - NDX additive basis from PRIOR day: NQ EOD close minus NDX EOD spot."""
    nq_prev = sym_rth(C.BARS_1M_NQ, prev_day)
    if nq_prev is None:
        return None
    return float(nq_prev["close"].iloc[-1]) - walls_prev["spot"]


def walls_at_ndx(walls_prev: dict, basis: float) -> list[float]:
    out = []
    for col in WALL_COLS:
        v = walls_prev[col]
        if np.isfinite(v):
            out.append(_tick(v + basis))
    return out


def pick_wall(walls: list[float], entry: float, direction: int, atr: float):
    """Nearest wall in the trigger's direction within [MIN_PTS_NQ, MAX_ATR*ATR]."""
    cap = C.TRIG_TGT_MAX_ATR * atr
    lo = C.TRIG_TGT_MIN_PTS_NQ
    if direction > 0:
        cands = [w for w in walls if lo <= w - entry <= cap]
        return min(cands) if cands else None
    cands = [w for w in walls if lo <= entry - w <= cap]
    return max(cands) if cands else None


def build_day(day: Date, walls_prev: dict, atr: float, basis: float, stop_atr: float,
              intraday_lut: dict | None = None) -> list[dict]:
    nq = sym_rth(C.BARS_1M_NQ, day)
    if nq is None or len(nq) < 60:
        return []
    es_rth = sym_rth(C.BARS_1M, day)
    ctx = T.DayCtx.build(nq, es_rth)          # primary=NQ, confirm=ES
    static_walls = walls_at_ndx(walls_prev, basis)
    if intraday_lut is None and not static_walls:
        return []

    rows = []
    for ms in GRID_MS:
        if ms > C.TRIG_LAST_ENTRY_MS:
            break
        t = D.et_ts(day, ms)
        pre = nq[nq["et"] <= t - pd.Timedelta(minutes=1)]   # NQ bars closed by t
        if len(pre) < C.SWEEP_LOOKBACK_MIN + 2:
            continue
        idx = len(pre) - 1                                   # ctx built from same rth rows
        C.assert_no_lookahead(pre["et"].iloc[-1] + pd.Timedelta(minutes=1), t, "ndx trigger bars")

        walls = intraday_lut.get((day.isoformat(), ms), []) if intraday_lut is not None else static_walls
        if not walls:
            continue

        dirs = {"sweep": T.sweep_dir(ctx, idx), "smt": T.smt_dir(ctx, idx), "flow": 0}

        fwd = nq[(nq["et"] >= t) & (nq["et"] < D.et_ts(day, SESSION_END_MS))]
        if fwd.empty:
            continue
        entry = float(fwd["open"].iloc[0])

        for direction in (1, -1):
            fired = {k: (v == direction) for k, v in dirs.items()}
            conf = sum(fired.values())
            if conf == 0:
                continue
            target = pick_wall(walls, entry, direction, atr)
            if target is None:
                continue
            stop = entry - stop_atr * atr if direction > 0 else entry + stop_atr * atr
            up, dn = (target, stop) if direction > 0 else (stop, target)
            if not (dn < entry < up):
                continue
            y, close_end, mins = OL.race_label(fwd, up, dn)
            if y is None:
                continue
            r_long, r_short = OL.realized_r(y, entry, up, dn, close_end, C.COST_PTS_NQ)
            r_signed = r_long if direction > 0 else r_short
            reached = (y == 1) if direction > 0 else (y == 0)

            r_d1 = np.nan                                    # delayed (next-bar) entry robustness
            fwd1 = fwd[fwd["et"] >= t + pd.Timedelta(minutes=1)]
            if len(fwd1):
                e1 = float(fwd1["open"].iloc[0])
                up1, dn1 = (target, e1 - stop_atr * atr) if direction > 0 else (e1 + stop_atr * atr, target)
                if dn1 < e1 < up1:
                    yd, ce1, _ = OL.race_label(fwd1, up1, dn1)
                    if yd is not None:
                        rl1, rs1 = OL.realized_r(yd, e1, up1, dn1, ce1, C.COST_PTS_NQ)
                        r_d1 = rl1 if direction > 0 else rs1

            rows.append({
                "date": day.isoformat(), "ms": ms, "dir": direction, "entry": entry,
                "target": target, "stop": stop,
                "target_dist_pts": abs(target - entry), "stop_dist_pts": abs(entry - stop),
                "fired_sweep": fired["sweep"], "fired_smt": fired["smt"], "fired_flow": False,
                "confluence": conf, "y": y, "reached": reached, "mins_to_resolve": mins,
                "r_signed": r_signed, "r_signed_d1": r_d1, "atr": atr,
            })
    return rows


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default=None)
    ap.add_argument("--walls", choices=["daily", "intraday"], default="daily")
    ap.add_argument("--stop-atr", type=float, default=C.TRIG_STOP_ATR)
    ap.add_argument("--end", default=C.DEV_END, help="last day (holdout discipline: keep <= 2026-03-31)")
    args = ap.parse_args()
    tag = args.tag or ("ndx_intraday" if args.walls == "intraday" else "ndx")
    intraday_lut = load_intraday_walls() if args.walls == "intraday" else None

    walls = load_walls_ndx()
    wall_days = sorted(d for d in walls if C.DEV_START <= d.isoformat() <= args.end)
    all_days = sorted(walls)
    atr_tr, all_rows, last_basis, skips = D.AtrTracker(), [], None, 0
    print(f"NASDAQ port: {len(wall_days)} dev days with NDX walls ({wall_days[0]}..{wall_days[-1]})")

    # ATR(14) on NQ RTH needs a warm-up across ALL available days, not just dev days
    seen = set()
    for day in all_days:
        if day.isoformat() > args.end:
            break
        prev = next((p for p in reversed(all_days) if p < day), None)
        nq_today = sym_rth(C.BARS_1M_NQ, day)
        if nq_today is None:
            continue
        if day in set(wall_days) and prev is not None and prev in walls:
            atr = atr_tr.atr()
            basis = ndx_nq_basis(prev, walls[prev])
            basis = basis if basis is not None else last_basis
            if basis is not None:
                last_basis = basis
            if atr is not None and basis is not None:
                all_rows.extend(build_day(day, walls[prev], atr, basis, args.stop_atr, intraday_lut))
            else:
                skips += 1
        atr_tr.push_day(nq_today)
        seen.add(day)
        if len(seen) % 40 == 0:
            print(f"  ...{len(seen)} days, {len(all_rows)} events")

    df = pd.DataFrame(all_rows)
    assert df["date"].max() <= args.end, "holdout leak"
    OUTDIR.mkdir(exist_ok=True)
    out = OUTDIR / f"events_{tag}.parquet"
    df.to_parquet(out)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=C.REPO).stdout.strip()
    manifest = {"git_sha": sha, "tag": tag, "asset": "NQ/NDX", "walls": args.walls, "stop_atr": args.stop_atr,
                "dev_end": args.end, "events": len(df), "days": int(df["date"].nunique()),
                "skips_no_atr_or_basis": skips,
                "by_trigger": {k: int(df[f"fired_{k}"].sum()) for k in ("sweep", "smt", "flow")},
                "confluence_counts": {int(k): int(v) for k, v in df["confluence"].value_counts().items()},
                "reach_rate": float(df["reached"].mean()),
                "median_target_pts": float(df["target_dist_pts"].median()),
                "median_stop_pts": float(df["stop_dist_pts"].median()),
                "cost_pts_nq": C.COST_PTS_NQ}
    (OUTDIR / f"events_{tag}.manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n{len(df)} events / {df['date'].nunique()} days -> {out}")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
