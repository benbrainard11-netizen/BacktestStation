# sizing_v1 — Iteration 1 Results (funded phase)

Generated: 2026-05-28T02:48:54.026541+00:00

Funded-phase simulation: N accounts with staggered start dates,
each run forward up to `sim_max_days`. Model = milk-v1 LightGBM
ensemble. Sizing = fixed 1 contract. Exit = time-only at horizon.

**Headline metric: total $ collected per account (profit + payouts).**

---

## TOPSTEP — 100 accounts

| metric | value |
|---|---|
| survived to end | 34 (34%) |
| blown daily limit | 66 (66%) |
| blown trailing DD | 0 (0%) |
| got ≥1 payout | 1 (1%) |
| mean $ collected | $261 |
| median $ collected | $-734 |
| p25 / p75 | $-1,063 / $604 |
| worst / best | $-2,392 / $21,476 |
| mean payouts/account | 0.01 |
| mean $ paid out | $35 |
| mean trades/account | 8.6 |

### Revenue-rate math

```
Mean $/account over sim window:   $261
If you run 50 funded accounts:     $13,066 expected
Blow rate:                         66%
Payout-reaching rate:              1%
```

**Best account (topstep_50k_042):** started 2022-10-25, collected $21,476, 0 payouts, 23 trades, status=blown_daily

---

## Verdict + next steps

See report narrative. Key v1 finding: time-only exits + tight daily
loss limit → high blow rate. v1.5 levers: per-trade stops, micro
contracts, daily trade caps.
