# Risk-Conditioner v0 — Locked Plan

**Status:** scaffolded, no model trained yet
**Version:** 0
**Branch:** `experiments/risk-conditioner-v0`
**Created:** 2026-05-26

This is the locked spec. Anything outside this scope is v0.3 expansion work and must wait until v0 baselines have been beaten.

---

## Decision

Build a **Type A / Type B portfolio risk-conditioner**. The model receives detector-fired trade candidates from the existing BacktestStation engine and outputs a sizing multiplier in `{0.0, 0.25, 0.5, 0.75, 1.0}`. It does NOT create new trades, flip direction, or increase size above 1.0.

The conditioner respects the **Type A / Type B distinction** (audit completed 2026-05-16):

- **Type A (predictive)** — event population is direction-neutral; a model picks the alpha subset. Full risk prediction (`p_bad`, `pred_MAE_q80`, `time_to_target`, `p_target_before_stop`) → sizing multiplier. Goal: skip likely-bad trades, downsize moderate-risk ones.
- **Type B (confirmatory)** — event class IS the alpha; direction is embedded in the event. The model's ONLY allowed job is tail-risk reduction (predict and downsize trades whose realized MAE_R > 2.0R). Goal: protect the headline edge (+10,420R FVG zone_reaction) from outlier drawdowns without filtering the normal variance that produces the edge.

### Why this and not something else

- Mira already does sweep-event prediction. Atlas already does regime classification. A new directional alpha model would duplicate work.
- The Type B portfolio (FVG zone_reaction +10,420R, OB break +X R, etc.) is the best discovered edge and currently has no risk layer.
- Meta-labeling / risk-sizing on existing detector fires is the López de Prado playbook and the highest-EV-per-week-of-work option for this lab.

---

## Path Locked

### Path A (v0 only)

- Training universe: detector-fired trades with full MBP-1 feature availability
- Date range: **2025-05-01 → 2026-05-22** (~13 months, ~329 trading days)
- Backbone substrate: **MBP-1** (depth-1 quote + trade data)
- Auxiliary substrate: **MBO** (5 tail-risk features, see §2.I)
  - Available from ~2026-01-01 onward, ~53 trading days as of 2026-05-26, **backfill in progress**
  - For trades outside MBO coverage, MBO features are `null` + `mbo_available=False` flag
- Pre-May-2025 detector fires: **EXCLUDED** from v0

### Path B (v1, deferred)

Train on the full ~6 years of detector fires using OHLCV-only features for pre-May-2025 trades and MBP-1+MBO features for post-May-2025 trades. Requires feature-availability handling and missing-feature regime controls. Revisit only after v0 ships.

---

## §1. Exact Labels

Each training row is one detector-fired candidate trade.

### Core timestamps

```
symbol_i
detector_i
family_type_i ∈ {A, B}
side_i ∈ {+1 long, -1 short}
ts_signal_i = timestamp when detector fires
ts_decision_i = timestamp when Strategy.on_bar() is allowed to act
ts_entry_i = first executable timestamp after ts_decision_i + latency_config
entry_price_i
stop_price_i
target_price_i
T_cap_i (default = 60 minutes)
```

### Label window

Ends at the earliest of:
- target hit
- stop hit
- strategy exit
- T_cap timeout
- session close / forced flat time

### R definition

```
risk_ticks_i = abs(entry_price_i - stop_price_i) / tick_size_symbol
```

Reject the sample if `risk_ticks_i <= 0`, null, or `entry_price_i` / `stop_price_i` is null.

For **longs**:
```
adverse_ticks(τ)   = max(0, entry_price_i - low_or_bid_proxy(τ)) / tick_size
favorable_ticks(τ) = max(0, high_or_ask_proxy(τ) - entry_price_i) / tick_size
```

For **shorts**: flip high/low.

Then:
```
MAE_R_i = max adverse_ticks(τ) / risk_ticks_i
MFE_R_i = max favorable_ticks(τ) / risk_ticks_i
```

