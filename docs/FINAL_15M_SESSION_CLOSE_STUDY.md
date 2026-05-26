# Final 15m Session Close Study

## Beginner Summary

This study tests a simple idea:

> Does the final 15-minute candle of the NQ futures session tell us anything about the next trading session?

It is a research study, not a trading strategy. It does not enter trades. It builds a table where each row is one completed Globex session and asks:

- Where did the final 15-minute candle close?
- What happened in the next Globex session?
- Did the next session continue, sweep liquidity, or break its opening range first?
- Are the differences large enough to matter statistically?

## 1. Final 15m Candle Definition

Default session: CME Globex day.

For NQ futures, this repo defines a Globex day as:

```text
18:00 ET previous calendar day -> 17:00 ET current calendar day
```

So the final 15-minute candle is:

```text
16:45 ET -> 17:00 ET
```

The candle timestamp in the warehouse is the candle start time. For example, during daylight saving time:

```text
16:45 ET = 20:45 UTC
17:00 ET = 21:00 UTC
```

If you meant the regular cash-market close instead, that is a different variant:

```text
15:45 ET -> 16:00 ET
```

This first version uses the official futures session close at 17:00 ET.

Code:

- `backend/app/research/sessions.py`
- `backend/app/research/final_15m_session_close.py`

## 2. Close Position Math

The study measures where the final candle closed inside its own high-low range:

```text
close_position = (close - low) / (high - low)
```

Interpretation:

```text
0.00 = closed at the low
0.50 = closed in the middle
1.00 = closed at the high
```

If the candle has no range, the value is `undefined`.

## 3. Close Categories

Five-bucket version:

| Close position | Category |
|---:|---|
| `0.00` to `0.20` | `strong_bearish` |
| `>0.20` to `0.40` | `bearish` |
| `>0.40` to `<0.60` | `middle` |
| `>=0.60` to `<0.80` | `bullish` |
| `>=0.80` to `1.00` | `strong_bullish` |

Simple bias version:

| Close position | Bias |
|---:|---|
| `<=0.40` | `bearish` |
| `>0.40` and `<0.60` | `neutral` |
| `>=0.60` | `bullish` |

## 4. Next-Day Outcome Labels

For each session, the outcome is measured on the next completed Globex session only.

Main labels:

- `next_direction`: next session close minus next session open.
- `next_close_position`: where the next session closed inside its own full-session range.
- `next_close_bucket`: bucketed version of `next_close_position`.
- `next_took_prior_session_high`: whether next session traded above the current session high.
- `next_took_prior_session_low`: whether next session traded below the current session low.
- `next_first_break`: whether next session broke the prior high first, prior low first, both in the same 15m bar, or neither.
- `next_first_liquidity_sweep`: trader-friendly name for the same prior-session high/low sweep test.
- `next_first_sweep_closed_back_inside_prior_range`: whether the first sweep later closed back inside the prior range.
- `next_gap_from_session_close_pts`: next session open minus current session close.
- `next_overnight_return_pts`: next Globex open to next RTH open at 09:30 ET.
- `next_overnight_direction`: bullish, bearish, or flat for that overnight window.
- `next_overnight_continues_final_bias`: whether overnight direction matched the final candle bias.
- `next_early_globex_2h_return_pts`: first two hours after the next Globex open.
- `next_early_globex_2h_direction`: bullish, bearish, or flat for the first two Globex hours.
- `next_or30_*`: next RTH 09:30-10:00 ET opening range stats.
- `next_or30_first_break`: whether price broke the opening range high first or low first after 10:00 ET.
- `next_rth_first_60m_return_pts`: next RTH 09:30-10:30 ET move.
- `next_rth_first_60m_direction`: bullish, bearish, or flat for the first RTH hour.
- `next_mfe_up_pts`: next session high minus next session open.
- `next_mae_down_pts`: next session open minus next session low.
- `next_range_vs_current_range`: next session range divided by current session range.

These are outcome columns. They are the answers, not inputs for a live decision.

## 5. Context And Regime Columns

The study also adds context columns to ask whether the final candle matters more in certain conditions.

Safe context columns:

- `day_name_et`: Monday, Tuesday, etc. using the session close date.
- `session_direction`: whether the current completed Globex session closed up or down.
- `session_close_position`: where the current session closed in its full-session range.
- `session_close_bucket` and `session_close_bias`: bucketed versions of session close position.
- `final_body_direction`: whether the final 15m candle body closed up or down.
- `final_body_frac_of_range`: final candle body size divided by final candle range.
- `final_range_frac_of_session`: final candle range divided by full session range.
- `prior_session_direction`: previous completed session direction.
- `prior_session_range_pts`: previous completed session range.
- `prior20_session_range_percentile`: current session range versus the prior 20 completed sessions.
- `prior20_range_regime`: `low_range`, `normal_range`, `high_range`, or `unknown`.

The rolling regime columns use prior sessions only. They do not peek into the next session.

## 6. Lookahead Rules

Safe feature columns:

- current session OHLC
- final 15m candle OHLC
- final close position
- final close category
- current-session context/regime columns listed above
- prior-session context/regime columns listed above

Outcome columns:

- anything beginning with `next_`

The study groups future outcomes by current-session close category. It must never use `next_*` columns as strategy inputs.

## 7. How To Run

From the backend folder:

```powershell
.\.venv\Scripts\python.exe -m app.cli.final_15m_session_close_study `
  --symbol NQ.c.0 `
  --start 2025-05-01 `
  --end 2026-05-01 `
  --output-dir ..\data\research\final_15m_session_close_nq_1y
```

Output files:

```text
rows.csv
close_bucket_distribution.csv
close_bias_distribution.csv
bucket_stats.csv
targeted_effect_stats.csv
context_effects.csv
categorical_tests.csv
numeric_tests.csv
summary.json
```

`data/` is gitignored, so large generated study outputs stay local.

## 8. Output Tables

Important output files:

- `rows.csv`: one row per completed session, with all features, contexts, and next-session labels.
- `bucket_stats.csv`: broad next-day direction, return, MFE/MAE, and prior high/low break stats by final close bucket.
- `targeted_effect_stats.csv`: overnight, first two Globex hours, RTH first hour, first liquidity sweep, and opening range behavior by final close bucket.
- `context_effects.csv`: the same targeted effects split by day of week, session direction, session close bias, prior session direction, and prior 20-session range regime.
- `categorical_tests.csv`: chi-square tests for categorical labels.
- `numeric_tests.csv`: Kruskal-Wallis tests for numeric labels.

## 9. Statistical Checks

The CLI runs:

- Chi-square tests for category-vs-category relationships.
- Cramer's V effect size for categorical relationships.
- Kruskal-Wallis tests for numeric outcome differences across close buckets.

Beginner interpretation:

- A small p-value says the table probably is not random noise.
- Effect size says whether the difference is actually meaningful.
- A tiny p-value with tiny effect size may still be useless for trading.
- Multiple tests increase false-positive risk, so any promising result needs out-of-sample validation.

## 10. Files Added

- `backend/app/research/final_15m_session_close.py`
- `backend/app/cli/final_15m_session_close_study.py`
- `backend/tests/test_final_15m_session_close.py`
- `docs/FINAL_15M_SESSION_CLOSE_STUDY.md`

Latest NQ 1-year result summary:

- `docs/FINAL_15M_SESSION_CLOSE_NQ_1Y_RESULTS.md`
- `docs/FINAL_15M_SESSION_CLOSE_NQ_TARGETED_RESULTS.md`
