# Composable strategy spec

The `composable` strategy plugin reads a JSON spec (`spec_json` on a
`StrategyVersion`) and emits bracket orders without anyone writing
Python. The spec is parsed by `app.strategies.composable.config.ComposableSpec.from_dict`.
The visual builder at `/strategies/[id]/build` edits this same shape.

## Role taxonomy

Each entry in the recipe is a feature call tagged with a role. A feature
in the registry declares which roles it can serve (a single feature may
support multiple — `prior_level_sweep` works as both setup and trigger).

| Role | What it does | Common features |
|---|---|---|
| **setup** | Persistent state that ARMS an entry window. Re-evaluates every bar; once all setup features pass the engine arms the trigger window. Empty setup = always armed. | `prior_level_sweep`, `swing_sweep`, `fvg_touch_recent`, `smt_at_level` |
| **trigger** | Moment-in-time signal that FIRES the entry. All trigger features must pass on the bar where the entry is placed. Required for any entry. | `decisive_close`, `co_score`, also the setup-capable features above |
| **filter** | Block conditions evaluated against any candidate entry. Global `filter` applies both directions; `filter_long` / `filter_short` apply only to that direction. AND semantic — every filter must pass. | `time_window`, `volatility_regime`, `co_score` |

## Spec shape

```jsonc
{
  // 7 feature buckets (all default to []):
  "setup_long":     [{"feature": "...", "params": {...}}, ...],
  "trigger_long":   [...],
  "setup_short":    [...],
  "trigger_short":  [...],
  "filter":         [...],   // global, both directions
  "filter_long":    [...],   // additional, long entries only
  "filter_short":   [...],   // additional, short entries only

  // How long a fired setup arms the trigger window, per direction.
  // null = persist until end of trading day (cleared on Globex
  // 18:00 ET rollover).
  "setup_window": { "long": null, "short": 10 },

  // Stop / target rules:
  "stop":   { "type": "fixed_pts", "stop_pts": 10 }
            // or { "type": "fvg_buffer", "buffer_pts": 5 }
  "target": { "type": "r_multiple", "r": 3 }
            // or { "type": "fixed_pts", "target_pts": 30 }

  // Sizing + risk caps (all numeric):
  "qty": 1,
  "max_trades_per_day": 2,
  "entry_dedup_minutes": 15,
  "max_hold_bars": 120,
  "max_risk_pts": 150,
  "min_risk_pts": 0,

  // Cross-symbol features (e.g. SMT) declare their aux assets here.
  "aux_symbols": ["ES.c.0", "YM.c.0"]
}
```

## Engine eval order

Per bar, per direction:

```
setup features all pass?
  → arm window (refresh if already armed)

setup currently armed?  (empty setup_<dir> = always armed)
trigger features all pass?
global filter + per-direction filter all pass?
  → enter

(stop / target computed from the merged metadata of every passing
 setup + trigger; risk caps applied; bracket order returned)
```

Day rollover (Globex 18:00 ET → 17:00 ET roll-forward) clears all
armed-setup state. A sweep that armed late in session N never auto-arms
session N+1.

## Backward compatibility

Old-shape spec_json with only `entry_long` / `entry_short` (pre-2026-05-02)
auto-migrates into `trigger_long` / `trigger_short` at deserialization
time, both backend (`from_dict`) and frontend (`specFromJson` in
`build/page.tsx`). No migration UI, no SQL rewrite — the deserializer
just reads the old keys and routes them into the new buckets. The
deprecated `entry_long` / `entry_short` fields are still on the dataclass
but always empty post-migration; they will be removed in a future
release once we're confident no callers depend on them.

If a spec has both old AND new keys, new wins and a warning is logged.

## Authoring shape from the in-app agent

Compose-mode chat in the strategy builder produces patches as fenced
JSON blocks tagged `spec_json`. The user clicks "Apply to spec" to
merge them into the recipe. The system prompt at `app/api/chat.py`
teaches the agent the role taxonomy + the example shape above.

## Where the code lives

- Backend dataclass + parser: `backend/app/strategies/composable/config.py`
- Engine state machine: `backend/app/strategies/composable/strategy.py`
- Feature registry + role declarations: `backend/app/features/__init__.py` + `backend/app/features/*.py`
- Features API (exposes `roles`): `backend/app/api/features.py`
- Frontend Spec type + recipe layout: `frontend/app/strategies/[id]/build/page.tsx`
- Pantry (role chips + role-aware add buttons): `frontend/components/strategies/builder/FeaturePantry.tsx`
- Setup window control: `frontend/components/strategies/builder/SetupWindowControl.tsx`
- Tests: `backend/tests/test_composable_strategy.py` (spec + engine), `backend/tests/test_features_smoke.py` (registry roles + API contract)