over `τ ∈ (ts_entry_i, label_end_i]`.

### Shared labels (all detector families)

```
y_mae_r              = clip(MAE_R_i, 0, 3.0)
y_time_to_target_sec = seconds from ts_entry until first target touch,
                       capped at T_cap_i, set to T_cap_i + 1 if never touched.
y_target_before_stop = 1 if target touched before stop,
                       0 if stop touched before target,
                       null if neither touched before T_cap / session exit.
```

### Type A label (predictive families only)

```
y_bad = 1 if MAE_R_i >= 1.0 before target is reached, else 0
```

### Type B label (confirmatory families only)

```
y_tail = 1 if MAE_R_i > 2.0, else 0
```

**Forbidden Type B objectives for deployment:** generic `p_good`, generic `p_win`, generic `p_target_before_stop` as a primary skip criterion, directional alpha, expected R maximization. The Type B model must NOT learn "is this a good trade?" — that question is misframed for Type B and risks eating the edge.

---

## §2. Locked Feature Schema (45 features)

These are the only v0 features. Everything else is v0.3 expansion work.

All features computed using only information available at or before `ts_decision_i`. No future bars, no future target/stop outcomes, no future session high/low, no future VWAP.

### Data source (ALL MBP-1, MBO, TBBO reads MUST use these readers)

Per [`docs/MBO_TRADING_DAY_CONTRACT.md`](../../docs/MBO_TRADING_DAY_CONTRACT.md) — futures trading day = 18:00 ET prev day → 17:00 ET trading-day date. Use:

```python
from app.data import read_mbo_trading_day, read_mbp1_trading_day, read_tbbo_trading_day
```

The MBO reader prefers the clean trading-day cache at `D:/data/clean/databento/mbo_trading_day/` (snapshot carry-in rows already removed). Do NOT point model code at raw `D:/data/raw/databento/mbo/` partitions — those are UTC-calendar storage, not trading days.

### A. Detector context (8)

1. `detector__name_id`
2. `detector__family_type_id`
3. `detector__raw_score`
4. `detector__confidence`
5. `detector__age_bars`
6. `detector__setup_quality`
7. `detector__distance_to_entry_ticks`
8. `detector__reward_risk_ratio`

### B. Top-of-book MBP-1 (8)

1. `mbp1__spread_last_ticks`
2. `mbp1__top_imbalance_last`
3. `mbp1__side_imbalance_mean_60s`
4. `mbp1__microprice_dev_ticks`
5. `mbp1__bid_size_min_60s`
6. `mbp1__ask_size_min_60s`
7. `mbp1__side_fade_count_60s`
8. `mbp1__opposite_fade_count_60s`

Definitions:
```
mid                  = (best_bid + best_ask) / 2
spread_ticks         = (best_ask - best_bid) / tick_size
microprice           = (best_ask * bid_size_1 + best_bid * ask_size_1)
                       / max(epsilon, bid_size_1 + ask_size_1)
microprice_dev_ticks = (microprice - mid) / tick_size
top_imbalance        = (bid_size_1 - ask_size_1)
                       / max(epsilon, bid_size_1 + ask_size_1)
side_imbalance       = side * top_imbalance
```

For longs: `side liquidity = bid liquidity`, `opposite liquidity = ask liquidity`. Flip for shorts.

### C. Trade-flow MBP-1 (6)

1. `mbp1__trade_imbalance_60s`
2. `mbp1__side_trade_imbalance_60s`
3. `mbp1__message_rate_60s`
4. `mbp1__trade_rate_60s`
5. `mbp1__quote_to_trade_ratio_60s`
6. `mbp1__signed_volume_300s`

```
trade_imbalance      = (buy_trade_volume - sell_trade_volume)
                       / max(1, buy_trade_volume + sell_trade_volume)
side_trade_imbalance = side * trade_imbalance
```

