# Final 15m Session Close - NQ Targeted Effects

Generated on 2026-05-26 from R2-backed `NQ.c.0` 15-minute bars.

Study window:

```text
2025-05-01 -> 2026-05-01
```

Usable sessions:

```text
243 Globex sessions
```

Local output folder:

```text
data/research/final_15m_session_close_nq_1y_targeted/
```

## Bottom Line

The simple next-day up/down hypothesis stayed weak. The more targeted labels found a few watchlist effects, but nothing strong enough to call a proven edge yet.

Most interesting areas:

- First prior-session liquidity sweep direction.
- Next RTH first 60-minute momentum.
- Certain small context buckets, especially bullish final bias on Fridays and bullish final bias after bearish sessions.

Beginner translation:

```text
The final candle may matter more for "what happens first" than for "where the whole next day closes."
```

## Targeted Labels Tested

- First breakout direction next day: `next_first_liquidity_sweep`.
- Overnight continuation: `next_overnight_continues_final_bias`.
- Opening range behavior: `next_or30_first_break`.
- First liquidity sweep: prior session high swept first versus prior session low swept first.
- Early-session momentum: `next_early_globex_2h_direction` and `next_rth_first_60m_direction`.

All `next_*` columns are outcome labels, not live-entry inputs.

## Targeted Results By Final Close Bucket

| Final close bucket | Count | Overnight continuation | First 2h Globex continuation | RTH first 60m continuation | Prior high swept first | Prior low swept first | OR30 high first | OR30 low first |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| strong_bearish | 50 | 50.0% | 38.0% | 56.0% | 38.0% | 56.0% | 48.0% | 48.0% |
| bearish | 47 | 40.4% | 51.1% | 53.2% | 55.3% | 29.8% | 59.6% | 36.2% |
| middle | 48 | n/a | n/a | n/a | 52.1% | 29.2% | 54.2% | 41.7% |
| bullish | 48 | 62.5% | 47.9% | 60.4% | 47.9% | 41.7% | 54.2% | 45.8% |
| strong_bullish | 50 | 50.0% | 60.0% | 56.0% | 60.0% | 26.0% | 50.0% | 46.0% |

Notes:

- Bullish, but not strong bullish, had the best overnight continuation rate at 62.5%.
- Strong bullish had a 60.0% first two-hour Globex continuation rate and a 60.0% prior-high-swept-first rate.
- Strong bearish leaned toward prior-low-swept-first at 56.0%.
- The bearish bucket surprisingly leaned toward prior-high-swept-first and OR30-high-first. That is a warning that the final candle alone may not be the real driver.

## Statistical Tests

Categorical tests:

| Feature | Outcome | p-value | Effect size | Read |
|---|---|---:|---:|---|
| final_close_bucket | next_first_liquidity_sweep | 0.0665 | 0.174 | Watchlist only |
| final_close_bucket | next_overnight_direction | 0.1148 | 0.175 | Not confirmed |
| final_close_bucket | next_rth_first_60m_direction | 0.1404 | 0.159 | Not confirmed |
| final_close_bias | next_overnight_continues_final_bias | 0.1739 | 0.097 | Not confirmed |
| final_close_bucket | next_or30_first_break | 0.8033 | 0.107 | Not meaningful |

Numeric tests:

| Feature | Numeric outcome | p-value | Read |
|---|---|---:|---|
| final_close_bucket | next_rth_first_60m_return_pts | 0.0887 | Watchlist only |
| final_close_bucket | next_early_globex_2h_return_pts | 0.1591 | Not confirmed |
| final_close_bucket | next_overnight_return_pts | 0.8530 | Not meaningful |
| final_close_bucket | next_return_pts | 0.8730 | Not meaningful |

Important caution:

Some opening-range categories have very small expected cell counts, so the OR30 chi-square result is less reliable. Treat OR30 as descriptive until there is more data or cleaner grouping.

## Contexts Worth Watching

The context table is descriptive. These rows are not proof because they come from many subgroup checks.

| Context | Final bias | Count | Interesting behavior |
|---|---|---:|---|
| Friday | bullish | 22 | RTH first 60m continuation 81.8%; OR30 high first 72.7%; prior high swept first 68.2%. |
| Wednesday | bullish | 23 | Overnight continuation 65.2%; mean overnight return +65.7 pts. |
| Current session direction bearish | bullish | 42 | Overnight continuation 59.5%; RTH first 60m continuation 66.7%; mean overnight return +53.9 pts. |
| Prior session direction bearish | bullish | 48 | Overnight continuation 58.3%; RTH first 60m continuation 64.6%. |
| Prior 20-session low range regime | bullish | 29 | First 2h Globex and RTH first 60m continuation both 69.0%, but mean RTH first 60m return was negative because of downside outliers. |
| Prior 20-session normal range regime | bearish | 31 | RTH first 60m continuation 64.5%; mean RTH first 60m return -15.0 pts. |

Strongest liquidity sweep context:

- If the full current session closed bullish, the next session swept the prior high first about 76% of the time across final candle biases.
- If the full current session closed bearish, the next session swept the prior low first about 69% to 74% of the time across final candle biases.

That suggests the full-session close location may be more important for first liquidity sweep direction than the final 15-minute candle alone.

## Current Research Read

The final 15-minute candle is not a clean standalone direction predictor on this 1-year NQ sample.

Better next hypotheses:

1. Use final candle bias plus full-session close bias for first sweep direction.
2. Test bullish final bias after a bearish session for overnight and RTH first-hour continuation.
3. Test Friday bullish final bias separately, but require more years because `n = 22` is small.
4. Replace OR30 multi-category testing with simpler high-first versus low-first labels to avoid tiny expected cells.
5. Re-run on 3-5 years before promoting anything into a strategy rule.

Focused follow-up design:

- `docs/SESSION_SWEEP_CONTEXT_MBP1_STUDY_DESIGN.md`

## Leakage Check

Safe inputs:

- final candle OHLC and close position
- current completed session OHLC and close position
- day of week
- previous completed session direction/range
- prior 20-session range regime

Research-only outcomes:

- every `next_*` column

Do not build a live strategy that reads `next_*` columns. Those are the answers the study is trying to predict.
