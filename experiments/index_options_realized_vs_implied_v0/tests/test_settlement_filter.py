"""FAIL-CLOSED settlement gate: exclude the monthly-expiry risk zone (day 15-21 AND Thu/Fri), not
just the literal 3rd Friday -- so a holiday-shifted AM monthly can't slip in and get close-settled.
PM weeklies/dailies outside that zone are kept.
"""

import pandas as pd

from options.expiry_selection import is_am_settled, is_third_friday, select_expiry

TD = pd.bdate_range("2023-06-01", periods=30).values


def test_monthly_risk_zone_excluded():
    assert is_am_settled(pd.Timestamp("2023-06-16"))      # 3rd Friday (day 16) -> excluded
    assert is_am_settled(pd.Timestamp("2023-06-15"))      # Thu day 15, holiday-shift risk -> excluded
    assert not is_am_settled(pd.Timestamp("2023-06-09"))  # Fri day 9, outside 15-21 -> PM
    assert not is_am_settled(pd.Timestamp("2023-06-20"))  # Tue day 20, not Thu/Fri -> PM
    assert not is_am_settled(pd.Timestamp("2023-06-22"))  # Thu day 22, outside 15-21 -> PM
    assert is_third_friday(pd.Timestamp("2023-06-16"))    # helper still correct


def test_am_risk_expiry_excluded_in_favor_of_pm():
    t = pd.Timestamp("2023-06-13")  # Tue
    am = pd.Timestamp("2023-06-16")  # 3rd Friday, AM-risk, DTE 3 (nearer)
    pm = pd.Timestamp("2023-06-20")  # Tue, PM, DTE 5 (farther)
    exp, dte = select_expiry(t, [am, pm], TD)
    assert exp == pm and dte == 5  # picks the farther PM, skipping the nearer AM-risk expiry


def test_only_am_risk_in_band_returns_none():
    t = pd.Timestamp("2023-06-13")
    exp, reason = select_expiry(t, [pd.Timestamp("2023-06-16")], TD)
    assert exp is None
