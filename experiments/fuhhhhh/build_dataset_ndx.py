"""NASDAQ move-model dataset: predict WHICH MOVE happens first (up / down / chop).

Ben's design insight (2026-06-13): direction and magnitude are entangled — in chop,
direction is noise; you can only call direction when a real move is coming. So the
target is a 3-class forward-move race, not a naked up/down:

    y = 1  up-move    : +MOVE_ATR*ATR touched before -MOVE_ATR*ATR   within HORIZON
    y = 0  down-move  : -MOVE_ATR*ATR touched before +MOVE_ATR*ATR   within HORIZON
    y = 2  chop       : neither barrier touched by HORIZON (or ambiguous same-bar)

One row per (day, 5-min decision t) — NO trigger gating (triggers become FEATURES, not
filters). Feature families, each in its real role:
  geo_     : time-of-day, ATR (state/normalizer)
  struct_  : sweep_dir, smt_dir (NQ-primary / ES-confirm) — the WHEN
  opt_     : NDX gamma regime (prior-day, causal) — gamma sign, |GEX|, spot-vs-zero_gamma,
             distance to each wall in ATR units — the WEATHER (is a move coming, how big)
  (orderflow opt-in next: NQ MBP-1 OFI/CVD — the WHICH-WAY, Ben's documented edge)

Causality (rule 1): triggers use NQ bars closed by t; opt_ features use PRIOR-day NDX
walls; ATR from days < D; entry = first post-decision NQ print; label uses ONLY bars in
(t, t+HORIZON]. Net-cost R for a long and a short ±MOVE_ATR trade are carried for the
tradeable eval.

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\build_dataset_ndx.py
Output: out/dataset_ndx.parquet + manifest
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
from build_events_ndx import load_walls_ndx, sym_rth, ndx_nq_basis

OUTDIR = Path(__file__).resolve().parent / "out"
# barrier = +-MOVE_ATR * daily ATR. A real intraday move is a FRACTION of daily ATR
# (~sqrt(horizon/session)); 0.75*daily-ATR over 60min is ~98% chop. Tunable via CLI.
HORIZON_MIN = 60          # forward window for the move race
MOVE_ATR = 0.25           # symmetric -> 1:1 reward:risk


def opt_features(walls_prev: dict, basis: float, entry: float, atr: float) -> dict:
    """Prior-day NDX gamma-regime context, mapped to NQ space, normalized by ATR."""
    cw = walls_prev["call_wall"] + basis
    pw = walls_prev["put_wall"] + basis
    zg = (walls_prev["zero_gamma"] + basis) if np.isfinite(walls_prev["zero_gamma"]) else np.nan
    pin = walls_prev["pin"] + basis
    gex = walls_prev["gex_proxy"]
    return {
        "opt_gamma_sign": float(np.sign(gex)),
        "opt_gex_log": float(np.sign(gex) * np.log1p(abs(gex))),
        "opt_dist_call_atr": (cw - entry) / atr,
        "opt_dist_put_atr": (entry - pw) / atr,
        "opt_dist_pin_atr": (pin - entry) / atr,
        "opt_above_zero_gamma": (1.0 if (np.isfinite(zg) and entry > zg) else 0.0),
        "opt_dist_zero_atr": ((entry - zg) / atr) if np.isfinite(zg) else 0.0,
        "opt_wall_span_atr": (cw - pw) / atr,
    }


def build_day(day: Date, walls_prev: dict, atr: float, basis: float,
              horizon_min: int = HORIZON_MIN, move_atr: float = MOVE_ATR) -> list[dict]:
    nq = sym_rth(C.BARS_1M_NQ, day)
    if nq is None or len(nq) < 90:
        return []
    es_rth = sym_rth(C.BARS_1M, day)
    ctx = T.DayCtx.build(nq, es_rth)            # primary=NQ, confirm=ES
    move = move_atr * atr
    rows = []
    for ms in GRID_MS:
        if ms > C.TRIG_LAST_ENTRY_MS:
            break
        t = D.et_ts(day, ms)
        pre = nq[nq["et"] <= t - pd.Timedelta(minutes=1)]
        if len(pre) < C.SWEEP_LOOKBACK_MIN + 2:
            continue
        idx = len(pre) - 1
        C.assert_no_lookahead(pre["et"].iloc[-1] + pd.Timedelta(minutes=1), t, "ndx ds bars")

        end = min(ms + horizon_min * 60_000, SESSION_END_MS)
        fwd = nq[(nq["et"] >= t) & (nq["et"] < D.et_ts(day, end))]
        if len(fwd) < 5:
            continue
        entry = float(fwd["open"].iloc[0])
        up, dn = entry + move, entry - move
        y, close_end, mins = OL.race_label(fwd, up, dn)
        if y is None:
            continue
        y3 = 2 if y in (2, -1) else y           # ambiguous same-bar -> chop
        r_long, r_short = OL.realized_r(y if y != -1 else -1, entry, up, dn, close_end, C.COST_PTS_NQ)

        row = {"date": day.isoformat(), "ms": ms, "y": int(y3),
               "r_long": r_long, "r_short": r_short, "mins_to_resolve": mins,
               "geo_ms": float(ms), "geo_atr": atr, "geo_hour": float(ms // 3600_000),
               "struct_sweep": float(T.sweep_dir(ctx, idx)),
               "struct_smt": float(T.smt_dir(ctx, idx))}
        row.update(opt_features(walls_prev, basis, entry, atr))
        rows.append(row)
    return rows


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon", type=int, default=HORIZON_MIN)
    ap.add_argument("--move-atr", type=float, default=MOVE_ATR)
    args = ap.parse_args()

    walls = load_walls_ndx()
    all_days = sorted(walls)
    dev_days = [d for d in all_days if C.DEV_START <= d.isoformat() <= C.DEV_END]
    atr_tr, rows, last_basis, skips = D.AtrTracker(), [], None, 0
    print(f"move-model dataset H={args.horizon}m move={args.move_atr}ATR over "
          f"{len(dev_days)} dev days ({dev_days[0]}..{dev_days[-1]})")
    for day in all_days:
        if day.isoformat() > C.DEV_END:
            break
        prev = next((p for p in reversed(all_days) if p < day), None)
        nq_today = sym_rth(C.BARS_1M_NQ, day)
        if nq_today is None:
            continue
        if C.DEV_START <= day.isoformat() and prev is not None and prev in walls:
            atr = atr_tr.atr()
            basis = ndx_nq_basis(prev, walls[prev])
            basis = basis if basis is not None else last_basis
            if basis is not None:
                last_basis = basis
            if atr is not None and basis is not None:
                rows.extend(build_day(day, walls[prev], atr, basis, args.horizon, args.move_atr))
            else:
                skips += 1
        atr_tr.push_day(nq_today)

    df = pd.DataFrame(rows)
    assert df["date"].max() <= C.DEV_END, "holdout leak"
    OUTDIR.mkdir(exist_ok=True)
    out = OUTDIR / "dataset_ndx.parquet"
    df.to_parquet(out)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=C.REPO).stdout.strip()
    cls = {int(k): int(v) for k, v in df["y"].value_counts().items()}
    manifest = {"git_sha": sha, "asset": "NQ/NDX", "horizon_min": args.horizon, "move_atr": args.move_atr,
                "rows": len(df), "days": int(df["date"].nunique()), "skips": skips,
                "class_counts": cls, "class_names": {"0": "down-move", "1": "up-move", "2": "chop"},
                "feature_cols": [c for c in df.columns if c.split("_")[0] in ("geo", "struct", "opt")],
                "cost_pts_nq": C.COST_PTS_NQ}
    (OUTDIR / "dataset_ndx.manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n{len(df)} rows / {df['date'].nunique()} days -> {out}")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
