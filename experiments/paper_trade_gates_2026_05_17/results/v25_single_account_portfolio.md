# v25 — Single-Account Portfolio Simulator (Paper-Trade Gate 4)

_Generated 2026-05-18T01:33:49.622769Z_

Tests how much of the v20 independent-family edge survives when OB strict + Sweep reversed run on one account with concurrency caps.

## Baseline (independent silos, v20)

- OB strict: 1509.26 R
- Sweep reversed (filtered): 1042.72 R
- **Summed: 2551.98 R**

## Verdict: FAIL

### cap_total_1 (cap_total=1, per_symbol=1)

- Candidate trades: 6,381
- Trades taken: 2,370
- Blocked by per-symbol cap: 1,408
- Blocked by total cap: 2,603
- cum_R: **827.26** (32.4% of independent baseline)
- Worst day: -5.56 R
- Max drawdown: -9.23 R

Per-family taken:
  - OB strict: 1,628 trades / 553.33 R
  - Sweep reversed (filtered): 742 trades / 273.93 R

Per-holdout taken:
  - holdout_1_2018_2019: 2,239 trades / 770.62 R
  - holdout_2_2026: 131 trades / 56.64 R

- Retention ≥ threshold: **False** (actual=32.4%, threshold=40%)
- cum_R positive across both holdouts: **True**
- **FAIL**

### cap_total_2 (cap_total=2, per_symbol=1)

- Candidate trades: 6,381
- Trades taken: 3,961
- Blocked by per-symbol cap: 2,420
- Blocked by total cap: 0
- cum_R: **1365.17** (53.5% of independent baseline)
- Worst day: -8.93 R
- Max drawdown: -10.70 R

Per-family taken:
  - OB strict: 2,633 trades / 870.02 R
  - Sweep reversed (filtered): 1,328 trades / 495.16 R

Per-holdout taken:
  - holdout_1_2018_2019: 3,737 trades / 1251.32 R
  - holdout_2_2026: 224 trades / 113.85 R

- Retention ≥ threshold: **False** (actual=53.5%, threshold=70%)
- cum_R positive across both holdouts: **True**
- **FAIL**

## Interpretation

- The independent baseline (~2.5K R combined) is what v20 reported. Real-world cum_R will be lower because of concurrency conflicts.
- cap_total=2 (one per symbol) is the natural cap for a 2-symbol universe — closely approximates 'run both families against both symbols.'
- cap_total=1 is the strictest case — only one trade across the whole account at a time. Useful if capital is tight.
- The split of blocked trades between per-symbol vs total-cap tells you which constraint binds.
