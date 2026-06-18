"""Greeks for the intraday option panels.

Reuses the futures-VALIDATED Black-Scholes engine in build_walls_ndx (bs_price / bs_gamma /
implied_vol, all r=q=0 on the underlying/forward) and adds vanna + charm. Under r=q=0 both vanna
and charm are the SAME for calls and puts (vega is identical; delta differs by a constant 1).

A finite-difference self-check (`selfcheck()`) verifies every analytic formula against a central
difference of bs_price/delta, so a sign or factor error surfaces at build time rather than silently
corrupting downstream gamma/vanna/charm. Run `python option_greeks.py` to execute it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_walls_ndx import bs_gamma, bs_price, implied_vol  # noqa: E402,F401  (re-exported)


def _d1d2(S, K, T, sig):
    T = np.maximum(np.asarray(T, float), 1e-9)
    sig = np.maximum(np.asarray(sig, float), 1e-9)
    sqT = np.sqrt(T)
    d1 = (np.log(S / K) + 0.5 * sig * sig * T) / (sig * sqT)
    return d1, d1 - sig * sqT, sqT


def bs_delta(S, K, T, sig, is_call):
    """Spot delta, r=q=0. Call N(d1); put N(d1)-1."""
    d1, _, _ = _d1d2(S, K, T, sig)
    call = norm.cdf(d1)
    return np.where(is_call, call, call - 1.0)


def bs_vega(S, K, T, sig):
    """dV/dsigma per 1.00 of vol. Same for call/put."""
    d1, _, sqT = _d1d2(S, K, T, sig)
    return S * norm.pdf(d1) * sqT


def bs_vanna(S, K, T, sig):
    """d(vega)/dS = d2V/dS dsigma = -phi(d1) d2 / sigma  (r=q=0). Call=put."""
    d1, d2, _ = _d1d2(S, K, T, sig)
    sig = np.maximum(np.asarray(sig, float), 1e-9)
    v = -norm.pdf(d1) * d2 / sig
    return np.where(np.isfinite(v), v, 0.0)


def bs_charm(S, K, T, sig):
    """Charm = d(delta)/dT per YEAR of time-to-expiry (r=q=0): -phi(d1) d2 / (2T). Call=put.

    Since d(d1)/dT = -d2/(2T), d(delta)/dT = phi(d1) d(d1)/dT = -phi(d1) d2 / (2T). As expiry
    APPROACHES (t up, T down), delta moves by the opposite sign. Verified vs a central FD of
    delta-w.r.t.-T in selfcheck() — the FD caught the original (+) sign bug.
    """
    d1, d2, _ = _d1d2(S, K, T, sig)
    T = np.maximum(np.asarray(T, float), 1e-9)
    c = -norm.pdf(d1) * d2 / (2.0 * T)
    return np.where(np.isfinite(c), c, 0.0)


def selfcheck(verbose: bool = True) -> bool:
    """Central finite differences vs the analytic formulas. Raises AssertionError on mismatch."""
    rng_S = np.array([95.0, 100.0, 105.0, 110.0])
    K, T, sig, is_call = 100.0, 0.25, 0.20, np.array([True, False, True, False])
    hS, hSig, hT = 1e-3 * rng_S, 1e-4, 1e-5

    def price(S, sg, t, c):
        return bs_price(S, K, t, sg, c)

    gamma_fd = (
        price(rng_S + hS, sig, T, is_call)
        - 2 * price(rng_S, sig, T, is_call)
        + price(rng_S - hS, sig, T, is_call)
    ) / (hS * hS)
    delta_fd = (price(rng_S + hS, sig, T, is_call) - price(rng_S - hS, sig, T, is_call)) / (2 * hS)
    vega_fd = (price(rng_S, sig + hSig, T, is_call) - price(rng_S, sig - hSig, T, is_call)) / (2 * hSig)
    vanna_fd = (bs_delta(rng_S, K, T, sig + hSig, is_call) - bs_delta(rng_S, K, T, sig - hSig, is_call)) / (
        2 * hSig
    )
    charm_fd = (bs_delta(rng_S, K, T + hT, sig, is_call) - bs_delta(rng_S, K, T - hT, sig, is_call)) / (
        2 * hT
    )

    checks = {
        "gamma": (bs_gamma(rng_S, K, T, sig), gamma_fd),
        "delta": (bs_delta(rng_S, K, T, sig, is_call), delta_fd),
        "vega": (bs_vega(rng_S, K, T, sig), vega_fd),
        "vanna": (bs_vanna(rng_S, K, T, sig), vanna_fd),
        "charm": (bs_charm(rng_S, K, T, sig), charm_fd),
    }
    ok = True
    for name, (ana, fd) in checks.items():
        err = float(np.max(np.abs(ana - fd)))
        tol = 1e-4 * max(1.0, float(np.max(np.abs(fd))))
        good = err <= tol
        ok &= good
        if verbose:
            print(f"  {name:6s} max|analytic-FD| = {err:.3e}  tol={tol:.1e}  {'OK' if good else 'FAIL'}")
    assert ok, "greeks self-check FAILED — do not build panels with these formulas"
    return ok


if __name__ == "__main__":
    print("option_greeks finite-difference self-check (r=q=0):")
    selfcheck()
    print("ALL GREEKS OK")
