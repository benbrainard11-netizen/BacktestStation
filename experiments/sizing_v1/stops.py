"""Stop placement for the risk engine — ATR-anchored with a structural snap.

The stop answers "what makes this trade wrong." A signal supplies its invalidation
`level` (swing / opening-range edge / the traded level); we place the stop just beyond
it (+ buffer), clamped to ATR bounds so it's never absurd. No usable level -> ATR fallback.
Always causal (level + atr known at entry). Returns stop DISTANCE in index points.
"""
from __future__ import annotations


def compute_stop(
    entry: float,
    direction: int,                 # +1 long, -1 short
    atr: float,                     # intraday ATR (points)
    *,
    level: float | None = None,     # the setup's invalidation price (None -> ATR fallback)
    k_fallback: float = 0.2,        # ATR multiple when no usable level
    clamp: tuple[float, float] = (0.05, 0.6),   # min/max stop as ATR multiples
    buffer_ticks: float = 3.0,
    tick: float = 0.25,
) -> float:
    """Stop distance (points): just beyond the invalidation level, clamped to [lo, hi]*ATR;
    ATR-multiple fallback if no level on the stop side."""
    lo, hi = clamp[0] * atr, clamp[1] * atr
    if level is not None:
        on_stop_side = (direction > 0 and level < entry) or (direction < 0 and level > entry)
        if on_stop_side:
            d = abs(entry - level) + buffer_ticks * tick
            return float(min(max(d, lo), hi))
    return float(min(max(k_fallback * atr, lo), hi))
