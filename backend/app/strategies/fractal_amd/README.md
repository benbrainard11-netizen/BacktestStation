# Fractal AMD strategy port — scaffold

**Status:** scaffold only. The plugin loads, runs, returns no orders. Filling in the signal logic is the multi-session port.

## Source of truth

Port target: `C:/Users/benbr/FractalAMD-/production/live_bot.py` (1325 lines, the trusted live bot per memory `project_live_bot.md`). The scaffold's class shapes (`Setup`, config constants) mirror that file 1:1 so future port chunks are mechanical.

The validated trusted-strategy results that the port must reproduce:
- 2024-2026 (2.25y): 586 trades, 40.8% WR, +274R, avg +0.47R, -20R maxDD
- 2022-2026 (4y): 1103 trades, 39.0% WR, +421R
- 8/9 quarters profitable

## Files

| File | Status | Port target |
|---|---|---|
| `__init__.py` | done | re-exports `FractalAMD` |
| `config.py` | done | constants (entry window, risk caps, TARGET_R, max trades, aux symbols) |
| `signals.py` | stubs | `_candle_bounds`, `detect_rejection`, FVG helpers, `check_touch` from live_bot.py |
| `strategy.py` | scaffold | `SignalEngine.scan_for_setups` + entry/exit loop |

## Port checklist (TODO order from strategy.py)

1. **scan_for_setups (HTF + SMT detection).** Implement `signals.build_htf_candles` + `signals.detect_smt_rejection`. Wire from `on_bar`. Most of the SignalEngine.scan_for_setups loop in live_bot.py:345-505.

2. **validate_pending_setups (LTF FVG resolution).** Implement `signals.detect_fvg`. Setups discovered at HTF candle close need an FVG validation on the next LTF candle close.

3. **check_touch on watching setups.** Implement `signals.check_touch`. Bar-by-bar scan of WATCHING setups for entry-trigger contact.

4. **Emit BracketOrder when TOUCHED + in entry window.** Stop = FVG far edge, target = entry +/- TARGET_R * risk. Honor `min_risk_pts` / `max_risk_pts` gates.

5. **Daily counter on fill.** Increment `trades_today` when an exit fills (already wired). Add fill-side dedup of `entries_today` once setup detection lands.

## Multi-instrument

Already correctly wired via the engine's `aux_symbols` support (commit b14770a). NQ is the primary; ES + YM are aux. Strategy reads them via `context.aux["ES.c.0"]` / `context.aux["YM.c.0"]`. The SMT divergence detector (live_bot.py: `detect_rejection`) needs all three to fire.

## What the scaffold deliberately doesn't try to be

- A complete strategy. It returns no orders.
- A research-grade implementation of any single signal layer. Each function is a typed stub.
- A registry. CLAUDE.md §9 — one resolver lookup branch in `runner._resolve_strategy` is fine until there are 3+ strategies.
- A re-implementation of the live bot. The goal is structural parity so future ports are mechanical, not a rewrite that drifts from the validated logic.

## Smoke test

`backend/tests/test_fractal_amd_scaffold.py` runs the strategy against synthetic NQ + ES + YM bars and asserts:
- no crash
- zero trades (expected — no signal logic yet)
- aux bars are visible to the strategy via `context.aux`

Real backtest results will only show up as the TODOs above land.
