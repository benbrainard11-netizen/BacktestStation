"""Iteration 3 event dataset: trigger fires -> seek the options wall -> stop = ATR, EOD.

One row per (day, 5-min time, direction) where >=1 trigger fires that direction toward
a reachable gamma wall. Carries which triggers fired (so each is testable separately
AND as confluence), the first-passage label to EOD, and signed realized R. fut_/opt_/
mbp_ feature blocks are NOT recomputed here — they join from the existing caches by
(date, ms) in the model step (they're objective-independent state at t).

Causality: triggers use bars closed by t (et <= t-1m); walls use the gex panel row
<= t; basis from day D-1; ATR from days < D. Entry = first post-decision print.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\build_events.py
Output: out/events_v3.parquet + out/events_v3.manifest.json
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

OUTDIR = Path(__file__).resolve().parent / "out"
GRID_MS = list(range(9 * 3600_000 + 35 * 60_000, 15 * 3600_000 + 45 * 60_000 + 1, C.GRID_STEP_MIN * 60_000))
SESSION_END_MS = 16 * 3600_000


def _tick(x: float) -> float:
    return round(x / C.TICK) * C.TICK


def walls_at(gex_row, basis: float) -> list[float]:
    if gex_row is None:
        return []
    out = []
    for col in ("call_wall", "put_wall", "zero_gamma", "pin"):
        v = float(gex_row[col])
        if np.isfinite(v):
            out.append(_tick(v + basis))
    return out


def pick_wall(walls: list[float], entry: float, direction: int, atr: float):
    """Nearest wall in the trigger's direction within [MIN_PTS, MAX_ATR*ATR]."""
    cap = C.TRIG_TGT_MAX_ATR * atr
    if direction > 0:
        cands = [w for w in walls if C.TRIG_TGT_MIN_PTS <= w - entry <= cap]
        return min(cands) if cands else None
    cands = [w for w in walls if C.TRIG_TGT_MIN_PTS <= entry - w <= cap]
    return max(cands) if cands else None


def build_day(day: Date, prev_day: Date, panels: dict, atr: float, basis: float,
              sv_lut: dict, stop_atr: float) -> list[dict]:
    es = D.rth_bars(day)
    if es is None or len(es) < 60:
        return []
    nq = D.load_bars_sym(C.BARS_1M_NQ, day)
    nq_rth = nq[(nq["et"] >= D.et_ts(day, 9 * 3600_000 + 30 * 60_000)) &
                (nq["et"] < D.et_ts(day, SESSION_END_MS))] if nq is not None else None
    ctx = T.DayCtx.build(es, nq_rth)
    gex_day = panels["gex"][panels["gex"]["d"] == day]

    rows = []
    for ms in GRID_MS:
        if ms > C.TRIG_LAST_ENTRY_MS:
            break
        t = D.et_ts(day, ms)
        pre = es[es["et"] <= t - pd.Timedelta(minutes=1)]   # bars closed by t
        if len(pre) < C.SWEEP_LOOKBACK_MIN + 2:
            continue
        idx = len(pre) - 1   # ctx is built from the same rth rows in et order -> aligns
        C.assert_no_lookahead(pre["et"].iloc[-1] + pd.Timedelta(minutes=1), t, "trigger bars")
        gex_row = OL_last(gex_day, ms)
        if gex_row is not None:
            C.assert_no_lookahead(int(gex_row["ms_of_day"]), ms, "gex panel")  # review F6
        walls = walls_at(gex_row, basis)
        if not walls:
            continue
        sv_z = sv_lut.get((day.isoformat(), ms), np.nan)
        dirs = {"sweep": T.sweep_dir(ctx, idx), "smt": T.smt_dir(ctx, idx), "flow": T.flow_dir(sv_z)}

        fwd = es[(es["et"] >= t) & (es["et"] < D.et_ts(day, SESSION_END_MS))]
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
            r_long, r_short = OL.realized_r(y, entry, up, dn, close_end)
            r_signed = r_long if direction > 0 else r_short
            reached = (y == 1) if direction > 0 else (y == 0)

            # delayed-entry (next bar) robustness
            r_d1 = np.nan
            fwd1 = fwd[fwd["et"] >= t + pd.Timedelta(minutes=1)]
            if len(fwd1):
                e1 = float(fwd1["open"].iloc[0])
                up1, dn1 = (target, e1 - stop_atr * atr) if direction > 0 else (e1 + stop_atr * atr, target)  # review F8
                if dn1 < e1 < up1:
                    yd, ce1, _ = OL.race_label(fwd1, up1, dn1)
                    if yd is not None:
                        rl1, rs1 = OL.realized_r(yd, e1, up1, dn1, ce1)
                        r_d1 = rl1 if direction > 0 else rs1

            rows.append({
                "date": day.isoformat(), "ms": ms, "dir": direction, "entry": entry,
                "target": target, "stop": stop,
                "target_dist_pts": abs(target - entry), "stop_dist_pts": abs(entry - stop),
                "fired_sweep": fired["sweep"], "fired_smt": fired["smt"], "fired_flow": fired["flow"],
                "confluence": conf, "y": y, "reached": reached, "mins_to_resolve": mins,
                "r_signed": r_signed, "r_signed_d1": r_d1, "atr": atr,
            })
    return rows


