"""Build a dataset: one row per (day, 5-min decision time) with geo_/fut_/opt_
feature blocks, race label y, net realized-R columns, and cost-burden columns.
Dev window ONLY — holdout rows are never built here (SPEC §2).

Causality (rule 1): price/futures features use bars with ts_event <= t-1m (a 1m bar
stamped s spans [s, s+1m) — fully known only at s+1m); options panels use rows with
ms_of_day <= t; EOD context uses dates < D; basis uses day D-1. Asserted inline.

v2 (Iteration 2B) economic objective filters are passed on the CLI; the registered
v0/v1 artifact is protected (refuses to overwrite dataset_v0).

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\build_dataset.py ^
       --tag v2_c006 --min-pts 9.6 --cap-atr 1.0
Output: out/dataset_<tag>.parquet + out/dataset_<tag>.manifest.json
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date as Date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
import data_io as D
import features as F
import objectives_labels as OL

OUTDIR = Path(__file__).resolve().parent / "out"
GRID_MS = list(range(9 * 3600_000 + 35 * 60_000, 15 * 3600_000 + 45 * 60_000 + 1, C.GRID_STEP_MIN * 60_000))
OR_END_MS = 9 * 3600_000 + 30 * 60_000 + C.OPENING_RANGE_MIN * 60_000


def session_levels(prev_rth: pd.DataFrame | None, on: pd.DataFrame | None) -> dict[str, float]:
    lv: dict[str, float] = {}
    if prev_rth is not None:
        lv["pdh"], lv["pdl"] = float(prev_rth["high"].max()), float(prev_rth["low"].min())
    if on is not None:
        lv["onh"], lv["onl"] = float(on["high"].max()), float(on["low"].min())
    return lv


def build_day(day: Date, prev_day: Date, panels: dict, atr: float, basis: float,
              min_pts: float | None = None, cap_atr: float | None = None) -> list[dict]:
    rth = D.rth_bars(day)
    if rth is None or len(rth) < 60:
        return []
    levels = session_levels(D.rth_bars(prev_day), D.overnight_bars(prev_day, day))
    prior_close = float(D.rth_bars(prev_day)["close"].iloc[-1]) if D.rth_bars(prev_day) is not None else None
    gex_day = panels["gex"][panels["gex"]["d"] == day]
    dte0_day = panels["dte0"][panels["dte0"]["d"] == day]
    iv_day = panels["iv"][panels["iv"]["d"] == day]
    eod_prev_rows = panels["eod"][panels["eod"]["d"] < day]
    eod_prev = eod_prev_rows.iloc[-1] if len(eod_prev_rows) else None
    if eod_prev is not None and (day - eod_prev["d"]).days > 5:
        eod_prev = None  # stale beyond a long weekend — treat as unavailable

    or_bars = rth[rth["et"] < D.et_ts(day, OR_END_MS)]
    rows = []
    for ms in GRID_MS:
        t = D.et_ts(day, ms)
        pre = rth[rth["et"] <= t - pd.Timedelta(minutes=1)]  # bars fully closed by t
        if len(pre) < 5:
            continue
        C.assert_no_lookahead(pre["et"].iloc[-1] + pd.Timedelta(minutes=1), t, "bars")
        price = float(pre["close"].iloc[-1])
        lv = dict(levels)
        if ms >= OR_END_MS and len(or_bars):
            lv["orh"], lv["orl"] = float(or_bars["high"].max()), float(or_bars["low"].min())

        fut = F.futures_features(pre, lv, ms, atr, prior_close)
        vol = pre["volume"].to_numpy(float)
        vwap = float((pre["vwap"].to_numpy(float) * vol).sum() / vol.sum()) if vol.sum() > 0 else float("nan")
        gex_row = F._last_at_or_before(gex_day, ms)
        if gex_row is not None:
            C.assert_no_lookahead(int(gex_row["ms_of_day"]), ms, "gex panel")
        picked = OL.pick_objectives(OL.candidate_levels(gex_row, lv, vwap, basis), price, atr,
                                    min_pts=min_pts, cap_atr=cap_atr)
        if picked is None:
            continue
        (up, fam_up), (dn, fam_dn) = picked

        end = min(t + pd.Timedelta(minutes=C.TIME_BARRIER_MIN), D.et_ts(day, 16 * 3600_000))
        fwd = rth[(rth["et"] >= t) & (rth["et"] < end)]
        if fwd.empty:
            continue  # early close — no forward bars, no race (review F9)
        entry = float(fwd["open"].iloc[0])  # first attainable post-decision print (review F3)
        if entry >= up or entry <= dn:
            continue  # gapped through an objective before entry — race pre-decided (PRIOR_ART 1.7d trap)
        y, close_end, mins_res = OL.race_label(fwd, up, dn)
        if y is None:
            continue
        r_long, r_short = OL.realized_r(y, entry, up, dn, close_end)

        # one-bar-delayed-entry outcomes (robustness test I): enter at open(t+1m),
        # race the SAME objectives to the SAME deadline. NaN when delayed entry is
        # impossible (gapped through an objective / no bars left). Primary y untouched.
        y1, rl1, rs1 = np.nan, np.nan, np.nan
        fwd1 = fwd[fwd["et"] >= t + pd.Timedelta(minutes=1)]
        if len(fwd1):
            entry1 = float(fwd1["open"].iloc[0])
            if dn < entry1 < up:
                yd, ce1, _ = OL.race_label(fwd1, up, dn)
                if yd is not None:
                    y1 = yd
                    rl1, rs1 = OL.realized_r(yd, entry1, up, dn, ce1)

        du, dd = up - entry, entry - dn
        row: dict = {"date": day.isoformat(), "ms": ms, "price": price, "entry": entry,
                     "obj_up": up, "obj_dn": dn, "y": y, "r_long_net": r_long, "r_short_net": r_short,
                     "y_d1": y1, "r_long_net_d1": rl1, "r_short_net_d1": rs1,
                     "mins_to_resolve": mins_res, "dist_up_pts": du, "dist_dn_pts": dd,
                     "cost_to_up": C.COST_PTS / du, "cost_to_dn": C.COST_PTS / dd}
        row.update(OL.geo_features(price, up, dn, fam_up, fam_dn, atr))
        row.update(fut)
        row.update(F.options_features(gex_day, dte0_day, iv_day, eod_prev, ms, price, basis, atr))
        rows.append(row)
    return rows


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="dataset tag, e.g. v2_c006")
    ap.add_argument("--min-pts", type=float, default=None, help="objective floor, points (both sides)")
    ap.add_argument("--cap-atr", type=float, default=None, help="objective cap, ATR fraction")
    args = ap.parse_args()
    if args.tag == "v0":
        raise SystemExit("dataset_v0 is a locked artifact — pick a new tag")

    panels = D.load_panels()
    gex_days = sorted(panels["gex"]["d"].unique())
    dev_days = [d for d in gex_days if C.DEV_START <= d.isoformat() <= C.DEV_END]
    atr_tr, all_rows, skips = D.AtrTracker(), [], {"no_atr": 0, "no_basis": 0, "no_bars": 0}
    last_basis: float | None = None
    print(f"building [{args.tag}] min_pts={args.min_pts} cap_atr={args.cap_atr}: "
          f"{len(dev_days)} dev days {dev_days[0]} -> {dev_days[-1]}")
    for i, day in enumerate(dev_days):
        prev = next((p for p in reversed(gex_days) if p < day), None)
        rth_today = D.rth_bars(day)
        if prev is None or rth_today is None:
            skips["no_bars"] += 1
            continue
        atr = atr_tr.atr()
        b = D.basis_for(day, prev, panels["gex"][panels["gex"]["d"] == prev])
        basis = b if b is not None else last_basis  # 0.0 is a legal basis (review F5)
        if basis is not None:
            last_basis = basis
        if atr is None:
            skips["no_atr"] += 1
        elif basis is None:
            skips["no_basis"] += 1
        else:
            all_rows.extend(build_day(day, prev, panels, atr, basis,
                                      min_pts=args.min_pts, cap_atr=args.cap_atr))
        atr_tr.push_day(rth_today)  # AFTER use: day D's TR never feeds day D
        if i and i % 40 == 0:
            print(f"  ...{i}/{len(dev_days)} days, {len(all_rows)} rows")

    df = pd.DataFrame(all_rows)
    assert df["date"].max() <= C.DEV_END, "holdout row leaked into dev dataset"
    OUTDIR.mkdir(exist_ok=True)
    out = OUTDIR / f"dataset_{args.tag}.parquet"
    df.to_parquet(out)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=C.REPO).stdout.strip()
    manifest = {"tag": args.tag, "git_sha": sha, "rows": len(df), "days": int(df["date"].nunique()),
                "skips": skips, "ambiguous": int((df["y"] == -1).sum()),
                "class_counts": {str(k): int(v) for k, v in df["y"].value_counts().items()},
                "objective_filter": {"min_pts": args.min_pts, "cap_atr": args.cap_atr},
                "median_dist_up": float(df["dist_up_pts"].median()),
                "median_dist_dn": float(df["dist_dn_pts"].median()),
                "median_cost_to_up": float(df["cost_to_up"].median()),
                "median_cost_to_dn": float(df["cost_to_dn"].median()),
                "timeout_rate": float((df["y"] == 2).mean()),
                "median_mins_to_resolve": float(df["mins_to_resolve"].median()),
                "params": {k: getattr(C, k) for k in ("OBJ_MIN_PTS", "OBJ_CAP_ATR_FRAC", "TIME_BARRIER_MIN",
                                                      "GRID_STEP_MIN", "COST_PTS", "ATR_LEN")}}
    (OUTDIR / f"dataset_{args.tag}.manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n{len(df)} rows / {df['date'].nunique()} days -> {out}")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
