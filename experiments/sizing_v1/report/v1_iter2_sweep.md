# sizing_v1 — Iteration 2 config sweep (funded phase)

Firm: topstep $50K, 100 accounts per config, staggered starts.
Model = milk-v1 LightGBM ensemble. Threshold 0.45.

| contract | n | stop$ | survive% | payout% | mean $ | median $ | best $ | mean trades |
|---|---|---|---|---|---|---|---|---|
| mini | 1 | 0 | 34% | 1% | $261 | $-734 | $21,476 | 9 |
| mini | 1 | 400 | 65% | 0% | $-56 | $-681 | $3,903 | 10 |
| mini | 1 | 800 | 58% | 0% | $-162 | $-826 | $11,130 | 6 |
| micro | 1 | 0 | 100% | 0% | $-411 | $-571 | $2,637 | 56 |
| micro | 5 | 0 | 38% | 4% | $-142 | $-517 | $10,218 | 14 |
| micro | 10 | 0 | 36% | 1% | $179 | $-779 | $21,166 | 8 |
| micro | 5 | 400 | 38% | 4% | $-151 | $-517 | $10,218 | 14 |
| micro | 10 | 400 | 36% | 1% | $179 | $-779 | $21,166 | 8 |
| micro | 20 | 400 | 12% | 4% | $403 | $-825 | $21,780 | 5 |

**Read:** want high survive% AND high payout% AND positive mean $.
Micros reduce per-trade risk 10x so the $1k daily limit is far
harder to breach; more contracts scale the size back up.
