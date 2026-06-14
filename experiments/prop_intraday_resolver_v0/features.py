"""Layer 2a -- event-time feature builder (AT the touch).

Phase 1 reproduce: the Tier-1 features computed in zone_events.process_day over
the [t0, t0+W_OFI] window, signed in the break direction:
  ofi_signed   -- CKS OFI sum
  qimb_signed  -- top-of-book depth/queue imbalance (mean over the window)
  svol_signed  -- net signed aggressor trade size
  nq/rty/ym_ofi -- peer-index CKS OFI over the same window

THE CARDINAL RULE (assert_no_lookahead): the feature window must end at or
before the decision boundary. Here the boundary IS t0+W_OFI (the label is
measured strictly after it), so feature_end == decision -- the assert guards
against anyone later widening the window past the decision point. The Mira gate's
"edge" was a lookahead artifact from features that ran past the decision; never
again.
"""

from __future__ import annotations

import _paths  # noqa: F401

import zone_events as ze


def assert_no_lookahead(t_feature_end, t_decision) -> None:
    if not (t_feature_end <= t_decision):
        raise AssertionError(
            f"LOOKAHEAD: feature window ends {t_feature_end} > decision {t_decision}. "
            "Feature window must be <= decision time on every row."
        )


def build_features(ctx, i0: int, t0, dr: int) -> dict:
    """Event-time feature dict for one touch. Reuses ctx arrays; signs by dr."""
    decision = t0 + ze.W_OFI
    jo = int(ctx.tsi.searchsorted(decision, side="right"))
    assert_no_lookahead(
        decision, decision
    )  # feature window [t0, t0+W_OFI] ends at the boundary

    of = float(ctx.ofi[i0:jo].sum()) * dr
    svol = float(ctx.strade[i0:jo].sum()) * dr
    jw = max(jo, i0 + 1)  # depth window (>=1 row)
    bw, aw = float(ctx.bid_sz[i0:jw].mean()), float(ctx.ask_sz[i0:jw].mean())
    qimb = (((bw - aw) / (bw + aw)) if (bw + aw) > 0 else 0.0) * dr

    feats = {
        "ofi_signed": of,
        "qimb_signed": qimb,
        "svol_signed": svol,
        "nq_ofi": 0.0,
        "rty_ofi": 0.0,
        "ym_ofi": 0.0,
    }
    for pk, (ptsi, pofi) in ctx.peers.items():
        a = int(ptsi.searchsorted(t0))
        b = int(ptsi.searchsorted(decision, side="right"))
        feats[f"{pk}_ofi"] = float(pofi[a:b].sum()) * dr
    return feats
