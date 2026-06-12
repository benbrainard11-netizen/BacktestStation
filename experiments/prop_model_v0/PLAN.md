# prop_model_v0 — the prop business as a model (three layers)

**Goal:** maximize expected funded-payout value across ~20 prop accounts, treating the
eval ecosystem as the asymmetric bet it is. Edge in the MARKET is optional for layer 1;
layers stack so each one adds value independently.

## Layer 1 — eval economics (pure math; builds on sizing_v1)

An eval = fee F for a shot at a funded account worth V (expected lifetime payouts).
Pass probability P depends on the strategy's distribution shape (win rate, R, trades/day,
EV≈0 allowed) versus the firm's geometry (target, trailing DD + lock mechanics, daily
limit, consistency %, min days). sizing_v1's account.py + firm_rules + block-bootstrap MC
already simulate this — extension needed: **EV_eval = P(pass)·V − F − E[resets]·F_reset**,
swept over strategy shapes per firm, with V itself simulated (funded-stage survival ×
payout policy). Output: per firm — the optimal variance shape, expected cost-to-funded,
and EV per eval ticket. HONESTY RULES: shapes constrained to what real day-flat trading
produces (no sim-fill dependence — level_scalp_v0 verdict stands); consistency rules
modeled exactly (they exist to tax variance-gaming); copy-trading policies respected
per firm.

## Layer 2 — the trade generator (day-flat, modest bar)

Requirement: NOT-NEGATIVE expectancy after honest costs, controllable variance,
hold times minutes-to-hours, flat by close, zero compliance smell. Candidate #1
(best-supported untested construction): **vol-gated opening-range breakout** —
trade OR breakouts only on days the vol forecast says range will support them.
Combines the repo's ONE validated forecast (realized vol → fwd range, corr ~0.52;
the only survivor of phase_model_v0) with the academically supported ORB-breakout
(Holmberg et al; our own atlas tested OR levels only as FADES, never as gated
breakouts). Test through the existing honest machinery: bar-legal construction,
MBP-1 fill verification on a sample, selection/confirmation discipline, stressed
costs. Bar to clear: ≥ −0.05R net (a free coin with the right shape is acceptable
to layer 1; anything positive is bonus).

## Layer 3 — the per-firm optimizer

Generator shape × audited firm rules × layer-1 math → which firms get accounts,
config per firm, expected monthly payout per account and per fleet of 20.
Output feeds the existing copier deployment path.

## Inputs / status

- [~] **Firm-rule audit** (workflow running 2026-06-12): exact fees, targets, DD
  mechanics, daily limits, consistency %, day-flat rules, micro permissions, copy
  policies, payout policies × 6 firms → updates sizing_v1/config/firms/*.yaml with
  citations (closes sizing_v1's parked phase).
- [ ] Layer-1 calculator (extends sizing_v1; buildable immediately after audit).
- [ ] Layer-2 vol-gated ORB study (new module work; SELECTION/CONFIRMATION split on
  index bars + MBP-1 verification; constitution rules inherited from level_scalp_v0).
- Known constraints honored: energy RV book is NOT prop-compatible (multi-day holds
  vs day-flat rules — measured 2026-06-12); microscalping/sim-fill strategies banned
  (compliance research 2026-06-12); minutes-scale microstructure edge = dead (5
  honest constructions).
