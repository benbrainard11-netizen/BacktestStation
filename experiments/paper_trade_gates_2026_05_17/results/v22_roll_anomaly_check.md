# v22 — Roll-Anomaly Check (Paper-Trade Gate 1)

_Generated 2026-05-18T01:27:09.409809Z_

Tests whether the v20 OB strict + Sweep reversed result is inflated by continuous-contract roll-window distortions. Limited check — no per-contract bars on disk.

## Roll windows tested

40 quarterly windows. Each is [expiry - 5 days, expiry + 1 day].

## Verdict: PASS

### OB strict

- Span: 2018-01-02 → 2026-05-08 (3049 days)
- Roll days in span: 231 (7.6% of days)
- Total trades: 4,359 (roll-adj: 354, non-adj: 4,005)
- Total cum_R: 1509.26
- Cum_R roll-adjacent: 145.23 (9.6%)
- Cum_R non-adjacent: 1364.02
- Inflation ratio (actual_share / expected_share): 1.27
- avg_R roll-adj: 0.4103 / non-adj: 0.3406 (ratio: 1.205)
- Checks: inflation ≤ 2x = True, avg_R ratio in [0.5, 2] = True
- **PASS**

### Sweep reversed (filtered)

- Span: 2018-01-02 → 2026-05-08 (3049 days)
- Roll days in span: 231 (7.6% of days)
- Total trades: 2,022 (roll-adj: 147, non-adj: 1,875)
- Total cum_R: 1042.72
- Cum_R roll-adjacent: 79.25 (7.6%)
- Cum_R non-adjacent: 963.47
- Inflation ratio (actual_share / expected_share): 1.003
- avg_R roll-adj: 0.5391 / non-adj: 0.5139 (ratio: 1.049)
- Checks: inflation ≤ 2x = True, avg_R ratio in [0.5, 2] = True
- **PASS**

## Interpretation

- `inflation_ratio` > 2 → cum_R disproportionately concentrated on roll days; likely artifact.
- `avg_R ratio` outside [0.5, 2] → per-trade R behaves very differently in roll windows; suspicious.
- Both passing → result is not roll-dominated (within the limits of continuous-symbol data).

## Limitations

- No per-contract bars, so we can't compare continuous-symbol prints to true contract prints.
- Roll-window definition is heuristic (5 days before, 1 day after the 3rd-Friday expiry).
- A pass here does NOT prove zero roll distortion — it just rules out gross concentration.
