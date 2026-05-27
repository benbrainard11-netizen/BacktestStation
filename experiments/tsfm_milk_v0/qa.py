"""Quality-assurance audit + tests for tsfm_milk_v0.

Modes:
  --audit    Resolve PLAN.md §9 ambiguities (dataset audit).
             Output: report/v0_iter0_dataset_audit.md
             Read-only. Runs first.

  --tests    QA tests against built dataset + predictions.
             Required before any model ships.

Audit topics (--audit mode, PLAN §9):
  1. Bar coverage gaps — per symbol, count days with < 200 RTH bars.
     Identify roll boundaries that might break anchor continuity.
  2. Tick size + slippage — confirm per-symbol tick sizes against
     (high - low) distributions; confirm $1.50 round-trip commission.
  3. Cross-symbol time alignment — at minute t, do all 4 symbols have a
     bar? If not, frequency + when + handling proposal.
  4. Class balance per horizon at k=0.5σ — actual up/down/flat fractions
     vs. expected_balance in labels_and_horizons.yaml.
  5. Vol regime distribution across folds — sigma_60 quantile histograms
     per fold to detect regime imbalances.

Tests (--tests mode):
  - no_lookahead         input bars all have ts < ts_decision
  - label_alignment      label bars all have ts > ts_decision
  - split_purging        train label windows don't overlap val/test
  - embargo_respected    1h gap between train and val/test windows
  - roll_exclusion       anchors whose label window crosses a roll are dropped
  - class_balance        no horizon has < 5% in any class on train
  - cross_symbol_align   all 4 symbols present in every anchor row

NOT YET IMPLEMENTED. --audit mode is the first thing to populate (read-only
pass over bar parquet + walk_forward.yaml that informs everything else).
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError(
        "qa.py is a stub. Implement --audit mode first (PLAN §9). "
        "That output drives build_dataset.py implementation."
    )


if __name__ == "__main__":
    raise SystemExit(main())
