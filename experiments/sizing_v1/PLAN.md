# Sizing v1 — Locked Plan

**Status:** scaffolded, no simulator built yet
**Version:** 1
**Branch:** `experiments/sizing-v1`
**Created:** 2026-05-28

The sizing/risk layer that converts `experiments/milk-v1` model probabilities into per-account contract counts, simulates prop firm evaluation accounts, and reports the actual milking metric: **percent of accounts that pass.**

This is the upstream-of-money layer. The model is signal; the sizing layer is the business.

---

## Decision

Build a multi-account simulator that:
1. Reads LightGBM ensemble predictions from `experiments/tsfm_milk_v0/out/predictions/lightgbm_ensemble/`
2. For each (firm × account) combo, walks forward through walk-forward fold test windows
3. At each predicted signal, decides: trade or skip, what direction, how many contracts
4. Tracks account state (daily P&L, drawdown, total P&L, profit target progress)
5. Enforces per-firm rules in real-time
6. Reports per-firm pass rate, expected dollar value per account, and the milking math

---

## §1. Scope (v1)

### IN

- Multi-account router (one signal → N accounts)
- Per-firm rule engines for: **Topstep, Tradeify, Apex, MFFU, Ludic, TPT** (six configs)
- Strategy config: which (symbol, horizon) cells to trade, with what threshold
- Sizing methods:
  - `fixed_1` (default — 1 contract per trade, simplest baseline)
  - `kelly_fractional` (0.10-0.25 × Kelly, v1.5)
  - `vol_targeted` (inverse-vol sizing, v1.5)
- Exit: time-only at horizon boundary
- Skip rules: confidence threshold, account state (loss limits / DD), time-of-day jitter
- Evaluation: 100+ simulated accounts per firm, compute pass rate
- Anti-bot: small randomized timestamp jitter on entries (0–59 seconds)

### OUT (v1.5+ or v2)

- Stop-loss / trailing stops on individual trades (v1.5)
- News / macro event blackout windows (v2, requires news pipeline)
- Realistic slippage model beyond 2-tick flat assumption (v2, requires MBO depth model)
- Live shadow trading on paper accounts (v2)
- Real-time inference latency modeling (v2)
- Symbol-correlated drawdown risk (v2)

### NOT IN ANY VERSION (out-of-character)

- Direction flipping (model says up, we trade down) — never
- Size > 1.0 multiplier on model confidence (never increase beyond model intent)
- Silent fallback when prediction is unavailable — always log explicit skip

---

## §2. Inputs

```
Source:                               Use:
─────────────────────────────────     ─────────────────────────────────
out/predictions/                      Model probability vectors
  lightgbm_ensemble/                  (the winner from milk-v1 iter-1)
  fold_{1-6}_test.parquet
  fold_holdout_holdout.parquet

D:/data/processed/bars/timeframe=1m/  Entry/exit price simulation
  symbol=*/date=*/*.parquet           (use bar open of next minute after entry)

experiments/sizing_v1/config/
  firms/*.yaml                        Per-firm rule engines
  strategy_v0.yaml                    Which cells to trade, confidence thresholds
```

---

## §3. Per-firm rule schema

Each firm gets a YAML in `config/firms/`. Universal schema:

```yaml
firm_name: topstep
account_size: 50000          # USD
evaluation_account_type: combine    # combine | personal-funded | etc.

# Daily loss limit (intraday + EOD).
daily_loss_limit: 1000       # account closes for the day if hit
daily_loss_intraday: true    # most firms enforce intraday; some only at EOD

# Trailing drawdown (account-killing).
trailing_drawdown: 2000
trailing_drawdown_locks_at_starting_balance: true   # Topstep style: stops trailing at account start
trailing_drawdown_resets_daily: false               # Apex style: resets daily; not common

# Profit target (to pass evaluation).
profit_target: 3000

# Consistency rule.
consistency_rule_pct: 30     # no single day can exceed 30% of total profit
consistency_rule_applies_at_funded: true   # most: only at funded stage

# Min activity.
min_trade_days: 5            # must trade on at least N distinct days
min_trade_count: 0           # some firms: no min count, just days

# News / event restrictions.
news_blackout_minutes_before: 0    # 0 = no restriction
news_blackout_minutes_after: 0     # most retail-accessible firms allow news
events_blocked: []                  # FOMC, CPI, NFP, etc. — empty = none

# Eval window.
max_eval_days: 30            # must complete eval within this many calendar days
                              # 0 = no time limit (e.g., Topstep personal eval)

# Contract limits.
max_position_size: 5         # max contracts per symbol concurrent
max_total_position: 10       # max contracts across all symbols
allowed_symbols: [ES.c.0, NQ.c.0, YM.c.0, RTY.c.0]

# Reset / restart.
allow_reset: true            # can buy a reset if you blow the eval
reset_cost_usd: 80           # what reset costs

# Economics (used in milking-math summary).
eval_fee_usd: 165            # cost to start an eval
funded_account_value_usd: 1000   # rough $ value of a passed funded account
                                  # (resale value or expected operate value)
```

