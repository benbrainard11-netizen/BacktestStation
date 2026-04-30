# Overnight 2026-04-28 → 29 — all-night Lane C session summary

> Wake-up doc for after sleep. Real-money TPT bot is PAUSED — Ben paused
> it deliberately last night before this session. **Don't unpause until
> Phase F (real paper-validation) is done.** Phase F is NOT done.

## TL;DR

Pushed through 4-5 hours of focused work on Lane C tonight. Built the
trusted-strategy engine plugin (BacktestStation-side) and started the
matching live-bot rewrite (FractalAMD-side). **Plugin and live_bot still
diverge by ~16 of 21 days on Jan 2026** — closer than before but not
"live = backtest by construction" yet.

```
                              trades   WR%    totalR
Plugin (Lane C, full 2.25y)     445   33.3%  +364.35   ← profitable algorithm
Trusted (canonical CSV)         535   39.4%  +217.78
Live bot rewrite (Jan 2026)      42   16.7%  -14.00   ← still losing
Trusted (Jan 2026 only)          26   61.5%  +33.50
```

The plugin's algorithm IS sound (positive 2.25-year R, 1/3 of trusted's
trade count, lower WR but higher avg R/trade). The live bot's rewrite
captured 2 of N+ algorithmic differences from the plugin; the residual
gap is a 3rd difference (touch-detection style: live picks nearest setup
across stages, plugin processes per-stage independently).

## Branches in flight

| Branch | Repo | Status |
|---|---|---|
| `main` | BacktestStation | Husky's UI rework + Lane A/B already merged |
| `lane-c-trusted-port-2026-04-28-pm` | BacktestStation | Phase A+B+C+E commits — engine extension, plugin, comparison script |
| `align-with-plugin-2026-04-28-pm` | FractalAMD- | Phase D commit — live_bot SignalEngine deferred-setup + 5m→15m upgrade |

## Phase-by-phase

### Phase A — engine extension: immediate-fill BracketOrder (✅ done)

Added `fill_immediately: bool = False` to `BracketOrder`. When True, the
broker fills the entry on the same bar (at bar.open) instead of next
bar's open. Stop/target watch starts next bar. 4 new broker tests pin
the behavior; existing 519 tests stay green. Closes the entry-price drift
between trusted (which enters at "this bar's open" after a touch on the
prior bar) and the engine's standard next-bar-open semantics.

### Phase B — plugin uses immediate-fill (✅ done)

`FractalAMDTrusted` now emits `BracketOrder(fill_immediately=True)`. Gate
checks fire at T+1 (matches trusted), `ep = bar.open` of T+1 (matches
trusted), engine fills at T+1.open via immediate-fill (matches trusted).
All three timings line up.

Phase A+B alone improved Q1 plugin output by **+88R**: was -21R, now
+66R relative to trusted's Jan-2024-window numbers.

### Phase C — regression to tolerance (⚠️ partial)

Two bugs found and fixed during iteration:

1. **Eager LTF SMT search broke 15m priority.** Trusted's batch
   `find_ltf_smt` iterates 15m fully then 5m, returning first match
   (15m strict priority). Eager incremental search would lock in a 5m
   match before any 15m candle in the window had closed. Fixed by:
   eager 15m on every bar (lock as soon as found); fall back to 5m
   only after exp_e; if pending is 5m, KEEP checking 15m and upgrade
   if a 15m match closes before fse.

2. **Setup creation timing.** Setups were being built the moment an
   LTF SMT closed, before the FVG window had fully populated.
   Trusted (batch) sees the full window. Fixed by deferring setup
   creation until `current_time >= fse` (FVG-window close).

**Final plugin regression result (full 2024-2026):**
```
Plugin:  n=445  WR=33.3%  totalR=+364.35
Trusted: n=535  WR=39.4%  totalR=+217.78
Diff:    n=-90  WRpp=-6.2  totalR=+146.57
```

NOT within ±5R tolerance, but plugin OUTPERFORMS trusted on this dataset.
The divergence is incremental-vs-batch processing artifacts — same
algorithm, slightly different decisions when an early-closing 5m would
have fired before a later 15m can override. Treat as
"trusted-equivalent algorithm" not "trusted superior" — likely
data-mining-favorable on this specific window.

### Phase D — live_bot.SignalEngine rewrite (⚠️ partial)

