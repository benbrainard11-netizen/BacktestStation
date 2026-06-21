"""ATM strike selection, straddle quote assembly, implied move + quote filters.

LOCKED: ATM = strike minimizing |K - underlying|; both call & put need valid quotes; search the
nearest 3 strikes, take the first valid pair, never the most-liquid/profitable. Implied move is the
ACTUAL straddle price (ask = what you pay), not IV*sqrt(T). Quote filter on straddle spread/mid.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SPREAD_MID_MAX = 0.20  # frozen primary quote-quality threshold
ATM_SEARCH_N = 3       # search the nearest 3 strikes by |K - underlying|


def valid_leg(bid: float, ask: float) -> bool:
    """ask >= bid > 0 and mid > 0."""
    return bid > 0 and ask >= bid and (bid + ask) / 2 > 0


def select_atm(quotes: pd.DataFrame, underlying: float) -> dict | None:
    """`quotes`: rows for ONE date+expiry with columns strike, right(C/P), bid, ask.

    Returns the ATM call+put pair (nearest valid strike within ATM_SEARCH_N), or None.
    """
    strikes = np.sort(quotes["strike"].unique())
    order = strikes[np.argsort(np.abs(strikes - underlying))][:ATM_SEARCH_N]
    for i, k in enumerate(order):
        c = quotes[(quotes["strike"] == k) & (quotes["right"] == "C")]
        p = quotes[(quotes["strike"] == k) & (quotes["right"] == "P")]
        if c.empty or p.empty:
            continue
        cb, ca = float(c["bid"].iloc[0]), float(c["ask"].iloc[0])
        pb, pa = float(p["bid"].iloc[0]), float(p["ask"].iloc[0])
        if valid_leg(cb, ca) and valid_leg(pb, pa):
            return {"strike": float(k), "exact_nearest": i == 0,
                    "call_bid": cb, "call_ask": ca, "put_bid": pb, "put_ask": pa}
    return None


def straddle_quotes(atm: dict) -> dict:
    """Derive straddle ask/mid/spread from an ATM call+put pair."""
    call_mid = (atm["call_bid"] + atm["call_ask"]) / 2
    put_mid = (atm["put_bid"] + atm["put_ask"]) / 2
    ask = atm["call_ask"] + atm["put_ask"]
    mid = call_mid + put_mid
    spread = (atm["call_ask"] - atm["call_bid"]) + (atm["put_ask"] - atm["put_bid"])
    return {"straddle_ask": ask, "straddle_mid": mid, "straddle_spread": spread}


def passes_quote_filter(sq: dict, max_spread_mid: float = SPREAD_MID_MAX) -> bool:
    return sq["straddle_mid"] > 0 and (sq["straddle_spread"] / sq["straddle_mid"]) <= max_spread_mid


def implied_move_ask(straddle_ask: float, underlying: float) -> float:
    """Tradable 1-sigma-ish move you actually pay (primary)."""
    return straddle_ask / underlying


def implied_move_mid(straddle_mid: float, underlying: float) -> float:
    """Mid-based implied move (diagnostic)."""
    return straddle_mid / underlying


def dte_norm_implied_move(im_mid: float, trading_dte: int) -> float:
    """Per-sqrt-day implied move so the expensiveness rank is comparable across DTEs."""
    return im_mid / np.sqrt(trading_dte) if trading_dte > 0 else np.nan
