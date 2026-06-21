"""The expensiveness rank must use only STRICTLY-PRIOR observations.

If a future observation can move a past rank, the bucket assignment is lookahead -- the exact trap
that has bitten this lab repeatedly. So: mutating a future value must not change any earlier rank;
mutating an in-window prior value MUST (positive control).
"""

import numpy as np
import pandas as pd

from validation.state_buckets import bucket_3, rolling_prior_percentile

WINDOW = 20


def _series(seed=0, n=80):
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(0, 1, n), index=pd.RangeIndex(n))


def test_future_values_cannot_move_past_rank():
    s = _series()
    base = rolling_prior_percentile(s, WINDOW)
    j = 60
    bumped = s.copy()
    bumped.iloc[j] += 10.0  # shock the future
    after = rolling_prior_percentile(bumped, WINDOW)
    # every rank strictly before j must be byte-identical
    pd.testing.assert_series_equal(after.iloc[:j], base.iloc[:j])


def test_in_window_prior_value_changes_rank():
    """A prior obs inside i's window must affect rank_i. Push v[i-1] to -inf vs +inf: at -inf it
    counts as below v_i, at +inf it does not -> rank_i must differ (guaranteed, data-independent)."""
    s = _series()
    i = 50
    lo, hi = s.copy(), s.copy()
    lo.iloc[i - 1] = -1e9
    hi.iloc[i - 1] = 1e9
    r_lo = rolling_prior_percentile(lo, WINDOW).iloc[i]
    r_hi = rolling_prior_percentile(hi, WINDOW).iloc[i]
    assert r_lo > r_hi  # the in-window prior genuinely enters the rank


def test_first_window_is_nan_and_buckets_map():
    s = _series()
    r = rolling_prior_percentile(s, WINDOW)
    assert r.iloc[:WINDOW].isna().all()
    b = bucket_3(r)
    assert set(b.dropna().unique()) <= {"cheap", "mid", "rich"}
