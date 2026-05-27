# risk_conditioner_v0 — Iteration 1 Ambiguities Audit

Generated: 2026-05-27T05:56:42.350829+00:00

This report resolves PLAN.md §10 ambiguities. Sections marked **MANUAL REVIEW REQUIRED** still need human inspection — automation can only narrow the candidate set.

---

## 1. Stop source

**Status:** ⚠️ MANUAL REVIEW REQUIRED

**Summary:** Found 8 files with stop-related assignments. Manual review still required to pick the canonical stop source per detector family, but the candidate list is now narrow.

**Candidate files (8):**

- `backend/app/strategies/composable/config.py` (2 hits)
  - L168: `stop=_parse_stop(raw.get("stop", {"type": "fixed_pts"})),`
  - L252: `stop_pts=float(raw.get("stop_pts", 10.0)),`
- `backend/app/strategies/composable/strategy.py` (2 hits)
  - L256: `stop_price = self._compute_stop(direction, ep, merged_metadata)`
  - L269: `stop_price=stop_price,`
- `backend/app/strategies/examples/moving_average_crossover.py` (3 hits)
  - L57: `stop_ticks=int(params.get("stop_ticks", 8)),`
  - L95: `stop_price=entry_estimate - self.stop_ticks * self.tick_size,`
  - L106: `stop_price=entry_estimate + self.stop_ticks * self.tick_size,`
- `backend/app/strategies/fractal_amd/strategy.py` (3 hits)
  - L361: `stop = setup.fvg_high + self.config.stop_buffer_pts`
  - L366: `stop = setup.fvg_low - self.config.stop_buffer_pts`
  - L418: `stop_price=stop,`
- `backend/app/backtest/broker.py` (2 hits)
  - L244: `stop = order.intent.stop_price`
  - L247: `stop_touched = current_bar.low <= stop <= current_bar.high`
- `backend/app/backtest/engine.py` (4 hits)
  - L364: `stop_price = None`
  - L369: `stop_price = order.intent.stop_price`
  - L378: `stop_price=stop_price,`
- `backend/app/backtest/events.py` (1 hits)
  - L23: `STOP_HIT = "stop_hit"`
- `backend/app/backtest/runner.py` (1 hits)
  - L398: `stop_price=t.stop_price,`

---

## 2. Execution timestamp rule

**Status:** ✅ resolved / auto-extracted

**Summary:** Strategy interface confirms bar-close → next-bar-open execution by default. BracketOrder.fill_immediately option exists (Fractal AMD uses it) — Codex must check per detector whether next-bar-open or same-bar-open is the right convention.

**Default rule (PLAN.md §10):**

```
Engine is bar-driven. on_bar(bar, context) fires AFTER bar.ts_event with bar.close known.
  ts_signal   = bar.ts_event (current bar close)
  ts_decision = bar.ts_event (same bar — strategy emits OrderIntent here)
  ts_entry    = next bar's open  (BracketOrder fills at next-bar open + slippage)
  EXCEPTION:  fill_immediately=True fills on the SAME bar's open (FractalAMD pattern).
              For v0, we treat this as a per-detector config — must verify per family.
```

**Bar dataclass** (backend/app/backtest/strategy.py):

```python
@dataclass(frozen=True)
class Bar:
    """One OHLCV bar. The Strategy only ever sees the current bar.

    Frozen so strategies can't mutate it. Fields mirror the bar parquet
    written by `app.ingest.parquet_mirror`.
    """

    ts_event: dt.datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    trade_count: int
    vwap: float



```

**Strategy.on_bar signature** (backend/app/backtest/strategy.py):

```python
def on_bar(self, bar: Bar, context: Context) -> "list[OrderIntent]":
        """Called for each bar. Return any orders you want to submit."""
        return []
```

**BracketOrder dataclass (fill_immediately, max_hold_bars)** (backend/app/backtest/orders.py):

