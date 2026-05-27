"""OrderIntent adapter — consumes predictions, emits sizing.

Plugs into Strategy.on_bar() to apply size_mult based on risk predictions.

Reads:
  out/predictions/                (offline parquet, joined by trade_id or ts_decision)
  detector_families.yaml          (family dispatch)
  feature_schema.yaml             (input feature names)

Output contract:
  risk_score      ∈ [0, 1]
  tail_risk_score ∈ [0, 1]
  size_mult       ∈ {0.0, 0.25, 0.5, 0.75, 1.0}

Dispatch:
  family_type = detector_family_config[signal.detector_name].family_type
  if family_type == "A":  pred = risk_conditioner_type_a.predict(...);  size_mult = policy_type_a(pred)
  elif family_type == "B": pred = tail_conditioner_type_b.predict(...); size_mult = policy_type_b(pred)
  else: size_mult = 1.0; status = "unknown_family_fallback"

Fallback rule (NO silent failure):
  If model unavailable, stale, or feature row missing:
      size_mult = 1.0
      risk_model_status = "missing_fallback"
      log this

Rollout stages:
  Stage 1: shadow only        (model predicts, engine logs, no sizing impact)
  Stage 2: skip only          (size_mult ∈ {0, 1})
  Stage 3: downsize ladder    (size_mult ∈ {0, 0.25, 0.5, 0.75, 1.0})
  Stage 4: size > 1.0         NOT ALLOWED IN v0

Engine integration (Strategy.on_bar()):
  See PLAN §7 for the full code sample.

NOT YET IMPLEMENTED.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError(
        "integration.py is a stub. "
        "Implement after evaluate.py confirms the v0 model passes kill criteria."
    )


if __name__ == "__main__":
    raise SystemExit(main())
