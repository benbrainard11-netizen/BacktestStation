# BTC anomaly screen v0 — design window 2017-12 -> 2025-06 (holdout sealed)

## Directional families (net of 60-pt RT cost on flips, bps/day)

            family    n  net_bps_day     p5  h1_bps  h2_bps  consistent
          tsmom_5d 1889        -1.41 -16.60   15.62  -21.18       False
         tsmom_20d 1889         8.86  -6.64   11.35    5.97        True
         tsmom_60d 1889        11.02  -4.89   15.40    5.94        True
  above_50dma_long 1889        16.86   5.57   23.02    9.70        True
     bigday_follow 1889        -4.18  -7.90   -9.54    2.05       False
weekend_gap_follow  383       -13.08 -61.84    7.04  -36.74       False

## Day-of-week (gross, descriptive)
 weekday   n  gross_bps    p5
       0 383       58.2  10.6
       1 388       18.1 -13.8
       2 386       26.3  -6.9
       3 390      -21.0 -52.5
       4 342        9.3 -21.6

## Session buckets (gross, descriptive)
session    n  gross_bps    p5
   asia 1931       -8.7 -15.8
 europe 1930        9.8   3.2
  us_am 1930       -0.5  -7.7
  us_pm 1814       -2.7  -8.3

## Vol persistence: spearman(20d vol, next-5d vol) = 0.32

CANDIDATE bar: p5 > 0 AND consistent across both halves. Anything passing
gets ONE pre-registered config for the sealed holdout. Exploratory screen —
no config optimization performed.