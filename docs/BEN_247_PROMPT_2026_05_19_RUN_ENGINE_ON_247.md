# 247 — Run the tradebot engine on your PC

_From benpc, 2026-05-19. The ob_sweep_v8a strategy is now ready to run in the engine. Set it up + start it on your PC so signals can be viewed live in the InsyncApp webapp._

## What's ready (already on InsyncApp main)

- `services/tradebot/app/strategies/ob_sweep_v8a/` — OB + Sweep state machines, 17 tests pass
- `services/tradebot/app/config/strategies.json` — ob_sweep_v8a enabled on MNQ (qty=1) alongside insync_classic
- `services/tradebot/app/config/profiles/lucid_50k.json` — your risk profile
- `services/tradebot/RITHMIC_SETUP.md` — Rithmic setup runbook (your own work, reference)
- 137 tests pass on a clean checkout

The strategy generates signals on real bars; just needs the engine running on a machine with a market-data feed.

## Setup steps

### 1. Pull + verify
```
cd C:\Users\YOU\InsyncAPP   # adjust path
git pull origin main
git log --oneline -5   # confirm 8710b6c at top
```

### 2. Python 3.12 venv

async-rithmic pins protobuf<5 which breaks on Python 3.14 (metaclass issue). Use **Python 3.12** for the tradebot venv. If you don't have it: `winget install Python.Python.3.12`.

```
cd services\tradebot
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
pip install async-rithmic   # if not pulled by pyproject yet
```

Verify:
```
python -c "import sys; print(sys.version)"
# should print 3.12.x
python -m pytest -q
# should print "137 passed"
```

### 3. .env configuration

`.env` is gitignored — never commit it. Copy from `.env.example`:

```
copy .env.example .env
```

For initial paper-mode running with **replay data** (no live market feed), you DON'T need rithmic or databento creds — leave them empty or use placeholders. For **live market data**, you'll need a `DATABENTO_API_KEY` (or your existing rithmic market-data subscription if you have one).

For paper-only-with-replay, this minimal `.env` works:
```
DATABENTO_API_KEY=
RITHMIC_USER=
RITHMIC_PASSWORD=
RITHMIC_SYSTEM=
```

For LIVE market data (no orders yet, just signals against live bars):
```
DATABENTO_API_KEY=<your databento key>
```

### 4. runtime.json — pick a market-data + broker config

Look in `services/tradebot/app/config/` for `runtime.json` (existing) and `runtime.live.rithmic.json.example` (your template).

Two safe starting configs:

**A. Replay against synthetic bars (zero-risk, signals fire in seconds):**
```json
{
  "market_data": {"kind": "replay", "replay": {"path": "./data/synthetic_bars.parquet", "symbols": ["MNQ"], "pace_seconds": 0.0}},
  "broker": {"kind": "paper", "paper": {"slippage_ticks": 1, "starting_equity": 50000.0}},
  "risk": {"daily_loss_dollars": 1500.0, "max_consec_losses": 3, "max_position_qty": 5}
}
```

**B. Live databento NQ/MNQ + paper broker (signals against real bars, no order risk):**
```json
{
  "market_data": {"kind": "databento", "databento": {"symbols": ["MNQ"], "dataset": "GLBX.MDP3"}},
  "broker": {"kind": "paper", "paper": {"slippage_ticks": 1, "starting_equity": 50000.0}},
  "risk": {"daily_loss_dollars": 1500.0, "max_consec_losses": 3, "max_position_qty": 5}
}
```

Optionally apply the Lucid profile (overlays risk settings + enforces $1500 soft daily DD):
```
python scripts\apply_profile.py lucid_50k
```

### 5. Start the engine

```
python scripts\run_engine.py
```

Expected output: engine startup messages, strategies registered (insync_classic + ob_sweep_v8a), bar feed connecting, log lines per bar.

For long-running operation, install as a Windows service via `production/install_pre10_service.ps1` adapted for tradebot — but for the smoke test, just running it in a terminal is fine.

### 6. Open InsyncApp webapp + verify

Start the webapp:
```
cd ..\..\apps\webapp
pnpm install   # if first time
pnpm run dev
```

Open `http://localhost:3000` (or whatever port pnpm picks). Navigate to TradeView. You should see:
- Engine status: running
- `apiOnline: true`
- Process status with both strategies listed
- Log tail showing bar processing + signal fires when conditions are met

### 7. Confirm signals appear

`ob_sweep_v8a` fires when:
- The current day's HTF (1h) bar sweeps the prior day's high or low
- For OB: an additional confirmation HTF bar closes past the OB body
- For Sweep: any sweep fires (reversed direction, with UTC 22-06 hour filter)

In paper-replay mode with `synthetic_bars.parquet`, signals should fire within minutes (depending on the synthetic data). In live databento mode, signals fire when real market conditions match — could be hours between fires on a calm day.

When a signal fires, you'll see a log line like:
```
INFO ob_sweep_v8a:strategy emitted BracketOrder symbol=MNQ side=LONG stop=... target=...
```

And the engine logs it to its position/state tracking.

## Out of scope

- Don't enable `--live` (real Rithmic orders) yet — paper mode only for the smoke
- Don't worry about a dedicated signals HTTP endpoint — the log tail in TradeView covers visibility for v0
- The remaining 12 OB modes + 12 Sweep modes are deferred — current 2-mode-per-family port is enough to verify the pipeline works

## What to send back

A note saying "engine running, signals firing" + maybe a screenshot of the TradeView page. If you hit a snag (venv, deps, market feed, engine startup), report what you tried and what failed.

## Coordination

I'm not blocking on this on benpc — I'll continue research-side work (the 12 more modes, paper-replay smoke against real NQ bars, signals dashboard view) until you confirm the engine is up. If you find a real bug in my port, post a branch + I'll review.

— benpc