def OL_last(panel_day: pd.DataFrame, ms: int):
    rows = panel_day[panel_day["ms_of_day"] <= ms]
    return rows.iloc[-1] if len(rows) else None


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="v3")
    ap.add_argument("--stop-atr", type=float, default=C.TRIG_STOP_ATR)
    args = ap.parse_args()

    panels = D.load_panels()
    mbp = pd.read_parquet(OUTDIR / "mbp_features_v0.parquet", columns=["date", "ms", "mbp_sv_1m_z"])
    sv_lut = {(d, int(m)): float(z) for d, m, z in
              zip(mbp["date"], mbp["ms"], mbp["mbp_sv_1m_z"])}
    gex_days = sorted(panels["gex"]["d"].unique())
    dev_days = [d for d in gex_days if C.DEV_START <= d.isoformat() <= C.DEV_END]
    atr_tr, all_rows, skips = D.AtrTracker(), [], 0
    last_basis = None
    print(f"building trigger events over {len(dev_days)} dev days")
    for i, day in enumerate(dev_days):
        prev = next((p for p in reversed(gex_days) if p < day), None)
        rth_today = D.rth_bars(day)
        if prev is None or rth_today is None:
            continue
        atr = atr_tr.atr()
        b = D.basis_for(day, prev, panels["gex"][panels["gex"]["d"] == prev])
        basis = b if b is not None else last_basis
        if basis is not None:
            last_basis = basis
        if atr is not None and basis is not None:
            all_rows.extend(build_day(day, prev, panels, atr, basis, sv_lut, args.stop_atr))
        else:
            skips += 1
        atr_tr.push_day(rth_today)
        if i and i % 40 == 0:
            print(f"  ...{i}/{len(dev_days)} days, {len(all_rows)} events")

    df = pd.DataFrame(all_rows)
    assert df["date"].max() <= C.DEV_END, "holdout leak"
    OUTDIR.mkdir(exist_ok=True)
    out = OUTDIR / f"events_{args.tag}.parquet"
    df.to_parquet(out)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=C.REPO).stdout.strip()
    manifest = {"git_sha": sha, "tag": args.tag, "stop_atr": args.stop_atr,
                "events": len(df), "days": int(df["date"].nunique()),
                "by_trigger": {k: int(df[f"fired_{k}"].sum()) for k in ("sweep", "smt", "flow")},
                "confluence_counts": {int(k): int(v) for k, v in df["confluence"].value_counts().items()},
                "reach_rate": float(df["reached"].mean()),
                "median_target_pts": float(df["target_dist_pts"].median()),
                "median_stop_pts": float(df["stop_dist_pts"].median()),
                "params": {k: getattr(C, k) for k in ("TRIG_STOP_ATR", "TRIG_TGT_MIN_PTS",
                            "TRIG_TGT_MAX_ATR", "SWING_K", "SWEEP_LOOKBACK_MIN", "SWEEP_RECENT_MIN",
                            "SWEEP_BUF_TK", "FLOW_Z", "TRIG_LAST_ENTRY_MS")}}
    (OUTDIR / f"events_{args.tag}.manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n{len(df)} events / {df['date'].nunique()} days -> {out}")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
