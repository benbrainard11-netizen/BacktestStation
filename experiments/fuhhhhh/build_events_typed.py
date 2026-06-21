"""Iteration 3.1 typed event dataset: tagged sweeps + TF-tagged SMT + flow -> wall -> EOD.

Same labeling/causality as build_events.py (v3), but triggers come from typed_triggers
(multi-TF sweep menu + per-TF SMT). Each sweep event carries swept_type/_tf/_dist/
overshoot/confirm_* tags so the study can classify which sweeps work. v3 events left
intact; this writes events_v3t.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\build_events_typed.py
Output: out/events_v3t.parquet + manifest
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
import typed_triggers as TT
from build_events import GRID_MS, SESSION_END_MS, walls_at, pick_wall, OL_last

OUTDIR = Path(__file__).resolve().parent / "out"
SWEEP_TAG_COLS = ["swept_type", "swept_tf", "swept_dist_atr", "overshoot_tk",
                  "n_levels_swept", "confirm_5m", "confirm_15m"]


def session_levels(prev_rth, on):
    lv = {}
    if prev_rth is not None:
        lv["pdh"], lv["pdl"] = float(prev_rth["high"].max()), float(prev_rth["low"].min())
    if on is not None:
        lv["onh"], lv["onl"] = float(on["high"].max()), float(on["low"].min())
    return lv


def build_day(day, prev_day, panels, atr, basis, sv_lut, stop_atr):
    es = D.rth_bars(day)
    if es is None or len(es) < 60:
        return []
    on = D.overnight_bars(prev_day, day)
    es_full = pd.concat([b for b in (on, es) if b is not None], ignore_index=True).sort_values("et")
    # NQ overnight loaded SYMMETRICALLY to ES (same [18:00 prev, 09:30 day) window) so
    # the resampled ES/NQ bin grids align by timestamp (SMT fix, review #5)
    nq_on = D.overnight_bars(prev_day, day, root=C.BARS_1M_NQ)
    nq_day = D.load_bars_sym(C.BARS_1M_NQ, day)
    nq_rth = nq_day[(nq_day["et"] >= D.et_ts(day, 9 * 3600_000 + 30 * 60_000)) &
                    (nq_day["et"] < D.et_ts(day, SESSION_END_MS))] if nq_day is not None else None
    nq_full = pd.concat([b for b in (nq_on, nq_rth) if b is not None], ignore_index=True).sort_values("et") \
        if nq_rth is not None else None
    sess = session_levels(D.rth_bars(prev_day), on)
    sess["orh"] = sess["orl"] = None
    or_bars = es[es["et"] < D.et_ts(day, 9 * 3600_000 + 30 * 60_000 + C.OPENING_RANGE_MIN * 60_000)]
    ctx = TT.TypedDayCtx.build(es, es_full, nq_full, sess)
    gex_day = panels["gex"][panels["gex"]["d"] == day]

    rows = []
    for ms in GRID_MS:
        if ms > C.TRIG_LAST_ENTRY_MS:
            break
        t = D.et_ts(day, ms)
        pre = es[es["et"] <= t - pd.Timedelta(minutes=1)]
        if len(pre) < TT.SWEEP_RECENT_BARS + 2:
            continue
        idx = len(pre) - 1
        C.assert_no_lookahead(pre["et"].iloc[-1] + pd.Timedelta(minutes=1), t, "typed trig bars")
        if ms >= 9 * 3600_000 + 45 * 60_000 and len(or_bars):   # OR formed by 09:45
            ctx.session["orh"], ctx.session["orl"] = float(or_bars["high"].max()), float(or_bars["low"].min())
        gex_row = OL_last(gex_day, ms)
        if gex_row is not None:
            C.assert_no_lookahead(int(gex_row["ms_of_day"]), ms, "gex panel")
        walls = walls_at(gex_row, basis)
        if not walls:
            continue

        sweep = TT.detect_sweep(ctx, idx, atr)
        smt = TT.detect_smt(ctx, idx)
        sv_z = sv_lut.get((day.isoformat(), ms), np.nan)
        flow = (1 if sv_z >= C.FLOW_Z else (-1 if sv_z <= -C.FLOW_Z else 0)) if np.isfinite(sv_z) else 0

        fwd = es[(es["et"] >= t) & (es["et"] < D.et_ts(day, SESSION_END_MS))]
        if fwd.empty:
            continue
        entry = float(fwd["open"].iloc[0])

        for direction in (1, -1):
            sw = sweep if (sweep and sweep[0] == direction) else None
            sm = smt if (smt and smt[0] == direction) else None
            fl = flow == direction
            conf = int(bool(sw)) + int(bool(sm)) + int(fl)
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
            r_d1 = np.nan
            fwd1 = fwd[fwd["et"] >= t + pd.Timedelta(minutes=1)]
            if len(fwd1):
                e1 = float(fwd1["open"].iloc[0])
                up1, dn1 = (target, e1 - stop_atr * atr) if direction > 0 else (e1 + stop_atr * atr, target)
                if dn1 < e1 < up1:
                    yd, ce1, _ = OL.race_label(fwd1, up1, dn1)
                    if yd is not None:
                        rl1, rs1 = OL.realized_r(yd, e1, up1, dn1, ce1)
                        r_d1 = rl1 if direction > 0 else rs1

            row = {"date": day.isoformat(), "ms": ms, "dir": direction, "entry": entry,
                   "target": target, "stop": stop, "target_dist_pts": abs(target - entry),
                   "stop_dist_pts": abs(entry - stop), "fired_sweep": bool(sw),
                   "fired_smt": bool(sm), "fired_flow": fl, "confluence": conf,
                   "smt_tf": sm[1]["smt_tf"] if sm else None, "y": y, "reached": reached,
                   "mins_to_resolve": mins, "r_signed": r_signed, "r_signed_d1": r_d1, "atr": atr}
            for cset in SWEEP_TAG_COLS:
                row[cset] = sw[1][cset] if sw else (np.nan if cset in
                            ("swept_dist_atr", "overshoot_tk", "n_levels_swept") else None)
            rows.append(row)
    return rows


def main() -> int:
    panels = D.load_panels()
    mbp = pd.read_parquet(OUTDIR / "mbp_features_v0.parquet", columns=["date", "ms", "mbp_sv_1m_z"])
    sv_lut = {(d, int(m)): float(z) for d, m, z in zip(mbp["date"], mbp["ms"], mbp["mbp_sv_1m_z"])}
    gex_days = sorted(panels["gex"]["d"].unique())
    dev_days = [d for d in gex_days if C.DEV_START <= d.isoformat() <= C.DEV_END]
    atr_tr, all_rows, last_basis = D.AtrTracker(), [], None
    print(f"building typed trigger events over {len(dev_days)} dev days")
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
            all_rows.extend(build_day(day, prev, panels, atr, basis, sv_lut, C.TRIG_STOP_ATR))
        atr_tr.push_day(rth_today)
        if i and i % 40 == 0:
            print(f"  ...{i}/{len(dev_days)} days, {len(all_rows)} events")

    df = pd.DataFrame(all_rows)
    assert df["date"].max() <= C.DEV_END, "holdout leak"
    OUTDIR.mkdir(exist_ok=True)
    out = OUTDIR / "events_v3t.parquet"
    df.to_parquet(out)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=C.REPO).stdout.strip()
    sw = df[df["fired_sweep"]]
    manifest = {"git_sha": sha, "events": len(df), "days": int(df["date"].nunique()),
                "by_trigger": {k: int(df[f"fired_{k}"].sum()) for k in ("sweep", "smt", "flow")},
                "sweep_by_type": {str(k): int(v) for k, v in sw["swept_type"].value_counts().items()},
                "sweep_by_tf": {str(k): int(v) for k, v in sw["swept_tf"].value_counts().items()},
                "smt_by_tf": {str(k): int(v) for k, v in df[df["fired_smt"]]["smt_tf"].value_counts().items()},
                "reach_rate": float(df["reached"].mean())}
    (OUTDIR / "events_v3t.manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n{len(df)} events / {df['date'].nunique()} days -> {out}")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
