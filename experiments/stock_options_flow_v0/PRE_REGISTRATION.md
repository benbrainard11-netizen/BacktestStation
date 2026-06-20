# stock_options_flow_v0 — pre-registration

Status: **DRAFT, awaiting go** (2026-06-19). Nothing pulled, nothing fit. Lock before building.

## North star
A high-return, low-capacity single-stock options strategy. Tiny size → we can fish the
inefficient mid-tier (high-options-activity, high-IV, retail-heavy names) where dealer-positioning
effects are strong and under-arbitraged. Express convex (long options) for fat right-tail wins.

## Hypothesis (forecast-first, ONE shot)
**Single-stock dealer gamma positioning predicts next-day stock behavior — vol and direction —
*incrementally over price and IV alone*.**

Mechanism (structural, not a mined correlation): when dealers are **short gamma** (net negative GEX)
they hedge *with* the move → vol expands, moves trend/extend. When **long gamma** (net positive GEX)
they hedge *against* the move → vol suppressed, price mean-reverts toward / pins to gamma walls.

## Primary metric + baseline (this is the bar)
PRIMARY = does the gamma signal beat a **price+IV-only baseline** out-of-sample, on a sealed holdout.
Two registered reads, both vs baseline:
1. **Vol read:** rank-IC of (net-GEX sign & magnitude, distance-to-gamma-flip) vs **next-day realized
   vol**, measured as Δ over a baseline that forecasts realized vol from {past realized vol, ATM IV}.
   GEX must add beyond IV — IV already prices expected vol; the claim is GEX refines *when* it lands.
2. **Direction read:** rank-IC of (signed distance to call-wall/put-wall, GEX sign) vs **next-day
   stock return**, Δ over a baseline of {past return, past vol} (momentum/reversal only).

Edge = the **incremental** IC over baseline is positive and survives the holdout. Not the raw IC.

## Expression stages (do not skip ahead)
- **v0 — PREDICT only.** Establish the signal beats baseline OOS. No trading, no fills. Cheapest kill.
- **v1 — trade the UNDERLYING.** Regime-conditioned directional / mean-reversion, honest stop-vs-target
  fills (CLAUDE.md rule 8). Confirms the signal is tradeable before paying option spreads.
- **v2 — CONVEX options expression** (the "huge wins" version). Short-gamma regime → buy
  straddles/strangles/directional options for cheap convexity ahead of the vol expansion. **Honest
  per-contract bid/ask fills + theta decay, no post-hoc strike/expiry selection.** This stage is the
  most mirage-prone thing in the repo — it only runs if v0 + v1 are green.

## Universe (frozen, return-agnostic selection)
Pilot = ~30 names chosen by **options activity / tradeable option liquidity only** (return-agnostic, so
no name-selection look-ahead): high-IV, high-options-OI mid-tier + a few mega-caps as a control, **plus
delisted names** for survivorship realism (ThetaData retains them — verified SIVB options through 2024-01).
Frozen list lives in `universe_pilot.txt`. The production universe rule (later) = point-in-time top-N by
trailing options dollar-volume. Hold out by **TIME**, not by name, so the same names appear in train+test.

## Data window + split
- Window: **2023-01 → 2026-06** for the pilot (option floor is ~2012 for old names if we extend;
  monthlies-only first cut). Train/validate on 2023-01 → 2025-06; **SEALED HOLDOUT = 2025-07 → 2026-06**
  (`HOLDOUT_START = 20250701`), untouched until the v0 verdict is called. Max 2 holdout reads, ever.

## Feasibility read (mega-cap, EXPLORATORY — does NOT touch the pilot holdout) — 2026-06-19
Ran the gamma→behavior test on the 8 mega-cap walls already on disk (2023-2026, 6,903 name-days):
- **Direction: dead** (~0 IC, all features, p>0.1).
- **Vol: a pulse with the right sign**, but after controlling for price structure (distance-from-20d-high,
  momentum) the gamma call-wall's incremental IC fell **+0.096 → +0.033**, and a NON-gamma overhead level
  (20d-high) was at least as predictive. So on the EFFICIENT end the gamma-vol edge is mostly price-structure.
- **Implication:** lowered prior; the live channel is vol/convexity not direction; the bet rests entirely on
  the inefficient mid-tier being different. This pilot tests exactly that. Scripts: `feasibility_megacap.py`,
  `feasibility_confound.py`.

## Data engine
- **Signal:** ThetaData ($160 options sub). Pull per-expiration **`eod` prices + `open_interest`** (both
  fast: OI ~11s/exp; the `eod_greeks` endpoint is ~180s/exp → AVOID). **Self-compute IV + gamma** with the
  validated BS engine (`build_walls_selfcompute.py` / `option_greeks.py`) — same path that built NDX walls.
  Produce per-(stock,date) walls: `[spot, call_wall, put_wall, zero_gamma, pin, gex_proxy]` (walls_v2 schema).
- **Underlying + universe:** the local **survivorship-clean Polygon equities** (daily + entry-day minute,
  delisted incl). Cleaner & deeper than the $80 ThetaData stock-bars sub (which floors 2023-06).
- **Cache:** `theta_store` (pull-once → `D:\data\raw\thetadata`). Re-runs never re-pull.

## Discipline (non-negotiable)
- **No look-ahead.** Signal for day D uses only data ≤ D close (prior-day OI when joining intraday, as the
  index panels do). Gamma computed from the chain as of D, traded at D+1 open or later.
- **Honest fills.** v2 options fills cross the bid/ask from the per-contract quote; theta is paid. No
  picking the strike/expiry that happened to win.
- **Sealed holdout, ≤2 reads.** Pre-registered metric only. A pretty in-sample curve means nothing
  (the lab's scar tissue: index-internals, level_scalp, the gamma "mirage").

## Kill criteria
- v0 incremental IC over baseline ≤ 0 (or below a permutation null) on the holdout → **kill or pivot
  signal** (e.g. to flow-imbalance). Do not "tune until it works."
- v2 convex backtest positive only because of < 5 monster trades (fat-tail fragility) → **not deployable**;
  report and stop.

## Build order
1. `pull_chain.py` — per-(root, expiration) eod + OI pull via theta_store, pilot universe, cached.
2. `build_stock_walls.py` — self-compute IV/gamma → per-(stock,date) walls (reuse selfcompute engine).
3. `signal_v0.py` — assemble daily GEX/wall features + the price/IV baseline; compute incremental IC
   (train/validate only). **STOP at the holdout.**
4. (gated) v1 underlying backtest → v2 convex options backtest.
