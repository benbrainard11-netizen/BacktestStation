"""WALL RACE — which options wall gets hit first? (structure-as-target, Ben's framing)

Label per day D: on D's 1-minute ES closes, does price touch the (prior-day) call
wall first (+1), the put wall first (-1), or neither (0)? Walls mapped to ES via the
D-1 close ratio. Features = the full feature row AS OF D-1's close (price/vol/cross
/gx/ox blocks) + race geometry (position-in-range, wall distances in vol units).

HONESTY STRUCTURE: three runs — shuffled control, DISTANCE-ONLY baseline (position/
distance features alone; "nearer wall hits first" is trivial and must not be sold as
edge), and the full model. The full model's value = improvement over distance-only.
Trade sim: top-decile |pred| -> enter at D open toward the favored wall, target =
that wall, stop = halfway to the other wall, flat at close; net R after 2-pt costs.

Run: backend/.venv/Scripts/python.exe experiments/prop_model_v0/wall_race.py
Artifact: report/wall_race_v0.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

MODULE = Path(__file__).resolve().parent
REPO = MODULE.parents[1]
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(REPO / "experiments" / "btc_model_v0"))
from features_index import load_es_minutes  # noqa: E402
from model_wf import fold_ic, run_wf, week_boot_p  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

COST_PTS = 2.0


def build_race() -> pd.DataFrame:
    w = pd.read_parquet(MODULE / "data" / "walls_deep.parquet")
    w.index = pd.to_datetime(w["date"], format="%Y%m%d")
    f = pd.read_parquet(MODULE / "data" / "features_es.parquet")
    m = load_es_minutes("ES.c.0")
    es_close = f["c_px"]
    # walls known at D-1 close -> race runs on day D
    prev = (
        pd.DataFrame(
            {
                "cw": w["call_wall"],
                "pw": w["put_wall"],
                "spot": w["spot"],
                "gex": w["gex_proxy"],
            }
        )
        .reindex(f.index)
        .shift(1)
    )
    ratio = es_close.shift(1) / prev["spot"]
    cw_es, pw_es = prev["cw"] * ratio, prev["pw"] * ratio
    feat_prev = f.shift(1)  # full feature row as of D-1 close

    mc, mtd = m["c"].to_numpy(float), m["td"].to_numpy()
    days = f.index.to_numpy()
    starts = np.searchsorted(mtd, days)
    rows = []
    for i, d in enumerate(f.index):
        cw, pw = cw_es.iloc[i], pw_es.iloc[i]
        if not (np.isfinite(cw) and np.isfinite(pw) and cw > pw):
            continue
        a = starts[i]
        b = starts[i + 1] if i + 1 < len(days) else len(mc)
        seg = mc[a:b]
        if len(seg) < 100:
            continue
        hit_c = np.flatnonzero(seg >= cw)
        hit_p = np.flatnonzero(seg <= pw)
        ic_ = hit_c[0] if len(hit_c) else 10**12
        ip_ = hit_p[0] if len(hit_p) else 10**12
        y = 1.0 if ic_ < ip_ else (-1.0 if ip_ < ic_ else 0.0)
        entry = seg[0]
        rows.append(
            {
                "d": d,
                "y_race": y,
                "entry": entry,
                "cw": cw,
                "pw": pw,
                "close_d": seg[-1],
                "pos": (entry - pw) / (cw - pw),
                "dist_c_rv": (cw / entry - 1)
                / max(f["rv_20"].iloc[i - 1] if i else np.nan, 1e-5),
                "dist_p_rv": (1 - pw / entry)
                / max(f["rv_20"].iloc[i - 1] if i else np.nan, 1e-5),
                "width_rv": (cw - pw)
                / entry
                / max(f["rv_20"].iloc[i - 1] if i else np.nan, 1e-5),
                "gex_z": np.nan,  # filled below
            }
        )
    r = pd.DataFrame(rows).set_index("d")
    gz = (prev["gex"] - prev["gex"].rolling(60).mean()) / prev["gex"].rolling(60).std()
    r["gex_z"] = gz.reindex(r.index)
    fp = feat_prev.reindex(r.index)
    fp = fp[
        [
            c
            for c in fp.columns
            if not c.startswith("y_") and c not in ("rv20_bps", "c_px")
        ]
    ]
    return pd.concat([r, fp.add_prefix("f_")], axis=1)


def trade_sim(pred: pd.Series, r: pd.DataFrame, mask) -> pd.DataFrame:
    rows = []
    pb = pred[mask]
    thr = pb.abs().quantile(0.9)
    for d in pb.index[pb.abs() >= thr]:
        row = r.loc[d]
        long = pb.loc[d] > 0
        tgt = row["cw"] if long else row["pw"]
        stp = (
            row["entry"] - 0.5 * (row["entry"] - row["pw"])
            if long
            else row["entry"] + 0.5 * (row["cw"] - row["entry"])
        )
        risk = abs(row["entry"] - stp)
        if risk <= 0:
            continue
        if (long and row["y_race"] == 1) or (not long and row["y_race"] == -1):
            pnl = abs(tgt - row["entry"])
        elif row["y_race"] == 0:
            pnl = (row["close_d"] - row["entry"]) * (1 if long else -1)
            pnl = max(pnl, -risk)  # stop bounds the day-flat loss
        else:
            pnl = -risk
        rows.append({"d": d, "net_r": pnl / risk - COST_PTS / risk})
    return pd.DataFrame(rows)


def main() -> int:
    r = build_race()
    print(f"race days: {len(r)} ({r.index.min().date()} -> {r.index.max().date()})")
    print(
        f"base rates: call-first {(r['y_race'] == 1).mean():.0%}, "
        f"put-first {(r['y_race'] == -1).mean():.0%}, neither {(r['y_race'] == 0).mean():.0%}"
    )
    y = r["y_race"]
    geo = ["pos", "dist_c_rv", "dist_p_rv", "width_rv"]
    full = geo + ["gex_z"] + [c for c in r.columns if c.startswith("f_")]

    pc, fc = run_wf(r[full], y, shuffle_target=True)
    ic_c = fold_ic(pc, y, fc, pc.notna() & y.notna())
    print(f"control: {ic_c:+.3f}")
    if abs(ic_c) > 0.06:
        raise RuntimeError(f"CONTROL SCORED {ic_c:+.3f}")
    pg, fg = run_wf(r[geo], y, shuffle_target=False)
    ic_g = fold_ic(pg, y, fg, pg.notna() & y.notna())
    pf, ff = run_wf(r[full], y, shuffle_target=False)
    ic_f = fold_ic(pf, y, ff, pf.notna() & y.notna())
    print(
        f"distance-only IC {ic_g:+.3f} | FULL model IC {ic_f:+.3f} | value-add {ic_f - ic_g:+.3f}"
    )

    mask = pf.notna() & y.notna()
    tr_g = trade_sim(pg, r, pg.notna() & y.notna())
    tr_f = trade_sim(pf, r, mask)
    lines = [
        f"# Wall race — {len(r)} days, control {ic_c:+.3f}",
        f"base rates C/P/neither: {(y == 1).mean():.0%}/{(y == -1).mean():.0%}/{(y == 0).mean():.0%}",
        f"distance-only IC {ic_g:+.3f} | full IC {ic_f:+.3f} | VALUE-ADD {ic_f - ic_g:+.3f}",
        "",
    ]
    for nm, tr in [("distance-only", tr_g), ("full", tr_f)]:
        if len(tr):
            net = tr["net_r"].to_numpy(float)
            wk = pd.DatetimeIndex(tr["d"]).to_period("W").astype(str).to_numpy()
            lines.append(
                f"{nm} trades n={len(tr)}: mean net R {net.mean():+.3f}, "
                f"week-block p5 {week_boot_p(net, wk, 5):+.3f}"
            )
    report = "\n".join(lines)
    (MODULE / "report" / "wall_race_v0.md").write_text(report, encoding="utf-8")
    print("\n" + report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
