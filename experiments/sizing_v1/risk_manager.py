"""Take/skip decision — the gatekeeper.

Given a model signal + an account, decide whether to enter a trade and at
what size. This is the most safety-critical module: bad decisions = blown
accounts.

Decision order (skip on first failure):
  1. Account must be active (account.can_take_trade handles status/symbol/size/buffers)
  2. Prediction must not be FLAT
  3. Confidence (max prob) must clear the cell threshold
  4. Direction-asymmetry filter (max - runner_up >= configured gap)
  5. News blackout (v1 stub: never blocks)
  6. Symbol must have no open position already (one-per-symbol, enforced by simulator)

Returns a Decision describing take/skip + reason + sizing.

See PLAN.md §6.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from account import Account
from firm_rules import FirmConfig, is_news_blackout
from sizing import POINT_VALUE, size_position

CLASS_FLAT = 0
CLASS_UP = 1
CLASS_DOWN = 2


@dataclass(frozen=True)
class Decision:
    take: bool
    reason: str
    direction: int = 0       # +1 long, -1 short, 0 none
    contracts: int = 0


def decide(
    *,
    account: Account,
    firm: FirmConfig,
    symbol: str,
    horizon_key: str,
    ts_decision,
    p_proba: np.ndarray,             # [p_flat, p_up, p_down]
    threshold: float,
    sizing_method: str,
    sizing_params: dict,
    direction_min_gap: float = 0.0,
    max_contracts: int | None = None,
    atr: float | None = None,
) -> Decision:
    """Return a Decision for this signal against this account.

    `max_contracts` overrides firm.max_position_size (for micro-contract
    runs where the firm cap is in mini-equivalents). `atr` (index points) is
    required for vol_targeted sizing; without it vol_targeted falls back to 1 lot.
    """
    cap = max_contracts if max_contracts is not None else firm.max_position_size

    # 2. Not flat
    pred_class = int(np.argmax(p_proba))
    if pred_class == CLASS_FLAT:
        return Decision(False, "flat_prediction")

    # 3. Confidence threshold
    conf = float(p_proba.max())
    if conf < threshold:
        return Decision(False, f"below_threshold:{conf:.3f}<{threshold:.2f}")

    # 4. Direction asymmetry: max class must beat runner-up by min gap
    if direction_min_gap > 0:
        sorted_p = np.sort(p_proba)[::-1]
        gap = float(sorted_p[0] - sorted_p[1])
        if gap < direction_min_gap:
            return Decision(False, f"direction_gap_too_small:{gap:.3f}<{direction_min_gap:.2f}")

    # 5. News blackout (v1 stub)
    if is_news_blackout(firm, ts_decision):
        return Decision(False, "news_blackout")

    # Direction
    direction = 1 if pred_class == CLASS_UP else -1

    # Size — build the risk context (drawdown headroom is the binding prop constraint)
    dd_components = [account.balance - account.trailing_dd_floor]
    daily_limit = getattr(firm, "daily_loss_limit", 0) or 0
    if daily_limit > 0:
        dd_components.append(daily_limit + account.day_pnl_low_water)   # day_pnl_low_water <= 0
    ctx = {
        "atr": atr,
        "point_value": POINT_VALUE.get(symbol),
        "dd_buffer": max(0.0, min(dd_components)),
        "balance": account.balance,
    }
    contracts = size_position(
        method=sizing_method,
        p_proba=p_proba,
        threshold=threshold,
        params=sizing_params,
        max_position_size=cap,
        ctx=ctx,
    )
    if contracts <= 0:
        return Decision(False, "sizing_returned_zero")

    # 1. Account-level gate (status, symbol allowed, size cap, daily/DD buffers)
    ok, reason = account.can_take_trade(symbol, contracts, max_contracts=cap)
    if not ok:
        return Decision(False, f"account_gate:{reason}")

    return Decision(True, "take", direction=direction, contracts=contracts)
