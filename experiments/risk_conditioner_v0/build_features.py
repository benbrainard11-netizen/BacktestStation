"""Build the 45-feature table for the candidate-trade universe.

For each trade row in trades_universe.parquet, compute exactly the 45 v0
features defined in feature_schema.yaml. Strict no-lookahead: only use
information available at or before ts_decision_i.

Input:  out/trades_universe.parquet
Output: out/features.parquet
Schema: feature_schema.yaml (45 features + mbo_available metadata flag)

Feature group counts:
  detector_context        8
  top_of_book_mbp1        8
  trade_flow_mbp1         6
  realized_vol            4
  higher_timeframe        6
  cross_asset             3
  session_time            3
  lagged_detector_perf    2
  mbo_tail_risk           5
  ---
  TOTAL                  45

MBO features are null for trades outside the MBO-available window
(~2026-01-01 onward as of 2026-05-26, backfill in progress). The
mbo_available column is metadata, not a model feature.

Reusable code: experiments/mbo_features_v0/scan.py already computes
cancel_to_trade, add_to_cancel, aggressive_buy_ratio, iceberg_proxy
per 1m bin from raw DBN. Adapt for rolling 60s/300s windows on the
trade-decision side.

NOT YET IMPLEMENTED.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError(
        "build_features.py is a stub. "
        "Implement after build_trade_universe.py produces a valid universe."
    )


if __name__ == "__main__":
    raise SystemExit(main())
