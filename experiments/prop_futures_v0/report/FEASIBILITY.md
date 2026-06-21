# prop_futures_v0 — Phase A FEASIBILITY (instrument tradeability scorecard)

**Date:** 2026-06-20
**Question:** Across the 31 CME instruments we hold MBP-1 data for, which clear the prop
day-flat scale/cost bar — and which are the 1–3 finalists worth a Phase-C edge build?

The Phase-A scorecard is **descriptive** (it samples the whole window, no sealing) — it is a
liquidity/cost/range screen, *not* an edge test. Sealing/holdout discipline applies only to
Phase-C edge claims (see `README.md`).

## How to read the scorecard

- **`range_to_spread` is the headline tradeability metric** — room (median daily range, ticks)
  per unit of friction (median spread, ticks). High = the move pays for the cost wall; low =
  the cost wall eats the edge before it starts. This is the metric that killed BTC
  (`range_to_spread` 41.9 only because the $-move is huge, but $200 round-trip friction).
- **`spread_usd_med`** is the dollar friction per side at the touch (full-size contract).
- **`daily_range_usd_med`** is full-size; **divide by 10 for the micro** (MES/MNQ/MYM/M2K/MCL/MGC),
  which is the actual prop vehicle. The dollar-fit reasoning below is done at micro scale.
- **`tob_depth_med`** = contracts resting at the touch (size-impact proxy).
- Metals rows (GC/SI/HG/PL/PA) carry **STALE-BOOK-INFLATED** raw `spread_ticks_med`; their
  `range_to_spread` is computed from the realistic *trade-tape-bounce* effective spread (noted
  per row). Their `trades_per_min` / `tob_depth=1` come from a sparse event-filtered mirror and
  are **valid for ranking only**, not as absolute liquidity.
- FX Asian/European-session pairs (6A/6B/6C/6J, partly 6E) show artificially low RTH
  `trades_per_min` because the common 09:30–16:00 ET window catches their *quiet* hours.

## Ranked scorecard (all 31, by prop_score)

| # | symbol | class | prop_score | range_to_spread | spread_usd_med | daily_range_usd_med | tob_depth_med | trades_per_min_med | spread_ticks_med |
|---|--------|-------|-----------:|----------------:|---------------:|--------------------:|--------------:|-------------------:|-----------------:|
| 1 | **ES** | index | 0.907 | 233.0 | 12.50 | 2,912.5 | 15.5 | 865.22 | 1.0 |
| 2 | **RTY** | index | 0.857 | **398.0** | 5.00 | 1,990.0 | 3.0 | 187.01 | 1.0 |
| 3 | NQ | index | 0.807 | 356.8 | 12.50 | 4,460.0 | 1.5 | 669.50 | 2.5 |
| 4 | YM | index | 0.770 | 195.5 | 10.00 | 1,955.0 | 2.0 | 109.44 | 2.0 |
| 5 | **CL** | energy | 0.737 | 99.0 | 10.00 | 990.0 | 4.0 | 85.33 | 1.0 |
| 6 | **NG** | energy | 0.713 | 102.0 | 10.00 | 1,020.0 | 3.0 | 53.94 | 1.0 |
| 7 | MBT | crypto | 0.683 | 123.7 | 1.50 | 185.5 | 1.0 | 38.68 | 3.0 |
| 8 | ZS | grains | 0.637 | 45.0 | 12.50 | 562.5 | 15.5 | 30.06 | 1.0 |
| 9 | 6N | fx | 0.590 | 52.5 | 10.00 | 525.0 | 7.5 | 9.03 | 1.0 |
| 10 | ZF | rates | 0.583 | 20.0 | 7.81 | 156.25 | 424.5 | 56.34 | 1.0 |
| 11 | ZW | grains | 0.567 | 36.0 | 12.50 | 450.0 | 18.5 | 18.78 | 1.0 |
| 12 | 6S | fx | 0.560 | 51.5 | 25.00 | 1,287.5 | 2.5 | 12.49 | 2.0 |
| 13 | ZN | rates | 0.533 | 14.5 | 15.625 | 226.56 | 877.5 | 81.87 | 1.0 |
| 14 | ZC | grains | 0.530 | 20.5 | 12.50 | 256.25 | 104.5 | 22.72 | 1.0 |
| 15 | ZB | rates | 0.527 | 15.5 | 31.25 | 484.38 | 209.5 | 31.30 | 1.0 |
| 16 | ETH | crypto | 0.497 | 45.0 | 75.00 | 3,375.0 | 1.0 | 11.15 | 3.0 |
| 17 | HO | energy | 0.490 | 70.5 | 29.40 | 2,072.7 | 1.0 | 21.01 | 7.0 |
| 18 | ZT | rates | 0.490 | 14.5 | 7.81 | 113.28 | 419.5 | 25.11 | 1.0 |
| 19 | GC | metals | 0.483 | 169.5† | 8,350† | 1,695.0 | 1.0 | 0.035 | 835† |
| 20 | BTC | crypto | 0.430 | 41.9 | 200.00 | 8,387.5 | 1.0 | 9.62 | 8.0 |
| 21 | HG | metals | 0.427 | 62.5† | 5,950† | 781.25 | 1.0 | 0.041 | 476† |
| 22 | RB | energy | 0.360 | 36.3 | 33.60 | 1,220.1 | 1.0 | 19.64 | 8.0 |
| 23 | BZ | energy | 0.340 | 44.8 | 25.00 | 1,120.0 | 1.0 | 9.40 | 2.5 |
| 24 | 6B | fx | 0.310 | 14.2 | 18.75 | 265.63 | 15.5 | 0.106 | 3.0 |
| 25 | 6E | fx | 0.307 | 27.0 | 15.625 | 421.88 | 1.0 | 0.567 | 2.5 |
| 26 | SI | metals | 0.253 | 32.0† | 14,850† | 1,600.0 | 1.0 | 0.033 | 594† |
| 27 | PL | metals | 0.253 | 30.25† | 6,300† | 605.0 | 1.0 | 0.003 | 1260† |
| 28 | 6A | fx | 0.250 | 13.2 | 30.00 | 395.0 | 10.0 | 0.090 | 3.0 |
| 29 | 6C | fx | 0.250 | 11.0 | 20.00 | 220.0 | 13.0 | 0.104 | 2.0 |
| 30 | 6J | fx | 0.193 | 14.3 | 18.75 | 268.75 | 1.0 | 0.183 | 3.0 |
| 31 | PA | metals | 0.167 | 15.0† | 2,785† | 150.0 | 1.0 | 0.005 | 278.5† |

