"""market_state validation harness — the spine of the whole project.

THE ONE RULE: a label/signal earns a tile ONLY if it forward-predicts an outcome
OOS with no lookahead. This module is the single, reusable judge of that claim.

It takes an ALREADY-ALIGNED (signal_t, outcome) frame where the caller has built
the outcome to be measured STRICTLY AFTER t (the harness cannot see your raw data,
so it cannot enforce no-lookahead for you — it enforces the IS/OOS split + honest
effect sizes + n logging, and trusts that `outcome` is forward-only). Every caller
that builds an outcome must document the shift it used.

Two relationship kinds:
  - "continuous": signal_t (float) -> forward outcome (float). Effect = Spearman corr
    (rank, robust to the fat tails in returns/vol) + a top-vs-bottom-tercile lift.
  - "binary": a boolean signal splits the outcome; effect = mean(outcome | True) -
    mean(outcome | False), plus the toward-event fraction when outcome is a {-,+} pull.

A relationship PASSES only if BOTH in-sample and out-of-sample agree in sign AND the
OOS effect clears a caller-supplied floor with enough n. Anything else is NULL. We do
NOT bless a relationship on in-sample alone — that is exactly the trap the project exists
to avoid. Numbers are returned, never just printed; callers log n for everything.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

# Named constants (CLAUDE.md rule 7 — no inlined magic numbers).
DEFAULT_OOS_START = pd.Timestamp("2023-01-01")  # daily history split per task spec
TERCILE_LO, TERCILE_HI = 1.0 / 3.0, 2.0 / 3.0   # top/bottom bucket cuts for lift
MIN_N_PER_SIDE = 30      # below this a group mean is too noisy to trust
TOWARD_FAIR = 0.50       # a directional pull is coin-flip at 0.50


@dataclass
class EffectResult:
    """One side (IS or OOS) of a relationship test. All effect sizes + n live here."""

    n: int
    kind: str
    # continuous
    spearman: float = float("nan")
    spearman_p: float = float("nan")
    tercile_lift: float = float("nan")          # mean(outcome|top signal) - mean(|bottom)
    # binary
    mean_true: float = float("nan")
    mean_false: float = float("nan")
    group_diff: float = float("nan")            # mean_true - mean_false
    group_p: float = float("nan")
    toward_frac_true: float = float("nan")      # P(outcome>0 | signal True)
    n_true: int = 0
    n_false: int = 0

    def effect(self) -> float:
        """The single headline effect size used for sign/threshold checks."""
        if self.kind == "continuous":
            return self.spearman
        return self.group_diff


@dataclass
class HarnessResult:
    name: str
    kind: str
    verdict: str                 # "PASS" | "NULL"
    reason: str
    is_res: EffectResult
    oos_res: EffectResult
    oos_start: pd.Timestamp
    min_effect: float
    notes: list[str] = field(default_factory=list)

    def as_row(self) -> dict:
        return {
            "name": self.name, "kind": self.kind, "verdict": self.verdict,
            "n_is": self.is_res.n, "n_oos": self.oos_res.n,
            "effect_is": self.is_res.effect(), "effect_oos": self.oos_res.effect(),
            "min_effect": self.min_effect, "reason": self.reason,
        }


def _continuous_effect(sig: np.ndarray, out: np.ndarray) -> EffectResult:
    n = int(sig.size)
    if n < MIN_N_PER_SIDE:
        return EffectResult(n=n, kind="continuous")
    rho, p = stats.spearmanr(sig, out)
    order = np.argsort(sig)
    k = max(1, int(round(n * TERCILE_LO)))
    bottom = out[order[:k]].mean()
    top = out[order[-k:]].mean()
    return EffectResult(n=n, kind="continuous", spearman=float(rho),
                        spearman_p=float(p), tercile_lift=float(top - bottom))


def _binary_effect(sig: np.ndarray, out: np.ndarray) -> EffectResult:
    sig = sig.astype(bool)
    t, f = out[sig], out[~sig]
    res = EffectResult(n=int(out.size), kind="binary",
                       n_true=int(t.size), n_false=int(f.size))
    if t.size < MIN_N_PER_SIDE or f.size < MIN_N_PER_SIDE:
        return res
    res.mean_true, res.mean_false = float(t.mean()), float(f.mean())
    res.group_diff = res.mean_true - res.mean_false
    res.toward_frac_true = float((t > 0).mean())
    res.group_p = float(stats.ttest_ind(t, f, equal_var=False).pvalue)
    return res


def _measure(frame: pd.DataFrame, kind: str) -> EffectResult:
    s = frame["signal"].to_numpy()
    o = frame["outcome"].to_numpy()
    ok = np.isfinite(o) & (np.isfinite(s) if kind == "continuous" else True)
    s, o = s[ok], o[ok]
    return _continuous_effect(s, o) if kind == "continuous" else _binary_effect(s, o)


def forward_test(
    frame: pd.DataFrame,
    *,
    name: str,
    kind: str,
    oos_start: pd.Timestamp = DEFAULT_OOS_START,
    min_effect: float = 0.0,
    expect_sign: int = 1,
) -> HarnessResult:
    """Judge one forward (signal -> outcome) relationship under an IS/OOS split.

    `frame` must be DatetimeIndexed with columns 'signal' and 'outcome', where
    'outcome' was ALREADY built forward-only (measured strictly after each index t).
    `expect_sign` = +1 / -1: the sign the effect must take to count (e.g. vol-persistence
    is +1; gamma toward-wall has no prior, pass 0 to skip the sign gate).

    Verdict PASS requires: IS and OOS effects share `expect_sign` (if given) AND the
    OOS |effect| >= min_effect with both sides having >= MIN_N_PER_SIDE usable rows.
    Everything else is NULL with a stated reason. (in-sample-only is NEVER a pass.)
    """
    if kind not in ("continuous", "binary"):
        raise ValueError(f"kind must be continuous|binary, got {kind!r}")
    idx = pd.DatetimeIndex(frame.index)
    if idx.tz is not None:
        oos_start = oos_start.tz_localize(idx.tz) if oos_start.tz is None else oos_start
    is_f = frame[idx < oos_start]
    oos_f = frame[idx >= oos_start]
    is_res, oos_res = _measure(is_f, kind), _measure(oos_f, kind)

    notes: list[str] = []
    verdict, reason = "NULL", ""
    e_is, e_oos = is_res.effect(), oos_res.effect()

    if not (np.isfinite(e_is) and np.isfinite(e_oos)):
        reason = f"insufficient n (is={is_res.n}, oos={oos_res.n}; need >={MIN_N_PER_SIDE}/side)"
    elif expect_sign != 0 and np.sign(e_oos) != expect_sign:
        reason = f"OOS effect sign {np.sign(e_oos):+.0f} != expected {expect_sign:+d} (OOS {e_oos:+.3f})"
    elif expect_sign != 0 and np.sign(e_is) != expect_sign:
        reason = f"IS effect sign {np.sign(e_is):+.0f} != expected {expect_sign:+d} (held only OOS = fluke risk)"
    elif abs(e_oos) < min_effect:
        reason = f"OOS |effect| {abs(e_oos):.3f} < floor {min_effect:.3f}"
    else:
        verdict = "PASS"
        reason = f"IS {e_is:+.3f} & OOS {e_oos:+.3f} agree (sign {expect_sign:+d}), OOS clears {min_effect:.3f}"
    return HarnessResult(name=name, kind=kind, verdict=verdict, reason=reason,
                         is_res=is_res, oos_res=oos_res, oos_start=oos_start,
                         min_effect=min_effect, notes=notes)


def print_result(r: HarnessResult) -> None:
    """ASCII-only one-block readout (Windows cp1252-safe)."""
    print(f"  [{r.verdict}] {r.name}  ({r.kind}, OOS>= {r.oos_start.date()})")
    if r.kind == "continuous":
        for tag, e in (("IS", r.is_res), ("OOS", r.oos_res)):
            print(f"     {tag:3} n={e.n:5d}  spearman={e.spearman:+.3f} (p={e.spearman_p:.3f})  "
                  f"tercile_lift={e.tercile_lift:+.4f}")
    else:
        for tag, e in (("IS", r.is_res), ("OOS", r.oos_res)):
            print(f"     {tag:3} n={e.n:5d}  diff(T-F)={e.group_diff:+.4f} (p={e.group_p:.3f})  "
                  f"mean_T={e.mean_true:+.4f} mean_F={e.mean_false:+.4f}  "
                  f"toward_T={e.toward_frac_true:.2f}  nT={e.n_true} nF={e.n_false}")
    print(f"     -> {r.reason}")
