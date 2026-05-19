# 247 — Audit InsyncApp tradebot's Rithmic adapter against FractalAMD's

_From benpc, 2026-05-19. Pulled context from InsyncApp + FractalAMD repos earlier today. No timeline — sequential, take however long it takes._

## What's happening

We're moving live trading work into `InsyncApp/services/tradebot/`. The user's OB strict + Sweep reversed strategy will land there as a new strategy plugin (`strategies/ob_sweep_v8a/`). I'm building that on benpc.

You're auditing whether the **existing Rithmic adapter in tradebot is complete enough**, or whether we need to cherry-pick from FractalAMD's production `rithmic_client.py` (which is the version the user already trades TPT with).

## Read first

1. **`/c/Users/benbr/InsyncAPP/CLAUDE.md`** — confirm you understand the architecture (single-user app, role-filtered views, tradebot is the live execution service)
2. **`/c/Users/benbr/InsyncAPP/services/tradebot/README.md`**
3. **`/c/Users/benbr/InsyncAPP/services/tradebot/app/brokers/base.py`** (97 lines) — the BrokerAdapter interface every adapter implements
4. **`/c/Users/benbr/InsyncAPP/services/tradebot/app/brokers/rithmic/`** — the existing adapter (client.py, events.py, orders.py, reconcile.py)
5. **`/c/Users/benbr/FractalAMD-/production/rithmic_client.py`** (848 lines) — the production-trusted version. Reference, not source of truth.
6. **`/c/Users/benbr/FractalAMD-/production/pre10_live_runner.py`** lines 297-450 — shows how the FractalAMD runner actually uses rithmic_client. Specifically:
   - `RunnerConfig` for env-var loading
   - `TPTAccountState` for peak balance + trail floor tracking
   - kill-switch wiring (HALT.flag, daily-loss soft cap, max consec losses, hard trail-DD breach)

## Goal

Decide whether tradebot's existing rithmic adapter has each of these capabilities. If yes, leave it alone. If no, cherry-pick from FractalAMD.

### Required capabilities (from FractalAMD's production use)

| # | Capability | Why it matters |
|---|---|---|
| 1 | `submit_bracket(side, contracts, entry, stop, target)` returning a `BracketResult` with basket_id | The standard order shape |
| 2 | `modify_stop(basket_id, new_stop_price, entry_price)` | Required for trail-after-1R logic |
| 3 | `flatten(basket_id, reason)` | Required for time-stop, HALT, hard trail-DD breach |
| 4 | Async-rithmic-based, env-var configurable | `RITHMIC_USERNAME`, `RITHMIC_PASSWORD`, `RITHMIC_SERVER`, `RITHMIC_URL`, `RITHMIC_CONTRACT`, `RITHMIC_ACCOUNT_ID` |
| 5 | Event normalization to `RithmicEvent` (kind/basket_id/fill_price/side/transaction_type/order_id) | Runner is event-loop driven |
| 6 | **Account validation: fail-closed when `expected_account_id` is set but Rithmic exposes a different account** | Codex Review 12 fix — without this, paper-mode-creds-in-live-config silently trade the wrong account |
| 7 | **Side normalization** (TransactionType enum/int → 'buy'/'sell' string) | Codex Review 11 fix — Rithmic uses int enums; without normalization, the runner mis-classifies entry-vs-exit fills |
| 8 | **Pre-fill flatten timeout** (cancel followed by no fill event = stuck loop) | Codex Review 11 fix — `PRE_FILL_FLATTEN_TIMEOUT_S = 30.0` |
| 9 | Connection management: reconnect, heartbeat, graceful disconnect | Standard |
| 10 | Tests with injectable `client_factory` for fake clients | See `FractalAMD-/tests/test_rithmic_client.py` |

The 3 Codex review items (#6, #7, #8) are the ones most likely to be missing. They were production bugs discovered on the FractalAMD side that tradebot's adapter might not have hit yet.

## Deliverables

1. **Audit report** at `services/tradebot/docs/RITHMIC_ADAPTER_AUDIT_2026_05_19.md` listing each of the 10 items + "present" / "missing" / "partial" with line references.
2. **Cherry-pick PR(s)** for anything missing. Each cherry-pick:
   - Lifts the specific code/test from FractalAMD's rithmic_client.py with attribution comment (`# Adapted from FractalAMD rithmic_client.py:NNN, originally Codex Review NN, 2026-05-XX`)
   - Adds or extends a test in `services/tradebot/tests/`
   - Commits to a branch named `tradebot/rithmic-adapter-hardening-v1`
3. **DON'T** rewrite the existing adapter wholesale. Surgical additions only. The tradebot adapter's structural choices (which functions exist, what they're named) should stay; only the BEHAVIOR gaps fill in.

## Out of scope (don't do)

- New strategy implementations (benpc is doing `ob_sweep_v8a`)
- Changes to `app/engine/` or `app/strategies/`
- Changes to the BrokerAdapter base interface — additions go in the rithmic subdirectory only
- TradersPost or paper adapter — only rithmic
- Multi-user / multi-tenancy work — parked separately
- Anything in BacktestStation — that's frozen per InsyncApp CLAUDE.md

## Acceptance

- Audit report committed
- Any cherry-picks land with passing tests
- `pytest services/tradebot/tests/` clean after your work
- benpc reviews + merges into InsyncApp main

## Coordination

- I'm building `strategies/ob_sweep_v8a/` on benpc. That work doesn't touch the rithmic adapter, so we shouldn't conflict.
- Per InsyncApp's CLAUDE.md self-contained policy, your audit doesn't need anything outside InsyncApp/services/tradebot/. FractalAMD is reference-only — DON'T add a dep on it.

— benpc