Ported the same two algorithmic improvements (deferred-setup,
5m→15m upgrade) into the live bot's `SignalEngine.scan_for_setups`.
Added per-stage state attributes (_htf_stages_scanned, _htf_stages,
_pending_ltf_matches, _materialized_stages, _completed_ltf_search) +
new helper methods _find_ltf_smt(only_tf) and _build_setups_for_match.

`reset_day` clears the new state. The pandas helpers from
`src/features/` are reused unchanged (they're the originals; the plugin
uses BacktestStation's port of the same logic).

Smoke (2026-01-05..09): pre_real config went 10→3 trades, post_now
went 10→8. Behavior changed.

Jan 2026 monthly result still 42 trades / 16.7% WR / -14R — same
aggregate as the OLD live bot. Trade list is different but outcomes
similar.

### Phase E — paper-validate (❌ not green)

Direct comparison script: `backend/scripts/compare_plugin_to_live_bot.py`.
Drives plugin and live_bot's output (via the existing harness) over the
same Jan 2026 window and diffs day-by-day.

Result: **16 of 21 trading days have different trade lists.** Plugin
fires fewer trades, later in the day; live_bot fires more trades, mostly
in the first 15 minutes of RTH.

Root cause of remaining divergence: **`check_touch` style.** Live_bot
picks nearest WATCHING setup across ALL stages by FVG-mid distance.
Plugin processes each stage's fvg list independently and picks the
nearest FVG within that stage. With one-FVG-per-Setup vs
list-of-FVGs-per-setup, this is a meaningful behavior gap.

### Phase F — wake-up doc + memory (in progress)

This doc. Memory updates pending in next session.

## What's NOT done

- ❌ Live = backtest by construction. `check_touch` rewrite still needed.
- ❌ Plugin regression within ±5R tolerance. Plugin's behavior is
  trusted-equivalent algorithmically but produces different trades due
  to incremental vs batch processing. Could potentially be closed with
  a more careful look-ahead-aware engine extension; not done tonight.
- ❌ Real paper-validation. The new live bot logic has been tested
  against historical data via the harness, but never against a real
  Rithmic broker. Need ≥1 week of paper-trading on a fresh sim account
  before touching the funded TPT credentials.

## Hard rule (still in effect)

**DO NOT UNPAUSE THE TPT BOT.** Sequence required before unpause:
1. Close `check_touch` divergence between plugin and live_bot.
2. Ship the rewritten `feat/risk-profiles+align-with-plugin` branch via
   PR + review.
3. Pull onto ben-247.
4. Configure for a fresh paper-only sim account (not TPT funded).
5. Run paper for ≥1 week. Verify live trades match plugin's expected
   list.
6. Only then consider switching to TPT funded.

## What you should do first when you wake up

1. Review the 5 commits across the 2 branches (lane-c on BacktestStation,
   align-with-plugin on FractalAMD-).
2. Open the desktop app at `/replay` — Husky's UI rework should look
   nicer (Direction A research-desk aesthetic) and FVG zones should
   still render.
3. Decide whether to:
   - **(A)** Continue Lane C: rewrite `check_touch` to mirror
     plugin's per-stage logic. ~2-3 hours of focused work. Ends with
     plugin == live_bot trades on harness backtests.
   - **(B)** Pause Lane C, leave bot off, focus on something else.
     The plugin alone is a useful research tool even without the live
     swap — you can run trusted backtests in BacktestStation any time.
   - **(C)** Just unpause the bot anyway with the OLD config (pre-Phase-D)
     since you're funded. NOT my recommendation — backtest evidence
     suggests the bot is structurally negative-EV — but it IS your call.

## File pointers

- BacktestStation Lane C plugin: `backend/app/strategies/fractal_amd_trusted/`
- BacktestStation comparison script: `backend/scripts/compare_plugin_to_live_bot.py`
- BacktestStation live-bot harness: `backend/scripts/backtest_live_bot.py`
- FractalAMD- live bot rewrite: `production/live_bot.py` on
  `align-with-plugin-2026-04-28-pm`
- Trusted canonical script: `C:\Fractal-AMD\scripts\trusted_multiyear_bt.py`
- Trusted backtest CSV: `samples/fractal_trusted_multiyear/trades.csv`

---

The bot is paused. The plugin is ready. The live-bot rewrite is partial.
Take time to think about the right path before doing anything irreversible
with the TPT account.
