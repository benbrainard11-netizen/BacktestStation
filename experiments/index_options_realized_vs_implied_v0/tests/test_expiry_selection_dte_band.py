"""Expiry selection must take the NEAREST PM expiry with trading DTE in [1,7], and nothing else."""

import numpy as np
import pandas as pd

from options.expiry_selection import select_expiry, trading_dte

TD = pd.bdate_range("2023-06-01", periods=30).values  # business-day calendar


def test_trading_dte_counts_business_days_after_t():
    t = pd.Timestamp("2023-06-01")  # Thu
    assert trading_dte(t, pd.Timestamp("2023-06-02"), TD) == 1   # next business day
    assert trading_dte(t, pd.Timestamp("2023-06-08"), TD) == 5
    assert trading_dte(t, pd.Timestamp("2023-06-14"), TD) == 9


def test_picks_nearest_in_band_pm_expiry():
    t = pd.Timestamp("2023-06-01")
    expiries = [pd.Timestamp("2023-06-02"), pd.Timestamp("2023-06-08"), pd.Timestamp("2023-06-14")]
    exp, dte = select_expiry(t, expiries, TD)
    assert exp == pd.Timestamp("2023-06-02") and dte == 1  # nearest, DTE in [1,7]


def test_rejects_when_only_out_of_band():
    t = pd.Timestamp("2023-06-01")
    exp, reason = select_expiry(t, [pd.Timestamp("2023-06-14")], TD)  # DTE 9 > 7
    assert exp is None
