# DATA — local inventory and the joint window (surveyed 2026-06-12)

Warehouse root: `D:\data` (`BS_DATA_ROOT`, per-user env var). Raw is append-only.

## 1. The joint window that makes this experiment possible

| Layer | Coverage | Source |
|---|---|---|
| SPX intraday 5-min greeks/IV (chain) | 2025-05-01 → 2026-06-05 | `D:\data\raw\thetadata\bulk_hist_option_greeks` (11.5M rows, SPX only) |
| SPX intraday option OHLC (5-min) | 2025-05-01 → 2026-06-05 | `...\bulk_hist_option_ohlc` |
| Per-minute GEX panel (net_gex, zero_gamma, walls, pin, spot) | 2025-05-02 → 2026-06-05 | `experiments\options_signals_v0\out\intraday_gex_spx.parquet` (21,216 rows) |
| 0DTE flow panel (net gamma/vanna/charm from cum. volume) | 2025-05 → 2026-06-05 | `...\out\dte0_intraday_spx.parquet` |
| Intraday IV/skew + spot | same | `...\out\iv_intraday_spx.parquet`, `spot_intraday_spx.parquet` |
| ES MBP-1 (parquet mirror) | 2025-05-01 → 2026-06-09 (342 dates, 24 GB) | `D:\data\raw\databento\mbp-1\symbol=ES.c.0\date=*` |
| ES 1m bars | 2015-01-01 → 2026-06-09 (gapless) | `D:\data\processed\bars\timeframe=1m\symbol=ES.c.0\` |
| ES MBO (clean, Globex-day-stitched) | 2026-01-02 → 2026-06-09 (112 days; 2026-05-22 missing) | `D:\data\clean\databento\mbo_trading_day\symbol=ES.c.0\` |
| ES TBBO | 2025-05-01 → 2026-05-05 (stale; prefer MBP-1) | `D:\data\raw\databento\tbbo\symbol=ES.c.0\` |

**Dev window 2025-05-01 → 2026-03-31, sealed holdout 2026-04-01 → end** (SPEC §2).
MBO exists only for the last ~5 months — MBO-derived features are a *secondary* track
(can't cover the dev window); MBP-1 is the primary microstructure source.

## 2. Deep history (event-study / context only — daily modeling is closed)

| Layer | Coverage | Source |
|---|---|---|
| SPX EOD greeks (full set incl. gamma/vanna/charm) + OI | 2017-01-03 → 2026-06-10, **2021→mid-2023 gap still backfilling** | `D:\data\raw\thetadata\bulk_hist_option_eod_greeks` (+`_open_interest`), 1.6 GB, 20M rows |
| Deep daily walls (call/put wall, gex_proxy) | 2019-08-21 → 2026-06-10 (1,038 days) | `experiments\prop_model_v0\data\walls_deep.parquet` |
| Daily GEX levels (audited) | 2025-05-01 → 2026-06-04 | `experiments\options_signals_v0\out\gex_levels_spx.parquet` (+ ndx/rut/djx) |
| OPRA EOD chains (Databento: definition/statistics/ohlcv-1d) | 2025-01 → 2025-12, SPX+NDX | `D:\data\raw\opra\` |

Vendor caps (hard): SPXW eod_greeks start 2017 (2015–16 = no data). NDX eod_greeks
start 2026-05-08; raw NDX quotes+OI exist server-side earlier → the fix is computing
IV→BS gamma ourselves (SPEC §6 extension). DJX quotes Dow/100.

## 3. Access patterns

- Canonical reader: `backend/app/data/reader.py` — `read_bars(symbol="ES.c.0",
  timeframe="1m", start=, end=)`, `read_mbp1_trading_day(symbol=, trading_day=,
  columns=)`, `read_mbo_trading_day(...)`. Import via `sys.path.insert(0, r"C:\Users\benbr\BacktestStation\backend")`.
  Half-open [start, end); missing days silently skipped; bars include Sundays — filter
  sessions via `backend/app/research/sessions.py` (Globex day = 18:00 ET → 17:00 ET).
- Hot loops: direct `pd.read_parquet` on the Hive day partitions (pattern:
  `mira_gate_harness/realized_r.py`).
- Options cache: `options_signals_v0/theta_store.py` (`fetch`, `fetch_flat`,
  `expirations`) — requires Theta Terminal on 127.0.0.1:25510. Filenames are MD5 keys;
  root is NOT in the path (identify by underlying_price + date).
- Python: `backend\.venv\Scripts\python.exe` (lightgbm 4.6.0, xgboost 3.2.0, pandas
  3.0.2; **no catboost anywhere**, `.venv-ml` has no lightgbm).

## 4. Backfill status (running as of 2026-06-12)

The 2017→2026 ThetaData backfill runs as a sharded fleet (`gex_shard.py` ×N + Theta
Terminal), auto-revived every 15 min by Task Scheduler (`revive_pulls.ps1`). SPX done
2017–2020 and mid-2023→2026; the 2021→mid-2023 gap is in flight; RUT/DJX/NDX/GLD/SLV
queued behind it. **Completion signal:** 3 files matching
`experiments\options_signals_v0\out\_shards\spx_s*.parquet`, then merge via
`merge_gex_shards.py` and regenerate `gex_levels_*.parquet` (current ones predate the
deep backfill). Don't fight the revive task for Terminal bandwidth (≤3 concurrent
streams) — schedule heavy new pulls after it finishes.

## 5. Known data gotchas

- `intraday_gex_spx.parquet` is built by EOD-OI **reprice** (`intraday_gex.py`) —
  phase-0 audit must confirm it uses the **T-1 chain** intraday (rule 2) before reuse.
- Clean MBO missing 2026-05-22. Bars have no holiday calendar (half-days unmarked).
- No per-contract futures data or roll calendar on disk — everything is `.c.0`
  (quarterly index rolls; minor for intraday day-flat work, but don't difference prices
  across roll dates).
- Options `ms_of_day` timestamps are ET; futures `ts_event` is UTC tz-aware. Align
  explicitly (see `phase0_sanity.py`).
