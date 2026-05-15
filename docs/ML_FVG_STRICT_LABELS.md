# FVG Strict Labels

_Generated `2026-05-15T14:51:15.870506+00:00`._

These labels combine raw FVG mitigation, zone reaction, and post-tap outcomes into stricter reaction targets.
They are appended to `label_columns` only. They are not features.

## Definitions

| Pattern | Meaning |
|---|---|
| `label.strict.tap_wick_rejected` | First FVG tap entered by wick only and closed back outside the gap. |
| `label.strict.partial_touch_rejected` | First tap was a wick reject, did not reach the midpoint, and produced a clean 10-candle thesis move after tap. |
| `label.strict.mid_fill_rejected` | FVG reached midpoint but not full fill, avoided close-through, and produced a 10-candle thesis move after tap. |
| `label.strict.full_fill_rejected_inside` | FVG fully filled but rejected back inside the zone instead of closing through the far side. |
| `label.strict.full_fill_continued_through` | FVG fully filled and later closed through the far side of the zone. |
| `label.strict.no_touch_continuation` | FVG never tapped and made a clean 2x-width thesis move within 50 native candles. |
| `label.strict.forward_<n>c.thesis_1x_clean` | From FVG confirmation, price moved at least 1x FVG width in thesis direction with limited adverse excursion. |
| `label.strict.forward_<n>c.thesis_2x` | From FVG confirmation, price moved at least 2x FVG width in thesis direction. |
| `label.strict.forward_<n>c.failed_1x_against` | From FVG confirmation, adverse excursion reached at least 1x FVG width before a 1x thesis move. |
| `label.strict.forward_<n>c.after_tap_1x_clean` | After first tap, price moved at least 1x FVG width in thesis direction with limited adverse excursion. |
| `label.strict.forward_<n>c.after_tap_2x` | After first tap, price moved at least 2x FVG width in thesis direction. |
| `label.strict.forward_<n>c.after_tap_failed_1x_against` | After first tap, adverse excursion reached at least 1x FVG width before a 1x thesis move. |

## Generated Columns

- Strict label columns: `24`
- Native forward windows: `3, 10, 50` candles

## Overall Rates

| Label | Rows | Positives | Rate |
|---|---|---|---|
| `label.strict.forward_50c.thesis_2x` | 209339 | 178277 | 85.2% |
| `label.strict.forward_50c.after_tap_2x` | 209339 | 157950 | 75.5% |
| `label.strict.full_fill_continued_through` | 209339 | 153911 | 73.5% |
| `label.strict.forward_10c.thesis_2x` | 209339 | 146173 | 69.8% |
| `label.strict.forward_10c.after_tap_2x` | 209339 | 132839 | 63.5% |
| `label.strict.forward_3c.thesis_2x` | 209339 | 112039 | 53.5% |
| `label.strict.forward_3c.after_tap_2x` | 209339 | 104086 | 49.7% |
| `label.strict.tap_wick_rejected` | 209339 | 94657 | 45.2% |
| `label.strict.forward_3c.failed_1x_against` | 209339 | 42076 | 20.1% |
| `label.strict.forward_3c.after_tap_failed_1x_against` | 209339 | 34584 | 16.5% |
| `label.strict.forward_10c.failed_1x_against` | 209339 | 29960 | 14.3% |
| `label.strict.forward_3c.thesis_1x_clean` | 209339 | 27629 | 13.2% |
| `label.strict.forward_10c.after_tap_failed_1x_against` | 209339 | 24923 | 11.9% |
| `label.strict.forward_3c.after_tap_1x_clean` | 209339 | 24409 | 11.7% |
| `label.strict.forward_10c.thesis_1x_clean` | 209339 | 18080 | 8.6% |
| `label.strict.forward_10c.after_tap_1x_clean` | 209339 | 15748 | 7.5% |
| `label.strict.forward_50c.failed_1x_against` | 209339 | 15066 | 7.2% |
| `label.strict.forward_50c.after_tap_failed_1x_against` | 209339 | 13787 | 6.6% |
| `label.strict.no_touch_continuation` | 209339 | 10882 | 5.2% |
| `label.strict.forward_50c.thesis_1x_clean` | 209339 | 9209 | 4.4% |
| `label.strict.forward_50c.after_tap_1x_clean` | 209339 | 8143 | 3.9% |
| `label.strict.partial_touch_rejected` | 209339 | 2941 | 1.4% |
| `label.strict.mid_fill_rejected` | 209339 | 2196 | 1.0% |
| `label.strict.full_fill_rejected_inside` | 209339 | 920 | 0.4% |
