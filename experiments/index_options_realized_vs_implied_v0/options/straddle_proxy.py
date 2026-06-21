"""Quote-based long-ATM-straddle payoff, held to expiry, settled to intrinsic.

LOCKED primary: buy at ask, settle to intrinsic at expiry. Report points, % of underlying, and R
(R explodes for cheap options -> never the only measure). 1.5x spread stress widens each half-spread.
"""

from __future__ import annotations


def settlement_value(s_expiry: float, strike: float) -> float:
    """Long straddle intrinsic at expiry = |S_exp - K| (call + put intrinsic)."""
    return max(s_expiry - strike, 0.0) + max(strike - s_expiry, 0.0)


def straddle_pnl(atm: dict, s_entry: float, s_expiry: float, fees: float = 0.0) -> dict:
    """Primary P&L: enter long straddle at ask, hold to expiry, settle to intrinsic."""
    entry_ask = atm["call_ask"] + atm["put_ask"]
    settle = settlement_value(s_expiry, atm["strike"])
    pnl_points = settle - entry_ask - fees
    return {
        "entry_cost_ask": entry_ask,
        "settlement_value": settle,
        "pnl_points": pnl_points,
        "pnl_pct": pnl_points / s_entry if s_entry else float("nan"),
        "pnl_R": pnl_points / entry_ask if entry_ask else float("nan"),
    }


def stressed_entry_cost(atm: dict, spread_mult: float = 1.5) -> float:
    """Entry cost if you pay `spread_mult` x the quoted half-spread on each leg (>= ask at 1.0)."""
    cost = 0.0
    for side in ("call", "put"):
        bid, ask = atm[f"{side}_bid"], atm[f"{side}_ask"]
        mid = (bid + ask) / 2
        cost += mid + spread_mult * (ask - mid)
    return cost


def straddle_pnl_stressed(atm: dict, s_entry: float, s_expiry: float,
                          spread_mult: float = 1.5, fees: float = 0.0) -> dict:
    """P&L under 1.5x (default) spread stress on entry."""
    entry = stressed_entry_cost(atm, spread_mult)
    settle = settlement_value(s_expiry, atm["strike"])
    pnl_points = settle - entry - fees
    return {"entry_cost": entry, "pnl_points": pnl_points,
            "pnl_pct": pnl_points / s_entry if s_entry else float("nan")}


# --- v1: SHORT straddle (audit measuring instrument only -- NEVER live naked) ---

def _straddle_spread(atm: dict) -> float:
    return (atm["call_ask"] - atm["call_bid"]) + (atm["put_ask"] - atm["put_bid"])


def short_straddle_pnl(atm: dict, s_entry: float, s_expiry: float, fees: float = 0.0) -> dict:
    """SELL ATM straddle at bid, hold to expiry, settle to intrinsic. P&L = credit - |S_exp-K| - fees.
    R is relative to the credit received (the seller's at-risk-per-credit unit)."""
    credit = atm["call_bid"] + atm["put_bid"]
    loss = settlement_value(s_expiry, atm["strike"])
    pnl = credit - loss - fees
    return {"entry_credit": credit, "settle_loss": loss, "pnl_points": pnl,
            "pnl_pct": pnl / s_entry if s_entry else float("nan"),
            "pnl_R": pnl / credit if credit else float("nan")}


def short_straddle_pnl_stressed(atm: dict, s_entry: float, s_expiry: float, fees: float = 0.0) -> dict:
    """Short P&L under spread stress: collect a worse (lower) credit = bid - 0.5*straddle_spread."""
    credit = (atm["call_bid"] + atm["put_bid"]) - 0.5 * _straddle_spread(atm)
    pnl = credit - settlement_value(s_expiry, atm["strike"]) - fees
    return {"stress_credit": credit, "pnl_points": pnl,
            "pnl_pct": pnl / s_entry if s_entry else float("nan")}
