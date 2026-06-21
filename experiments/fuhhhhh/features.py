"""Feature engines: options (opt_) and futures (fut_) blocks at a decision time t.

Every function takes only data ≤ t (callers slice; build_dataset.py asserts). Distances
are in daily-ATR units unless suffixed _pts. NaN = feature unavailable (LightGBM-native).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

GEX_SCALE = 1e10  # net dealer GEX is O(1e10) $/1% — scale to O(1) for readability


def _last_at_or_before(panel_day: pd.DataFrame, ms: int) -> pd.Series | None:
    rows = panel_day[panel_day["ms_of_day"] <= ms]
    return rows.iloc[-1] if len(rows) else None


def _delta(panel_day: pd.DataFrame, ms: int, col: str, back_min: int) -> float:
    now = _last_at_or_before(panel_day, ms)
    then = _last_at_or_before(panel_day, ms - back_min * 60_000)
    if now is None or then is None:
        return np.nan
    return float(now[col]) - float(then[col])


def options_features(
    gex_day: pd.DataFrame,
    dte0_day: pd.DataFrame,
    iv_day: pd.DataFrame,
    eod_prev: pd.Series | None,
    ms: int,
    price: float,
    basis: float,
    atr: float,
) -> dict[str, float]:
    """opt_ block at ET-ms `ms` on the decision day. Index levels mapped to ES via +basis."""
    f: dict[str, float] = {}
    g = _last_at_or_before(gex_day, ms)
    if g is not None:
        f["opt_net_gex"] = float(g["net_gex"]) / GEX_SCALE
        f["opt_net_gex_sign"] = float(np.sign(g["net_gex"]))
        for lvl, name in (("zero_gamma", "zg"), ("call_wall", "cw"), ("put_wall", "pw"), ("pin", "pin")):
            v = float(g[lvl])
            f[f"opt_dist_{name}"] = ((v + basis) - price) / atr if np.isfinite(v) else np.nan
        for back in (15, 30, 60):
            f[f"opt_gex_chg_{back}m"] = _delta(gex_day, ms, "net_gex", back) / GEX_SCALE
    d = _last_at_or_before(dte0_day, ms)
    if d is not None:
        f["opt_dte0_gex"] = float(d["net_gex"]) / GEX_SCALE
        f["opt_dte0_vanna"] = float(d["net_vanna"]) / GEX_SCALE
        f["opt_dte0_charm"] = float(d["net_charm"]) / GEX_SCALE
        pin = float(d["pin"])
        f["opt_dte0_pin_dist"] = ((pin + basis) - price) / atr if np.isfinite(pin) else np.nan
        for back in (15, 30, 60):
            f[f"opt_dte0_gex_chg_{back}m"] = _delta(dte0_day, ms, "net_gex", back) / GEX_SCALE
        f["opt_dte0_charm_chg_30m"] = _delta(dte0_day, ms, "net_charm", 30) / GEX_SCALE
    v = _last_at_or_before(iv_day, ms)
    if v is not None:
        f["opt_atm_iv"] = float(v["atm_iv"])
        f["opt_skew"] = float(v["skew"])
        f["opt_iv_chg_30m"] = _delta(iv_day, ms, "atm_iv", 30)
        f["opt_skew_chg_30m"] = _delta(iv_day, ms, "skew", 30)
    if eod_prev is not None:  # T-1 EOD context (rule 2)
        f["opt_t1_total_gex"] = float(eod_prev["total_gex"]) / GEX_SCALE
        f["opt_t1_dist_cw"] = ((float(eod_prev["call_wall"]) + basis) - price) / atr
        f["opt_t1_dist_pw"] = ((float(eod_prev["put_wall"]) + basis) - price) / atr
    return f


def _ret(closes: np.ndarray, n: int) -> float:
    if len(closes) <= n:
        return np.nan
    return float(closes[-1] / closes[-1 - n] - 1.0) * 1e4  # bps


def futures_features(
    rth_pre: pd.DataFrame,
    levels: dict[str, float],
    ms: int,
    atr: float,
    prior_close: float | None,
) -> dict[str, float]:
    """fut_ block from RTH bars strictly before t (rth_pre) + session levels."""
    closes = rth_pre["close"].to_numpy(float)
    price = float(closes[-1])
    f: dict[str, float] = {
        "fut_ret_1m": _ret(closes, 1),
        "fut_ret_5m": _ret(closes, 5),
        "fut_ret_15m": _ret(closes, 15),
        "fut_ret_30m": _ret(closes, 30),
    }
    lr = np.diff(np.log(closes))
    f["fut_rv_5m"] = float(np.std(lr[-5:]) * 1e4) if len(lr) >= 5 else np.nan
    f["fut_rv_30m"] = float(np.std(lr[-30:]) * 1e4) if len(lr) >= 30 else np.nan
    vol = rth_pre["volume"].to_numpy(float)
    f["fut_vol_burst"] = float(vol[-5:].mean() / vol.mean()) if len(vol) >= 10 else np.nan

    cum_v = vol.cumsum()
    cum_pv = (rth_pre["vwap"].to_numpy(float) * vol).cumsum()
    vwap = cum_pv[-1] / cum_v[-1] if cum_v[-1] > 0 else np.nan
    f["fut_dist_vwap"] = (price - vwap) / atr

    day_hi, day_lo = float(rth_pre["high"].max()), float(rth_pre["low"].min())
    rng = day_hi - day_lo
    f["fut_range_pos"] = (price - day_lo) / rng if rng > 0 else np.nan
    f["fut_day_range_atr"] = rng / atr
    for k in ("pdh", "pdl", "onh", "onl"):
        f[f"fut_dist_{k}"] = (price - levels[k]) / atr if k in levels else np.nan
    for k in ("orh", "orl"):  # NaN before 09:45 (valid_from discipline)
        f[f"fut_dist_{k}"] = (price - levels[k]) / atr if k in levels else np.nan
    f["fut_gap_open"] = (
        (float(rth_pre["open"].iloc[0]) - prior_close) / atr if prior_close is not None else np.nan
    )
    f["fut_min_since_open"] = (ms - (9 * 3600_000 + 30 * 60_000)) / 60_000
    f["fut_min_to_close"] = (16 * 3600_000 - ms) / 60_000
    f["fut_atr_pts"] = atr
    return f
