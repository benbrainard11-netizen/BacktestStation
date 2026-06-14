"""Layer 2b -- triple-barrier hold/break labeler.

Phase 1 reproduce: binary hold(0)/break(1) measured STRICTLY AFTER the feature
window, reusing zone_events.label_touch verbatim (first-hit over mid[jo:k1],
break = through the level by B, hold = revert by R, None = timeout at HORIZON).

The multi-head extension (chop, target-before-stop, R-distribution, tail) is
Phase 2 -- it builds on this same forward window.
"""

from __future__ import annotations

import _paths  # noqa: F401

import zone_events as ze


def label_event(ctx, t0, level_price: float, dr: int):
    """Binary hold/break for one touch, or None on timeout. Outcome AFTER the window."""
    jo = int(ctx.tsi.searchsorted(t0 + ze.W_OFI, side="right"))
    k1 = int(ctx.tsi.searchsorted(t0 + ze.HORIZON, side="right"))
    return ze.label_touch(ctx.mid, jo, k1, level_price, dr)
