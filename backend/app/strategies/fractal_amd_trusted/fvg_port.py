"""Faithful list[HTFCandle] port of `C:/Fractal-AMD/src/features/fvg_detector.py`.

The list[Bar] port in `app.strategies.fractal_amd.signals` ALSO ports
this module but its `avg_range` computation for early bars (i < 20)
differs from the pandas original. On short windows (~7 LTF candles, the
trusted strategy's typical FVG-detection window) that difference changes
which gaps clear `gap_width >= avg_range * min_gap_pct` — and therefore
which FVGs are detected. The trusted strategy's setup-level fidelity
depends on getting this right, so we port the original's exact
avg_range logic here.

The original's behavior: when `len(bars) <= 20`, EVERY bar's avg_range
is filled with `avg_range[first_valid]` which is itself NaN (because
`range(20, len(bars))` is empty), then the inner FVG loop falls back
to `ar = 1.0` on NaN/zero. Net effect on short windows: ar = 1.0 for
all bars, so `gap_width >= 0.3 * 1.0 = 0.3` filters virtually nothing.

The signals.py port instead uses a rolling-mean of WHATEVER bars are
available at each index, which can be 1-3 bars on the early candles —
producing a much smaller avg_range and a much tighter threshold. That
filters out FVGs the original would have kept.
"""
from __future__ import annotations

import math
from typing import Literal

from app.strategies.fractal_amd.signals import FVG, HTFCandle

Direction = Literal["BULLISH", "BEARISH"]


def detect_fvgs_trusted(
    candles: list[HTFCandle],
    direction: Direction,
    min_gap_pct: float = 0.3,
    expiry_bars: int = 60,
) -> list[FVG]:
    """Faithful port of original detect_fvgs to list[HTFCandle].

    Returns FVG objects with .creation_bar_idx set to position in
    `candles` so `find_nearest_unfilled_fvg` can compute age correctly.
    """
    if len(candles) < 3:
        return []

    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    ranges = [h - l for h, l in zip(highs, lows)]

    # Rolling 20-bar avg range. NaN for i < 20.
    avg_range: list[float] = [math.nan] * len(candles)
    for i in range(20, len(candles)):
        avg_range[i] = sum(ranges[i - 20 : i]) / 20

    # Original's logic: pick `first_valid` = 20 if len > 20 else len-1.
    # Then if avg_range[first_valid] is NaN (the short-window case),
    # leave it NaN; otherwise propagate it backward.
    first_valid = 20 if len(candles) > 20 else len(candles) - 1
    if math.isnan(avg_range[first_valid]):
        # Short window — all values stay NaN, the inner loop's
        # `ar = 1.0` fallback kicks in.
        pass
    else:
        for i in range(first_valid):
            avg_range[i] = avg_range[first_valid]

    fvgs: list[FVG] = []
    for i in range(2, len(candles)):
        c1_h = highs[i - 2]
        c1_l = lows[i - 2]
        c3_h = highs[i]
        c3_l = lows[i]

        ar = avg_range[i]
        if math.isnan(ar) or ar <= 0:
            ar = 1.0

        if direction == "BULLISH":
            gap_low = c1_h
            gap_high = c3_l
            gap_width = gap_high - gap_low
            if gap_width > 0 and gap_width >= ar * min_gap_pct:
                fvgs.append(
                    FVG(
                        direction="BULLISH",
                        high=gap_high,
                        low=gap_low,
                        creation_time=candles[i].start,
                        creation_bar_idx=i,
                    )
                )
        else:
            gap_high = c1_l
            gap_low = c3_h
            gap_width = gap_high - gap_low
            if gap_width > 0 and gap_width >= ar * min_gap_pct:
                fvgs.append(
                    FVG(
                        direction="BEARISH",
                        high=gap_high,
                        low=gap_low,
                        creation_time=candles[i].start,
                        creation_bar_idx=i,
                    )
                )

    # Forward-walk to mark fills + expiries.
    for fvg in fvgs:
        start = fvg.creation_bar_idx + 1
        end = min(start + expiry_bars, len(candles))
        for j in range(start, end):
            if fvg.direction == "BULLISH":
                if lows[j] <= fvg.low:
                    fvg.filled = True
                    fvg.fill_time = candles[j].start
                    fvg.fill_bar_idx = j
                    break
            else:
                if highs[j] >= fvg.high:
                    fvg.filled = True
                    fvg.fill_time = candles[j].start
                    fvg.fill_bar_idx = j
                    break
        if not fvg.filled and (end - start) >= expiry_bars:
            fvg.expired = True

    return fvgs
