"""Volume profile primitives — pure helpers, no Bar imports.

Computes a price→volume histogram for a window of bars and derives
POC (Point of Control), VAH (Value Area High), and VAL (Value Area Low)
using the standard "expand from POC" algorithm.

Volume distribution per OHLCV bar:
    Each bar's volume is spread *uniformly* across its [low, high] range,
    bucketed by `tick_size`. This is the standard approximation when only
    OHLCV is available (no intra-bar tick data). Bars where high == low
    drop their full volume into the close-rounded bucket.

Pure functions only. No Bar class import — accepts a lightweight
`BarTuple = (high, low, volume)` so the helpers can be unit-tested
without Bar/datetime fixtures.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Iterable, NamedTuple, Optional


class BarTuple(NamedTuple):
    """Minimum bar fields needed to compute volume profile.

    Compatible with `app.backtest.strategy.Bar` — the volume_profile
    feature module passes `(b.high, b.low, b.volume)` for each bar.
    """

    high: float
    low: float
    volume: float


def compute_profile(
    bars: Iterable[BarTuple], *, tick_size: float
) -> dict[float, float]:
    """Build a price → volume histogram bucketed by tick_size.

    Each bar's volume is distributed uniformly across its [low, high]
    range using `n = round((high - low) / tick_size)` buckets. Bars
    with high <= low collapse their volume onto the rounded close
    bucket — but since we don't take close here, we use the midpoint.
    """
    if tick_size <= 0:
        raise ValueError("tick_size must be positive")
    profile: dict[float, float] = defaultdict(float)
    for bar in bars:
        if bar.volume <= 0:
            continue
        if bar.high <= bar.low:
            bucket = math.floor(bar.low / tick_size) * tick_size
            profile[bucket] += bar.volume
            continue
        n_buckets = max(1, int(round((bar.high - bar.low) / tick_size)))
        per_bucket = bar.volume / n_buckets
        # Anchor buckets to floor(low / tick) so adjacent mids don't
        # collide under banker's rounding (e.g. 100.125 and 100.375 both
        # round to 100.0 with `round()` but floor-bucket cleanly to
        # 100.00 and 100.25). Bucket key = lower edge of the slot.
        base = math.floor(bar.low / tick_size) * tick_size
        for i in range(n_buckets):
            bucket = base + i * tick_size
            profile[bucket] += per_bucket
    return dict(profile)


def find_poc(profile: dict[float, float]) -> Optional[float]:
    """Return the price bucket with highest volume, or None on empty."""
    if not profile:
        return None
    return max(profile.items(), key=lambda kv: (kv[1], -kv[0]))[0]


def find_value_area(
    profile: dict[float, float], *, target_pct: float = 0.7
) -> Optional[tuple[float, float]]:
    """Return (VAL, VAH) covering ~target_pct of total volume.

    Standard algorithm:
      1. Start at POC, accumulator = profile[POC].
      2. Repeatedly look at the next bucket above and the next below.
         Add whichever has more volume to the value area; advance that
         side's index.
      3. Stop when accumulator >= total * target_pct, or both sides
         are exhausted.

    Ties (above vol == below vol) break upward — matches the convention
    in most charting tools.
    """
    if not (0.0 < target_pct <= 1.0):
        raise ValueError("target_pct must be in (0, 1]")
    if not profile:
        return None

    total = sum(profile.values())
    if total <= 0:
        return None
    target = total * target_pct

    prices = sorted(profile.keys())
    poc = find_poc(profile)
    if poc is None:
        return None
    poc_idx = prices.index(poc)

    accumulated = profile[poc]
    low_idx = poc_idx
    high_idx = poc_idx

    while accumulated < target:
        up_avail = high_idx < len(prices) - 1
        dn_avail = low_idx > 0
        if not up_avail and not dn_avail:
            break

        up_vol = profile[prices[high_idx + 1]] if up_avail else 0.0
        dn_vol = profile[prices[low_idx - 1]] if dn_avail else 0.0

        # Tie-break upward.
        if up_avail and (not dn_avail or up_vol >= dn_vol):
            accumulated += up_vol
            high_idx += 1
        elif dn_avail:
            accumulated += dn_vol
            low_idx -= 1
        else:
            break

    return prices[low_idx], prices[high_idx]


def position_vs_value_area(
    price: float,
    *,
    val: float,
    vah: float,
    poc: float,
    tolerance: float = 0.0,
) -> str:
    """Categorize `price` relative to the value area:

      "below_va"  — price is below VAL by more than tolerance
      "at_val"    — within tolerance of VAL
      "in_va"     — strictly between VAL and VAH (excluding edges if tolerance > 0)
      "at_poc"    — within tolerance of POC
      "at_vah"    — within tolerance of VAH
      "above_va"  — above VAH by more than tolerance

    "at_poc" wins over "in_va" / "at_val" / "at_vah" when ranges overlap
    (POC is more specific). Edge tags ("at_val", "at_vah") win over the
    bulk "in_va" tag.
    """
    if tolerance < 0:
        raise ValueError("tolerance must be >= 0")
    if val > vah:
        raise ValueError(f"val ({val}) must be <= vah ({vah})")

    if abs(price - poc) <= tolerance:
        return "at_poc"
    if abs(price - vah) <= tolerance:
        return "at_vah"
    if abs(price - val) <= tolerance:
        return "at_val"
    if price > vah + tolerance:
        return "above_va"
    if price < val - tolerance:
        return "below_va"
    return "in_va"
