# Final 15m Session Close Study

## Beginner Summary

This study tests a simple idea:

> Does the final 15-minute candle of the NQ futures session tell us anything about the next trading session?

It is a research study, not a trading strategy. It does not enter trades. It builds a table where each row is one completed Globex session and asks:

- Where did the final 15-minute candle close?
- What happened in the next Globex session?
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
- `next_mfe_up_pts`: next session high minus next session open.
- `next_mae_down_pts`: next session open minus next session low.
- `next_range_vs_current_range`: next session range divided by current session range.

These are outcome columns. They are the answers, not inputs for a live decision.

## 5. Lookahead Rules

Safe feature columns:

- current session OHLC
- final 15m candle OHLC
- final close position
- final close category

Outcome columns:

- anything beginning with `next_`

The study groups future outcomes by current-session close category. It must never use `next_*` columns as strategy inputs.

## 6. How To Run

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
categorical_tests.csv
numeric_tests.csv
summary.json
```

`data/` is gitignored, so large generated study outputs stay local.

## 7. Statistical Checks

The CLI runs:

- Chi-square tests for category-vs-category relationships.
- Cramer's V effect size for categorical relationships.
- Kruskal-Wallis tests for numeric outcome differences across close buckets.

Beginner interpretation:

- A small p-value says the table probably is not random noise.
- Effect size says whether the difference is actually meaningful.
- A tiny p-value with tiny effect size may still be useless for trading.
- Multiple tests increase false-positive risk, so any promising result needs out-of-sample validation.

## 8. Files Added

- `backend/app/research/final_15m_session_close.py`
- `backend/app/cli/final_15m_session_close_study.py`
- `backend/tests/test_final_15m_session_close.py`
- `docs/FINAL_15M_SESSION_CLOSE_STUDY.md`

Latest NQ 1-year result summary:

- `docs/FINAL_15M_SESSION_CLOSE_NQ_1Y_RESULTS.md`
