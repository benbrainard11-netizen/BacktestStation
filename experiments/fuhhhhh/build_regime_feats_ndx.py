"""ANGLE 1 — build CAUSAL regime features for NQ direction, keyed (date, ms).

Every feature at decision (date, ms) uses only NQ 1m bars whose ET close is STRICTLY
BEFORE the decision time (assert_no_lookahead at build). Writes a uniquely-named file
out/dirhunt_regime.parquet (rule 4: never touch shared artifacts).

Regime families (all causal):
  rv_*    : realized-vol state (last-30m std of 1m log-rets, vs trailing intraday + daily ATR)
  trend_* : trend / momentum state (signed cumret over 15/30/60m, distance from VWAP)
  chop_*  : autocorrelation / choppiness (lag-1 autocorr of 1m rets, |net|/sum|moves|, hi-lo efficiency)
  tod_*   : time of day (minutes since open, session-third one-hots)
  gap_*   : overnight gap state (today open vs prior RTH close, causal — prior day fixed)
  gam_*   : dealer-gamma regime from PRIOR-day walls (distance spot->zero-gamma / pin / call/put wall)

Run: backend\\.venv\\Scripts\\python.exe experiments\\fuhhhhh\\build_regime_feats_ndx.py
"""
from __future__ import annotations

import sys
from datetime import date as Date, datetime, time as Time
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C
import data_io as D

OUT = Path(__file__).resolve().parent / "out"
ET = ZoneInfo(C.ET)
OPEN_MS = 9 * 3600_000 + 30 * 60_000  # 09:30 ET


