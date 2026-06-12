"""Lever 2 — the champion signal at INTRADAY grain (ES, hourly decisions).

Decision points: every hour 18:00 ET -> 15:00 ET (22/day). Features strictly <= t:
self momentum/vol/position (1m-derived), peer returns minute-synced (NQ/GC/6E/ZN —
the NQ-lead hypothesis says these matter MORE at hours), session clock, prior-day
champion context via asof. Labels (pre-stated ladder, no post-hoc pick): bracket
race (+1.0 sigma_t / -0.75 sigma_t, sigma_t = trailing-6h vol projected to horizon)
resolved over (a) REST-OF-SESSION [primary — day-flat native], (b) next 4h, (c) next
1h. Control-first day-purged WF; era subset + decile net R (2-pt costs) reported.

Run: backend/.venv/Scripts/python.exe experiments/prop_model_v0/intraday_index.py
Artifacts: data/intraday_es.parquet, report/intraday_index.md
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
DEC_HOURS_ET = list(range(18, 24)) + list(range(0, 16))  # 18:00 -> 15:00
ERA = pd.Timestamp("2024-07-01")
COST_PTS = 2.0
MIN_TRAIN_D, TEST_D, EMBARGO_D = 400, 90, 2


def minute_series(sym: str):
    m = load_es_minutes(sym)
    ts = pd.DatetimeIndex(m.index.tz_localize(None))
    return ts, m["c"].to_numpy(float)


def build_matrix() -> pd.DataFrame:
    es = load_es_minutes("ES.c.0")
    ets = pd.DatetimeIndex(es.index.tz_localize(None))
    ec = es["c"].to_numpy(float)
    etd = es["td"].to_numpy()
    peers = {p.split(".")[0].lower(): minute_series(p) for p in PEERS}
    daily = pd.read_parquet(MODULE / "data" / "features_es.parquet")
    dfeat = daily[
        [
            c
            for c in daily.columns
            if not c.startswith(("y_", "gx_", "ox_", "xs_"))
            and c not in ("rv20_bps", "c_px")
        ]
    ]
    dd = dfeat.copy()
    dd.index = dd.index + pd.Timedelta(
        hours=18
    )  # day D row valid from its 18:00 close+1h

    # decision timestamps: hourly marks present in the ES minute index
    tod_h = es.index.hour
    is_mark = (es.index.minute == 0) & np.isin(tod_h, DEC_HOURS_ET)
    dec_idx = np.flatnonzero(is_mark)
    rows = []
    day_end = {}  # td -> last index
    for i, td in enumerate(etd):
        day_end[td] = i
    ret1m = np.r_[0.0, np.diff(ec) / ec[:-1]]
    for i0 in dec_idx:
        t = ets[i0]
        td = etd[i0]
        i_close = day_end[td]
        if i_close - i0 < 30 or i0 < 1500:
            continue
        r = {"t": t, "td": td, "price": ec[i0]}
        for lb, nm in [(60, "1h"), (240, "4h"), (1440, "24h")]:
            j = int(ets.searchsorted(t - pd.Timedelta(minutes=lb)))
            r[f"self_ret_{nm}"] = ec[i0] / ec[j] - 1 if j < i0 else np.nan
        j6 = int(ets.searchsorted(t - pd.Timedelta(hours=6)))
        w = ret1m[j6:i0]
        r["vol_6h"] = float(np.std(w)) if len(w) > 30 else np.nan
        j24 = int(ets.searchsorted(t - pd.Timedelta(hours=24)))
        w24 = ec[j24:i0]
        r["rng_pos_24h"] = (
            (ec[i0] - w24.min()) / (w24.max() - w24.min())
            if len(w24) > 10 and w24.max() > w24.min()
            else np.nan
        )
        for tag, (pts_, pc_) in peers.items():
            k0 = int(pts_.searchsorted(t)) - 1
            if k0 < 100:
                continue
            for lb, nm in [(60, "1h"), (240, "4h"), (1440, "24h")]:
                k1 = int(pts_.searchsorted(t - pd.Timedelta(minutes=lb)))
                r[f"x_{tag}_{nm}"] = pc_[k0] / pc_[k1] - 1 if k1 < k0 else np.nan
        r["hour_sin"] = np.sin(2 * np.pi * t.hour / 24)
        r["hour_cos"] = np.cos(2 * np.pi * t.hour / 24)
        r["dow"] = float(pd.Timestamp(td).weekday())
        r["mins_left"] = float(i_close - i0)
        # labels: bracket race to each horizon (sigma scaled by sqrt(horizon))
        for horizon, nm in [
            (i_close, "rs"),
            (min(i0 + 240, i_close), "4h"),
            (min(i0 + 60, i_close), "1h"),
        ]:
            n_min = horizon - i0
            sig = (
                r["vol_6h"] * np.sqrt(max(n_min, 1))
                if np.isfinite(r.get("vol_6h", np.nan))
                else np.nan
            )
            if not (np.isfinite(sig) and sig > 0):
                r[f"y_{nm}"] = np.nan
                continue
            seg = ec[i0:horizon]
            tgt, stp = ec[i0] * (1 + 1.0 * sig), ec[i0] * (1 - 0.75 * sig)
            ht = np.flatnonzero(seg >= tgt)
            hs = np.flatnonzero(seg <= stp)
            it = ht[0] if len(ht) else 10**12
            is_ = hs[0] if len(hs) else 10**12
            if is_ <= it and is_ < 10**12:
                r[f"y_{nm}"] = -1.0
            elif it < 10**12:
                r[f"y_{nm}"] = 1.0 / 0.75
            else:
                r[f"y_{nm}"] = float((seg[-1] / ec[i0] - 1) / (0.75 * sig))
            if nm == "rs":
                r["risk_pts"] = 0.75 * sig * ec[i0]
        rows.append(r)
    f = pd.DataFrame(rows).set_index("t").sort_index()
    f = pd.merge_asof(f, dd, left_index=True, right_index=True)
    f = f.copy()
    f.to_parquet(MODULE / "data" / "intraday_es.parquet")
    print(
        f"intraday matrix: {len(f)} decisions, "
        f"{len([c for c in f.columns if not c.startswith('y_')])} features"
    )
    return f


def wf_days(f: pd.DataFrame, y: pd.Series, shuffle: bool):
    dates = pd.DatetimeIndex(pd.to_datetime(f["td"]))
    udays = dates.unique().sort_values()
    feats = [
        c
        for c in f.columns
        if not c.startswith("y_") and c not in ("td", "risk_pts", "price")
    ]
    preds = pd.Series(np.nan, index=f.index)
    folds = pd.Series(-1, index=f.index)
    rng = np.random.default_rng(3)
    start, fid = MIN_TRAIN_D, 0
    while start < len(udays):
        test_days = udays[start : start + TEST_D]
        trm = dates < (test_days[0] - pd.Timedelta(days=EMBARGO_D))
        tem = dates.isin(test_days)
        ytr = y[trm].dropna()
        if len(ytr) < 2000:
            start += TEST_D
            continue
        if shuffle:
            ytr = pd.Series(rng.permutation(ytr.to_numpy()), index=ytr.index)
        mdl = lgb.LGBMRegressor(**PARAMS)
        mdl.fit(f.loc[ytr.index, feats], ytr)
        preds[tem] = mdl.predict(f.loc[tem, feats])
        folds[tem] = fid
        fid += 1
        start += TEST_D
    return preds, folds


def mean_fold_ic(pred, y, folds, mask):
    ics = []
    for fd in sorted(folds[mask].unique()):
        m = mask & (folds == fd)
        if m.sum() >= 100:
            ics.append(spearmanr(pred[m], y[m]).statistic)
    return float(np.nanmean(ics)) if ics else np.nan


def main() -> int:
    fp = MODULE / "data" / "intraday_es.parquet"
    f = pd.read_parquet(fp) if fp.exists() else build_matrix()
    lines = ["# Intraday-grain ES model (hourly decisions)", ""]
    y_rs = f["y_rs"]
    pc, fc = wf_days(f, y_rs, shuffle=True)
    ic_c = mean_fold_ic(pc, y_rs, fc, pc.notna() & y_rs.notna())
    lines.append(f"control (rest-of-session): {ic_c:+.3f}")
    print(lines[-1])
    if abs(ic_c) > 0.04:
        raise RuntimeError(f"CONTROL SCORED {ic_c:+.3f}")
    era_mask = pd.DatetimeIndex(f.index) >= ERA
    for nm in ("rs", "4h", "1h"):
        yy = f[f"y_{nm}"]
        pr, fr_ = wf_days(f, yy, shuffle=False)
        m = pr.notna() & yy.notna()
        ic = mean_fold_ic(pr, yy, fr_, m)
        ic_era = float(spearmanr(pr[m & era_mask], yy[m & era_mask]).statistic)
        lines.append(
            f"y_{nm}: mean-fold IC {ic:+.3f} | era IC {ic_era:+.3f} (n_era={int((m & era_mask).sum())})"
        )
        print(lines[-1])
        if nm == "rs":
            cost_r = COST_PTS / f["risk_pts"]
            trades = []
            for fd in sorted(fr_[m].unique()):
                mm = m & (fr_ == fd)
                if mm.sum() < 200:
                    continue
                pb = pr[mm]
                hi, lo = pb.quantile(0.95), pb.quantile(0.05)
                for d in pb.index[(pb >= hi)]:
                    trades.append({"d": d, "net": yy.loc[d] - cost_r.loc[d]})
                for d in pb.index[(pb <= lo)]:
                    trades.append({"d": d, "net": -yy.loc[d] - cost_r.loc[d]})
            tr = pd.DataFrame(trades)
            wk = pd.DatetimeIndex(tr["d"]).to_period("W").astype(str).to_numpy()
            net = tr["net"].to_numpy(float)
            era_t = pd.DatetimeIndex(tr["d"]) >= ERA
            lines.append(
                f"  top/bottom-5% trades n={len(tr)}: mean net R {net.mean():+.3f}, "
                f"wk p5 {week_boot_p(net, wk, 5):+.3f} | era n={int(era_t.sum())} "
                f"mean {tr.loc[era_t, 'net'].mean():+.3f}"
            )
            print(lines[-1])
    (MODULE / "report" / "intraday_index.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
