"""Write v0 prediction artifacts for downstream consumption (the v1 sizing layer).

v0 has NO engine integration — output is a parquet artifact that lives at
out/predictions/. The v1 sizing/risk layer (separate experiment) will read
these predictions and convert to per-account contract counts.

Prediction schema (one row per (anchor_ts, symbol)):

  ts_decision               UTC timestamp of the anchor row
  symbol                    ES.c.0 / NQ.c.0 / YM.c.0 / RTY.c.0
  model_name                e.g., "ttm_v0_2026-05-28"
  model_version
  feature_version
  label_version
  fold_id                   which fold this prediction came from
  h_15m_p_flat
  h_15m_p_up
  h_15m_p_down
  h_30m_p_flat
  h_30m_p_up
  h_30m_p_down
  h_60m_p_flat / p_up / p_down
  h_90m_p_flat / p_up / p_down
  h_240m_p_flat / p_up / p_down
  prediction_created_at

NOT YET IMPLEMENTED.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError("integration.py is a stub.")


if __name__ == "__main__":
    raise SystemExit(main())