We'll start with Topstep $50K Combine as the canonical example. Other firms get TBD fields where I don't know the exact value — to be filled in by user / friend.

---

## §4. Strategy config

```yaml
# config/strategy_v0.yaml
strategy_name: lightgbm_ensemble_v0
model_predictions_dir: ../tsfm_milk_v0/out/predictions/lightgbm_ensemble

# Cells to trade — only the ones with proven honest edge.
active_cells:
  - {symbol: NQ.c.0, horizon: h_60m, threshold: 0.55}    # +$43k aggregate in milk-v1 iter-1
  - {symbol: RTY.c.0, horizon: h_90m, threshold: 0.55}   # +$19k
  - {symbol: ES.c.0,  horizon: h_15m, threshold: 0.55}   # small but positive
  - {symbol: YM.c.0,  horizon: h_30m, threshold: 0.55}   # small but positive

# Sizing.
sizing_method: fixed_1       # v1 default. fixed_1 | kelly_fractional | vol_targeted
sizing_params:
  contracts: 1               # for fixed_1
  kelly_fraction: 0.15       # for kelly_fractional (v1.5)
  vol_target_R: 1.0          # for vol_targeted (v1.5)

# Entry timing.
entry_jitter_seconds: [0, 59]    # random seconds within minute, anti-bot
entry_at: next_bar_open          # entry uses the minute AFTER ts_decision

# Exit.
exit_method: time_only           # time_only | stop_target | stop_target_trailing
exit_params:
  horizon_minutes: from_signal   # exit horizon = the signal's horizon
```

---

## §5. Account state

Per account, the simulator tracks:

```
account_id              str         "topstep_50k_account_001"
firm_config             str         "topstep_50k.yaml"
account_balance         float       starts at account_size, evolves with P&L
day_start_balance       float       at start of each trading day
day_high_water          float       intraday high water mark
day_pnl                 float       balance - day_start_balance
account_high_water      float       all-time peak of account_balance
trailing_dd_floor       float       account_high_water - trailing_dd
                                    (locks if rule applies)

n_trade_days            int         distinct dates with ≥ 1 trade
trade_log               list[Trade] every trade with entry/exit/contracts/pnl

status                  str         "active" | "blown_daily" | "blown_dd" |
                                    "passed" | "expired"
blown_reason            str | None  human-readable reason if not active
```

At every signal arrival, before deciding to trade, the simulator asks:
- Is account status "active"?
- Would this trade's size exceed `max_position_size`?
- Would this trade place us at risk of breaching `trailing_dd_floor` after one max-loss?
- Are we inside a `news_blackout` window?

---

## §6. The take/skip decision (the heart of v1)

For each signal `(ts_decision, symbol, horizon, p_proba)`:

```
for each account in active_accounts:
    if account.status != "active":
        skip

    if symbol not in firm.allowed_symbols:
        skip
    if horizon not in strategy.active_cells_at(symbol):
        skip

    direction = argmax(p_proba)
    confidence = max(p_proba)
    if direction == FLAT:                          skip
    if confidence < strategy.threshold(symbol, horizon):  skip

    if account.day_pnl <= -firm.daily_loss_limit + safety_buffer:
        skip   # too close to daily blowout
    if account.balance - firm.max_loss_per_trade_estimate <= account.trailing_dd_floor:
        skip   # one bad trade could blow the account

    if in_news_blackout(ts_decision, firm):        skip
    if firm.consistency_rule and would_violate(...):  skip (optional)

    size = strategy.sizing(p_proba, account, firm)
    trade = enter(account, symbol, direction, size, ts_decision)
    account.open_positions.append(trade)
```

---

## §7. Exit logic (v1)

Time-only exit. When a trade has been open for `horizon_minutes`:

```
exit_price = bar_open at (entry_ts + horizon_minutes)
pnl = (exit_price - entry_price) * direction * contracts * point_value
    - 2 * tick_size * point_value           # 2-tick total slippage
    - 1.50                                   # commission round trip

account.balance += pnl
account.day_pnl += pnl

if account.day_pnl <= -firm.daily_loss_limit:    account.blown_daily(today)
if account.balance <= account.trailing_dd_floor: account.blown_dd()
if account.balance - firm.account_size >= firm.profit_target and account.n_trade_days >= firm.min_trade_days:
    account.passed()
```

---

## §8. Multi-account simulation

For each firm, simulate **N accounts in parallel**:

```
N = 100                              # accounts per firm per simulation
random_seed = per-account            # accounts are independent draws
                                     # (same signals, different jitter / order)

for sim_run in range(N):
    account = Account(firm_config, account_id=f"{firm}_{sim_run:03d}")
    for signal in walk_forward_signals:
        route_signal_to_account(account, signal)
    account.finalize_at_eval_deadline()
    record(account.final_status, account.trade_log, account.balance)
```

Accounts are independent — they don't share P&L. The N=100 measures the **distribution of outcomes** when running this strategy with this firm. The key metric is **pass rate**.

---

## §9. Output metrics (§9 is what makes us money)

For each firm:

```
n_accounts:           100
n_passed:             54
n_blown_daily:        12
n_blown_dd:           19
n_expired:            15
pass_rate:            54%

mean_balance_at_end:  $51,200
median_balance:       $50,800
p25_balance:          $49,100
p75_balance:          $52,400
worst_balance:        $48,000 (lost an account)
best_balance:         $54,300 (passed easily)

mean_days_to_pass:    18 days
median_days_to_pass:  16 days

mean_trades_per_account:  87
median_trades_per_account: 79
```

And the **milking math**:

```
For 100 accounts at Topstep $50K Combine:
  Total eval fees paid:         100 × $165 = $16,500
  Passes:                       54
  Funded account value:         54 × $1,000 = $54,000
  Net per 100 evals:            $54,000 - $16,500 = +$37,500
  Expected $/eval:              +$375
  Break-even pass rate:         165/1000 = 16.5%

If we run 1,000 evals over a year:
  Expected gross:               $375 × 1000 = $375,000
  Operating cost (your time, resets, etc.): TBD
```

That's the actual milkable math. Pass rate is what matters.

---

## §10. Ship / kill criteria

**Ship to next iteration if:**
- At least one firm × strategy combo has pass rate ≥ 50%
- Expected $ per eval > 0 across at least 2 firms
- No simulation bugs (results reproducible, no lookahead detected)
- Mean days-to-pass ≤ firm.max_eval_days for at least one firm

**Kill / rework if:**
- All firms show pass rate < 25%  (the math doesn't work)
- Mean days-to-pass > eval deadline (system can't generate trades fast enough)
- Trailing DD breaches > 40% of accounts (system has tail risk)

---

## §11. File layout

```
experiments/sizing_v1/
├── PLAN.md                            (this file)
├── README.md
├── MODEL_CARD.md                      v1 sizing layer "card"
│
├── config/
│   ├── strategy_v0.yaml               which cells, what threshold, what sizing
│   └── firms/
│       ├── topstep_50k.yaml           Topstep Combine $50K (canonical)
│       ├── tradeify_50k.yaml          TBD
│       ├── apex_50k.yaml              TBD
│       ├── mffu_50k.yaml              TBD
│       ├── ludic_50k.yaml             TBD
│       └── tpt_50k.yaml               TBD
│
├── account.py                         Account state machine (P&L, DD, status)
├── firm_rules.py                      Rule engines per firm
├── sizing.py                          Probability → contract count
├── risk_manager.py                    Take/skip decision (the gatekeeper)
├── simulator.py                       Walk-forward trade simulation per account
├── multi_account_router.py            One signal → N accounts
├── evaluate_sizing.py                 Pass rate computation, milking math
├── qa.py                              QA tests (lookahead, account-state consistency)
│
├── out/                               gitignored
│   ├── trades/{firm}/                 per-account trade logs
│   ├── accounts/{firm}/               per-account final state
│   └── pass_rates.parquet             aggregated metrics
└── report/                            markdown writeups
```

---

## §12. Five ambiguities — RESOLVE BEFORE CODING

1. **Exact prop firm rule numbers** for Tradeify, Apex, MFFU, Ludic, TPT. Topstep we can get from public docs. Others may need your friend's input or external research.

2. **How "trailing drawdown locks at starting balance" works exactly** at each firm. Topstep locks once you go above $50K. Other firms' lock behavior varies.

3. **News-blackout enforcement** — some firms enforce strictly, others don't. Easiest: list scheduled events from a calendar, block ±N minutes. For v1, default 0 minutes (no restriction). Real numbers come later when news pipeline exists.

4. **Consistency rule** — does it apply at evaluation stage or only at funded stage? Some firms only enforce at funded. For v1, apply at funded only (most lenient).

5. **Allowed symbol set per firm.** Most allow ES/NQ/YM/RTY. Some restrict gold, oil, or crypto. For v1, assume all 4 indices allowed everywhere. Confirm later.

---

## §13. Codex instruction block (when ambiguities resolve)

Send to Codex when §12 is filled in:

```
Build sizing_v1 per experiments/sizing_v1/PLAN.md.

Hard constraints:
- Never flip direction (model says up = we go up).
- Never size > 1× confidence (no over-betting).
- No lookahead — entry uses bar AFTER ts_decision.
- Apply jitter (0-59s) to entry timestamps.
- Account state must reset cleanly per simulation seed (no leakage between runs).

Tasks (in order):
 1. account.py: Account class with all state per §5.
 2. firm_rules.py: load YAML, expose take/skip helper methods.
 3. sizing.py: fixed_1 sizing (rest are v1.5).
 4. risk_manager.py: the take/skip gatekeeper per §6.
 5. simulator.py: walk-forward through a single account's trade lifecycle per §7.
 6. multi_account_router.py: parallel N-account simulation per §8.
 7. evaluate_sizing.py: pass rate + milking math per §9.
 8. qa.py: lookahead, state consistency, jitter randomness.

Report:
  report/v1_iter1_results.md — per-firm pass rates, expected $/eval,
  breakdown by termination reason (passed / blown_daily / blown_dd / expired).
```

---

**Updated:** 2026-05-28
**Owner:** Ben Brainard
**Reviewers:** GPT Pro (research design), Codex / Claude Code (implementation)