If true aggressor side is unavailable: infer trade side via bid/ask test first, tick rule fallback. Set `trade_side_inferred = True` as metadata.

### D. Realized volatility (4)

1. `vol__realized_vol_ticks_60s`
2. `vol__realized_vol_ticks_300s`
3. `vol__range_ticks_900s`
4. `vol__atr_5m_20bars`

### E. Higher-timeframe context (6)

1. `htf__close_to_session_vwap_ticks_1m`
2. `htf__ema_fast_minus_slow_ticks_5m`
3. `htf__rsi_14_5m`
4. `htf__distance_to_prior_day_high_ticks`
5. `htf__distance_to_session_high_ticks`
6. `htf__opening_range_position_pct`

**Critical:** `session_high` is "high so far only," never the final session high. `session_vwap` is VWAP-so-far. `opening_range_position_pct` is valid only after the opening range window closes; otherwise null + an availability flag in metadata (NOT a feature).

### F. Cross-asset context (3)

1. `xasset__NQ_minus_ES_ret_z_300s`
2. `xasset__ZN_ret_z_300s`
3. `xasset__risk_off_score_300s`

```
risk_off_score_300s = z(ZN_ret_300s) - z(equity_basket_ret_300s)
equity_basket       = mean(z-scored returns of ES/NQ/YM/RTY)
```

### G. Session / time (3)

1. `time__sin_time_of_day`
2. `time__minutes_since_rth_open`
3. `time__rth_edge_bucket` ∈ {0=normal, 1=first_15m_rth, 2=last_30m_rth}

### H. Lagged detector performance (2)

1. `hist__detector_win_rate_50`
2. `hist__detector_mean_mae_r_50`

**Strict rule:** for trade `i`, these features may only use trades whose `label_end < ts_signal_i`. No same-day future leakage. No completed-later-but-started-earlier leakage.

### I. MBO tail-risk features (5) — NEW in v0

Computed only where MBO data is available (~2026-01-01 onward, growing). Missing for trades outside that window → `null` + `mbo_available=False` flag.

1. `mbo__side_cancel_rate_60s` — side-liquidity cancel rate, predicts adverse flow
2. `mbo__add_to_cancel_ratio_60s` — passive aggression intent (high = adds being pulled, thinner than book looks)
3. `mbo__opposite_iceberg_refills_300s` — hidden size replenishing against you
4. `mbo__seconds_since_side_sweep` — recent liquidity sweep on entry side = mean-reversion risk
5. `mbo__l2_to_l5_imbalance_shift_60s` — institutional intent visible in deeper book changes

**Reusable code:** `experiments/mbo_features_v0/scan.py` already computes `cancel_to_trade`, `add_to_cancel`, `aggressive_buy_ratio`, and `iceberg_proxy` per 1-minute bin from raw DBN. Adapt that logic for the rolling 60s/300s windows on the trade-decision side; do not start from scratch.

### Availability flag (metadata, not a feature)

```
mbo_available : bool
```

Tells the model when MBO features are real vs null. LightGBM handles `null` natively.

### Expansion candidates (NOT in v0)

Locked out until baselines saturate:
- More MBP-1 windows (15s, 300s, 900s, 3600s)
- More cross-asset features (CL, GC, ZB, ZF, ZT, NG, HG)
- Zone/FVG geometry features
- More detector history windows (20, 100, 250)
- TSFM embeddings
- Path B (6-year OHLCV-only training)

---

## §3. Walk-Forward Splits — Path A Expanding Window

Training universe: detector-fired trades with full MBP-1 feature availability, 2025-05-01 → 2026-05-22 (~13 months).

### Folds (4 folds + final holdout)

