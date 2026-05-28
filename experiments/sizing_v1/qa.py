"""QA tests + ambiguity audit for sizing_v1.

Modes:
  --audit    Resolve PLAN.md §12 ambiguities (per-firm rule confirmation).
             Output: report/v1_iter0_firm_rules_audit.md

  --tests    QA tests:
             - no_lookahead: entry uses bar AFTER ts_decision
             - state_consistency: account state never goes backward
             - jitter_randomness: distinct accounts get distinct entry times
             - reproducibility: same seed → same result
             - no_silent_skip: every skipped signal has a logged reason

NOT YET IMPLEMENTED.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError(
        "qa.py is a stub. Run --audit first to populate firm rule configs."
    )


if __name__ == "__main__":
    raise SystemExit(main())
