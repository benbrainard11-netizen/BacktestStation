"""Layer 2c -- the resolver model + the NON-NEGOTIABLE judge.

Phase 1 reproduce: re-run the existing judges on the pipeline-built event frame,
reusing the exact functions:
  per_feature_forward_test -> market_state validation harness (zone_events.forward_test)
  judge                    -> hold_break_model walk-forward + day-block bootstrap

The multi-head LightGBM resolver (P_hold/break/chop, P_target_before_stop,
R-quantiles, tail) is Phase 2; it slots onto this same harness.
"""

from __future__ import annotations

import _paths  # noqa: F401

import numpy as np
import pandas as pd

import hold_break_model as hb
import zone_events as ze

FEATURES_TESTED = (
    "ofi_signed",
    "qimb_signed",
    "svol_signed",
    "nq_ofi",
    "rty_ofi",
    "ym_ofi",
)


def per_feature_forward_test(
    df: pd.DataFrame, oos_start=ze.OOS_START, printout=True
) -> dict:
    """Reproduce SPEC §2: each feature's IS/OOS Spearman + verdict via the harness."""
    out = {}
    for feat in FEATURES_TESTED:
        fr = df.rename(columns={feat: "signal", "label": "outcome"})[
            ["signal", "outcome"]
        ]
        res = ze.forward_test(
            fr,
            name=f"{feat}->break[ES]",
            kind="continuous",
            oos_start=oos_start,
            min_effect=0.05,
            expect_sign=1,
        )
        if printout:
            ze.print_result(res)
        out[feat] = res
    return out


def ofi_only_baseline(df: pd.DataFrame) -> dict:
    """The non-negotiable baseline = the OFI-only entry of the judge (see judge())."""
    return judge(df, printout=False)


def judge(df: pd.DataFrame, printout=True) -> dict:
    """Reproduce SPEC §3: walk-forward AUC + day-block bootstrap delta-CI.

    Prep mirrors hold_break_model.main exactly (es_complex_agree, day, fold), then
    reuses hb.walk_forward / hb.oos_probs / hb.block_bootstrap / hb.ci.
    """
    df = df.copy()
    df.index = pd.to_datetime(df.index, utc=True)
    df["day"] = df.index.normalize()
    df["complex_mean"] = df[["nq_ofi", "rty_ofi", "ym_ofi"]].mean(axis=1)
    df["es_complex_agree"] = df["ofi_signed"] * df["complex_mean"]
    order = {d: i for i, d in enumerate(sorted(df["day"].unique()))}
    nd = len(order)
    df["fold"] = (df["day"].map(order).to_numpy() * hb.N_FOLDS // nd).clip(
        0, hb.N_FOLDS - 1
    )
    tr, te = df[df.index < hb.OOS_START], df[df.index >= hb.OOS_START]

    wf = hb.walk_forward(df)
    probs = {n: hb.oos_probs(tr, te, f) for n, f in hb.FEATURE_SETS.items()}
    aucs, deltas = hb.block_bootstrap(te, probs)
    res = {
        "n": int(len(df)),
        "n_oos": int(len(te)),
        "oos_days": int(te["day"].nunique()),
        "walk_forward": {
            n: (float(np.mean(wf[n])), float(np.std(wf[n]))) for n in hb.FEATURE_SETS
        },
        "bootstrap_auc": {
            n: tuple(float(x) for x in hb.ci(aucs[n])) for n in hb.FEATURE_SETS
        },
        "delta": tuple(float(x) for x in hb.ci(deltas)),
    }
    if printout:
        print(f"\njudge: n={res['n']} OOS={res['n_oos']} ({res['oos_days']} days)")
        print("  walk-forward AUC (mean +- std):")
        for n in hb.FEATURE_SETS:
            m, s = res["walk_forward"][n]
            print(f"    {n:22} {m:.3f} +- {s:.3f}")
        print("  day-block bootstrap AUC (median [5,95]):")
        for n in hb.FEATURE_SETS:
            m, lo, hi = res["bootstrap_auc"][n]
            print(f"    {n:22} {m:.3f} [{lo:.3f}, {hi:.3f}]")
        dm, dlo, dhi = res["delta"]
        verdict = "REAL (CI excludes 0)" if dlo > 0 else "WITHIN NOISE (CI straddles 0)"
        print(
            f"  DELTA ({hb.FULL} - {hb.BASELINE}) = {dm:+.3f} [{dlo:+.3f}, {dhi:+.3f}] -> {verdict}"
        )
    return res
