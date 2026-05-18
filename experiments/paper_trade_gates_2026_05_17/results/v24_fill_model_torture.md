# v24 — Fill-Model Torture (Paper-Trade Gate 3)

_Generated 2026-05-18T01:32:21.915029Z_

Tests OHLC-level range consistency + volume credibility of v20 fills for OB strict + Sweep reversed (filtered). Complements v18's TBBO honest-fill check.

## Verdict: PASS

### OB strict

- Total trades: 4,359
- Total cum_R: 1509.26
- Entry-bar matched: 4,359
- % trades with entry or exit price OUTSIDE bar [low, high] (INFORMATIONAL — see header note): 63.8449%

| Volume gate | Trades kept | Trades dropped | cum_R kept | Retention |
|---|---:|---:|---:|---:|
| 10+ contracts/min | 4,086 | 273 | 1431.90 | 94.9% |
| 25+ contracts/min | 3,713 | 646 | 1355.98 | 89.8% |
| 100+ contracts/min | 2,618 | 1,741 | 1043.26 | 69.1% |

- ≥ 80% retention at vol-gate 25: **True**
- ≥ 90% retention at vol-gate 10: **True**
- **PASS**

### Sweep reversed (filtered)

- Total trades: 2,022
- Total cum_R: 1042.72
- Entry-bar matched: 2,022
- % trades with entry or exit price OUTSIDE bar [low, high] (INFORMATIONAL — see header note): 49.1592%

| Volume gate | Trades kept | Trades dropped | cum_R kept | Retention |
|---|---:|---:|---:|---:|
| 10+ contracts/min | 1,997 | 25 | 1023.90 | 98.2% |
| 25+ contracts/min | 1,961 | 61 | 998.58 | 95.8% |
| 100+ contracts/min | 1,687 | 335 | 826.66 | 79.3% |

- ≥ 80% retention at vol-gate 25: **True**
- ≥ 90% retention at vol-gate 10: **True**
- **PASS**

## Interpretation

- Volume-gate retention measures how much edge is preserved if we filter out trades whose entry minute had too little real volume to absorb our order. 1 contract is small, so even thin bars should hold up.
- Vol-25 retention < 80% means an uncomfortable share of edge comes from sub-25-contract-per-minute bars — possibly Asia session or low-liquidity holiday hours.
- The OOR % is informational only: 2-tick adverse slippage on stops/entries/time-exits is intentionally OUTSIDE the bar range (the simulator being pessimistic). A high OOR % just means slippage is being applied; it does NOT indicate fill dishonesty.
- v18 already verified honest-fill against actual trade tape at 89% R retention (TBBO replay). This gate adds the orthogonal volume question.