† Metals raw book spread is **stale-book-inflated**; `range_to_spread` uses the realistic
trade-tape-bounce effective spread (GC/HG/PA ≈ 1t, SI ≈ 2t, PL ≈ 4t). All metals liquidity
numbers are sparse-mirror, ranking-only.

## Prop-rule summary (the day-flat reality, set before any result)

- **DAY-FLAT IS UNIVERSAL (corrected 2026-06-20).** All five audited firms now force flat-by-close
  (Topstep 3:10 PM CT, Tradeify 4:59 PM EST, TPT/Apex ~5:00 PM ET). The prior "Topstep allows
  overnight" note is **stale/wrong** for 2026. **There is no overnight lane** — this is why the
  lab's one robust edge (energy-RV cointegration, multi-day) is disqualified everywhere.
- **Micros allowed at all five firms (10:1 sizing on TopstepX/TPT).** Small-tick-value micros
  (MES/MNQ/MYM/M2K/MCL/MGC) are the natural prop vehicles; full-size $ in the scorecard ÷10.
- **Honest cost wall is the FIRST filter** — spread + 1-tick slip + commission, stressed, per
  flip. It already killed `btc_edge_v0` (9-tick BTC spread) and `level_scalp_v0` (adverse
  selection −2.7t/fill). Thin-book / wide-spread instruments are structurally out before any
  edge test.
- **News heterogeneity drives instrument choice.** Tradeify = ZERO news restrictions (best for
  event-driven). TPT *funded* forces flat around FOMC/NFP **and crude-oil inventories for crude
  positions** → a CL edge collides with TPT-funded. Apex bans two-sided news gambling but allows
  directional news trades.
- **Automation:** TPT bans bots entirely → excluded from an automated fleet. Design for
  Apex/Topstep/MFFU/Tradeify; treat TPT as discretionary-only.
