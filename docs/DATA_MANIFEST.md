# DATA MANIFEST

What local data exists and is ready to test. Last verified **2026-06-17**.

Drives: `D:\data\` holds raw/derived market data (append-only raw; see CLAUDE.md rule 7).
Derived research artifacts live under `experiments\`.

Python with numpy/pandas/scipy/pyarrow:
`C:\Users\benbr\BacktestStation\backend\.venv\Scripts\python.exe`

**Universal loader — `data_io.py` (repo root).** One consistent call per dataset; hides the path /
partition-key / date-format differences. `python data_io.py` prints the menu.
```python
from data_io import load_futures, load_stock, load_option_panel, load_walls, load_mbp1, load_mbo, load_aux, datasets
es  = load_futures("ES.c.0", "2026-06-09")     # futures 1m, one day
opt = load_option_panel("SPXW", 20250515)       # intraday option panel, one day (IV/greeks/OI)
w   = load_walls("NDX")                          # daily gamma walls
```

Index -> future map: **SPX->ES, NDX->NQ, RUT->RTY, DJX->YM**.

---

## 1. Futures 1m bars

Root: `D:\data\processed\bars\timeframe=1m\symbol=<SYM>\date=<YYYY-MM-DD>\`
(Hive-partitioned Parquet; 31 symbols total — full index/FX/energy/metals/rates/grains set.)

| Symbol  | Date range              | Trading days | Path |
|---------|-------------------------|--------------|------|
| ES.c.0  | 2015-01-01 .. 2026-06-09 | 3553 | `D:\data\processed\bars\timeframe=1m\symbol=ES.c.0` |
| NQ.c.0  | 2015-01-01 .. 2026-06-09 | 3554 | `...\symbol=NQ.c.0` |
| YM.c.0  | 2015-01-01 .. 2026-06-09 | 3552 | `...\symbol=YM.c.0` |
| RTY.c.0 | 2018-05-01 .. 2026-06-09 | 2520 | `...\symbol=RTY.c.0` |

Other 27 symbols (same layout): 6A 6B 6C 6E 6J 6N 6S BTC BZ CL ETH GC HG HO MBT NG PA PL RB SI ZB ZC ZF ZN ZS ZT ZW.

**How to load:** point pyarrow/pandas at the symbol dir; the partitions become columns.
```python
import pandas as pd
df = pd.read_parquet(r"D:\data\processed\bars\timeframe=1m\symbol=ES.c.0")
# or a single day:
df = pd.read_parquet(r"D:\data\processed\bars\timeframe=1m\symbol=ES.c.0\date=2026-06-09")
```

### Stock bars (NDX-100 universe) — added 2026-06-15
Root: `D:\data\processed\stocks\eod\<T>.parquet` (daily OHLCV) and `\m1\<T>.parquet` (1-min, ET clock via `ts_et`).
**133 names** = the current Nasdaq-100 + still-trading historical members (the PIT union for breadth research).
From ThetaData equities (sub covers stock + stock options). Built by `pull_stock_bars.py` (chunks EOD
quarterly / 1-min monthly to dodge the hist/stock/eod 475-on-long-range).
- **2023-06 .. 2026-06: DONE & audited** (median 761 trading-days/name, every day = 390 bars). The 3 short
  names are corporate actions, not gaps: SNDK (re-listed 2025-02), FER (listed 2024-05), WBA (taken private 2025-08).
- **Pre-2023-06: NOT AVAILABLE** on this sub. The ThetaData stock subscription caps history at ~3 years
  (rolling): any stock request (1m or EOD) before ~2023-06 returns HTTP 471 `permissions/:End date cannot`.
  Verified 2026-06-15 (Phase B 2014-backfill was a no-op). Deep history needs a ThetaData historical-tier
  upgrade ($), or free **Stooq EOD** for daily-only 2014+.
Universe sourced from the Nasdaq-100 components list (Wikipedia, 2026-06-15).

---

## 2. MBP-1 (top-of-book + trades, Databento)

Root: `D:\data\raw\databento\mbp-1\symbol=<SYM>\date=<YYYY-MM-DD>\`
**31 symbols**, each **2025-05-01 .. 2026-06-09** (~342 days). Raw / append-only.

Symbols: 6A 6B 6C 6E 6J 6N 6S BTC BZ CL ES ETH GC HG HO MBT NG NQ PA PL RB RTY SI YM ZB ZC ZF ZN ZS ZT ZW.

Index-complex symbols of interest: ES, NQ, RTY, YM (each 2025-05-01 .. 2026-06-09).

**How to load:**
```python
df = pd.read_parquet(r"D:\data\raw\databento\mbp-1\symbol=ES.c.0\date=2026-06-09")
```
Use for honest stop-vs-target trade-sequence fills (CLAUDE.md rule 8): trade prints are in order within the window -> `fill_confidence = exact`.

---

## 3. MBO (full order book, Databento)

Root: `D:\data\clean\databento\mbo_trading_day\symbol=<SYM>\trading_day=<YYYY-MM-DD>\`
Partition key is **`trading_day=`** (not `date=`).

| Symbol  | Date range              | Trading days |
|---------|-------------------------|--------------|
| ES.c.0  | 2026-01-02 .. 2026-06-09 | 112 |
| NQ.c.0  | 2026-01-02 .. 2026-06-09 | 112 |
| RTY.c.0 | 2026-01-02 .. 2026-06-09 | 112 |
| YM.c.0  | 2026-01-02 .. 2026-06-09 | 112 |

**How to load:**
```python
df = pd.read_parquet(r"D:\data\clean\databento\mbo_trading_day\symbol=ES.c.0\trading_day=2026-06-09")
```
Manifests in the root list materialized days. MBO is the basis for the Mira orderflow gate (see MEMORY).

---

## 4. Options RAW (ThetaData cache)

Root: `D:\data\raw\thetadata\` — append-only, **hash-keyed cache** (~3,625 MB), read via
`experiments/options_signals_v0/theta_store.py` (`TS.fetch()` reads the disk cache, no network).
**Read the cache; do not re-download.** A Terminal (`THETA_PORT` 25510/25511/25512) is only needed
for the light `TS.expirations(root)` list call.

> **Freeze-proofing cache-only builds (2026-06-14):** `TS.fetch()` falls through to the network on a
> cache MISS, and `_get()` retries 4× at a 180s timeout = up to ~12 min per missing key. The 2021-22
> NDX vendor gap has ~107 such keys -> the NDX rebuild hung ~2h. Fix: set **`THETA_CACHE_ONLY=1`** for
> any derived build over already-pulled raw — `theta_store._cached` then returns empty INSTANTLY on a
> miss (no network). Default off, so live pulls still raise on a dead feed (CLAUDE.md rule 6).

### Vendor EOD greeks — `bulk_hist_option_eod_greeks` (4084 files, ~26M+ rows)
Coverage by underlying band (the source for walls SPX/RUT/DJX):

| Index | Range (rows present)            | Rows   | Notes |
|-------|---------------------------------|--------|-------|
| SPX   | 2018-01-03 .. 2026-06-10        | ~26.1M | continuous |
| RUT   | 2024-06-03 .. 2026-06-10        | (subset of 5.9M) | **recent-only in this cache** — earlier "2017..+gap" rows were classifier contamination; true clean RUT starts 2024-06 |
| DJX   | 2024-06-03 .. 2026-06-10        | ~955k  | recent-only |
| NDX   | effectively **NONE**            | ~45k stray | no usable vendor greeks -> NDX walls are self-computed from raw prices |

### Open interest — `bulk_hist_option_open_interest` (5747 files)
No `underlying_price` column (classified by strike). SPX 2633, NDX 1435, RUT 1354, DJX 325 files.

### Raw option prices — `bulk_hist_option_eod` (1443 files)
- **NDX** strikes (>8000): **10,726,425 rows, 2018-01-19 .. 2026-06-12 (all years)** — powers full-history NDX walls.
- **SPX** strikes: 946,219 rows (partial; parity fallback only).

### Other cached endpoints
`bulk_hist_option_greeks` 278 (intraday), `bulk_hist_option_ohlc` 278, `hist_option_greeks` 276.

**How to load:** use the store, not raw files.
```python
from experiments.options_signals_v0.theta_store import TS
df = TS.fetch(...)   # disk-cache read for already-pulled data
```

---

## 5. Options WALLS (derived dealer-gamma levels)

Per-index daily levels. **walls_v2 schema** (7 cols) is the standard:
`[date (int YYYYMMDD), spot, call_wall, put_wall, zero_gamma, pin, gex_proxy]`
(`date` int64, rest float64; `zero_gamma` may be NaN on days with no cumsum sign-crossing).

All four cross-validated against the index FUTURE (`verify_walls_vs_futures.py`, 2026-06-14): each
walls file's `spot` vs the matching future's daily close (NQ~=NDX, ES~=SPX, RTY~=RUT, YM/100~=DJX).
Median spot/future ratio shown; "clean %" = days within 8% of the future.

| Index | File | Rows (days) | Date range | Status (vs future) |
|-------|------|-------------|------------|--------------------|
| NDX | `experiments\fuhhhhh\out\walls_ndx.parquet` | **2091** | 20180119..20260612 | **FULL HISTORY (2018+)**; 99.6% clean (ratio 0.998), 9 thin-day parity outliers |
| SPX | `experiments\fuhhhhh\out\walls_v2.parquet` | **2337** | 20170103..20260610 | **2017+, 2021 gap filled** (year-aware filter); 100% clean (ratio 0.999) |
| DJX | `experiments\options_signals_v0\out\walls_djx.parquet` | **1543** | 20180129..20260609 | **2018+** (greeks backfilled 2018-2023); 100% clean (ratio 0.9995) after YM-anchor; 2018 & 2024 thin (early OI) |
| RUT | `experiments\options_signals_v0\out\walls_rut.parquet` | **2118** | 20180102..20260610 | **2018+, gapless** (self-compute 2018-2023 + vendor greeks 2024+); 100% clean (ratio 0.999) |

Builders:
- SPX: `experiments\fuhhhhh\build_walls_v2.py` (vendor greeks -> net dealer gamma). SPX band [1800,8500], excluding [1800,3000) only for year>=2024 (that sub-band is RUT then) -> covers SPX 2017+ where it traded below 3000.
- DJX: `experiments\options_signals_v0\build_walls_djx.py` (band [250,520) **then YM-anchored** — keeps only contract-days whose `underlying_price` is within 5% of YM_close/100, dropping a ~327-400 product that contaminates the raw band. No year gate -> covers all greeks years 2018+. Run after YM bars exist).
- RUT: TWO paths. `build_walls_rut.py` (vendor greeks, classifier [1100,3000) AND year>=2024) for 2024+; `build_walls_selfcompute.py RUT <start> <end> <merge_into>` (self-compute from raw, reuses the NDX engine) for 2018-2023 where greeks don't exist, merged under the greeks days.
- NDX: `experiments\options_signals_v0\build_walls_ndx.py` (self-computed: parity-forward -> BS-bisection IV -> BS gamma; no vendor greeks). **Run cache-only:** `THETA_CACHE_ONLY=1` (see §4).
- `build_walls_selfcompute.py` generalizes the NDX engine to ANY root (monkeypatches ROOT/OUT) for greeks-less years.

### Single-stock gamma walls (NVDA / AAPL / MSFT / TSLA) — added 2026-06-15
Same 7-col schema, built by `build_walls_stock.py` (reads one ticker via per-expiration TS.fetch since
stock prices overlap and can't be band-classified; EOD greeks carry gamma directly). Validated vs each
stock's own EOD close (ratio 1.0000, 100% within 3%).

Top-8 mega-caps (`experiments\options_signals_v0\out\walls_<t>.parquet`), all 2023-01→2026-06, all
validated vs own close (ratio 1.0000): **NVDA** 860d, **AAPL** 863d, **MSFT** 864d, **TSLA** 864d,
**GOOGL** 863d, **AMZN** 864d, **META** 863d, **AVGO** 862d.

**Intraday options — SOLVED 2026-06-17 (per-contract + quote feed).** The 2026-06-15 wedges were a
METHOD bug, not a vendor limit: the bulk intraday endpoint (`bulk_hist/option/greeks`) returns the whole
chain (~73k-400k rows/fetch) and permanently wedges terminals. Fix = pull **PER CONTRACT**
(`hist/option/quote` with strike+right) which is tiny (~400 rows/contract-day) and never wedges, and use
the **QUOTE feed** (the greeks feed is recent-only ~2026-05+; quote has full 2025-05+ history). The
resulting 1-minute intraday options dataset is **§6 below**.

### Secondary / reference walls (do not use as primary)
| File | Rows | Range | Schema | Note |
|------|------|-------|--------|------|
| `experiments\prop_model_v0\data\walls_deep.parquet` | 1038 | 20190821..20260610 | 5 cols (no zero_gamma/pin) | SPX, **OLD split-side definition** |
| `experiments\options_signals_v0\out\gex_levels_spx.parquet` | 275 | 20250501..20260604 | 6 cols (total_gex,zero_gamma,call_wall,put_wall,spot) | SPX **audited validation reference** |
| `experiments\options_signals_v0\out\gex_levels_{ndx,rut,djx}.parquet` | — | — | gex-levels schema | per-index audited EOD levels (companion to walls) |
| `experiments\fuhhhhh\out\walls_ndx_intraday.parquet` | — | — | ISO-date strings | NDX intraday walls |

**How to load:**
```python
import pandas as pd
w = pd.read_parquet(r"C:\Users\benbr\BacktestStation\experiments\options_signals_v0\out\walls_rut.parquet")
# date is int YYYYMMDD; convert to align with bars:
w["date_dt"] = pd.to_datetime(w["date"], format="%Y%m%d")
```
Join walls to a future via the index map (SPX->ES, NDX->NQ, RUT->RTY, DJX->YM) on the trading date.

---

## 6. Intraday options — 1-minute quotes (per-contract) — added 2026-06-17

Root: `experiments\options_signals_v0\out\intraday_pc\root=<R>\exp=<YYYYMMDD>\<strike1000>_<right>.parquet`
One file per **contract** (root, expiration, strike, right). Strike in the filename is ×1000 (vendor units).
Cols: `[date, ms_of_day, strike, right, expiration, bid, ask, bid_size, ask_size, root, exp]`.
`ms_of_day` is ET-clock milliseconds (34200000 = 09:30); rows are **1-minute** quote bars.

Built by `scoped_intraday_pc.py` (`OPT_EP=hist/option/quote`, `BAND=0.07`, `DTE_MAX=45`, recent-first
shards). Per Ben's scope: strikes within **±7% of futures spot**, **DTE ≤ 45**, span **2025-05-01 → present**
(matches the NQ/ES/RTY/YM MBP-1 window). Spot for the band comes from the index future (NQ/ES/RTY/YM).

| Index | Contracts | Size | Expirations |
|-------|-----------|------|-------------|
| NDXP | 182,687 | 7,238 MB | 309 |
| SPXW | 115,908 | 6,263 MB | 309 |
| RUTW | 65,804 | 2,825 MB | 297 |
| DJX | 1,362 | 34 MB | 40 (DJX intraday is genuinely thin/illiquid) |
| **Total** | **~365,761** | **~16.4 GB** | — |

> **NOTE — stored on `C:` (not `D:`).** ~16.4 GB currently under `experiments\...\out\intraday_pc`. This
> is per-(root,exp,strike,right), NOT yet (root,date)-queryable. The **assembly/BS-invert build** (pending)
> reshapes it into model-ready per-(root,date) panels — see "Pending build" below.

**What's NOT in the quote files (added by the build):** `underlying_price`, `implied_vol`, `gamma/vanna/charm`.
Per Ben's scope these are derived: BS-invert IV from the mid quote against the index forward (put-call
parity / Black-76, reusing the validated `build_walls_ndx` engine — no rates/dividends needed), then
compute greeks analytically. Quotes + underlying are guarded above all; IV/greeks are recomputable.

## 7. Intraday-band OI (daily open interest companion) — added 2026-06-17

Root: `experiments\options_signals_v0\out\intraday_oi\root=<R>\exp=<YYYYMMDD>.parquet`
Cols: `[date, strike, right, expiration, open_interest, root]`. OI is **daily** (no intraday variation);
this is the OI for the same ±7% band / DTE≤45 contracts as §6. Built by `build_intraday_oi.py`
(`bulk_hist/option/open_interest` per exp over its life window, band-filtered).
**Pairing rule (Ben's scope): use PRIOR-day OI** when joining to a quote timestamp — leak-clean.
The OI bulk fetch is moderately heavy, so the puller runs at low concurrency (W2/terminal) to avoid
saturating terminals. *(In progress 2026-06-17.)*

## 8. Auxiliary EOD data — added 2026-06-17 (`pull_aux_data.py`)

All tiny, EOD-only (index/vol intraday is paywalled → HTTP 471; rates absent on this sub).
- **Vol indices** `out\vol_indices\<R>.parquet`: VIX, VXN (Nasdaq), VXD (Dow), RVX (Russell), VIX9D, VIX1D, VVIX. EOD OHLC.
- **Index EOD levels** `out\index_eod\<R>.parquet`: NDX, SPX, RUT, DJX. EOD OHLC (intraday paywalled — use the futures bars in §1 for index intraday).
- **Dividends** `out\dividends\<T>.parquet`: the 8 mega-caps (NVDA AAPL MSFT TSLA GOOGL AMZN META AVGO).

## 9. Model-ready option panels — BUILT 2026-06-18 (`build_option_panels.py` + `option_greeks.py`)

Root: `D:\data\processed\option_panels\panel\root=<R>\date=<YYYYMMDD>\` — hive-partitioned, queryable
by (root, date). Assembled from §6 quotes + §7 OI. Columns: `date, ms_of_day, expiration, strike,
right, bid, ask, bid_size, ask_size, mid, underlying_price, fut_price, fwd_parity, dte, implied_vol,
gamma, vanna, charm, oi_prior`.

| Root | Rows | Dates | underlying | iv/gamma | oi_prior | Monday oi_prior |
|------|------|-------|------------|----------|----------|-----------------|
| NDXP | 695M | 284 | 96.5% | 87.9% | 76.5% | 76.9% |
| SPXW | 822M | 292 | 94.5% | 88.0% | 83.8% | 85.3% |
| RUTW | 369M | 286 | 95.1% | 85.8% | 81.0% | 81.4% |
| DJX  | 4.7M | 265 | 95.7% | 82.4% | 78.2% | 88.4% |

~**1.89B rows**, panel **~93 GB** (+ `panel_byexp` intermediate ~74 GB, safe to delete once panels verified).
Relocate via `PANEL_BASE` env (defaults to `experiments\...\out`; the build ran with `PANEL_BASE=D:\data\processed\option_panels`).

**Method:** `underlying_price` = per-(date) put-call-parity forward (the build_walls_ndx engine) tracked
intraday by the index future via `merge_asof` (nearest prior minute); IV bisected from the mid; gamma/
vanna/charm from `option_greeks` (finite-difference verified — a charm sign bug was caught this way). IV
is set **NaN when unreliable** (bisection bracket-pinned/saturated to 500%, vega-unidentifiable deep ITM,
or < 10 min to expiry); greeks are **NaN (not 0.0)** wherever IV is NaN, so GEX sums don't under-count.
`oi_prior` = OI from the **prior *trading* day** (calendar built from RTH sessions, NOT the 24h futures
clock — the futures clock includes Sunday Globex dates, which silently nulled every Monday's OI).

**Validated:** greeks vs finite differences; EOD dealer-gamma walls reproduce the daily walls (§5) — SPX
call+put exact, RUT put exact, spots match < 0.1% on all four. NDX walls are noisier (NDX OI is thin +
prior-day) — the panel's underlying/IV/gamma are sound; stable NDX wall derivation just needs denser-OI
handling. The build was hardened against a 12-finding adversarial code review (OI calendar, NaN policy,
IV saturation, near-expiry charm, futures-gap handling, repartition schema/guards).

**Caveats:** (1) v0 `underlying_price` carries a small whole-day-basis intraday lookahead (the per-day
parity anchor uses the full day) — make it causal (prior-day basis) before any live/backtest use.
(2) Strikes limited to the ±7% quote band (§6), so walls beyond ±7% of spot are not visible.

**How to load (queryable by root+date):**
```python
import pyarrow.dataset as ds
dset = ds.dataset(r"D:\data\processed\option_panels\panel\root=SPXW", format="parquet", partitioning="hive")
df = dset.to_table(filter=ds.field("date") == 20250515).to_pandas()   # one day, all minutes/strikes
```

## Vendor ceiling — what's still pullable beyond the cache (probed 2026-06-14, `vendor_probe.py`)
The vendor (ThetaData) HAS more than was cached; sampling real expirations:
- **NDX**: no vendor greeks ever; raw prices start **2018** (NDXP floor). **At the ceiling** — can't go earlier.
- **SPX**: vendor greeks from **2017** (2014-2016 = greeks-empty but RAW prices exist -> +3 yrs self-computable if wanted).
- **RUT**: vendor greeks ~**2021+**, raw prices **2018+** (probe: 2018 greeks=0 but raw=3582; 2021 greeks=2190). Pulled + built 2018-2026 (self-compute 2018-2023 + greeks 2024+).
- **DJX**: vendor greeks back to **2018** (probe: 2018 greeks=200). Pulled + built 2018-2026.
- Beyond options, the binding data constraint is ORDERFLOW (MBP-1 2025-05+, MBO 2026-01+) — those are Databento $ pulls on the 247 box, not free vendor pulls.

## Known gaps / caveats
- **NDX walls span full history (2018-2026, 2091 days).** Cache-only self-compute from raw prices; the 2021-22 vendor-greeks gap does NOT affect NDX (it self-computes from prices, cached for those years).
- **SPX walls 2017-2026, no gap** (year-aware filter; the old 2021 gap predated the backfill and is now filled).
- **DJX walls 2018-2026** (greeks backfilled 2018-2023); 2018 (103 d) & 2024 (93 d) are thin from sparse early open-interest. Band contaminated by a ~327-400 product -> builder anchors to YM/100; rebuild DJX only after YM bars are current.
- **RUT walls 2018-2026, gapless (2118 days).** 2024+ are vendor-greeks; 2018-2023 are self-computed from raw (greeks don't exist pre-~2021). A method seam exists at 2023/2024 — both legs validate vs RTY (100% within 8%). The self-compute leg lives at `walls_rut_sc.parquet`; `walls_rut.parquet` is the merged final.
- **No vendor greeks for NDX (ever)** — NDX gamma is always self-computed from raw prices.
- Walls `date` is an int `YYYYMMDD`; bars/MBP-1 partitions use `YYYY-MM-DD`; MBO uses `trading_day=YYYY-MM-DD`.

## Verification tooling (2026-06-14)
- `census_all_assets.py` — greeks + raw-prices + OI caches by asset × year (what history exists locally).
- `census_options_cache.py` — greeks-only census by year × underlying band.
- `vendor_probe.py` — samples expirations to see what the vendor still has beyond the cache.
- `verify_walls_vs_futures.py` — every walls file's `spot` vs its index future; the authoritative trust check.
- `diag_djx.py` — isolates the DJX band contaminant.
- `build_walls_selfcompute.py` — reuses the NDX self-compute engine for any root (greeks-less years).
- `scoped_intraday_pc.py` — per-contract 1-min quote puller (the intraday solve; §6). Per-contract + quote feed = no terminal wedge.
- `build_intraday_oi.py` — per-exp band OI companion (§7), prior-day pairing intended at build time.
- `pull_aux_data.py` — vol indices / index EOD / dividends (§8); also probes whether index/vol intraday is allowed (it isn't).
- `build_option_panels.py` — assembles §6 quotes + §7 OI into the §9 model-ready per-(root,date) panels (IV/greeks/underlying/prior-OI). `PANEL_BASE` env relocates output.
- `option_greeks.py` — vanna/charm on the validated BS engine, with a finite-difference self-check (`python option_greeks.py`) that aborts the build if any greek is wrong.
