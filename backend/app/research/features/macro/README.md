# Scheduled Macro Events

> Economic-calendar releases as pre-release anchors, then post-release reaction labels.

## What It Is

This feature records scheduled macro events like CPI, PPI, NFP, FOMC, jobless claims, retail sales, and GDP. It is source-agnostic: ForexFactory-style rows get cleaned into one canonical CSV, then the detector creates one pre-release anchor per symbol.

The goal is not to scrape live news. The goal is a clean historical macro context table for ML: what event was scheduled, what was known before release, what the market did before release, and what happened after release.

## Modes

| Mode | Meaning |
|---|---|
| `pre_release` | Anchor fires before the scheduled release, default one minute before release time. |

Event types are group-specific, like `pre_cpi`, `pre_nfp`, `pre_fomc`, or `pre_jobless_claims`.

## CSV Schema

Canonical columns:

```csv
event_id,event_name,event_group,country,currency,impact,release_ts_et,actual,forecast,previous,source,notes
```

Use a distinct `event_group` when multiple reports share the same release timestamp and currency. For example, split `cpi`, `core_cpi`, and `cpi_mom` if you want separate anchors at the same 08:30 ET release.

Default ignored data path:

```powershell
C:\Users\benbr\BacktestStation\data\research\macro_events\macro_events.csv
```

Tracked importer/template:

```powershell
python backend\scripts\import_macro_events.py --write-sample
python backend\scripts\import_macro_events.py --input C:\path\to\clean_macro_events.csv
```

## Where The Code Lives

| Component | Path |
|---|---|
| CSV utilities | `backend/app/research/macro_events.py` |
| Detector | `backend/app/research/detectors/macro_event_anchor.py` |
| Outcomes | `backend/app/research/outcomes/macro_event_reactions.py` |
| Importer | `backend/scripts/import_macro_events.py` |
| ForexFactory archive importer | `backend/scripts/import_forex_factory_archive.py` |
| Event-type breakdown | `backend/scripts/ml/macro_event_type_breakdown.py` |
| Feature matrix | `data/ml/features/macro.parquet` |
| Snapshot matrix | `data/ml/anchors/macro_event_snapshots.parquet` |
| Tests | `backend/tests/test_macro_event_anchor.py` |
| Live stats | `./stats.md` |

## What The Event Records

Safe pre-release fields include:

- Event name, group, country, currency, impact, source, release timestamp, and known timestamp.
- Forecast and previous values when available.
- Scheduled release hour/minute/day-of-week in Eastern Time.
- Leak-safe taxonomy: macro family/theme, event role, importance tier, expected horizon, and release-time bucket.
- Same-timestamp cluster context: how many scheduled reports fire together and whether nearby scheduled releases exist.
- Pre-release market context from bars before the known timestamp: 5m, 15m, and 60m range, return, close location, and reference close.

## What The Outcomes Record

Post-release labels include:

- Reaction direction and return from pre-release reference close.
- 1m, 5m, 15m, 60m, 240m, and 1d post-release range/body/MFE/MAE.
- Range expansion versus the pre-15m and pre-60m windows.
- Took pre-release high, took pre-release low, swept both sides, or closed outside the pre-release range.
- Stricter v2 labels for first-bar reversal, one-sided high/low takes, held breaks, rejected breaks, and closes back inside the pre-release range.

## Leakage Notes

The pre-release detector must not write `actual`, `actual_raw`, `actual_value`, `surprise`, or any realized post-release value into `event_data`.

Allowed in `event_data`: schedule metadata, forecast, previous, and market bars strictly before `known_ts_utc`.

Forward reaction values belong only in `outcomes` / `oc.*` / `label.*`. Use snapshot matrices for ML so the feature cutoff is `ed.known_ts_utc`.

## Implementation Direction

The macro feature is scheduled-news only. It should model:

- Pre-release context: compression, 5/15/60m ranges, location, and clustered events.
- Event identity: CPI, NFP, FOMC, PPI, GDP, claims, PMI, retail sales, auctions, speeches, and related families.
- First reaction: immediate expansion, first-bar direction, pre-range high/low take, and one-sided versus two-sided sweep.
- Follow-through: whether the first move holds, reverses, closes back inside, or keeps trending over 15m/60m/240m/1d.

Your discretionary rules should go into the taxonomy first. The current taxonomy lives in:

```powershell
backend\app\research\macro_taxonomy.py
```

## How To Refresh

Typical sequence after importing a real CSV:

```powershell
python backend\scripts\import_macro_events.py --input C:\path\to\clean_macro_events.csv
python backend\scripts\import_forex_factory_archive.py --input data\raw\macro_events\forex_factory_cache.csv --output data\research\macro_events\macro_events.csv --currencies USD --impacts HIGH,MEDIUM --start-year 2015 --merge
cd backend
python -m app.cli.scan_research_events --detector macro_event_anchor --mode pre_release --symbols NQ.c.0 ES.c.0 YM.c.0 --start 2015-01-01 --end 2026-05-14 --params "events_path=C:\Users\benbr\BacktestStation\data\research\macro_events\macro_events.csv;currencies=USD;impacts=high,medium"
python -m app.cli.compute_research_outcomes --computer macro_event_reactions_v1 --force
python scripts\ml\build_feature_matrix.py
python scripts\ml\build_generic_anchor_snapshots.py --anchors macro
python scripts\refresh_dashboards.py macro
```
