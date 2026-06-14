"""Layer 3 -- risk conditioner (size multiplier).

Adopts experiments/risk_conditioner_v0's LOCKED contract verbatim:
  input  : a valid, detector-fired candidate (the resolver's output)
  output : size_mult in {0.0, 0.25, 0.5, 0.75, 1.0}
  FORBIDDEN: creating new trades, flipping direction, sizing above 1.0.

Hard rule (risk_conditioner_v0/PLAN.md §4): do NOT pool Type A and Type B into
one model. Separate heads, separate objectives. Build the Type A path first
(Type B labels -- OB/FVG/SMT -- are under a durability cloud; defer until
re-verified).

risk_conditioner_v0 itself is PARKED and mostly stubbed, but its 45-feature
schema, walk-forward spec, head architecture, and iter-0 MBO validation
(cancel_rate_60s 5x decile lift, real) are reusable. See REUSE_MAP.md.
"""

from __future__ import annotations



def predict_risk(candidate):
    """Predict the risk block for a valid candidate.

    Outputs (per risk_conditioner_v0 MODEL_CARD): p_bad, p_tail,
    pred_MAE_R_q80/q95, p_target_before_stop, expected_time_in_trade.
    Reuse risk_conditioner_v0/feature_schema.yaml for inputs.
    """
    raise NotImplementedError(
        "Phase 3: train Type A head on risk_conditioner_v0 schema."
    )


def size_multiplier(risk_block) -> float:
    """Map the risk block to a multiplier in config.SIZE_MULT_LADDER.

    Never returns > 1.0, never flips direction, never creates a trade. Quarter
    or skip when p_tail is high; full only when edge is strong and tail is low.
    """
    raise NotImplementedError("Phase 3: policy mapping risk_block -> SIZE_MULT_LADDER.")
