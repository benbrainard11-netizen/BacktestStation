# prop_rv_intraday_v0 — intraday relative-value (cointegration spread mean-reversion), day-flat

**Thesis.** The lab's one robust, OOS-validated edge is cointegration mean-reversion (`energy_rv_v0` /
`xsectional_rv_v0`, +1.44 Sharpe) — but **multi-day**, so the universal prop flat-by-close rule
disqualifies it. This line tests whether the SAME cointegrated spreads revert **intraday**, which would
make the edge **day-flat AND market-neutral (two legs) — prop-compatible AND trivially automatable**
(z-score in/out). It is the intersection of "the edge that actually works" and "the constraint we need,"
and the goal Ben stated: *automate a futures strat.*

## Discipline (locked)
- **Causal hedge ratio:** rolling OLS of leg1~leg2 over the prior `BETA_LB=20` daily closes (no future).
- **Causal trailing z:** spread vs prior `W=60`-bar mean/std within the day, `.shift(1)` (no future).
  *(The first diagnostic used a full-day mean = look-ahead; it faked +1.6 std / 98% reversion and was
  caught + fixed. Causal z is the only valid version.)*
- **One position at a time** (no overlapping observations); enter |z|>ENTRY, exit |z|<EXIT / MAX_HOLD /
  session close (day-flat).
- **Honest 2-leg cost:** both legs cross ~1 tick on entry AND exit + per-contract commission, sized by
  the dollar-neutral hedge. This is the structural challenge — you pay TWO bid-asks for one spread move.
- **Sealed holdout:** design ≤ 2024-12-31, holdout 2025. Pre-registered threshold; bootstrap the OOS net.

## Findings (2026-06-20)
- **Causal diagnostic (`diag.py`):** the look-ahead fix correctly KILLED the crack spreads (HO-CL,
  RB-CL: +1.5 std → ~0), confirming the leak. **CL-BZ (+0.69 std/30m, 64%) and ZN-ZF (+0.73, 66%)
  survived** — genuine causal intraday reversion on tight same-unit cointegrated pairs.
- **Honest backtest (`rv_backtest.py`):** the reversion is REAL (gross +) but largely **cost-killed**
  (2-leg friction). CL-BZ: gross +$50 vs cost $44 → net +$6 design / −$11 holdout at |z|>2. ZN-ZF:
  cost ($59) > gross ($21) → hopeless.
- **Threshold sweep (the key result):** CL-BZ is **monotonic** — trade only bigger stretches → better
  net on BOTH splits; **holdout turns positive at |z|≥3.5** (+$3.1) and |z|>4 (+$8.8/trade, 68% win).
  Not a knife-edge; it's the economic logic (bigger dislocations revert past the fixed cost). Caveats:
  low-frequency, small-$, thin holdout n — verdict hinges on OOS significance + generalization to a
  PORTFOLIO of pairs (`expand.py`).

## Status
- [x] diagnostic + honest backtest + threshold sweep (CL-BZ promising, OOS+ at high z).
- [~] **expansion** (`expand.py`): same construction across index/rates/energy cointegrated pairs +
  OOS bootstrap — does it generalize (a scalable portfolio) or is CL-BZ a lucky single?
- [ ] if it generalizes: pre-register one config, holdout read, then live wiring.

Python: `backend/.venv/Scripts/python.exe`. Specs (CL/BZ/ZN/ZF/ZB/ZT/HO/RB + index) in
`backend/app/backtest/instruments.py`.
