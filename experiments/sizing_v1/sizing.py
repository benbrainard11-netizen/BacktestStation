"""Probability → contract count.

v1: fixed_1 only (1 contract per trade). v1.5 adds kelly_fractional,
vol_targeted, confidence_scaled.

See PLAN.md §6 (size-calculation step) and config/strategy_v0.yaml.
"""

from __future__ import annotations

import numpy as np


def size_position(
    *,
    method: str,
    p_proba: np.ndarray,        # [p_flat, p_up, p_down]
    threshold: float,
    params: dict,
    max_position_size: int,
) -> int:
    """Return contract count for a trade. 0 means do-not-trade.

    v1 supports 'fixed_1'. Others raise NotImplementedError until v1.5.
    """
    if method == "fixed_1":
        return min(int(params.get("contracts", 1)), max_position_size)

    if method == "confidence_scaled":
        # v1.5 preview: scale 1..max by how far above threshold we are.
        conf = float(p_proba.max())
        headroom = max(0.0, conf - threshold)
        # map [0, 1-threshold] -> [1, max_position_size]
        span = max(1e-6, 1.0 - threshold)
        size = 1 + int(round(headroom / span * (max_position_size - 1)))
        return max(1, min(size, max_position_size))

    if method in ("kelly_fractional", "vol_targeted"):
        raise NotImplementedError(f"sizing method {method!r} is v1.5 work")

    raise ValueError(f"unknown sizing method: {method!r}")
