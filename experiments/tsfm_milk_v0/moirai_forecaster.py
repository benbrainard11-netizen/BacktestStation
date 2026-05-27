"""MoiraiForecaster — Salesforce Moirai (Uni2TS), v0.5 challenger.

Reference: https://github.com/SalesforceAIResearch/uni2ts

Why Moirai:
  - Larger than TTM (~14M for base, ~311M for large)
  - Designed for "any-variate" multivariate forecasting
  - Strong benchmark performance on Monash time series archive
  - Fits on 5080 at base size, manageable at large with gradient checkpointing

v0.5 plan: same data + pipeline as TTM, swap the Forecaster implementation,
compare head-to-head. If v0.5 lifts numbers, keep. If not, ship TTM.

NOT YET IMPLEMENTED. Lives behind TTM in the v0.5 phase.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError("moirai_forecaster.py is a stub. v0.5 work.")


if __name__ == "__main__":
    raise SystemExit(main())
