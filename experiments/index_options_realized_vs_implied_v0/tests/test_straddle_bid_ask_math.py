"""Quote-based straddle math must be honest: enter at ASK, settle to intrinsic, spread filter right."""

import numpy as np

from options.implied_move import passes_quote_filter, straddle_quotes, valid_leg
from options.straddle_proxy import settlement_value, straddle_pnl, stressed_entry_cost

ATM = {"strike": 100.0, "call_bid": 1.0, "call_ask": 1.4, "put_bid": 0.8, "put_ask": 1.2}


def test_entry_cost_is_sum_of_asks():
    pnl = straddle_pnl(ATM, s_entry=100.0, s_expiry=100.0)
    assert np.isclose(pnl["entry_cost_ask"], 1.4 + 1.2)  # asks, not mids
    # ATM expiry -> intrinsic 0 -> lose the full entry
    assert np.isclose(pnl["settlement_value"], 0.0)
    assert np.isclose(pnl["pnl_points"], -(1.4 + 1.2))


def test_settlement_is_absolute_move():
    assert np.isclose(settlement_value(112.0, 100.0), 12.0)
    assert np.isclose(settlement_value(91.0, 100.0), 9.0)
    pnl = straddle_pnl(ATM, s_entry=100.0, s_expiry=112.0)
    assert np.isclose(pnl["pnl_points"], 12.0 - 2.6)
    assert np.isclose(pnl["pnl_pct"], (12.0 - 2.6) / 100.0)


def test_stressed_entry_exceeds_ask():
    ask_cost = ATM["call_ask"] + ATM["put_ask"]
    assert stressed_entry_cost(ATM, 1.5) > ask_cost  # paying 1.5x half-spread > paying the ask
    assert np.isclose(stressed_entry_cost(ATM, 1.0), ask_cost)  # 1.0x == the ask


def test_spread_filter_and_valid_leg():
    assert valid_leg(1.0, 1.4) and not valid_leg(0.0, 1.0) and not valid_leg(1.5, 1.0)
    sq = straddle_quotes(ATM)
    # spread = 0.4 + 0.4 = 0.8 ; mid = 1.2 + 1.0 = 2.2 ; ratio ~0.36 > 0.20 -> rejected
    assert np.isclose(sq["straddle_spread"], 0.8) and np.isclose(sq["straddle_mid"], 2.2)
    assert not passes_quote_filter(sq, 0.20)
    tight = straddle_quotes({"strike": 100, "call_bid": 1.95, "call_ask": 2.05,
                             "put_bid": 1.95, "put_ask": 2.05})
    assert passes_quote_filter(tight, 0.20)