```python
@dataclass(frozen=True)
class BracketOrder:
    """Market entry + atomic OCO stop and target.

    The engine fills the entry on the next bar's open, then watches
    subsequent bars for stop or target. Per CLAUDE.md §8, when a bar
    contains both stop and target levels, the conservative default is
    that the stop wins and `Fill.fill_confidence = "conservative"`.

    `contract_value` overrides the run-wide `RunConfig.contract_value`
    for this order's PnL math. Set this when a strategy wants to
    downshift to a different contract on a per-trade basis (e.g.
    Fractal AMD switching from NQ at $20/pt to MNQ at $2/pt for
    wide-stop setups so dollar risk stays inside the configured cap).
    `None` means use the run config's value.

    `max_hold_bars`: if set, the bracket force-closes at the bar's close
    once `bar_index - entry_bar_index >= max_hold_bars` (i.e., the
    position has been held for `max_hold_bars` complete bars after the
    entry-fill bar). The exit fill is recorded with `reason="timeout"`
    and `fill_confidence="exact"`. Mirrors `MAX_HOLD=120` in the trusted
    Fractal AMD backtest. `None` (default) = no timeout.

    `fill_immediately`: when True, the broker fills the entry on the
    SAME bar the order is submitted (at that bar's open + slippage)
    rather than next bar. Stop/target watch starts from the NEXT bar
    onward — the entry bar itself is excluded from the bracket-resolve
    range check because bar.open is the entry price and you can't
    legitimately stop or target on the same bar with OHLC-only data.
    Mirrors trusted Fra
```

---

## 3. Real exit logic

**Status:** ⚠️ MANUAL REVIEW REQUIRED

**Summary:** Found 10 exit-related references. Manual review still required to confirm session-close / forced-flat handling matches PLAN.md §1 label window.

**Default rule (PLAN.md §10):**

```
Default exit priority (earliest hit wins):
  1. target_price touched
  2. stop_price touched
  3. max_hold_bars timeout (per BracketOrder spec — exits at bar close with reason='timeout')
  4. T_cap = 60 minutes (PLAN.md default for labels)
  5. session close / forced flat time (must verify if engine enforces)
Conservative rule (CLAUDE.md §8): when stop and target are both reachable in same bar, stop wins; fill_confidence='conservative'.
```

**Exit-logic references:**

- `fill_immediately` — 2 hits
  - backend/app/backtest/orders.py:68  ``fill_immediately`: when True, the broker fills the entry on the`
  - backend/app/backtest/orders.py:86  `fill_immediately: bool = False`
- `max_hold_bars` — 5 hits
  - backend/app/backtest/orders.py:61  ``max_hold_bars`: if set, the bracket force-closes at the bar's close`
  - backend/app/backtest/orders.py:62  `once `bar_index - entry_bar_index >= max_hold_bars` (i.e., the`
  - backend/app/backtest/orders.py:63  `position has been held for `max_hold_bars` complete bars after the`
- `timeout` — 3 hits
  - backend/app/backtest/orders.py:64  `entry-fill bar). The exit fill is recorded with `reason="timeout"``
  - backend/app/backtest/orders.py:66  `Fractal AMD backtest. `None` (default) = no timeout.`
  - backend/app/backtest/orders.py:122  `# `BracketOrder.max_hold_bars` timeout. None until the entry fills.`

---

## 4. Continuous-contract roll boundaries

**Status:** ✅ resolved / auto-extracted

**Summary:** Inspected MBP-1 parquet schema for ES/NQ/YM/RTY. Look at per_symbol[*].has_instrument_id and n_distinct_instrument_ids_sample — if instrument_id changes across the year, those transitions are the roll boundaries. Strategy: exclude label-window samples where instrument_id changes during the window.

**Per-symbol findings:**

- **ES.c.0**: status=read_error: ArrowTypeError: Unable to merge: Field symbol has incompatible types: string vs dictionary<values=string, indices=int32, ordered=0>
- **NQ.c.0**: status=read_error: ArrowTypeError: Unable to merge: Field symbol has incompatible types: string vs dictionary<values=string, indices=int32, ordered=0>
- **YM.c.0**: status=read_error: ArrowTypeError: Unable to merge: Field symbol has incompatible types: string vs dictionary<values=string, indices=int32, ordered=0>
- **RTY.c.0**: status=read_error: ArrowTypeError: Unable to merge: Field symbol has incompatible types: string vs dictionary<values=string, indices=int32, ordered=0>

---

## 5. Sample counts per detector × family × fold

**Status:** ✅ resolved / auto-extracted

**Summary:** Wrote sample counts to experiments/risk_conditioner_v0/out/sample_counts.parquet. 14,940 (detector, symbol, day) rows aggregated. See viability table for thresholds (Type A ≥ 500, Type B ≥ 2000).

**Counts parquet:** `experiments/risk_conditioner_v0/out/sample_counts.parquet`

**Per-detector totals (Path A window 2025-05-01 → 2026-05-22, 4 index symbols):**

