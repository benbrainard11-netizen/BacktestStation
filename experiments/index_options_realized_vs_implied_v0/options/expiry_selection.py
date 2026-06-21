"""Expiry selection + settlement classification.

LOCKED: nearest eligible expiry with trading DTE in [1,7], PM/close-settled only. The settlement
gate is the biggest hidden trap -- standard monthly 3rd-Friday SPX is AM/SET-settled (opening
prices), so settling it at the close is wrong. v0 heuristic: 3rd-Friday => AM (exclude); else PM.
If an expiry can't be classified, the caller drops it (never settle AM at the close).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

DTE_LO = 1
DTE_HI = 7


def is_third_friday(ts: pd.Timestamp) -> bool:
    """Standard monthly expiry = the 3rd Friday of the month."""
    return ts.weekday() == 4 and 15 <= ts.day <= 21


def is_am_settled(expiration: pd.Timestamp) -> bool:
    """FAIL-CLOSED monthly-expiry-risk gate (per GPT review).

    The cache has no settlement/root field, so we cannot positively confirm PM settlement. The
    standard monthly SPX (AM/SET-settled) is the 3rd Friday, but holidays can shift it to Thursday.
    So we EXCLUDE the whole monthly-risk zone: day-of-month 15-21 AND weekday Thursday/Friday. This
    discards some valid PM weeklies/dailies, but that beats silently settling an AM contract at the
    close. If exclusion is too costly, source real settlement metadata before running.
    """
    return 15 <= expiration.day <= 21 and expiration.weekday() in (3, 4)  # Thu, Fri


def trading_dte(t: pd.Timestamp, expiry: pd.Timestamp, trading_dates: np.ndarray) -> int:
    """Count of trading days strictly after t, up to and including expiry."""
    td = np.asarray(trading_dates, dtype="datetime64[ns]")
    t64, e64 = np.datetime64(t, "ns"), np.datetime64(expiry, "ns")
    return int(np.searchsorted(td, e64, "right") - np.searchsorted(td, t64, "right"))


def select_expiry(
    t: pd.Timestamp,
    available_expiries,
    trading_dates: np.ndarray,
    dte_lo: int = DTE_LO,
    dte_hi: int = DTE_HI,
):
    """Return (expiry, dte) for the nearest PM-settled expiry with DTE in band, or (None, reason)."""
    cands = []
    for e in sorted(pd.to_datetime(pd.Index(available_expiries)).unique()):
        e = pd.Timestamp(e)
        dte = trading_dte(t, e, trading_dates)
        if dte < dte_lo or dte > dte_hi:
            continue
        if is_am_settled(e):
            continue  # AM-settled -> cannot settle to close; drop
        cands.append((e, dte))
    if not cands:
        return None, "no PM-settled expiry with DTE in band"
    cands.sort(key=lambda x: x[1])  # nearest by DTE
    return cands[0]
