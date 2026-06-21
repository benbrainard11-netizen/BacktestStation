"""Short-straddle math: collect the BID credit, lose |S_exp-K|, R relative to credit; stress collects less."""

import numpy as np

from options.straddle_proxy import short_straddle_pnl, short_straddle_pnl_stressed

ATM = {"strike": 100.0, "call_bid": 1.0, "call_ask": 1.4, "put_bid": 0.8, "put_ask": 1.2}


def test_credit_kept_when_no_move():
    p = short_straddle_pnl(ATM, s_entry=100.0, s_expiry=100.0)
    assert np.isclose(p["entry_credit"], 1.8)        # call_bid + put_bid (sold at bid)
    assert np.isclose(p["pnl_points"], 1.8)          # intrinsic 0 -> keep full credit
    assert np.isclose(p["pnl_R"], 1.0)               # R relative to credit


def test_big_move_is_a_large_R_loss():
    p = short_straddle_pnl(ATM, s_entry=100.0, s_expiry=112.0)
    assert np.isclose(p["pnl_points"], 1.8 - 12.0)   # credit - |112-100|
    assert p["pnl_R"] < -5                            # the seller's tail
    assert np.isclose(p["pnl_pct"], (1.8 - 12.0) / 100.0)


def test_stress_collects_less_credit():
    base = short_straddle_pnl(ATM, 100.0, 100.0)["pnl_points"]
    stressed = short_straddle_pnl_stressed(ATM, 100.0, 100.0)["pnl_points"]
    # straddle_spread = 0.4 + 0.4 = 0.8 -> stress credit = 1.8 - 0.4 = 1.4
    assert np.isclose(stressed, 1.4) and stressed < base
