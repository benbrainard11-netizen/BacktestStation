# Strategy Lab

This folder is the repo-facing entry point for using the exported ML data on another PC.

The large parquet files are not committed to Git because `/data` and `/exports` are intentionally ignored. Instead, this repo commits:

- the export builder script
- the export index
- safe loader utilities
- docs explaining what the data means

## Current Export Package

Package:

`strategy_lab_core_2026_05_12.zip`

Local path on the source machine:

`C:\Users\benbr\BacktestStation\exports\strategy_lab_core_2026_05_12.zip`

SHA256:

`9cd26243ba2152c1d3ee3f29e373c16273872ee2e7afffcfb4390efb5bfebd81`

Size:

`144,462,731` bytes

## How Another PC Uses It

1. Pull this repo.
2. Download the current export package.
3. Unzip it anywhere, for example:

`D:\BacktestStationData\strategy_lab_core_2026_05_12\`

You can download through GitHub Releases after the release asset has been published:

```powershell
python strategy_lab\download_export_release.py --output-dir D:\BacktestStationData --extract
```

Or, if you already have the zip, place it under `D:\BacktestStationData\` and extract it there.

4. Install the minimal reader packages if needed:

```powershell
pip install pandas pyarrow numpy scikit-learn lightgbm
```

5. Run the loader:

```powershell
python strategy_lab\load_anchor_matrix.py --export-root D:\BacktestStationData\strategy_lab_core_2026_05_12 --dataset fvg_xctx_fvggeom
```

## Included Datasets

| dataset | rows | features | labels |
|---|---:|---:|---:|
| `fvg_xctx_fvggeom` | 209,339 | 1,088 | 67 |
| `sweep_xctx_fvggeom` | 52,946 | 1,085 | 31 |
| `tp_xctx_fvggeom` | 19,414 | 1,077 | 24 |
| `smt_previous_day_xctx_fvggeom` | 4,676 | 1,324 | 18 |

## Safety Rule

Always load inputs from the schema's `feature_columns`.

Never use `label.*` columns as model inputs. Those are future outcomes.

## Main Docs

Inside the unzipped export:

- `README.md`
- `DATA_DICTIONARY.md`
- `MANIFEST.json`
- `docs/ML_DATA_LOCATION_GUIDE.md`
- `docs/ML_FVG_GEOMETRY_CONTEXT.md`
- `docs/ML_VP_V2_LABELS.md`

In this repo:

- `docs/ML_DATA_LOCATION_GUIDE.md`
- `docs/ML_FVG_GEOMETRY_CONTEXT.md`
- `docs/ML_VP_V2_LABELS.md`

## Regenerate Export

From this repo:

```powershell
cd C:\Users\benbr\BacktestStation\backend
python scripts\ml\export_strategy_lab.py --name strategy_lab_core_YYYY_MM_DD --force --zip
```

The generated export goes under:

`C:\Users\benbr\BacktestStation\exports\`

## Publish Export To GitHub Release

On the source machine, after creating the zip:

```powershell
python strategy_lab\publish_export_release.py
```

This verifies the zip checksum from `EXPORT_INDEX.json`, then creates or updates a GitHub Release asset.

Do this only for data you are allowed to redistribute. Market data subscriptions can have redistribution restrictions.

## One-Command Sync For Future Updates

After the database/anchor matrices are rebuilt, run this from the source machine:

```powershell
python strategy_lab\sync_export_to_github.py --all --name strategy_lab_core_YYYY_MM_DD --force
```

That command:

1. Creates a fresh export folder and zip.
2. Updates `strategy_lab/EXPORT_INDEX.json`.
3. Commits the index update.
4. Pushes `main`.
5. Publishes the zip as a GitHub Release asset.

To verify the current package is synced:

```powershell
python strategy_lab\sync_export_to_github.py --verify-current
```
