# Macro News Interactions

_Generated `2026-05-17T17:37:10.523543+00:00`._

This report checks whether SMT/PSP/FVG was present before scheduled macro releases, whether those concepts formed around/after the release, and how the first 1m post-release candle high/low performed as data levels.

## Scope

- Macro rows: `18,414`
- Symbols: `ES.c.0, NQ.c.0, YM.c.0`
- Date range: `2015-01-02 15:00:00+00:00` -> `2026-05-12 12:30:00+00:00`
- Concept rows loaded: `{'smt': 1966, 'psp': 10792, 'fvg': 153998}`
- Output matrix: `C:\Users\benbr\BacktestStation\data\ml\anchors\macro_news_interactions.parquet`
- Conditional summary: `C:\Users\benbr\BacktestStation\data\ml\anchors\macro_news_interaction_summary.csv`
- Data high/low stats: `C:\Users\benbr\BacktestStation\data\ml\anchors\macro_news_level_reaction_stats.csv`

## Interpretation

- `prex.*` means the concept was knowable before release. These are safe pre-news context features.
- `postx.*` means the concept occurred around/after release. These answer whether news produced/clustered with the concept, but they are not pre-release model inputs.
- `data_level.*` uses `oc.next_1m.high/low` as the news candle high/low. A later strict break means a future horizon traded beyond that first 1m extreme.

## Concept Timing Flags

| Flag | Rows | Share |
|---|---|---|
| `prex.fvg_known_prior_1d.has` | 11,280 | 61.3% |
| `prex.fvg_known_prior_240m.has` | 11,093 | 60.2% |
| `postx.fvg_event_after_240m.has` | 10,853 | 58.9% |
| `postx.fvg_event_around_60m.has` | 9,811 | 53.3% |
| `prex.psp_known_prior_1d.has` | 8,425 | 45.8% |
| `prex.fvg_known_prior_60m.has` | 7,900 | 42.9% |
| `postx.fvg_event_after_60m.has` | 7,247 | 39.4% |
| `postx.fvg_event_around_15m.has` | 4,141 | 22.5% |
| `prex.smt_known_prior_1d.has` | 3,101 | 16.8% |
| `prex.psp_known_prior_240m.has` | 3,041 | 16.5% |
| `postx.psp_event_after_240m.has` | 2,710 | 14.7% |
| `postx.fvg_event_after_15m.has` | 2,280 | 12.4% |
| `postx.psp_event_around_60m.has` | 1,730 | 9.4% |
| `prex.psp_known_prior_60m.has` | 934 | 5.1% |
| `postx.psp_event_after_60m.has` | 903 | 4.9% |
| `postx.smt_event_after_240m.has` | 343 | 1.9% |
| `postx.psp_event_around_15m.has` | 267 | 1.4% |
| `prex.smt_known_prior_240m.has` | 210 | 1.1% |
| `postx.psp_event_after_15m.has` | 200 | 1.1% |
| `postx.smt_event_around_60m.has` | 121 | 0.7% |
| `prex.smt_known_prior_60m.has` | 48 | 0.3% |
| `postx.smt_event_after_60m.has` | 43 | 0.2% |
| `postx.smt_event_around_15m.has` | 20 | 0.1% |
| `postx.smt_event_after_15m.has` | 16 | 0.1% |

## Top Conditional Macro Outcome Lifts