```
  forming_volume_profile               family=UNKNOWN  n=    29,666  (excluded — needs audit)
  fvg_formation                        family=UNKNOWN  n=    26,286  (excluded — needs audit)
  liquidity_sweep                      family=UNKNOWN  n=    11,741  (excluded — needs audit)
  order_block                          family=UNKNOWN  n=    10,220  (excluded — needs audit)
  smt_prev_candle_divergence           family=UNKNOWN  n=    10,130  (excluded — needs audit)
  swing_pivot                          family=UNKNOWN  n=     9,112  (excluded — needs audit)
  volume_profile                       family=UNKNOWN  n=     4,586  (excluded — needs audit)
  displacement_candle                  family=UNKNOWN  n=     4,453  (excluded — needs audit)
  interval_true_range                  family=UNKNOWN  n=     4,268  (excluded — needs audit)
  opening_range_breakout               family=UNKNOWN  n=     4,016  (excluded — needs audit)
  psp_candle_divergence                family=UNKNOWN  n=     2,314  (excluded — needs audit)
  time_profile                         family=UNKNOWN  n=     2,284  (excluded — needs audit)
  first_third_range                    family=UNKNOWN  n=     1,224  (excluded — needs audit)
  opening_gap_levels                   family=UNKNOWN  n=     1,141  (excluded — needs audit)
  smt_htf_reference_divergence         family=UNKNOWN  n=       355  (excluded — needs audit)
```

**Per-detector × symbol top 30:**

| detector | symbol | family | n |
|---|---|---|---|
| forming_volume_profile | NQ.c.0 | UNKNOWN | 7,418 |
| forming_volume_profile | RTY.c.0 | UNKNOWN | 7,416 |
| forming_volume_profile | YM.c.0 | UNKNOWN | 7,416 |
| forming_volume_profile | ES.c.0 | UNKNOWN | 7,416 |
| fvg_formation | RTY.c.0 | UNKNOWN | 6,863 |
| fvg_formation | YM.c.0 | UNKNOWN | 6,825 |
| fvg_formation | NQ.c.0 | UNKNOWN | 6,384 |
| fvg_formation | ES.c.0 | UNKNOWN | 6,214 |
| smt_prev_candle_divergence | ES.c.0 | UNKNOWN | 4,674 |
| liquidity_sweep | ES.c.0 | UNKNOWN | 2,995 |
| liquidity_sweep | NQ.c.0 | UNKNOWN | 2,992 |
| liquidity_sweep | YM.c.0 | UNKNOWN | 2,879 |
| liquidity_sweep | RTY.c.0 | UNKNOWN | 2,875 |
| order_block | ES.c.0 | UNKNOWN | 2,604 |
| order_block | NQ.c.0 | UNKNOWN | 2,563 |
| order_block | YM.c.0 | UNKNOWN | 2,527 |
| order_block | RTY.c.0 | UNKNOWN | 2,526 |
| swing_pivot | YM.c.0 | UNKNOWN | 2,317 |
| swing_pivot | RTY.c.0 | UNKNOWN | 2,291 |
| swing_pivot | NQ.c.0 | UNKNOWN | 2,290 |
| swing_pivot | ES.c.0 | UNKNOWN | 2,214 |
| smt_prev_candle_divergence | RTY.c.0 | UNKNOWN | 2,007 |
| smt_prev_candle_divergence | NQ.c.0 | UNKNOWN | 1,911 |
| smt_prev_candle_divergence | YM.c.0 | UNKNOWN | 1,538 |
| volume_profile | NQ.c.0 | UNKNOWN | 1,148 |
| volume_profile | ES.c.0 | UNKNOWN | 1,146 |
| volume_profile | RTY.c.0 | UNKNOWN | 1,146 |
| volume_profile | YM.c.0 | UNKNOWN | 1,146 |
| displacement_candle | RTY.c.0 | UNKNOWN | 1,118 |
| displacement_candle | YM.c.0 | UNKNOWN | 1,117 |

---

## Open decisions (post-audit)

Codex (or you) must still pick:

1. **stop_defaults.yaml** — per-symbol fallback stop sizes (PLAN §10.1).
2. **Per-detector entry rule** — `fill_immediately=True` vs next-bar-open (PLAN §10.2).
3. **Session-close / forced-flat behavior** — confirmation against engine source (PLAN §10.3).
4. **Roll-boundary exclusion logic** — implement based on §4 findings (PLAN §10.4).
5. **Type B family expansion** — re-audit detectors that are currently UNKNOWN in detector_families.yaml.
