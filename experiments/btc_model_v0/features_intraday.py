"""Intraday decision-point matrix — the session-cycle test (4 decisions/day).

Decision points at session boundaries (ET): 18:00 (asia), 03:00 (europe), 08:30
(us_am), 13:00 (us_pm). Per decision t: running intraday state strictly from 1m
closes <= t, the full DAILY feature row as-of the last completed trading day
(merge_asof — never same-day daily features), and funding asof-joined on event
timestamps. Label: vol-scaled triple-barrier over the NEXT session on 1m closes
(target +1.0 sigma_s, stop -0.5 sigma_s, sigma_s = trailing 20 same-session-type
return std, stop wins ties; unresolved = end-of-session value in R).

Run: backend/.venv/Scripts/python.exe experiments/btc_model_v0/features_intraday.py
Artifact: data/features_intraday.parquet
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

MODULE = Path(__file__).resolve().parent
sys.path.insert(0, str(MODULE))
from features import load_minutes  # noqa: E402

SESS_STARTS = [(1080, "asia"), (180, "europe"), (510, "us_am"), (780, "us_pm")]
LOOKBACKS_MIN = [60, 180, 360, 1440]

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def main() -> int:
    m = load_minutes()
    mc = m["c"].to_numpy(float)
    mv = m["v"].to_numpy(float)
    midx = pd.DatetimeIndex(m.index.tz_localize(None))
    daily = pd.read_parquet(MODULE / "data" / "features.parquet")
    daily_feats = daily[[c for c in daily.columns if not c.startswith("y_") and c not in ("rv20_bps", "c_px")]]
    fr = pd.read_parquet(MODULE / "data" / "funding.parquet")
    f_ts = pd.DatetimeIndex(fr["ts"].dt.tz_localize(None))
    f_rate = fr["rate"].to_numpy(float)

    # decision timestamps: every session boundary present in the minute index
    tods = midx.hour * 60 + midx.minute
    rows = []
    bounds = []
    for tod_min, name in SESS_STARTS:
        hits = np.flatnonzero((tods == tod_min) & np.r_[True, np.diff(midx.values) > np.timedelta64(30, "s")])
        for i in hits:
            bounds.append((midx[i], int(i), name))
    bounds.sort()
    # session returns history per type for sigma_s
    hist: dict[str, list[float]] = {n: [] for _, n in SESS_STARTS}
    for bi, (t, i, name) in enumerate(bounds):
        i_next = bounds[bi + 1][1] if bi + 1 < len(bounds) else len(mc)
        if i_next - i < 30 or i < 1500:
            continue
        seg = mc[i:i_next]
        sess_ret = seg[-1] / seg[0] - 1
        sig = float(np.std(hist[name][-20:])) if len(hist[name]) >= 10 else np.nan
        r = {"t": t, "sess": name, "price": mc[i]}
        for lb in LOOKBACKS_MIN:
            j = int(np.searchsorted(midx.values, (t - pd.Timedelta(minutes=lb)).to_datetime64()))
            r[f"ret_{lb}m"] = mc[i] / mc[j] - 1 if j < i else np.nan
            if lb >= 360:
                w = mc[j:i]
                r[f"vol_{lb}m"] = float(np.std(np.diff(w) / w[:-1])) if len(w) > 30 else np.nan
        j6 = int(np.searchsorted(midx.values, (t - pd.Timedelta(minutes=360)).to_datetime64()))
        j24 = int(np.searchsorted(midx.values, (t - pd.Timedelta(minutes=1440)).to_datetime64()))
        v6, v24 = mv[j6:i].sum(), mv[j24:i].sum()
        r["volu_ratio"] = (v6 / (v24 / 4)) if v24 > 0 else np.nan
        w24 = mc[j24:i]
        r["rng_pos_24h"] = (
            (mc[i] - w24.min()) / (w24.max() - w24.min())
            if len(w24) > 10 and w24.max() > w24.min() else np.nan
        )
        fj = int(np.searchsorted(f_ts.values, t.to_datetime64()))
        r["fund_last"] = f_rate[fj - 1] if fj > 0 else np.nan
        r["fund_3ev"] = f_rate[max(fj - 3, 0):fj].sum() if fj > 0 else np.nan
        # label on the next session
        if np.isfinite(sig) and sig > 0:
            tgt, stp = mc[i] * (1 + 1.0 * sig), mc[i] * (1 - 0.5 * sig)
            ht = np.flatnonzero(seg >= tgt)
            hs = np.flatnonzero(seg <= stp)
            it = ht[0] if len(ht) else 10**12
            is_ = hs[0] if len(hs) else 10**12
            if is_ <= it and is_ < 10**12:
                r["y_R"] = -1.0
            elif it < 10**12:
                r["y_R"] = 2.0
            else:
                r["y_R"] = float(sess_ret / (0.5 * sig))
            r["sigma_s"] = sig
        hist[name].append(sess_ret)
        rows.append(r)
    f = pd.DataFrame(rows).set_index("t").sort_index()
    for _, name in SESS_STARTS:
        f[f"sess_{name}"] = (f["sess"] == name).astype(float)
    # daily features as-of the LAST COMPLETED day (decision t maps to prior td row)
    dd = daily_feats.copy()
    dd.index = dd.index + pd.Timedelta(hours=18)  # row for day D becomes valid at D 18:00 ET close
    f = pd.merge_asof(f.drop(columns=["sess"]), dd, left_index=True, right_index=True,
                      allow_exact_matches=True)
    f.to_parquet(MODULE / "data" / "features_intraday.parquet")
    n_feat = len([c for c in f.columns if not c.startswith("y_") and c not in ("sigma_s", "price")])
    print(f"intraday: {n_feat} features x {len(f)} decisions "
          f"({f.index.min()} -> {f.index.max()}); label coverage {f['y_R'].notna().mean():.0%}; "
          f"win rate {(f['y_R'] > 0).mean():.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
