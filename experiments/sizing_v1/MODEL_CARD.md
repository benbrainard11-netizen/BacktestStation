# Model Card — sizing_v1

**Version:** 1
**Status:** Not yet implemented (planning phase)
**Owner:** Ben Brainard

## Intended use

Convert calibrated model probabilities from `experiments/tsfm_milk_v0` (milk-v1 iter-1, LightGBM ensemble) into per-account trade decisions, sized to respect prop firm rules. Simulate evaluation accounts at scale (100+ accounts per firm) to measure pass rate. Pass rate × funded account value − eval fee = expected dollar value per evaluation.

## Out-of-scope (v1)

- Direction flipping (model says up = we go up, period)
- Sizing beyond 1× model confidence (never bet bigger than model intent)
- Stop-loss / trailing stops (v1.5)
- News / macro event blackout (v2 — needs news pipeline)
- Realistic slippage / market impact modeling beyond flat 2-tick (v2)
- Live trading (v3 only after v1 + v2 simulation pass)

## Inputs

- Probability vectors from milk-v1: `(N, p_flat, p_up, p_down)` per `(ts_decision, symbol, horizon)`
- 1-minute OHLCV bars at `D:/data/processed/bars/timeframe=1m/` for entry/exit pricing
- Per-firm rule configs in `config/firms/`
- Strategy config in `config/strategy_v0.yaml`

## Outputs

- Per-account trade log (entry, exit, contracts, P&L, reason)
- Per-account daily P&L curve
- Per-account final status (passed / blown_daily / blown_dd / expired)
- Per-firm pass rate distribution
- Milking math: expected $/eval, break-even pass rate, ROI per firm

## Algorithm summary

```
For each firm (Topstep, Apex, ...):
  For each simulated account (N=100):
    For each model signal in walk-forward:
      If account is active:
        Check skip rules (confidence, account state, daily/trailing DD risk)
        If pass: size position (fixed_1 in v1), enter at next-bar open
      If account has open position:
        Hold for horizon minutes
        Exit at horizon-bar open + slippage + commission
        Update P&L, check breach
    Finalize at eval deadline
  Aggregate: pass rate, distribution
```

## Performance metrics

Not yet simulated. Ship / kill thresholds in [`PLAN.md`](PLAN.md) §10.

## Hard safety rules (cannot be turned off)

- Never flip direction
- Never size > 1× model intent
- Hard stop trading on daily-loss-limit breach
- Hard stop trading on trailing-DD breach
- Never trade with stale prediction (>24h old)
- Always log entry/exit with reason
- Reproducibility: same seeds → same results

## Limitations / known risks

- **Slippage model is flat.** Real slippage scales with size + book depth. v1 uses 2-tick total round trip; live results may be worse if we scale to 5+ contracts.
- **No correlated drawdown across accounts.** Each account is simulated independently; in real life, correlated bad days could blow multiple accounts at once.
- **No news event blackout.** v1 assumes you can trade through any macro event. Reality: firms may restrict; macro days have wider spreads + bigger slippage.
- **Probability distribution may shift live.** Model was trained on 2018-2025. Live in 2026+ may have different regime characteristics — pass rates could degrade.
- **Eval cost only.** v1 ignores potential funded-account operating costs, taxes, and your own time.

## Update / retrain cadence

Not yet defined. Initial proposal: retrain the upstream milk-v1 monthly, re-simulate sizing layer monthly, re-tune firm-specific parameters (confidence threshold per firm) quarterly.

## Production restrictions

This is RESEARCH ONLY in v1. No live trades. No real money. Live shadow / paper trading is v2.
