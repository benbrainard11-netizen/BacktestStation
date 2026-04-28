# `fractal_amd_trusted/` — engine plugin port (in progress)

This directory will hold the engine plugin port of the **trusted multi-year**
Fractal AMD strategy. It is intentionally empty as of 2026-04-28 PM. The
canonical strategy lives at `C:\Fractal-AMD\scripts\trusted_multiyear_bt.py`
and is wrapped for immediate use at `backend/scripts/run_trusted_backtest.py`.

This README explains what the port is, why it exists separately from the
existing `app/strategies/fractal_amd/` plugin, and what work remains.

## Why a second Fractal AMD plugin?

The existing `app/strategies/fractal_amd/` plugin mirrors `production/live_bot.py`
(the live bot on ben-247). That code path was supposed to be aligned with the
trusted strategy (per a 2026-04-12 commit message) but characterization on
2026-04-28 PM showed it diverges substantially:

```
                 trades    WR      total R    runtime
trusted (2.25y)     586   40.8%    +274.4R    ~22 min
engine port (2.25y) 989   29.9%     -77.5R    12 min
```

The engine port wins more trades but with much lower WR and big losses. The
divergence isn't a tuning issue — it's a structurally different code path. So
rather than try to bend the existing plugin into matching trusted, we're going
to port the trusted script into a fresh plugin and leave the existing one as
the live-bot mirror until execution code can be unified.

End state: the existing plugin gets retired once the trusted plugin is verified
and the live bot on ben-247 is rebuilt around it.

## Specific divergences trusted has that the engine port lacks

These are the things the engine plugin port needs to faithfully replicate:

1. **Continuation-OF gate.** Trusted requires
   `compute_continuation_of(...).co_continuation_score >= 3` to fire any entry.
   The engine port doesn't import this function at all (`order_flow.py` from
   the original repo wasn't ported). **The 2026-04-28 PM Q1 experiment
   (Lane D branch) showed adding *just* this gate barely changes the engine
   port's behavior** — see below — so #1 is necessary for trusted but not
   sufficient. The other divergences matter more than initially suspected.

2. **Entry trigger.** Trusted: bar's range intersects FVG → mark waiting →
   enter at NEXT bar's `open`. Engine port: TBBO tick price triggers and
   delayed entry via `check_touch` / `check_entry`.

3. **Setup selection.** Trusted: `find_nearest_unfilled_fvg(fvgs, close, ...)`
   per bar (always picks the FVG nearest to current close). Engine port:
   iterates `engine.setups` and fires on the first FVG-zone match in
   creation order.

4. **LTF SMT search.** Trusted: 15m → 5m, first match wins (early return inside
   `find_ltf_smt`). Engine port: iterates all LTF candle pairs, builds a setup
   per match.

5. **Scan frequency.** Trusted: HTF candles scanned ONCE per day at start.
   Engine port: re-scans every bar (with a `_fully_scanned` cache to skip
   candles whose expansion window is past).

## 2026-04-28 PM cont-OF gate experiment

Hypothesis: of the 5 divergences above, #1 (the missing continuation-OF gate)
is the dominant one — adding *just that gate* to the existing engine port
should close most of the gap to trusted.

Result on Q1 2024 (Lane D experimental branch, `min_co_score=3`):

```
config          trades   WR%    totalR   avgR
gate off          122   33.6%   +2.79   +0.02     <- Q1 baseline (Lane A)
gate on=3         120   31.7%   -1.77   -0.01     <- gate ON (this experiment)
trusted target     85   35.3%  +19.80   +0.23
```

**Hypothesis falsified.** Only 2 of 122 entries got rejected by the gate, and
WR/total-R both went slightly the wrong way. The engine port is already firing
on bars where the trusted gate would pass — so the divergence is somewhere else.
Patching the existing engine port with this gate alone is not the path to
trusted-level performance. The full plugin port (#1 + #2 + #3 + #4 + #5
together) is required.

The Lane D branch keeps the gate wiring (config knob, off by default) and the
Q1 experiment script for the audit trail, but it's not on the path to merge as
a feature.

## Work plan

When this gets picked up:

1. ~~**Port `compute_continuation_of`**~~ — DONE 2026-04-28 PM. See `orderflow.py`
   in this directory; bit-identical to the pandas original (verified via 8
   parametrized test cases in `backend/tests/test_fractal_amd_trusted_orderflow.py`).

2. **Build the strategy plugin** (`strategy.py`, `config.py`) mirroring the
   original `Strategy` interface. Key shape:
   - `_maybe_roll_day` triggers `_scan_htf_stages_once` at session start (not
     per bar). Result is a list of stages to evaluate.
   - For each stage's expansion window, find LTF SMT (early-return per
     trusted), build FVGs, iterate entry-window bars looking for a FVG-zone
     touch.
   - On touch, mark waiting; next bar emits BracketOrder at open with stop +
     3R target.
   - Validate at entry: 09:30-13:59 ET window, 15-min dedup, max 2/day,
     `cos >= 3`, risk in (0, 150] pts.

3. **Regression test**: `backend/tests/test_fractal_amd_trusted_regression.py`
   runs the plugin via `engine_run` on 2024-2026 NQ/ES/YM, asserts trade count
   = 586 ± 1, total_r = +274 ± 5, win_rate = 0.408 ± 0.02. The target numbers
   are from the bundled CSV.

4. **Strategy registry**: Add to `app/services/strategy_registry.py` and
   `app/backtest/runner.py:_resolve_strategy` so it's selectable in the
   Run-a-Backtest UI.

5. **Live bot integration** (separate change, requires ben-247 console
   access + risk review): Replace `production/live_bot.py` with a thin
   wrapper that calls the same plugin code, plugged into Rithmic for
   execution. One strategy definition, two run modes.

## What you can do today (without this plugin existing)

- Run `python -m scripts.run_trusted_backtest` from `backend/` to reproduce
  the trusted backtest on demand. Output lands at
  `backend/tests/_artifacts/trusted_multiyear_run.csv`.
- Compare the existing engine port's behavior against trusted by running
  both and diffing trades on shared days.
- Use `samples/fractal_trusted_multiyear/trades.csv` as the import source
  for the strategy dossier UI (it's already wired through `imports.py`).

## Why the canonical script lives outside this repo

`C:\Fractal-AMD\` is the original local research repo. It pulls from
`features/` modules that include order-flow features that were never ported
into BacktestStation. We could vendor those modules in here, but doing it
right means a careful list-of-Bar port (not a pandas copy-paste). That's the
work plan above.