def et_ts(day: Date, ms: int) -> pd.Timestamp:
    h, rem = divmod(ms // 1000, 3600)
    return pd.Timestamp(datetime.combine(day, Time(h, rem // 60, rem % 60), tzinfo=ET))


def safe_corr(x):
    x = np.asarray(x, float)
    if len(x) < 6 or np.std(x[:-1]) < 1e-12 or np.std(x[1:]) < 1e-12:
        return 0.0
    return float(np.corrcoef(x[:-1], x[1:])[0, 1])


def main() -> int:
    ds = pd.read_parquet(OUT / "dataset_ndx.parquet")
    days = sorted(ds["date"].unique())
    walls = pd.read_parquet(OUT / "walls_ndx.parquet").copy()
    walls["d"] = pd.to_datetime(walls["date"].astype(int).astype(str), format="%Y%m%d").dt.date

    rows = []
    for ds_date in days:
        day = pd.Timestamp(ds_date).date()
        rth = D.load_bars_sym(C.BARS_1M_NQ, day)
        if rth is None:
            continue
        # full session bars (incl overnight) up to et; we only use RTH-window stats but keep all
        rth = rth.sort_values("et").reset_index(drop=True)
        # prior NQ RTH close (causal: prior day fully closed). NOTE D.rth_bars is ES-only,
        # so compute the NQ close directly from NQ bars.
        prev_close = None
        idx = days.index(ds_date)
        if idx > 0:
            pday = pd.Timestamp(days[idx - 1]).date()
            pnq = D.load_bars_sym(C.BARS_1M_NQ, pday)
            if pnq is not None:
                prth = pnq[(pnq["et"] >= et_ts(pday, OPEN_MS)) & (pnq["et"] < et_ts(pday, 16 * 3600_000))]
                if len(prth):
                    prev_close = float(prth["close"].iloc[-1])
        # today's RTH open
        rth_today = rth[(rth["et"] >= et_ts(day, OPEN_MS)) & (rth["et"] < et_ts(day, 16 * 3600_000))]
        day_open = float(rth_today["open"].iloc[0]) if len(rth_today) else None

        # prior-day walls (causal gamma regime: OI fixed at prior EOD)
        wprev = walls[walls["d"] < day]
        wrow = wprev.iloc[-1] if len(wprev) else None

        # daily ATR proxy from dataset's geo_atr (already causal) — grab per-day value
        day_atr = float(ds[ds["date"] == ds_date]["geo_atr"].iloc[0])

        sub = ds[ds["date"] == ds_date]
        for ms in sub["ms"].unique():
            dts = et_ts(day, int(ms))
            # STRICT causality: only bars whose close is BEFORE the decision time.
            # 1m bar stamped at its OPEN ts_event; it closes 1 min later. So bar is
            # usable only if open_ts <= dts - 1min  (i.e. it fully closed by dts).
            hist = rth[rth["et"] <= dts - pd.Timedelta(minutes=1)]
            if len(hist) < 10:
                continue
            C.assert_no_lookahead(hist["et"].max(), dts - pd.Timedelta(minutes=1), "regime")
            closes = hist["close"].to_numpy(float)
            highs = hist["high"].to_numpy(float)
            lows = hist["low"].to_numpy(float)
            vols = hist["volume"].to_numpy(float)
            lr = np.diff(np.log(closes))

            def win(n):
                return lr[-n:] if len(lr) >= n else lr

            # --- rv_*: realized-vol state ---
            rv30 = float(np.std(win(30))) if len(lr) else 0.0
            rv15 = float(np.std(win(15))) if len(lr) else 0.0
            rv60 = float(np.std(win(60))) if len(lr) else 0.0
            # whole-session-so-far vol as the slow baseline
            rv_sess = float(np.std(lr)) if len(lr) > 2 else rv30
            rv_ratio = rv30 / (rv_sess + 1e-9)             # expansion vs session
            rv_accel = rv15 / (rv60 + 1e-9)                # short vs long vol
            # vol vs daily ATR scale (pts): last-30m realized range / ATR
            rng30 = float(highs[-30:].max() - lows[-30:].min()) if len(highs) >= 30 else float(highs.max() - lows.min())
            rv_atr = rng30 / (day_atr + 1e-9)

            # --- trend_*: momentum / trend state ---
            def cumret(n):
                if len(closes) <= n:
                    return float(np.log(closes[-1] / closes[0]))
                return float(np.log(closes[-1] / closes[-n - 1]))
            tr15 = cumret(15)
            tr30 = cumret(30)
            tr60 = cumret(60)
            # VWAP-relative (session VWAP so far)
            tp = (highs + lows + closes) / 3.0
            vwap = float((tp * vols).sum() / (vols.sum() + 1e-9))
            vwap_dev = float((closes[-1] - vwap) / (closes[-1] * (rv_sess + 1e-9)))  # z-ish dev
            trend_sign = float(np.sign(tr30))
            trend_align = float(np.sign(tr15) == np.sign(tr30)) * float(np.sign(tr30) == np.sign(tr60))

            # --- chop_*: autocorrelation / choppiness ---
            ac1 = safe_corr(win(30))                         # lag-1 autocorr (mean-revert<0, trend>0)
            net = abs(closes[-1] - (closes[-31] if len(closes) > 31 else closes[0]))
            path = float(np.abs(np.diff(closes[-31:])).sum()) if len(closes) > 1 else 1e-9
            efficiency = net / (path + 1e-9)                 # Kaufman efficiency ratio (trendiness)

            # --- tod_*: time of day ---
            mins_open = (int(ms) - OPEN_MS) / 60_000.0
            tod_third = min(2, int(mins_open // 130))        # 0/1/2 over ~6.5h

            # --- gap_*: overnight gap ---
            gap = 0.0
            if prev_close is not None and day_open is not None:
                gap = (day_open - prev_close) / (day_atr + 1e-9)

            # --- gam_*: dealer-gamma regime (prior-day walls) ---
            spot_now = closes[-1]
            gam_zero = gam_pin = gam_callw = gam_putw = 0.0
            gam_gex = 0.0
            if wrow is not None:
                zg = wrow["zero_gamma"]
                if pd.notna(zg) and abs(zg - spot_now) < 4 * day_atr:  # sane band only
                    gam_zero = (spot_now - float(zg)) / (day_atr + 1e-9)
                if pd.notna(wrow["pin"]):
                    gam_pin = (spot_now - float(wrow["pin"])) / (day_atr + 1e-9)
                if pd.notna(wrow["call_wall"]):
                    gam_callw = (float(wrow["call_wall"]) - spot_now) / (day_atr + 1e-9)
                if pd.notna(wrow["put_wall"]):
                    gam_putw = (spot_now - float(wrow["put_wall"])) / (day_atr + 1e-9)
                if pd.notna(wrow["gex_proxy"]):
                    gam_gex = float(np.sign(wrow["gex_proxy"]))

            rows.append(dict(
                date=ds_date, ms=int(ms),
                rv_rv30=rv30, rv_ratio=rv_ratio, rv_accel=rv_accel, rv_atr=rv_atr,
                trend_tr15=tr15, trend_tr30=tr30, trend_tr60=tr60,
                trend_vwap_dev=vwap_dev, trend_sign=trend_sign, trend_align=trend_align,
                chop_ac1=ac1, chop_eff=efficiency,
                tod_mins=mins_open, tod_third=tod_third,
                gap_z=gap,
                gam_zero=gam_zero, gam_pin=gam_pin, gam_callw=gam_callw,
                gam_putw=gam_putw, gam_gex=gam_gex,
            ))

    out = pd.DataFrame(rows)
    out.to_parquet(OUT / "dirhunt_regime.parquet", index=False)
    print(f"wrote dirhunt_regime.parquet  rows={len(out)} days={out['date'].nunique()}")
    print("cols:", [c for c in out.columns if c not in ("date", "ms")])
    print(out.describe().round(4).T.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
