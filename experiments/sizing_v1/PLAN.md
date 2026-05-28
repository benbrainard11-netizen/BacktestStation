# Sizing v1 — Locked Plan

**Status:** scaffolded, no simulator built yet
**Version:** 1 (funded-phase, locked 2026-05-28)
**Branch:** `experiments/sizing-v1`

The sizing/risk layer that converts `experiments/milk-v1` model probabilities into per-account contract counts, simulates prop firm **funded** accounts (post-eval), and reports the actual milking metric: **total $/account/year via payouts.**

**Why funded-phase first:** funded is where revenue is generated. If the strategy clears funded payouts under stricter rules (consistency + payout caps + trailing DD), eval is implied. Eval is a one-shot $165 fee; funded is recurring weekly/monthly cash flow. We measure the actual cash-flow rate directly.

The model is signal; this layer is the business.

---

## Decision

Build a multi-account funded-phase simulator that:
1. Reads LightGBM ensemble predictions from `experiments/tsfm_milk_v0/out/predictions/lightgbm_ensemble/`
2. For each (firm × N=100 funded accounts), walks forward through walk-forward fold test windows
3. At each predicted signal, decides: trade or skip, what direction, how many contracts
4. Tracks account state (daily P&L, EOD trailing floor, winning days, payout eligibility)
5. Triggers payouts when conditions met (5+ winning days ≥$200 AND profit ≥$3k)
6. Continues until account blown or simulation period ends (default: 365 days)
7. Reports total $/account, payouts per account, time-to-first-payout, blown-account rate

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

## §3. Per-firm rule schema (funded phase)

Each firm gets a YAML in `config/firms/`. See `topstep_50k.yaml` for the
canonical example; below is the schema, locked for v1 funded-phase sim:

```yaml
firm_name: topstep
account_size: 50000          # starting balance
evaluation_type: funded      # funded phase (skip eval entirely)

# Trailing DD: trails EOD high water by $2k UNTIL balance exceeds starting + $2k.
# Then locks permanently at starting balance.
trailing_drawdown: 2000
trailing_dd_uses_eod: true
trailing_dd_lock_threshold: 52000     # EOD balance that triggers the lock
trailing_dd_locked_value: 50000       # where it locks (= starting balance)

# Daily loss limit (intraday).
daily_loss_limit: 1000

# Payout rules (funded-phase specific).
payout_min_winning_days: 5
payout_winning_day_threshold_usd: 200   # day P&L ≥ this counts as a "winning day"
payout_profit_threshold: 3000           # total profit ≥ this to be eligible
payout_amount_method: half_of_profits
payout_cap_usd: 5000                    # per-payout cap (user-chosen $5k for v1)
payout_balance_after: keep_remainder    # balance = balance − payout (no reset)
payout_resets_winning_day_counter: true # counter resets after each payout

# Consistency rule.
consistency_rule_pct: 50                # no single day > 50% of total profit
                                        # (funded phase always applies)

# Symbols.
allowed_symbols: [ES.c.0, NQ.c.0, YM.c.0, RTY.c.0]
max_position_size: 5

# News.
news_blackout_minutes_before: 0
news_blackout_minutes_after: 0

# Sim horizon.
sim_max_days: 365            # simulate one year per account (or until blown)
```

Topstep $50K Combine is the canonical example. Other firms get the same
schema with their specific numbers — user/friend to fill in v1.5.

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

## §5. Account state (funded phase)

Per account, the simulator tracks:

```
account_id                    str       "topstep_50k_account_001"
firm_config                   str       "topstep_50k.yaml"
account_balance               float     starts at 50000, evolves with P&L
day_start_balance             float     reset each trading day at session open
day_pnl                       float     balance - day_start_balance
eod_balance_high_water        float     max EOD balance seen so far
trailing_dd_floor             float     computed from eod_high_water OR locked at 50000
trailing_dd_is_locked         bool      true once eod_balance crossed lock_threshold

winning_days_count            int       distinct days where day_pnl ≥ winning_day_threshold
                                        (resets to 0 after each payout)
total_payouts_received        float     cumulative cash collected via payouts
total_payouts_count           int       how many payouts taken
payouts_log                   list      each payout: ts, amount, balance_before, balance_after

n_trade_days                  int       distinct dates with ≥ 1 trade
trade_log                     list      every trade

status                        str       "active" | "blown_daily" | "blown_dd" | "completed"
blown_reason                  str|None  reason if not active
```

At every signal arrival, before deciding to trade, the simulator asks:
- Is account status "active"?
- Would this trade's size exceed `max_position_size`?
- Are we within `daily_loss_limit` plus a safety buffer?
- Is `account_balance − one_max_loss_estimate > trailing_dd_floor`?
- Are we inside a `news_blackout` window?

At each EOD close:
- Update `day_pnl` from intraday balance change
- If day_pnl ≥ winning_day_threshold: increment winning_days_count
- Update `eod_balance_high_water`
- Recompute `trailing_dd_floor` (may lock now)
- If `winning_days_count ≥ payout_min_winning_days` AND `balance − account_size ≥ payout_profit_threshold`:
  - Trigger payout: amount = min(0.5 × (balance − account_size), payout_cap_usd)
  - balance −= amount
  - total_payouts_received += amount
  - winning_days_count = 0  (counter resets)
  - Log the payout

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

## §9. Output metrics (the actual cash-flow numbers)

For each firm, simulated over `sim_max_days` (default 365):

```
n_accounts:                       100
n_alive_at_end:                   ?
n_blown_daily:                    ?
n_blown_dd:                       ?

Total $ collected across all accounts:    ?
Mean $/account over sim period:           ?
Median $/account:                          ?
P25 / P75 / worst / best $:                ?

Mean payouts per account:                 ?
Median time to first payout (days):       ?
Median time between subsequent payouts:    ?
Mean account lifespan in days (alive):    ?
Mean account lifespan in days (blown):    ?

Mean trades per account:                  ?
Mean winning days per account:            ?
```

And the **revenue rate math**:

```
For Topstep $50K, 100 funded accounts over 12 months:
  Total $ collected:           $X
  Mean per-account annual rate: $X / 100 = $Y/account/year
  Mean monthly revenue:         $Y / 12 = $Z/account/month

If 50% of accounts get blown within the year:
  Effective N at year-end: 50
  Ongoing monthly run-rate from survivors: 50 × $Z = $W/month sustained

Break-even threshold against operating costs:
  Eval cost per account: $165 (one-shot, before funded phase)
  Monthly subscription:  $0 (Topstep) — verify per firm
  Effective net per account = mean_$/account - $165
```

That's the actual milkable cash-flow math. **Total $/account/year is the
headline.** Pass rate is no longer the metric since we skip the eval phase
in v1.

---

## §10. Ship / kill criteria (funded phase)

**Ship to next iteration if (median across 100 simulated Topstep accounts):**
- Mean $/account/year > $2,000 (i.e., 1+ successful payouts per account on average)
- Account-blown rate < 60% over 12-month sim
- At least one payout reached on > 30% of accounts
- No simulation bugs (results reproducible, no lookahead detected)

**Kill / rework if:**
- Mean $/account/year ≤ $0 (system bleeds money)
- Account-blown rate > 80% (tail risk too high)
- Median time to first payout > 90 days (system too slow)
- Consistency rule violation rate > 20% (sizing too aggressive)

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
