# Opening Gap Level Reactions

_Generated `2026-05-17T00:38:29.027816+00:00`._

This is the first universal level-reaction artifact. It maps NDOG/NWOG
opening-gap outcomes into shared `level.*` and `lr.*` columns so gaps can
later be compared directly against FVGs, order blocks, sweeps, pivots,
and volume-profile levels.

- Source: `C:\Users\benbr\BacktestStation\data\ml\features\ogap.parquet`
- Output: `C:\Users\benbr\BacktestStation\data\ml\levels\opening_gap_level_reactions.parquet`
- Rows: `9,438`
- Columns: `155`

## Counts

| Subtype | Side | Rows |
|---|---|---|
| `ndog` | `gap_down` | 4,110 |
| `ndog` | `gap_up` | 3,705 |
| `nwog` | `gap_down` | 763 |
| `nwog` | `gap_up` | 860 |

## Overall Reaction Rates

| Horizon | Rows | Raw Touch | Meaningful Touch | Partial Touch | Full Fill | Directional Reject | Directional Break | Avg Away / Size |
|---|---|---|---|---|---|---|---|---|
| `next_60m` | 9,438 | 100.0% | 79.3% | 12.7% | 66.5% | 66.1% | 15.4% | 5.15x |
| `next_240m` | 9,438 | 100.0% | 85.9% | 9.0% | 76.9% | 66.1% | 15.4% | 9.70x |
| `next_1d` | 9,438 | 100.0% | 94.3% | 3.6% | 90.8% | 66.1% | 15.4% | 38.96x |
| `next_20d` | 9,438 | 100.0% | 98.7% | 1.3% | 97.4% | 66.1% | 15.4% | 164.96x |

## Meaningful-Touch Age Decay

| Subtype | Side | Age | Rows | Share | Reject | Break | Avg Away / Size |
|---|---|---|---|---|---|---|---|
| `ndog` | `gap_down` | `0-1h` | 3,353 | 81.6% | 58.3% | 18.8% | 201.39x |
| `ndog` | `gap_down` | `1-3d` | 48 | 1.2% | 100.0% | 0.0% | 30.39x |
| `ndog` | `gap_down` | `1-4h` | 311 | 7.6% | 99.0% | 0.0% | 87.75x |
| `ndog` | `gap_down` | `3-7d` | 30 | 0.7% | 100.0% | 0.0% | 75.75x |
| `ndog` | `gap_down` | `4h-1d` | 312 | 7.6% | 99.0% | 0.0% | 67.85x |
| `ndog` | `gap_down` | `7-20d` | 30 | 0.7% | 100.0% | 0.0% | 77.72x |
| `ndog` | `gap_up` | `0-1h` | 3,082 | 83.2% | 53.8% | 20.8% | 206.32x |
| `ndog` | `gap_up` | `1-3d` | 64 | 1.7% | 100.0% | 0.0% | 48.30x |
| `ndog` | `gap_up` | `1-4h` | 204 | 5.5% | 96.1% | 0.0% | 98.36x |
| `ndog` | `gap_up` | `3-7d` | 28 | 0.8% | 96.4% | 0.0% | 52.78x |
| `ndog` | `gap_up` | `4h-1d` | 235 | 6.3% | 99.6% | 0.0% | 64.96x |
| `ndog` | `gap_up` | `7-20d` | 38 | 1.0% | 100.0% | 0.0% | 42.20x |
| `nwog` | `gap_down` | `0-1h` | 479 | 62.8% | 61.2% | 21.3% | 111.13x |
| `nwog` | `gap_down` | `1-3d` | 32 | 4.2% | 100.0% | 0.0% | 9.66x |
| `nwog` | `gap_down` | `1-4h` | 67 | 8.8% | 100.0% | 0.0% | 20.37x |
| `nwog` | `gap_down` | `3-7d` | 14 | 1.8% | 100.0% | 0.0% | 9.89x |
| `nwog` | `gap_down` | `4h-1d` | 138 | 18.1% | 100.0% | 0.0% | 43.40x |
| `nwog` | `gap_down` | `7-20d` | 20 | 2.6% | 100.0% | 0.0% | 17.75x |
| `nwog` | `gap_up` | `0-1h` | 531 | 61.7% | 66.7% | 14.1% | 129.91x |
| `nwog` | `gap_up` | `1-3d` | 50 | 5.8% | 100.0% | 0.0% | 52.26x |
| `nwog` | `gap_up` | `1-4h` | 67 | 7.8% | 100.0% | 0.0% | 24.13x |
| `nwog` | `gap_up` | `3-7d` | 18 | 2.1% | 100.0% | 0.0% | 19.11x |
| `nwog` | `gap_up` | `4h-1d` | 124 | 14.4% | 100.0% | 0.0% | 28.50x |
| `nwog` | `gap_up` | `7-20d` | 36 | 4.2% | 100.0% | 0.0% | 30.87x |

## Columns

- `level.*` columns describe the level at creation time.
- `lr.<horizon>.touched` is raw zone overlap. For opening gaps this is usually trivial at birth.
- `lr.<horizon>.meaningful_touch` means midpoint/full-fill progress and is the field to use for age decay.
- `lr.<horizon>.*` columns describe future reaction labels.
- These are labels/outcomes, not model inputs.

## Why This Matters

This starts the shared level-reaction vocabulary. The next concepts can
reuse the same fields, which lets the RTX training box compare level
families apples-to-apples instead of learning separate custom labels for
every concept.
