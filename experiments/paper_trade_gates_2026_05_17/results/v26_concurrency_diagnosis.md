# v26 — Concurrency Diagnosis

## Why gate 4 failed: the blocking dynamics

- Independent baseline: **2551.98 R**
- Trades taken at cap=2: 3961 (1365.17 R)
- Trades blocked: 2420 (1186.80 R left on the table)

## Block directionality

- Same-direction blocks: **1190** (missed cum_R = 784.25)
- Opposite-direction blocks: **1230** (missed cum_R = 402.55)

Same-direction blocks are correlated signals — even if we could take both, the second one is mostly redundant. **Opposite-direction blocks would NET to zero in real life**, so the v25 'block' model is overly pessimistic on those. They represent a real opportunity to recover edge with smarter portfolio rules (e.g., open net position rather than first-come-first-serve).

## Block by family pair

- **OB strict blocks OB strict**: 1028 blocks, missed cum_R = 357.83
- **OB strict blocks Sweep reversed (filtered)**: 511 blocks, missed cum_R = 387.7
- **Sweep reversed (filtered) blocks OB strict**: 698 blocks, missed cum_R = 281.41
- **Sweep reversed (filtered) blocks Sweep reversed (filtered)**: 183 blocks, missed cum_R = 159.86

## Block by symbol

- **ES.c.0**: 1224 blocks, missed cum_R = 570.36
- **NQ.c.0**: 1196 blocks, missed cum_R = 616.44

## Mitigations modeled

### A. More symbols (uniform spread hypothetical)

| Symbol multiplier | cum_R | Retention |
|---|---:|---:|
| 2x (4 symbols) | 1730.14 | 67.8% |
| 4x (8 symbols) | 1967.56 | 77.1% |
| 6x (12 symbols) | 2276.40 | 89.2% |

Caveat: this assumes per-family trades distribute uniformly across symbols, which is an upper bound — different symbols have different liquidity / behavior. **The real test is to run OB + Sweep on actual additional symbols** (RTY, YM, MNQ, MES, etc.) and re-measure.

### B. Shorter trade window (free slot earlier)

Currently v8a holds for 240 min. If we cap at N min and keep the same R (conservative — actual R might be slightly worse with shorter hold):

| Window | cum_R | Retention |
|---|---:|---:|
| 60 min | 2101.30 | 82.3% |
| 120 min | 1663.66 | 65.2% |
| 180 min | 1496.65 | 58.6% |

Caveat: this keeps the same per-trade R but shrinks holding time. Actual R under shorter window would need a real backtest run (since exits could happen at different prices).

## Implications for v21 lockfile design

1. If many blocks are opposite-direction, a **net-position rule** (rather than first-come-first-serve) could recover material edge.
2. **More symbols** (4-6x universe) is the most plausible path to 70%+ retention without changing strategy logic.
3. **Tighter trade window** (120 min) is cheap to test in a re-simulation and may recover meaningful retention.
4. **Single-family OB-only paper trade** sidesteps the issue entirely while we sort the above.
