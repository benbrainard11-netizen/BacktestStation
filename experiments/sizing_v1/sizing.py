"""Probability → contract count.

v1: fixed_1 (1 contract). v1.5: confidence_scaled, vol_targeted (the keystone:
risk-normalize by ATR, scale by conviction, cap at a fraction of the drawdown
buffer so one trade can never blow the account). kelly_fractional still TODO.

The signal interface carries the vol forecast already: p_proba = [p_flat, p_up, p_down],
so (1 - p_flat) = P(move) and max(p_up, p_down) = directional conviction. vol_targeted
uses that plus ATR + the account's drawdown headroom (passed via `ctx`).

See PLAN.md §6 (size-calculation step) and config/strategy_v0.yaml.
"""

from __future__ import annotations

import numpy as np

# $ per 1.0 index point, per contract (minis; micros are 1/10)
POINT_VALUE = {
    "NQ.c.0": 20.0, "ES.c.0": 50.0, "YM.c.0": 5.0, "RTY.c.0": 50.0,
    "MNQ.c.0": 2.0, "MES.c.0": 5.0, "MYM.c.0": 0.5, "M2K.c.0": 5.0,
}


def _vol_targeted(p_proba: np.ndarray, threshold: float, params: dict,
                  max_position_size: int, ctx: dict) -> int:
    """Risk-normalized, conviction-scaled, drawdown-capped contract count.

    ctx keys: atr (points), point_value ($/pt), dd_buffer ($ left before blow),
              balance ($). Missing/!>0 atr or point_value -> safe fallback of 1.
    params: stop_atr_mult (default 0.5), risk_per_trade_pct (of balance, 0.004),
            max_dd_risk_pct (of remaining DD buffer, 0.10), conviction_scale (bool).
    """
    atr = ctx.get("atr") or 0.0
    pv = ctx.get("point_value") or 0.0
    if atr <= 0 or pv <= 0:
        return min(1, max_position_size)                       # can't risk-normalize -> 1 lot

    # use a precomputed stop distance (from compute_stop — structural snap) if provided,
    # else the tuned ATR stop (k~=0.18*ATR was the swept sweet spot; fits prop on micros).
    stop_pts = ctx.get("stop_dist") or (float(params.get("stop_atr_mult", 0.18)) * atr)
    if stop_pts <= 0:
        return min(1, max_position_size)
    risk_per_contract = stop_pts * pv                          # $ at risk per contract

    # risk budget = the BINDING of: % of balance and % of remaining drawdown buffer.
    # the DD-buffer cap is the prop-survival constraint — one trade can't blow the account.
    budgets = []
    bal = ctx.get("balance")
    if bal:
        budgets.append(float(params.get("risk_per_trade_pct", 0.004)) * bal)
    ddb = ctx.get("dd_buffer")
    if ddb is not None:
        budgets.append(float(params.get("max_dd_risk_pct", 0.10)) * max(0.0, ddb))
    risk_usd = min(budgets) if budgets else 0.0
    if risk_usd <= 0:
        return 0                                               # no room -> stand down

    base = risk_usd / risk_per_contract

    if params.get("conviction_scale", True):
        conf = float(max(p_proba[1], p_proba[2]))              # directional conviction (=move x dir)
        span = max(1e-6, 1.0 - threshold)
        mult = 0.5 + 0.5 * min(1.0, max(0.0, (conf - threshold) / span))   # 0.5 .. 1.0
        base *= mult

    # FLOOR (not round): a hard cap so realized risk never exceeds the budget. If you
    # can't fit one full contract in the risk budget, you don't trade (use micros / bigger acct).
    return max(0, min(int(base), max_position_size))


def size_position(
    *,
    method: str,
    p_proba: np.ndarray,        # [p_flat, p_up, p_down]
    threshold: float,
    params: dict,
    max_position_size: int,
    ctx: dict | None = None,    # {atr, point_value, dd_buffer, balance} for vol_targeted
) -> int:
    """Return contract count for a trade. 0 means do-not-trade."""
    if method == "fixed_1":
        return min(int(params.get("contracts", 1)), max_position_size)

    if method == "confidence_scaled":
        conf = float(p_proba.max())
        headroom = max(0.0, conf - threshold)
        span = max(1e-6, 1.0 - threshold)
        size = 1 + int(round(headroom / span * (max_position_size - 1)))
        return max(1, min(size, max_position_size))

    if method == "vol_targeted":
        return _vol_targeted(p_proba, threshold, params, max_position_size, ctx or {})

    if method == "kelly_fractional":
        raise NotImplementedError("kelly_fractional is still v1.5 TODO")

    raise ValueError(f"unknown sizing method: {method!r}")