```
Fold 1: Train 2025-05-01 → 2025-09-30  Val 2025-10-01 → 2025-10-31  Test 2025-11-03 → 2025-11-28
Fold 2: Train 2025-05-01 → 2025-10-31  Val 2025-11-03 → 2025-11-28  Test 2025-12-01 → 2025-12-31
Fold 3: Train 2025-05-01 → 2025-11-28  Val 2025-12-01 → 2025-12-31  Test 2026-01-02 → 2026-01-30
Fold 4: Train 2025-05-01 → 2025-12-31  Val 2026-01-02 → 2026-01-30  Test 2026-02-02 → 2026-02-27

Final untouched holdout:
  Train/val selection complete using Fold 1–4 only.
  Refit on:   2025-05-01 → 2026-02-27
  Holdout on: 2026-03-02 → 2026-05-22
```

### Embargo

```
embargo = max(1 full trading session, T_cap_i, max_feature_lookback)
       = 1 full trading session  (with T_cap=60min and max_window=900s)
```

### Purge

For every split boundary:
- Drop from train any trade whose `label_interval_i = [ts_entry_i, label_end_i]` overlaps validation/test
- Drop from val/test any trade whose features require unavailable warmup

A training sample is invalid for a test window if `label_interval_i ∩ test_time_window ≠ ∅`.

### Roll-boundary handling

Symbols are Databento continuous `.c.0`, **not back-adjusted**. Roll artifacts will create fake returns, fake MAE, and fake stop/target hits if not handled.

```
exclude_roll_day_default      = true
exclude_day_before_roll_default = false
```

Exclude samples where `instrument_id` changes during the label interval.

---

## §4. Type A vs Type B Differential Treatment

**Hard rule:** do NOT train a single pooled model that treats Type A and Type B the same. Use a shared dataset schema with separate heads and objectives.

### Detector family config

Maintained in `detector_families.yaml`. Unknown detectors default to `family_type = UNKNOWN` and are **excluded from training** until explicitly mapped.

Confirmed mappings (2026-05-16 audit):
| Detector | Family | Notes |
|---|---|---|
| `ogap_rejection` | A | v8a model gets +79R/6yr |
| `ob_break_continuation` | B | Confirmed Type B |
| `fvg_zone_reaction` | B | Headline edge +10,420R / 6yr / 69K trades |
| `swing_pivot_break_reversed` | B | Confirmed Type B, direction flipped |

### Type A head

Allowed objectives:
- `y_bad` classifier
- `y_mae_r` quantile regressor (q50, q80)
- `y_time_to_target_sec` regressor or bucket classifier
- `y_target_before_stop` classifier (where non-null)

Primary deployment output:
```
risk_score_A = weighted combination of:
    p_bad
    pred_mae_r_q80
    slow_target_penalty
    1 - p_target_before_stop
```

### Type B head

Allowed objectives:
- `y_tail` classifier
- `pred_mae_r_q80` / `pred_mae_r_q95` quantile regressor

Primary deployment output:
```
tail_risk_score_B = weighted combination of:
    p_tail
    pred_mae_r_q95
```

**Type B sizing must be conservative:** most trades keep `size_mult = 1.0`. Only extreme predicted tail-risk trades get reduced or skipped.

---

## §5. Baseline Ladder

Every stage reports SEPARATELY for: all trades, Type A only, Type B only, each detector family (FVG zone_reaction especially), each symbol. No single aggregate metric is allowed to hide a Type B edge being damaged.

| # | Baseline | What it answers |
|---|---|---|
| 0 | Current engine (`size_mult=1.0`) | Benchmark |
| 1 | Static `f(detector, family, symbol, session)` sizing | Can simple grouping beat current? |
| 2 | OHLCV-only feature subset (no MBP-1) | Is bar context enough? |
| 3 | + MBP-1 same-symbol features | Does top-of-book order-flow help? |
| 4 | + cross-asset features | Does futures-board context help? |
| 5 | + MBO tail-risk features + calibrated family policy | Does MBO add tail-risk lift? |

### Type A sizing policy (v0 example)