| Flag | Label | Rows | Rate If True | Rate If False | Lift |
|---|---|---|---|---|---|
| `postx.psp_event_after_15m.has` | `oc.next_60m.closed_inside_pre_60m_range` | 200 | 73.0% | 51.7% | 21.3% |
| `postx.psp_event_around_15m.has` | `oc.next_60m.closed_inside_pre_60m_range` | 267 | 70.0% | 51.6% | 18.4% |
| `postx.fvg_event_after_15m.has` | `oc.next_15m.one_sided_took_pre_60m_low` | 2,279 | 39.7% | 23.6% | 16.1% |
| `postx.smt_event_around_60m.has` | `oc.next_15m.took_pre_60m_high_held_above` | 121 | 31.4% | 15.6% | 15.8% |
| `postx.smt_event_around_60m.has` | `oc.next_15m.one_sided_took_pre_60m_high` | 121 | 43.0% | 28.6% | 14.3% |
| `postx.fvg_event_after_15m.has` | `oc.next_15m.one_sided_took_pre_60m_high` | 2,279 | 40.6% | 27.0% | 13.5% |
| `postx.fvg_event_after_15m.has` | `oc.next_15m.took_pre_60m_low_held_below` | 2,279 | 25.8% | 12.7% | 13.2% |
| `postx.fvg_event_after_15m.has` | `oc.next_15m.took_pre_60m_high_held_above` | 2,279 | 26.1% | 14.2% | 11.9% |
| `postx.fvg_event_after_60m.has` | `oc.next_15m.took_pre_60m_high_held_above` | 7,216 | 21.2% | 12.1% | 9.2% |
| `postx.fvg_event_around_15m.has` | `oc.next_15m.one_sided_took_pre_60m_low` | 4,135 | 32.4% | 23.6% | 8.9% |
| `postx.psp_event_after_60m.has` | `oc.next_240m.close_above_release_ref` | 903 | 61.4% | 53.0% | 8.4% |
| `postx.fvg_event_around_15m.has` | `oc.next_15m.one_sided_took_pre_60m_high` | 4,135 | 34.7% | 27.0% | 7.7% |
| `postx.fvg_event_after_60m.has` | `oc.next_15m.took_pre_60m_low_held_below` | 7,216 | 18.9% | 11.3% | 7.6% |
| `postx.psp_event_around_60m.has` | `oc.next_60m.closed_inside_pre_60m_range` | 1,725 | 58.3% | 51.2% | 7.1% |
| `postx.fvg_event_after_60m.has` | `oc.next_15m.one_sided_took_pre_60m_high` | 7,216 | 33.0% | 25.9% | 7.1% |
| `postx.smt_event_around_60m.has` | `oc.next_5m.range_expanded_2x_pre_15m` | 121 | 12.4% | 5.4% | 6.9% |
| `postx.psp_event_after_240m.has` | `oc.next_240m.close_above_release_ref` | 2,709 | 58.7% | 52.5% | 6.3% |
| `prex.smt_known_prior_240m.has` | `oc.next_15m.one_sided_took_pre_60m_high` | 209 | 34.9% | 28.7% | 6.3% |
| `postx.fvg_event_after_60m.has` | `oc.next_15m.one_sided_took_pre_60m_low` | 7,216 | 29.3% | 23.2% | 6.1% |
| `postx.fvg_event_around_15m.has` | `oc.next_15m.took_pre_60m_low_held_below` | 4,135 | 18.8% | 13.0% | 5.8% |
| `postx.smt_event_after_240m.has` | `oc.next_240m.direction_reversed_from_first_bar` | 342 | 46.8% | 41.0% | 5.8% |
| `postx.fvg_event_around_15m.has` | `oc.next_15m.took_pre_60m_high_held_above` | 4,135 | 20.1% | 14.4% | 5.7% |
| `postx.psp_event_after_15m.has` | `oc.next_240m.direction_reversed_from_first_bar` | 200 | 46.5% | 41.1% | 5.4% |
| `postx.smt_event_around_60m.has` | `oc.next_240m.close_above_release_ref` | 121 | 58.7% | 53.4% | 5.3% |
| `postx.smt_event_after_240m.has` | `oc.next_15m.one_sided_took_pre_60m_high` | 329 | 33.7% | 28.6% | 5.1% |

## Data High / Data Low Overall

| Horizon | Rows | Broke High | Broke Low | Swept Both | Closed Inside | High Rejected | Low Rejected | Avg Range / Data Range |
|---|---|---|---|---|---|---|---|---|
| `next_5m` | 18,414 | 59.4% | 56.5% | 23.0% | 38.3% | 28.2% | 27.6% | 2.23x |
| `next_15m` | 18,414 | 74.9% | 73.3% | 50.6% | 24.1% | 37.4% | 36.5% | 3.74x |
| `next_60m` | 18,414 | 85.0% | 84.0% | 70.8% | 14.2% | 39.9% | 44.9% | 7.36x |
| `next_240m` | 18,414 | 90.0% | 89.4% | 81.0% | 9.6% | 41.8% | 48.7% | 13.04x |
| `next_1d` | 18,414 | 94.6% | 94.3% | 90.4% | 4.2% | 42.6% | 52.0% | 31.99x |

## Data Levels By Macro Family - Next 60m

| Family | Rows | Broke High | Broke Low | Closed Inside | High Rejected | Low Rejected |
|---|---|---|---|---|---|---|
| `scheduled_speech` | 3,378 | 82.4% | 80.9% | 10.9% | 39.0% | 40.8% |
| `labor` | 3,111 | 87.1% | 84.2% | 14.6% | 41.5% | 44.5% |
| `inflation` | 2,333 | 80.8% | 83.1% | 16.8% | 37.7% | 43.5% |
| `survey_pmi` | 2,177 | 85.0% | 86.6% | 13.3% | 39.5% | 46.2% |
| `growth` | 2,175 | 85.0% | 86.4% | 16.0% | 40.3% | 47.3% |
| `housing` | 1,167 | 87.5% | 86.9% | 13.5% | 41.8% | 46.4% |
| `consumer_sentiment` | 1,038 | 85.3% | 82.7% | 14.6% | 40.9% | 45.1% |
| `energy_inventory` | 993 | 87.1% | 87.4% | 14.0% | 40.1% | 48.4% |
| `other_macro` | 704 | 88.4% | 88.2% | 9.7% | 39.8% | 47.3% |
| `fed_policy` | 651 | 87.1% | 76.3% | 18.4% | 35.0% | 47.6% |
| `treasury_supply` | 258 | 84.9% | 81.0% | 15.1% | 43.0% | 42.6% |
| `fed_minutes` | 249 | 92.4% | 82.7% | 21.3% | 41.8% | 54.6% |
| `trade` | 168 | 89.9% | 81.0% | 24.4% | 45.8% | 49.4% |
| `calendar_risk` | 12 | 100.0% | 100.0% | 0.0% | 50.0% | 50.0% |

## Current Read

- This is descriptive performance, not a trade strategy.
- The strongest useful feature candidates are the `prex.*` flags because those are knowable before release.
- The `postx.*` flags are useful for labeling what news created, such as FVG formation after release.
- If you want a stricter ICT-style definition of data high/low, the next build should add first 5m/15m data candle variants too.
