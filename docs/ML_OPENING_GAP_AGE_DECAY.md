# Opening Gap Age Decay

_Generated `2026-05-14T04:23:13.767778+00:00`._

- Source: `C:\Users\benbr\BacktestStation\data\ml\features\ogap.parquet`
- Gap types: `ndog`, `nwog`
- Age buckets use first touch / first full fill inside the 20-day horizon.

## Fill / Touch Rates

| group | rows | 1h touch | 4h touch | 1d touch | 5d touch | 20d touch | 1h fill | 4h fill | 1d fill | 5d fill | 20d fill |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all | 9,438 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 66.5% | 76.9% | 90.8% | 95.2% | 97.4% |
| ndog | 7,815 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 71.1% | 81.4% | 93.2% | 96.4% | 98.0% |
| nwog | 1,623 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 44.4% | 55.1% | 78.9% | 89.6% | 94.5% |
| ndog/gap_down | 4,110 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 70.1% | 80.9% | 94.3% | 97.1% | 98.9% |
| ndog/gap_up | 3,705 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 72.3% | 82.0% | 92.0% | 95.6% | 97.1% |
| nwog/gap_down | 763 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 44.7% | 54.8% | 82.8% | 92.0% | 97.2% |
| nwog/gap_up | 860 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 44.1% | 55.3% | 75.5% | 87.4% | 92.0% |

## Age Bucket Reaction

| event_type | age_bucket | touches | touch_share | fills | fill_share | support_rej | resistance_rej | support_break | resistance_break |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ndog | 0-1h | 7,815 | 100.0% | 5,559 | 71.1% | 29.0% | 34.6% | 8.2% | 8.1% |
| ndog | 1-4h | 0 | 0.0% | 805 | 10.3% | - | - | - | - |
| ndog | 4h-1d | 0 | 0.0% | 920 | 11.8% | - | - | - | - |
| ndog | 1-3d | 0 | 0.0% | 176 | 2.3% | - | - | - | - |
| ndog | 3-7d | 0 | 0.0% | 94 | 1.2% | - | - | - | - |
| ndog | 1-2w | 0 | 0.0% | 74 | 0.9% | - | - | - | - |
| ndog | 2-20d | 0 | 0.0% | 31 | 0.4% | - | - | - | - |
| nwog | 0-1h | 1,623 | 100.0% | 720 | 44.4% | 42.1% | 35.6% | 4.6% | 6.3% |
| nwog | 1-4h | 0 | 0.0% | 174 | 10.7% | - | - | - | - |
| nwog | 4h-1d | 0 | 0.0% | 387 | 23.8% | - | - | - | - |
| nwog | 1-3d | 0 | 0.0% | 127 | 7.8% | - | - | - | - |
| nwog | 3-7d | 0 | 0.0% | 46 | 2.8% | - | - | - | - |
| nwog | 1-2w | 0 | 0.0% | 55 | 3.4% | - | - | - | - |
| nwog | 2-20d | 0 | 0.0% | 24 | 1.5% | - | - | - | - |

## Interpretation

- Higher early touch/fill rates mean the gap is mostly short-lived.
- Later age buckets show whether old gaps keep attracting price.
- Reaction rates are conditional on first touch occurring in that bucket.
- This is descriptive research, not an entry/exit rule.
