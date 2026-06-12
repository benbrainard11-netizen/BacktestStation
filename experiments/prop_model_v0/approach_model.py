"""APPROACH MODEL (Ben's reframed target idea): pick TARGET levels, then catch the
moments price pulls away and turns back while trading toward one — "the last
pullback before the hit" — and learn which turns actually run into the target.

Targets per day (ALL prior-day info only): call wall, put wall (scaled), prior-day
high, prior-day low, prior close (gap fill). Walls compete against dumb levels.
Event (causal state machine on ES 1m closes, per day x target, before first touch):
price advances toward the target, pulls back >= 0.25 daysig off the high-water,
then turns back >= 0.10 daysig off the pullback low. Entry at the turn confirm,
target = the level, stop = pullback extreme -/+ 0.10 daysig buffer. Resolved to the
session close (day-flat), stop-wins-ties, 2pt costs. Levels/highs from minute
closes (consistent with the close-only convention used everywhere here).

Discipline: GEOMETRY baseline model (distance/clock/vol) vs FULL feature model —
credit only the value-add. Shuffled-target control gate. Week-block bootstrap.
Single pre-stated params (0.25/0.10/0.10, max dist 3 daysig) — no sweeps.

Run: backend/.venv/Scripts/python.exe experiments/prop_model_v0/approach_model.py
Artifacts: data/events_approach.parquet, report/approach_model.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

MODULE = Path(__file__).resolve().parent
REPO = MODULE.parents[1]
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(REPO / "experiments" / "btc_model_v0"))
from features_index import load_es_minutes  # noqa: E402
from model_wf import PARAMS, week_boot_p  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

PEERS = ["NQ.c.0", "GC.c.0", "6E.c.0", "ZN.c.0"]
TARGETS = ("cw", "pw", "pdh", "pdl", "pcl")
PB_F, CF_F, BUF_F = 0.25, 0.10, 0.10  # pullback / turn-confirm / stop buffer (daysig)
MAX_DIST_SIG = 3.0
COST_PTS = 2.0
ERA = pd.Timestamp("2024-07-01")
MIN_TRAIN_D, TEST_D, EMBARGO_D = 400, 90, 2
GEO_FEATS = [
    "dist_sig",
    "pull_sig",
    "prog",
    "side_up",
    "n_prior",
    "mins_in",
    "mins_left",
    "vol_6h",
    "hour_sin",
    "hour_cos",
]


def minute_series(sym: str):
    m = load_es_minutes(sym)
    return pd.DatetimeIndex(m.index.tz_localize(None)), m["c"].to_numpy(float)


def build_events() -> pd.DataFrame:
    f = pd.read_parquet(MODULE / "data" / "features_es.parquet")
    w = pd.read_parquet(MODULE / "data" / "walls_deep.parquet")
    w.index = pd.to_datetime(w["date"], format="%Y%m%d")
    es = load_es_minutes("ES.c.0")
    ets = pd.DatetimeIndex(es.index.tz_localize(None))
    ec = es["c"].to_numpy(float)
    etd = es["td"].to_numpy()
    g = pd.DataFrame({"c": ec, "td": etd}).groupby("td")["c"]
    day_hi, day_lo, day_cl = g.max(), g.min(), g.last()

    prev = w[["call_wall", "put_wall", "spot"]].reindex(f.index).shift(1)
    ratio = f["c_px"].shift(1) / prev["spot"]
    tg = pd.DataFrame(index=f.index)
    tg["cw"] = prev["call_wall"] * ratio
    tg["pw"] = prev["put_wall"] * ratio
    tg["pdh"] = day_hi.reindex(f.index).shift(1)
    tg["pdl"] = day_lo.reindex(f.index).shift(1)
    tg["pcl"] = day_cl.reindex(f.index).shift(1)
    daysig = (f["rv_20"] * f["c_px"]).shift(1)  # prior-day 1-sigma move in points

    peers = {p.split(".")[0].lower(): minute_series(p) for p in PEERS}
    dfeat = f[
        [
            c
            for c in f.columns
            if not c.startswith(("y_", "gx_", "ox_", "xs_"))
            and c not in ("rv20_bps", "c_px")
        ]
    ]
    dd = dfeat.copy()
    dd.index = dd.index + pd.Timedelta(hours=18)  # day D row valid from D 18:00
    ret1m = np.r_[0.0, np.diff(ec) / ec[:-1]]

    days = f.index.to_numpy()
    starts = np.searchsorted(etd, days)
    rows = []
    for i in range(1, len(days)):
        a = starts[i]
        b = starts[i + 1] if i + 1 < len(days) else len(ec)
        seg = ec[a:b]
        dsig = daysig.iloc[i]
        if len(seg) < 200 or not (np.isfinite(dsig) and dsig > 0):
            continue
        pb, cf, buf = PB_F * dsig, CF_F * dsig, BUF_F * dsig
        for tt in TARGETS:
            tlv = tg[tt].iloc[i]
            if not np.isfinite(tlv):
                continue
            sign = 1.0 if tlv > seg[0] else -1.0
            dist0 = sign * (tlv - seg[0])
            if dist0 <= 0 or dist0 > MAX_DIST_SIG * dsig:
                continue
            p = sign * (seg - seg[0])  # progress toward the target
            run_hi, low, state, n_ev = p[0], np.nan, 0, 0
            for j in range(1, len(seg)):
                if sign * (seg[j] - tlv) >= 0:
                    break  # target touched — done for this day x target
                if state == 0:
                    run_hi = max(run_hi, p[j])
                    if run_hi - p[j] >= pb:
                        state, low = 1, p[j]
                    continue
                low = min(low, p[j])
                if p[j] - low < cf:
                    continue
                # turn confirmed -> event
                gi = a + j
                t = ets[gi]
                entry = seg[j]
                stop = entry - sign * ((p[j] - low) + buf)
                risk = sign * (entry - stop)
                rest = seg[j:]
                ht = np.flatnonzero(sign * (rest - tlv) >= 0)
                hs = np.flatnonzero(sign * (rest - stop) <= 0)
                it = ht[0] if len(ht) else 10**12
                is_ = hs[0] if len(hs) else 10**12
                if is_ <= it and is_ < 10**12:
                    pnl = -risk
                elif it < 10**12:
                    pnl = sign * (tlv - entry)
                else:
                    pnl = sign * (rest[-1] - entry)
                r = {
                    "t": t,
                    "td": days[i],
                    "tt": tt,
                    "dist_sig": sign * (tlv - entry) / dsig,
                    "pull_sig": (run_hi - low) / dsig,
                    "prog": p[j] / dist0,
                    "side_up": float(sign > 0),
                    "n_prior": float(n_ev),
                    "mins_in": float(j),
                    "mins_left": float(len(seg) - j),
                    "hour_sin": np.sin(2 * np.pi * t.hour / 24),
                    "hour_cos": np.cos(2 * np.pi * t.hour / 24),
                    "dow_ev": float(pd.Timestamp(days[i]).weekday()),
                    "risk_pts": risk,
                    "y_r": (pnl - COST_PTS) / risk,
                    "y_hit": float(it < is_),
                }
                for lb, nm in [(60, "1h"), (240, "4h"), (1440, "24h")]:
                    k = int(ets.searchsorted(t - pd.Timedelta(minutes=lb)))
                    r[f"self_ret_{nm}"] = entry / ec[k] - 1 if k < gi else np.nan
                j6 = int(ets.searchsorted(t - pd.Timedelta(hours=6)))
                wnd = ret1m[j6:gi]
                r["vol_6h"] = float(np.std(wnd)) if len(wnd) > 30 else np.nan
                for tag, (pts_, pc_) in peers.items():
                    k0 = int(pts_.searchsorted(t)) - 1
                    if k0 < 100:
                        continue
                    for lb, nm in [(60, "1h"), (240, "4h"), (1440, "24h")]:
                        k1 = int(pts_.searchsorted(t - pd.Timedelta(minutes=lb)))
                        r[f"x_{tag}_{nm}"] = (
                            pc_[k0] / pc_[k1] - 1 if k1 < k0 else np.nan
                        )
                rows.append(r)
                n_ev += 1
                state, run_hi = 0, p[j]
    e = pd.DataFrame(rows).sort_values("t")
    for tt in TARGETS:
        e[f"tt_{tt}"] = (e["tt"] == tt).astype(float)
    e = pd.merge_asof(e, dd, left_on="t", right_index=True)
    e = e.reset_index(drop=True)
    e.to_parquet(MODULE / "data" / "events_approach.parquet")
    print(f"events: {len(e)} across {e['td'].nunique()} days")
    return e


def wf(e: pd.DataFrame, yv: np.ndarray, feats: list[str], shuffle: bool):
    dates = pd.DatetimeIndex(pd.to_datetime(e["td"]))
    udays = pd.DatetimeIndex(dates.unique()).sort_values()
    preds = np.full(len(e), np.nan)
    folds = np.full(len(e), -1)
    rng = np.random.default_rng(3)
    start, fid = MIN_TRAIN_D, 0
    while start < len(udays):
        td0 = udays[start]
        tem = dates.isin(udays[start : start + TEST_D])
        trm = (dates < td0 - pd.Timedelta(days=EMBARGO_D)) & np.isfinite(yv)
        if trm.sum() < 1500:
            start += TEST_D
            continue
        ytr = yv[trm]
        if shuffle:
            ytr = rng.permutation(ytr)
        mdl = lgb.LGBMRegressor(**PARAMS)
        mdl.fit(e.loc[trm, feats], ytr)
        preds[tem] = mdl.predict(e.loc[tem, feats])
        folds[tem] = fid
        fid += 1
        start += TEST_D
    return preds, folds


def mean_fold_ic(pred, yv, folds, mask):
    ics = []
    for fd in np.unique(folds[mask]):
        m = mask & (folds == fd)
        if m.sum() >= 100:
            ics.append(spearmanr(pred[m], yv[m]).statistic)
    return float(np.nanmean(ics)) if ics else np.nan


def main() -> int:
    fp = MODULE / "data" / "events_approach.parquet"
    e = pd.read_parquet(fp) if fp.exists() else build_events()
    yv = e["y_r"].to_numpy(float)
    feats_all = [
        c
        for c in e.columns
        if c not in ("t", "td", "tt", "y_r", "y_hit", "risk_pts")
        and pd.api.types.is_numeric_dtype(e[c])
    ]
    lines = ["# Approach model — last pullback before the hit", ""]
    desc = e.groupby("tt").agg(
        n=("y_r", "size"),
        hit=("y_hit", "mean"),
        mean_r=("y_r", "mean"),
        dist=("dist_sig", "mean"),
    )
    lines += [desc.to_string(), ""]
    lines.append(f"all events: n={len(e)}, mean net R {np.nanmean(yv):+.3f}")
    print("\n".join(lines))

    pc, fc = wf(e, yv, feats_all, shuffle=True)
    mc = np.isfinite(pc) & np.isfinite(yv)
    ic_c = mean_fold_ic(pc, yv, fc, mc)
    lines.append(f"control (shuffled y, full feats): {ic_c:+.3f}")
    print(lines[-1])
    if abs(ic_c) > 0.04:
        raise RuntimeError(f"CONTROL SCORED {ic_c:+.3f}")

    pg, fg = wf(e, yv, GEO_FEATS, shuffle=False)
    pf_, ff_ = wf(e, yv, feats_all, shuffle=False)
    mg = np.isfinite(pg) & np.isfinite(yv)
    mf = np.isfinite(pf_) & np.isfinite(yv)
    ic_g = mean_fold_ic(pg, yv, fg, mg)
    ic_f = mean_fold_ic(pf_, yv, ff_, mf)
    era_all = pd.DatetimeIndex(pd.to_datetime(e["td"])) >= ERA
    ic_f_era = float(spearmanr(pf_[mf & era_all], yv[mf & era_all]).statistic)
    lines.append(
        f"geometry IC {ic_g:+.3f} | full IC {ic_f:+.3f} | "
        f"value-add {ic_f - ic_g:+.3f} | full era pooled {ic_f_era:+.3f}"
    )
    print(lines[-1])

    for nm, pp, ffo in [("geometry", pg, fg), ("full", pf_, ff_)]:
        sel_frames = []
        for fd in np.unique(ffo[ffo >= 0]):
            m = np.isfinite(pp) & np.isfinite(yv) & (ffo == fd)
            if m.sum() < 100:
                continue
            thr = np.quantile(pp[m], 0.8)
            s = m & (pp >= thr)
            sel_frames.append(pd.DataFrame({"d": e.loc[s, "td"], "net": yv[s]}))
        tr = pd.concat(sel_frames)
        wk = pd.DatetimeIndex(tr["d"]).to_period("W").astype(str).to_numpy()
        net = tr["net"].to_numpy(float)
        era_t = pd.DatetimeIndex(tr["d"]) >= ERA
        lines.append(
            f"top-quintile by {nm:8s}: n={len(tr)}, mean net R {net.mean():+.3f}, "
            f"wk p5 {week_boot_p(net, wk, 5):+.3f} | era n={int(era_t.sum())} "
            f"mean {tr.loc[era_t, 'net'].mean():+.3f}"
        )
        print(lines[-1])
    (MODULE / "report" / "approach_model.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