```
if p_bad >= 0.65 or pred_mae_r_q80 >= 1.20:
    size_mult = 0.0
elif p_bad >= 0.55 or pred_mae_r_q80 >= 0.90:
    size_mult = 0.5
elif p_bad <= 0.35 and pred_mae_r_q80 <= 0.60:
    size_mult = 1.0
else:
    size_mult = 0.75
```

### Type B sizing policy (v0 example)

```
if p_tail >= 0.80 or pred_mae_r_q95 >= 2.50:
    size_mult = 0.0
elif p_tail >= 0.70 or pred_mae_r_q95 >= 2.25:
    size_mult = 0.5
else:
    size_mult = 1.0
```

Type B default = take the trade at full size unless predicted tail risk is extreme.

### Forbidden in v0
- `size_mult > 1.0`
- direction flipping
- new trade creation
- generic Type B good/bad filtering

---

## §6. Kill Criteria

### Type A — success requires expectancy/risk improvement

**Statistical (Type A):**
- Median fold ROC-AUC for `y_bad` ≥ 0.57
- ≥ 3 of 4 folds ROC-AUC > 0.53
- Brier score improves ≥ 2% vs static detector baseline
- Calibration ECE ≤ 0.07
- Median Spearman IC between predicted risk and realized MAE_R ≥ 0.08
- ≥ 3 of 4 folds positive IC

**Economic (Type A):**
- `net_R` improves ≥ 5%
- `max_drawdown_R` improves ≥ 10%
- MAR-like ratio improves ≥ 15%
- 95th-percentile daily loss improves ≥ 10%
- Trade count retained ≥ 60%

**Type A ship threshold:** `net_R` ≥ +8%, `max_drawdown_R` ≥ +12%, MAR ≥ +20%, positive in ≥ 3 of 4 folds, no single fold contributes > 40% of total improvement.

**Type A kill:** Median ROC-AUC ≤ 0.53, median IC ≤ 0.03, economic lift < 2%, benefit only in one month, model only learns detector identity / time of day and MBP-1 adds no lift.

### Type B — success requires tail-risk reduction WITHOUT eroding aggregate +R

**Statistical (Type B):**
- Median fold ROC-AUC for `y_tail` ≥ 0.58
- ≥ 3 of 4 folds ROC-AUC > 0.54
- Top predicted-tail decile has ≥ 1.5x realized tail rate vs bottom half
- Calibration ECE ≤ 0.08

**Economic (Type B):**
- `p95_MAE_R` reduced ≥ 8%
- `p99_MAE_R` reduced ≥ 5%
- `tail_R_loss` reduced ≥ 10%
- `net_R` erosion ≤ 3%
- Trade count retained ≥ 85%

**Type B ship threshold:** `tail_R_loss` ≥ -15%, `p95_MAE_R` ≥ -10%, `net_R` erosion ≤ 2% or improves, trade count retained ≥ 90%, **effect holds for FVG zone_reaction separately**.

**Type B kill:** `net_R` erosion > 5%, trade count retained < 80%, tail-risk reduction comes mostly from skipping normal winners, FVG zone_reaction aggregate +R deteriorates materially, tail prediction works in only one fold/month, model behaves like generic good/bad selector instead of rare tail filter.

**Hard Type B rule:** if the Type B conditioner reduces the headline edge by filtering ordinary trades, kill it or restrict to shadow mode permanently.

---

## §7. Engine Integration

The model output is a **sizing annotation**, not a signal.

### Offline prediction artifact

Write to `experiments/risk_conditioner_v0/out/predictions/`.

Columns:
```
trade_id, symbol, ts_signal, ts_decision, detector_name, family_type, side
model_name, model_version, feature_version, label_version, fold_id
p_bad, p_tail, p_target_before_stop
pred_mae_r_q50, pred_mae_r_q80, pred_mae_r_q95
pred_ttt_sec_q50, pred_ttt_sec_q80
risk_score, tail_risk_score, size_mult, skip_reason, prediction_created_at
```

Type A rows may have null Type B fields; Type B rows may have null Type A fields.

