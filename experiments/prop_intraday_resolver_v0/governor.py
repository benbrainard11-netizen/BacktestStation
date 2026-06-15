"""Layer 4 -- prop-firm governor (account-safe, firm-compliant final size).

Almost entirely reuse. experiments/sizing_v1 + experiments/prop_model_v0 already
implement the account state machine, vol-targeted sizing, 6 audited firm
rule-sets, and the eval-EV / fleet / milkability Monte Carlo -- and they already
optimize PASS RATE / survival, not Sharpe or win rate.

Reuse:
  sizing_v1/account.py, firm_rules.py     -- DLL hard-stop, trailing-DD lock
  sizing_v1/sizing.py::size_position       -- vol_targeted (ATR + conviction + DD buffer)
  sizing_v1/risk_manager.py::decide        -- entry gate (extend w/ level-aware skip)
  prop_model_v0/eval_ev.py                 -- P(pass) x value - cost, per firm
  sizing_v1/{fleet_sim,monte_carlo_milkability}.py

NET-NEW (the real gap the design missed): intraday bar-grain mark-to-market.
account.py checks breaches only at trade close, so an intraday daily-loss-limit
breach that recovers by EOD is invisible -- which over-reports survival. The
governor MUST mark-to-market within the day.
"""

from __future__ import annotations


def govern(candidate, size_mult, account_state, firm):
    """Final firm-compliant size for a conditioned candidate.

    Fragile account -> require higher edge, cut size, stop after first loss,
    avoid correlated simultaneous trades. Healthy + strong edge -> normal size.
    Reuse risk_manager.decide + sizing.size_position; apply size_mult; enforce
    firm rules (config.FIRMS -> sizing_v1/config/firms/*.yaml).
    """
    raise NotImplementedError(
        "Phase 4: reuse sizing_v1 risk_manager + sizing + firm_rules."
    )


def intraday_mtm(account_state, bar):
    """NET-NEW: mark-to-market the open position within the day.

    Detects within-day DLL / trailing-DD breaches that trade-close accounting in
    sizing_v1/account.py misses. Required for an honest prop governor.
    """
    raise NotImplementedError(
        "Phase 4 net-new: bar-grain MTM for within-day breach detection."
    )
