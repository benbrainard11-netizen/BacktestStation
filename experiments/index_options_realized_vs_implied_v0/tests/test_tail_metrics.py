"""Tail metrics: CVaR is the mean of the worst alpha-fraction; loss probabilities are correct."""

import numpy as np
import pandas as pd

from validation.tail_metrics import cvar, prob_worse_than, tail_report


def test_cvar_is_mean_of_worst_tail():
    v = pd.Series([-100.0] * 5 + [1.0] * 95)  # worst 5% are -100
    assert np.isclose(cvar(v, 0.05), -100.0)
    # all-positive series -> CVaR is just the smallest few (still defined, negative-ish only if losses)
    assert cvar(pd.Series([1.0, 2.0, 3.0, 4.0]), 0.5) <= 2.0


def test_prob_worse_than():
    r = pd.Series([-6, -4, -2, 0, 1, 1, 1, 1, 1, 1])  # 1/10 below -5, 2/10 below -3
    assert np.isclose(prob_worse_than(r, -5), 0.1)
    assert np.isclose(prob_worse_than(r, -3), 0.2)


def test_tail_report_bundle_keys_and_ratio():
    rng = np.random.default_rng(0)
    pnl_pct = pd.Series(rng.normal(0.001, 0.01, 500))
    pnl_R = pd.Series(rng.normal(0.5, 2.0, 500))
    rep = tail_report(pnl_pct, pnl_R)
    for k in ("mean_pnl_pct", "cvar5_pct", "cvar5_R", "worst_loss_R",
              "p_R_lt_-3", "p_R_lt_-5", "mean_over_abs_cvar5"):
        assert k in rep
    # mean/|CVaR| sign follows the mean (CVaR of pct losses is negative)
    assert np.isfinite(rep["mean_over_abs_cvar5"])