### Output contract

```
risk_score      ∈ [0, 1]
tail_risk_score ∈ [0, 1]
size_mult       ∈ {0.0, 0.25, 0.5, 0.75, 1.0}
```

### Dispatch

```
family_type = detector_family_config[signal.detector_name].family_type

if family_type == "A":
    pred = risk_conditioner_type_a.predict(ctx.features)
    size_mult = policy_type_a(pred)
elif family_type == "B":
    pred = tail_conditioner_type_b.predict(ctx.features)
    size_mult = policy_type_b(pred)
else:
    size_mult = 1.0
    status = "unknown_family_fallback"
```

### Strategy.on_bar() consumption

```python
if signal:
    ctx = build_trade_context(signal, bar_context, feature_store)
    family_type = detector_family_config.get(signal.detector_name)
    risk_pred = risk_conditioner.predict_or_lookup(
        symbol=ctx.symbol,
        ts_decision=ctx.ts_decision,
        detector_name=ctx.detector_name,
        family_type=family_type,
        side=ctx.side,
        features=ctx.features,
    )
    size_mult = risk_pred.size_mult if risk_pred.available else 1.0
    if size_mult <= 0:
        log_skipped_signal(signal, risk_pred)
        return None
    order_qty = floor(base_qty(signal) * size_mult)
    if order_qty <= 0:
        log_skipped_signal(signal, risk_pred)
        return None
    return OrderIntent(
        symbol=signal.symbol, side=signal.side, qty=order_qty,
        entry=signal.entry, stop=signal.stop, target=signal.target,
        metadata={
            "risk_model_version": risk_pred.model_version,
            "family_type": family_type,
            "risk_score": risk_pred.risk_score,
            "tail_risk_score": risk_pred.tail_risk_score,
            "p_bad": risk_pred.p_bad,
            "p_tail": risk_pred.p_tail,
            "pred_mae_r_q80": risk_pred.pred_mae_r_q80,
            "pred_mae_r_q95": risk_pred.pred_mae_r_q95,
            "size_mult": size_mult,
        },
    )
```

### Fallback rule (no silent failure)

```
If model unavailable, stale, or feature row missing:
    size_mult = 1.0
    risk_model_status = "missing_fallback"  (explicit logged)
```

---

## §8. Rollout Stages

| Stage | Behavior |
|---|---|
| 1. Shadow | Model predicts. Engine logs. No sizing impact. |
| 2. Skip only | `size_mult ∈ {0, 1}`. Skip extreme-risk trades only. |
| 3. Downsize ladder | `size_mult ∈ {0, 0.25, 0.5, 0.75, 1.0}` |
| 4. Size > 1.0 | **Not allowed in v0.** Requires separate study. |

For prop-firm use, never allow `size_mult > 1.0` in v0. Passing evaluations is about not breaching, not maximizing raw expectancy.

---

## §9. Sample-Count Viability Check

Before any modeling, produce a report:
- trades by detector, family_type, symbol, month, fold, session bucket
- target / stop / timeout distribution
- MAE_R distribution
- tail event distribution (for Type B)

**Minimum viability:**

Type A:
- ≥ 500 trades per main detector family across train
- ≥ 100 test trades per fold aggregate

Type B:
- ≥ 2,000 trades per major Type B family across train
- ≥ 50 realized `y_tail=1` examples per train fold
- ≥ 20 realized `y_tail=1` examples per test fold aggregate

**Special rule:** FVG `zone_reaction` is always reported separately. Never allow pooled model results to hide deterioration in this family.

---

## §10. Five Ambiguities — RESOLVE BEFORE CODING

These are the audits to run before any model training. Output goes in `report/v0_iter1_ambiguities.md`.

### 1. Exact definition of R

Inspect existing engine output:
- Where does the stop come from?
- Is stop fixed, ATR-based, structure-based, zone-based, or detector-specific?
- Can every signal produce `planned_stop_price` before entry?