- **VERIFY-before-trading halts:** Apex reportedly halted ALL metals (~Mar 14 2026, official page
  403'd — UNCONFIRMED); MFFU reportedly restricted gold/silver/copper/platinum/**natural gas**
  (~Feb 2026). Metals/NG availability is firm-specific and in flux.

## Dead-ends respected (do NOT re-chase)

- **CME BTC intraday** — `btc_edge_v0` holdout FAILED (cost wall + drift-as-alpha). Screen-derived
  holdout SPENT.
- **Energy-RV cointegration** — the lab's robust edge, but **multi-day → not day-flat-compatible**
  on any firm. Cannot be naively intraday-truncated.
- **Index ORDERFLOW (Mira reclaim)** — exposed as look-ahead (feature window watched each trade's
  first minute). Implementable expectancy −0.05..−0.13 R. The index complex's one apparent
  intraday edge is dead. (Bar-only intraday on the index complex is *not* killed the same way.)
- **Minutes-scale microstructure / level-scalp** — NULL at registered spec (`level_scalp_v0`),
  5 honest constructions dead; sim-fill is also a compliance risk.
- **Options/gamma regime gate** — NULL across 5 cuts; reusable as a FEATURE only.

## Finalist selection (1–3) and rationale

Filters applied, in order: (1) prop-allowed + day-flat-viable, (2) not on a dead-end, (3)
`range_to_spread` clears the cost wall, (4) micro $-economics fit a ~50k eval, (5) prefer a real
cross-asset/own-series predictive hook, (6) avoid the index complex unless it *dominates*.

### Finalist 1 — CL (crude) via **MCL** (micro). PRIMARY.
- **Top non-index** prop_score 0.737; `range_to_spread` **99** — best room-vs-friction of the
  liquid energy group; tightest energy book (1-tick spread = $10 full / **$1 MCL**, ~4 at touch,
  ~85 trades/min).
- **Dollar fit (MCL):** full daily range $990 → **$99/day micro**. A 30-tick MCL stop = **$30**;
  the daily-loss limit ($1.1k) holds ~36 such MCL stops, so an honest multi-R day fits with deep
  room to scale R. Range ÷ stop ≈ 3.3R/day at 1 lot, scalable.
- **The decisive hook:** CL carries the **only genuine predictive structure found in the entire
  cross-asset study** — its *own* 10-min momentum (AR2 **+0.16**, the single largest predictive
  signal across all 31 symbols) plus a VIX prior-close **vol-regime** sort (rank-IC +0.10,
  non-directional → sizing/gate). No *cross-asset* lead exists, but the own-series + vol-gate combo
  is a clean, pre-registerable day-flat family.
- **Caveat (built into design):** TPT *funded* restricts crude around inventory reports → design
  for **Tradeify (no news rules) / Topstep / Apex / MFFU**, and gate around EIA windows.

### Finalist 2 — RTY (Russell 2000) via **M2K** (micro). The dominant-metric pick.
- **`range_to_spread` = 398 — the highest of ALL 31 instruments**, on a 1-tick spread that is the
  *lowest absolute dollar friction* in the set ($5 full / **$0.50 M2K**). This is the one place an
  index row is admitted under the brief's "unless it clearly dominates" clause — on the headline
  tradeability metric it does, by a wide margin.
- **Why it's not the dead index edge:** the Mira look-ahead death was an **MBO orderflow** edge on
  ES/NQ. RTY is the *least-arbed* corner of the index complex (small-cap, thinner participation),
  and the proposed family is **bar-only vol-gated ORB** — it never touches the dead orderflow
  construction. The lab's ONE validated forecast (realized vol → forward range, corr ~0.52) is the
  engine, and the index complex is "the cleanest tape to test a fresh look-ahead-free day-flat
  construction" (recommended_focus_classes).
- **Dollar fit (M2K):** full range $1990 → **$199/day micro**; a 40-tick M2K stop = $20 → ~10R of
  daily room at 1 lot, scales cleanly inside the $1.1k/$2.5k budget.
- **Honest risk flagged:** it *is* the over-arbed complex the brief wants to escape; thin touch
  (~3) means size has impact. Held as #2, not #1, for that reason.

### Finalist 3 — NG (natural gas). The un-arbed wildcard (subordinate).
- **`range_to_spread` 102 — highest of the liquid group**, 1-tick spread ($10 / micro $1), ~54
  trades/min, ~3 at touch. Genuinely **idiosyncratic** (weather/storage-driven) → the *least*
  arbed of any liquid finalist, which is exactly the "escape the over-mined complex" mandate.
- **Dollar fit:** full range $1020 → ~$102/day micro; comparable economics to CL.
- **Why subordinate:** (a) **NO cross-asset lead and no own-series momentum hook** — the
  cross-asset study returned a flat NULL for NG (only a faint, underpowered VIX vol-scaling link);
  (b) **firm-availability risk** — MFFU/Apex reportedly restricted NG (~Feb 2026), and there is no
  clean micro-NG at every firm. Carried as the third finalist to keep an un-arbed shot alive, but
  its only conditioning hook is the VIX vol-scaling gate.

**One-line verdict:** Build CL/MCL first (best non-index economics + the one real predictive
feature in the study), RTY/M2K second (dominant range-to-spread, bar-only ORB that sidesteps the
dead orderflow edge), NG third (un-arbed but no lead and firm-availability risk).

See `OPPORTUNITY_MAP.md` for per-finalist cross-asset evidence and the Phase-C families.
