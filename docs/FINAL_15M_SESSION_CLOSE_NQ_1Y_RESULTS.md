# Final 15m Session Close - NQ 1-Year Results

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
data/research/final_15m_session_close_nq_1y/
```

## Bottom Line

In this first 1-year NQ test, the final 15-minute Globex candle close position did **not** show a statistically meaningful relationship with next-session bullish/bearish direction.

The closest signal was `final_close_bucket` versus `next_first_break`, with `p = 0.0665` and Cramer's V `0.174`. That is interesting enough to watch, but it is not strong enough to treat as an edge.

Beginner translation:

```text
The idea is testable, but this first version does not prove it works.
```

## Close Bucket Distribution

| Final close bucket | Count | Percent |
|---|---:|---:|
| strong_bearish | 50 | 20.6% |
| bearish | 47 | 19.3% |
| middle | 48 | 19.8% |
| bullish | 48 | 19.8% |
| strong_bullish | 50 | 20.6% |

The buckets are very balanced, which is good for analysis.

## Bias Distribution

| Final close bias | Count | Percent |
|---|---:|---:|
| bearish | 97 | 39.9% |
| neutral | 48 | 19.8% |
| bullish | 98 | 40.3% |

## Outcome By Final Close Bucket

| Final close bucket | Count | Next bullish | Next bearish | Mean next return | Median next return | Prior high first | Prior low first |
|---|---:|---:|---:|---:|---:|---:|---:|
| strong_bearish | 50 | 50.0% | 50.0% | 3.2 pts | -1.4 pts | 38.0% | 56.0% |
| bearish | 47 | 53.2% | 46.8% | 46.8 pts | 20.5 pts | 55.3% | 29.8% |
| middle | 48 | 60.4% | 39.6% | 35.6 pts | 70.4 pts | 52.1% | 29.2% |
| bullish | 48 | 62.5% | 37.5% | 44.6 pts | 47.0 pts | 47.9% | 41.7% |
| strong_bullish | 50 | 48.0% | 52.0% | 17.0 pts | -7.1 pts | 60.0% | 26.0% |

Important observation:

Strong bullish final candles were **not** followed by the highest next-day bullish rate. Strong bearish final candles were also basically 50/50. That weakens the simple version of the hypothesis.

## Statistical Tests

| Feature | Outcome | Test | p-value | Effect size | Read |
|---|---|---|---:|---:|---|
| final_close_bucket | next_direction | chi-square | 0.5239 | 0.115 | Not meaningful |
| final_close_bias | next_direction | chi-square | 0.5979 | 0.065 | Not meaningful |
| final_close_bucket | next_first_break | chi-square | 0.0665 | 0.174 | Watchlist only |
| final_close_bucket | next_close_bucket | chi-square | 0.6658 | 0.116 | Not meaningful |
| final_close_bias | next_took_prior_session_high | chi-square | 0.6472 | 0.060 | Not meaningful |
| final_close_bias | next_took_prior_session_low | chi-square | 0.3469 | 0.093 | Not meaningful |

Numeric tests:

| Feature | Numeric outcome | Test | p-value | Read |
|---|---|---|---:|---|
| final_close_bucket | next_return_pts | Kruskal-Wallis | 0.8730 | Not meaningful |
| final_close_bucket | next_close_position | Kruskal-Wallis | 0.7146 | Not meaningful |
| final_close_bucket | next_mfe_up_pts | Kruskal-Wallis | 0.3605 | Not meaningful |
| final_close_bucket | next_mae_down_pts | Kruskal-Wallis | 0.4665 | Not meaningful |

## Current Interpretation

The simple close-position idea does not currently look like a standalone next-day direction predictor.

Possible next variants worth testing:

1. Use the RTH cash close candle instead of the Globex 17:00 ET close.
2. Split by day of week.
3. Split by volatility regime.
4. Split by whether the session closed above/below VWAP or prior day levels.
5. Test continuation versus reversal separately.
6. Run a longer 5-10 year study on 1-minute bars.

## Data Leakage Check

Feature columns use the current completed session only:

- final candle open/high/low/close
- final close position
- final close bucket
- final close bias

Outcome columns start with `next_` and use only the following Globex session.

Do not train or trade on `next_*` columns. Those are labels.