If no true planned stop exists, populate `stop_defaults.yaml` per symbol.

### 2. Exact execution timestamp

One canonical rule:
- Signal generated on bar close?
- Entry at next bar open?
- Entry at bid/ask?
- Market order or limit order?
- Latency assumption?

Default (until inspection says otherwise):
```
ts_decision = signal bar close
ts_entry    = first executable quote after ts_decision
long entry  = ask
short entry = bid
```

### 3. Real exit logic

Determine whether labels follow: existing strategy target/stop, triple-barrier synthetic, time exit, session close, prop-firm forced flat time.

Default: use existing strategy stop/target if available. Otherwise use `stop_defaults.yaml`. Always cap at `T_cap = 60 minutes`.

### 4. Continuous-contract roll boundaries

Inspect Parquet for: `instrument_id`, `raw_symbol`, roll date, stype metadata.

If `instrument_id` changes inside a label window: exclude sample by default.

### 5. Usable trades per detector/family/fold

Run the §9 sample-count check. If Type B tail events are too few in any fold, do NOT force a model — keep Type B in shadow and report insufficiency.

---

## §11. Codex Instruction Block

Send the following to Codex (Claude Code) when ambiguities §10 are resolved and configs are populated:

```
Build risk_conditioner_v0 per experiments/risk_conditioner_v0/PLAN.md.

Hard constraints:
- Do not build a new signal generator.
- Do not build TSFM yet.
- Do not train on MBO as the primary v0 dataset (use MBP-1 backbone + 5 MBO features).
- Use Path A only.
- No Path B in v0.
- No feature expansion beyond the locked 45.
- No direction flipping.
- No size increase above 1.0.
- No silent fallback.
- No generic Type B good/bad classifier.

Tasks (in order):
 1. Inspect engine signal/trade schema; finalize stop_defaults.yaml.
 2. Build trade universe (build_trade_universe.py) from detector fires
    in Path A date range. Output out/trades_universe.parquet.
 3. Build labels (build_labels.py): y_mae_r, y_bad, y_tail,
    y_time_to_target_sec, y_target_before_stop. Output out/labels.parquet.
 4. Build features (build_features.py): exactly 45, computed only on
    information ≤ ts_decision. Output out/features.parquet.
 5. Implement walk-forward folds with purge + 1-session embargo from
    walk_forward.yaml.
 6. Exclude continuous-contract roll-boundary samples.
 7. Train baseline ladder (train_walkforward.py) for both Type A and
    Type B heads. Save predictions per fold.
 8. Evaluate per family / per symbol / per detector. Compare against
    §6 kill criteria.
 9. Write Strategy.on_bar() adapter (integration.py).
10. Write QA tests (qa.py) covering no-lookahead, label alignment,
    purge integrity, roll exclusion, missing-feature fallback, lagged
    detector strictness, and Type A/B dispatch correctness.

Report metrics separately for all-trades / Type A / Type B / each
detector family (FVG zone_reaction especially) / each symbol.
```

---

## Notes / context

- Existing MBO feature scanner at `experiments/mbo_features_v0/scan.py` already computes 4 of the 5 v0 MBO features (cancel_to_trade, add_to_cancel, aggressive_buy_ratio, iceberg_proxy) per 1-minute bin from raw DBN. Adapt that logic for the rolling 60s/300s windows on the trade-decision side.
- Atlas v0 outputs (`experiments/atlas_v0/out/atlas_predictions.parquet`) and Mira features may eventually be useful inputs, but they're NOT in the v0 feature schema. Add only after baselines saturate.
- BacktestStation engine purity rules apply: this experiment must not import from `backend/app/db/`, `backend/app/api/`, or `backend/app/ingest/`. Read Parquet artifacts and use `backend/app/engine/` interfaces only.

---

**Updated:** 2026-05-26
**Owner:** Ben Brainard
**Reviewers:** GPT Pro (research design), Codex / Claude Code (implementation)
