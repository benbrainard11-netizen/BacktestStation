"""Continuation-orderflow features for FVG-retrace entries.

Port of `C:/Fractal-AMD/src/features/order_flow.py:compute_continuation_of`
to BacktestStation's `list[Bar]` interface. Pure OHLCV math — no TBBO /
L2 / tick data needed. The original was pandas-based; this port reads the
same fields off `Bar` dataclasses.

The strategy ports only consume `co_continuation_score` (the compound 0-8
tally), but we keep the full feature dict as a drop-in equivalent so a
future caller can inspect individual signals.

Verified bit-identical against the pandas original on a smoke window
(2024-01-02 09:30 ET, BEARISH, lookback=15) when this was committed.
"""
from __future__ import annotations

import numpy as np

from app.backtest.strategy import Bar


def _arrays(bars: list[Bar]):
    """Extract OHLCV numpy arrays + derived quantities from a window of Bars.

    Mirrors `_arrays(bars: pd.DataFrame)` in the original module — same
    column meanings, same `rng_safe` floor (0.01), same `close_pos` and
    delta-from-close-position formulas.
    """
    n = len(bars)
    h = np.empty(n, dtype=float)
    l = np.empty(n, dtype=float)
    o = np.empty(n, dtype=float)
    c = np.empty(n, dtype=float)
    v = np.empty(n, dtype=float)
    for i, b in enumerate(bars):
        h[i] = b.high
        l[i] = b.low
        o[i] = b.open
        c[i] = b.close
        v[i] = b.volume
    rng = h - l
    rng_safe = np.where(rng == 0, 0.01, rng)
    close_pos = (c - l) / rng_safe
    delta = v * (2 * close_pos - 1)
    body_signed = c - o
    body_abs = np.abs(body_signed)
    body_pct = body_abs / rng_safe
    return (
        h, l, o, c, v, rng, rng_safe, close_pos, delta,
        body_signed, body_abs, body_pct,
    )


def compute_continuation_of(
    bars_1m: list[Bar],
    at_idx: int,
    trend_direction: str,
    lookback: int = 15,
    atr: float = 50.0,
) -> dict:
    """Continuation orderflow features at `at_idx` for an FVG retrace entry.

    `trend_direction` is the TREND direction the entry would trade with —
    "BEARISH" means we're looking to short into a retrace up, so we want
    the retrace dying and bears reasserting. "BULLISH" symmetric.

    Returns a feature dict including `co_continuation_score` (0-8 compound
    tally). Trusted's gate is `co_continuation_score >= 3`. Empty dict if
    the window can't be built (insufficient lookback or out-of-range idx).

    `atr` is accepted for parity with the pandas original; the function
    body doesn't currently use it (the original didn't either).
    """
    if at_idx < lookback + 3 or at_idx >= len(bars_1m):
        return {}

    window = bars_1m[at_idx - lookback : at_idx + 1]
    if len(window) < lookback:
        return {}

    h, l, o, c, v, rng, rng_safe, close_pos, delta, body_s, body_a, body_pct = (
        _arrays(window)
    )

    f: dict = {}
    vol_mean = v[:-1].mean()
    rng_mean = rng[:-1].mean()

    # 1. RETRACE EXHAUSTION — last 5 bars vs prior 5 bars volume.
    if len(v) >= 10:
        f["co_retrace_vol_fade"] = v[-5:].mean() / max(v[-10:-5].mean(), 1) - 1
    else:
        f["co_retrace_vol_fade"] = 0.0

    # 2. DELTA SHIFT back to trend direction.
    recent_delta = delta[-3:].sum()
    prior_delta = delta[-6:-3].sum()
    if trend_direction == "BEARISH":
        f["co_delta_shift"] = prior_delta - recent_delta
        f["co_delta_trend_aligned"] = float(recent_delta < 0)
        f["co_delta_flipping"] = float(prior_delta > 0 and recent_delta < 0)
    else:
        f["co_delta_shift"] = recent_delta - prior_delta
        f["co_delta_trend_aligned"] = float(recent_delta > 0)
        f["co_delta_flipping"] = float(prior_delta < 0 and recent_delta > 0)

    # 3. ABSORPTION at the FVG level — vol up, range down.
    last3_vol = v[-3:].mean()
    last3_rng = rng[-3:].mean()
    f["co_absorption"] = (last3_vol / max(vol_mean, 1)) / max(
        last3_rng / max(rng_mean, 0.01), 0.01
    )

    if trend_direction == "BEARISH":
        last3_buy = sum(1 for x in delta[-3:] if x > 0)
        price_stalled = c[-1] <= c[-3] + rng_mean * 0.3
        f["co_retrace_absorbed"] = float(
            last3_buy >= 2 and price_stalled and last3_vol > vol_mean * 0.8
        )
    else:
        last3_sell = sum(1 for x in delta[-3:] if x < 0)
        price_stalled = c[-1] >= c[-3] - rng_mean * 0.3
        f["co_retrace_absorbed"] = float(
            last3_sell >= 2 and price_stalled and last3_vol > vol_mean * 0.8
        )

    # 4. AGGRESSION FLIP — close-position drift.
    agg_early = close_pos[-6:-3].mean() if len(close_pos) >= 6 else 0.5
    agg_late = close_pos[-3:].mean()
    if trend_direction == "BEARISH":
        f["co_aggression_flip"] = agg_early - agg_late
        f["co_sellers_aggressive"] = float(agg_late < 0.35)
    else:
        f["co_aggression_flip"] = agg_late - agg_early
        f["co_buyers_aggressive"] = float(agg_late > 0.65)

    # 5. RETRACE BODY WEAKNESS — small bodies = indecision.
    f["co_body_weakness"] = 1.0 - body_pct[-3:].mean()

    # 6. RANGE CONTRACTION on retrace.
    if len(rng) >= 6:
        f["co_range_contracting"] = float(rng[-3:].mean() < rng[-6:-3].mean() * 0.8)
    else:
        f["co_range_contracting"] = 0.0

    # 7. CVD DIVERGENCE — price retracing but CVD doesn't confirm.
    cvd = np.cumsum(delta)
    price_retrace = c[-1] - c[-5] if len(c) >= 5 else 0
    cvd_retrace = cvd[-1] - cvd[-5] if len(cvd) >= 5 else 0
    if trend_direction == "BEARISH":
        f["co_cvd_diverges_retrace"] = float(price_retrace > 0 and cvd_retrace < 0)
    else:
        f["co_cvd_diverges_retrace"] = float(price_retrace < 0 and cvd_retrace > 0)

    # 8. STALL BARS — tiny-body count among last 5.
    tiny_body = sum(1 for bp in body_pct[-5:] if bp < 0.3)
    f["co_stall_bars"] = tiny_body

    # COMPOUND CONTINUATION SCORE (0-8 tally, trusted's entry gate).
    score = 0
    if f["co_retrace_vol_fade"] < -0.15:
        score += 1
    if f["co_delta_trend_aligned"]:
        score += 1
    if f["co_delta_flipping"]:
        score += 1
    if f["co_absorption"] > 1.3:
        score += 1
    if f["co_retrace_absorbed"]:
        score += 1
    if trend_direction == "BEARISH" and f.get("co_sellers_aggressive", False):
        score += 1
    elif trend_direction == "BULLISH" and f.get("co_buyers_aggressive", False):
        score += 1
    if f["co_range_contracting"]:
        score += 1
    if f["co_cvd_diverges_retrace"]:
        score += 1

    f["co_continuation_score"] = score
    return f
