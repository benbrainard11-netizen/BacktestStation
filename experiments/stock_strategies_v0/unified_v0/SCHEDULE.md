# Autonomous paper bot — setup & operation

`auto_paper.py` runs one full daily cycle: refresh data → rebuild setups → trail exits → place entries.
PAPER ONLY. This doc is the autonomy layer around it.

## Prerequisites (one-time)
1. **IBKR paper account** (free at interactivebrokers.com → open a paper trading account).
2. **IB Gateway (paper mode)** running on this PC, listening on **port 7497** (TWS) or **4002** (Gateway).
   - For *unattended* daily runs, set up **IBC** (IBController) so Gateway auto-logs-in each morning and
     doesn't time out. Without IBC you must have Gateway logged in before the scheduled run.
3. `ib_async` — installed (v2.1.0 in `backend\.venv`).
4. `POLYGON_API_KEY` — set as a User env var (for the daily data refresh).

## The scheduled task
Created as **`BreakoutPaperBot`** (Windows Task Scheduler), runs `run_auto_paper.bat` weekdays.
- **Timing: set it to ~30-60 min before the 9:30 ET open IN YOUR LOCAL TIME.** It was created at 08:30
  local — if you're not on ET, fix the time in Task Scheduler (the data refresh needs the prior session's
  Polygon grouped-daily, which is ready overnight; entries must arm before the open).
- Enable/disable: `schtasks /Change /TN BreakoutPaperBot /ENABLE` (or `/DISABLE`). Delete: `/Delete /F`.
- Run it once manually to test: `schtasks /Run /TN BreakoutPaperBot`.

## The daily cycle (what it does)
1. Pull yesterday's Polygon grouped-daily, append to `daily_2026.parquet`.
2. `build_setups.py` — recompute setups + features incl. yesterday.
3. Connect IBKR paper; read account equity + positions.
4. **Exit manager:** for each open position, ratchet the chandelier stop up to `run_high − 3×ATR`;
   close anything past the 40-day max-hold. (This is the let-it-run logic — the edge.)
5. **Entries:** score today's setups, place stop-buy brackets (entry + initial 1-ATR stop) for the top
   pred>0 up to the free slots (max 5), pred-scaled sizing.
6. Persist `paper_state.json`, log to `auto_paper.log`.

## Monitoring
- `out\auto_paper.log` — every cycle's actions (exits trailed, entries placed, errors).
- `out\paper_state.json` — current tracked positions + stops.
- Reconcile against the IBKR paper account UI weekly.

## Staged rollout (do NOT skip)
1. **Dry-run** (`auto_paper.py` no `--live`) — confirm the take-list + exit logic look sane. ✅ done.
2. **Supervised paper** — let the task run `--live`, but **watch it daily for ~2-4 weeks.**
3. **Unattended paper** — once it's behaving, let it run on its own; check the log a few times/week.
4. **Real money** — only after months of paper that reproduces the edge, and start tiny ($1-2k).

## Known gaps to harden during supervised paper
The IBKR **reconciliation is simplified** — it does not yet robustly: cancel unfilled stop-buys at EOD
(a breakout that didn't trigger should not fill on a later day), detect partial fills, or recover from
mid-cycle disconnects. **Watch the first weeks closely** and harden these against real paper behavior.
This is a validation harness, not a finished product.
