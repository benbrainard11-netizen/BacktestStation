# btc_edge_v0 — is there exploitable structure in CME BTC futures at hours-to-days?

**Question:** the "easier edge in BTC" claim, tested honestly on the venue Ben can
actually trade (CME BTC futures via prop accounts), at horizons where the measured
cost wall (9-tick spread, 2-lot book — see level_scalp_v0 arena probe) doesn't
dominate: holds of hours to days, ~1 round trip per day or less.

**Status:** screen running 2026-06-12. Exploratory by construction.

## Discipline (set before any result was seen)

- **HOLDOUT: 2025-06-10 → 2026-06-09 — SEALED.** The screen reads 2017-12 → 2025-06-09
  only. Anything interesting gets ONE pre-registered config tested on the holdout,
  logged win or lose in this README.
- **Pre-listed families** (the documented BTC anomalies — nothing added after looking):
  1. TSMOM: sign of past {5, 20, 60}-day return → next-day return
  2. Day-of-week effects
  3. Session-bucket seasonality (Asia / Europe / US-AM / US-PM, ET)
  4. Big-day follow-through: |ret| > 2× 20d vol → next-day same-sign drift
  5. Weekend gap (Fri 17:00 close → Sun 18:00 reopen): follow vs fade
  6. Vol persistence: 20d realized vol → next-5d realized vol (sizing input, not direction)
  7. Trend-state drift split: above/below 50d MA
- **Stats:** week-block bootstrap p5; an effect is a CANDIDATE only if it also holds
  with the same sign in BOTH halves (2017-12→2021-12 and 2022-01→2025-06) — BTC's
  regimes changed too much for full-sample-only claims.
- **Costs:** taker round trip = 12 ticks = 60 points (measured spread + slip +
  commission, stressed), charged in bps of price at trade time, applied per implied
  position flip. No frictionless numbers reported.

## Data

`data/btc_1m.parquet` — CME BTC.c.0 1m bars 2017-12→2026-06 (Databento, scratch pull;
proper lake ingest via the 247 box if the module survives). Trading-day convention =
CME Globex (18:00 ET roll), same as the rest of the lab.

## HOLDOUT SHOT #1 — LOGGED 2026-06-12: FAIL

Config: above_50dma_long (the only screen survivor; pre-registered, zero tuning).
Holdout 2025-06-10 -> 2026-06-09: net −3.3 bps/day, cumulative −8.4%, week-block
p25 −8.2. Bar (mean > 0 AND p25 > 0): FAILED.

The diagnosis is in the context numbers: design-window buy-and-hold was +18.3 bps/day
while the "strategy" made +16.9 — the filter was riding BTC's 2017–2025 drift, not
generating alpha. The holdout year was BTC's first sustained bear in the sample
(buy-and-hold −47.3%); the filter did its DEFENSIVE job (−8.4% vs −47.3%, in position
only 43% of days) but absolute edge = none. The screen's two-halves consistency check
passed only because both halves were net-up regimes.

Verdict: "easier edge in BTC" on the prop-tradeable venue = BTC's historical drift
wearing a trend filter. Module's screen-derived holdout shot is SPENT; any future
claim from this screen (e.g. the unconfirmed Monday effect, gross +58 bps p5 +10.6)
requires NEW calendar data. The trend filter retains value as a defensive overlay IF
one wanted BTC beta — that is an allocation choice, not an edge.
