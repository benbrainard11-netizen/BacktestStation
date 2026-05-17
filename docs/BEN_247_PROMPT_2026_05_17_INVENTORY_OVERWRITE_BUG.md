# 247 prompt — inventory-overwrite bug in R2 publish/download

_2026-05-17 / benpc → ben-247._

## Headline

`_research_inventory.json` on R2 is fully overwritten on every `r2_artifacts.py` publish using only the publishing PC's locally-enumerable files. Files only present on the OTHER PC get silently dropped from the inventory — objects remain on R2, but the standard downloader (`r2_artifacts_download.py`) can't find them.

## Reproduction

1. ben-247 builds `data/ml/features/macro.parquet` locally and runs `python -m app.ingest.r2_artifacts --profile core`.
2. R2 now has both the macro.parquet object and an inventory listing it.
3. benpc runs builds (e.g. equal_levels chain) and runs `python -m app.ingest.r2_artifacts --profile core`. benpc does **not** have macro.parquet locally.
4. The new `_research_inventory.json` on R2 no longer lists `data/ml/features/macro.parquet` — the object remains, but the inventory entry is gone.
5. From benpc: `python -m app.ingest.r2_artifacts_download --keys 'data/ml/features/macro.parquet'` reports `selected=0` because the downloader only iterates inventory entries.

This was actually hit this morning when trying to run `b2dfc88` (macro news interactions). Worked around with a direct `boto3.download_file` call.

## Root cause

In `backend/app/ingest/r2_artifacts.py:run()`:

```python
specs = _default_specs(...)
artifacts, missing_roots = enumerate_artifacts(specs, ...)
# ...
put_json(client, bucket, INVENTORY_KEY,
         _inventory_payload(uploaded_or_existing, profile=profile, dry_run=False))
```

`enumerate_artifacts` walks the LOCAL filesystem. `_inventory_payload` writes those entries to `_research_inventory.json` on R2, replacing the previous version wholesale.

Result: inventory always reflects the publisher's local state, not the actual contents of the R2 bucket.

## Why this is a real problem

The architecture's stated goal is "either PC builds, either PC reads from R2." With the bug, that breaks down whenever:

- PC A builds artifact X, publishes
- PC B (which doesn't have X locally) republishes anything else
- → X disappears from the inventory; PC A's collaborators can no longer find it without bypassing the inventory

The longer the project runs, the more files accumulate in this delisted-but-present state. The R2 storage cost is unaffected, but discoverability rots.

## Proposed fix (ready-to-apply Python)

`_research_inventory.json` should be a **union** of:

1. The publishing PC's locally enumerable artifacts (what the publisher just uploaded).
2. Any existing R2 objects under the relevant prefixes (`data/ml/`, `data/research/`, `data/research_events/`, `exports/`, `strategy_lab/`) that aren't already covered by (1).

### Concrete implementation

Add this helper to `backend/app/ingest/r2_artifacts.py`:

```python
def _discover_r2_only_artifacts(
    client: Any,
    bucket: str,
    specs: list[ArtifactSpec],
    local_keys: set[str],
) -> list[Artifact]:
    """Scan R2 under each spec's prefix and return objects not in `local_keys`.

    These are artifacts that exist on R2 (uploaded by another PC) but aren't
    locally present on the current publisher. Including them in the inventory
    preserves discoverability across split-PC publish cycles.
    """
    found: list[Artifact] = []
    paginator = client.get_paginator("list_objects_v2")
    for spec in specs:
        prefix = spec.key_prefix.rstrip("/")
        if not prefix:
            continue
        scan_prefix = prefix if spec.source.is_file() else prefix + "/"
        for page in paginator.paginate(Bucket=bucket, Prefix=scan_prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key in local_keys:
                    continue
                # Skip excluded patterns (matches the local enumerator's exclude rules)
                if any(fnmatch.fnmatch(key.rsplit("/", 1)[-1], pat) for pat in DEFAULT_EXCLUDES):
                    continue
                mtime = obj["LastModified"]
                if mtime.tzinfo is None:
                    mtime = mtime.replace(tzinfo=dt.timezone.utc)
                found.append(Artifact(
                    group=spec.name,
                    local_path=Path("<r2-only>"),
                    rel_path=key,  # use the R2 key as rel_path
                    r2_key=key,
                    size=int(obj["Size"]),
                    mtime_utc=mtime.isoformat(),
                    sha256=None,
                ))
    return found
```

Then modify `run()` to call it just before writing the inventory:

```python
# After uploads finish, just before put_json(INVENTORY_KEY, ...):
local_keys = {a.r2_key for a in uploaded_or_existing}
r2_only = _discover_r2_only_artifacts(client, bucket, specs, local_keys)
inventory_artifacts = uploaded_or_existing + r2_only

put_json(
    client,
    bucket,
    INVENTORY_KEY,
    _inventory_payload(inventory_artifacts, profile=profile, dry_run=False),
)
stats.inventory_items = len(inventory_artifacts)
```

Notes:
- For R2-only artifacts, `mtime_utc` comes from `obj.LastModified`. `sha256` won't be available (no local file to hash) so it's omitted — the existing inventory schema already supports this (`sha256` is optional).
- `group` is inferred from the spec whose prefix matches the key.
- The discovery scan is one paginated `list_objects_v2` per prefix — cheap relative to the existing publish (~100ms / prefix for typical bucket sizes).

### Test to add

```python
# backend/tests/test_r2_artifacts.py
def test_inventory_preserves_r2_only_objects(mock_r2_client, tmp_path):
    """Files only on R2 (not locally) should still appear in the inventory."""
    # Setup: local has 1 file at data/ml/features/a.parquet
    # R2 has 2 files: a.parquet (matches local) and b.parquet (R2-only)
    # After publish, inventory should list BOTH a.parquet and b.parquet.
    ...
```

### Workaround for the downloader (until publish is fixed)

`r2_artifacts_download.py` could fall back to a paginated R2 listing when a `--keys` pattern matches no inventory entries. Logs a warning so the inventory issue is visible. This is a smaller, independent fix that doesn't require the publish-side fix to land first.

## Adjacent fix worth considering

`r2_artifacts_download.py` could fall back to a paginated R2 listing if a `--keys` pattern matches no inventory entries. That'd make the downloader robust to inventory drift without requiring the publish fix to land first. Could log a warning when this fallback fires so the inventory issue is visible.

## Files in scope

- `backend/app/ingest/r2_artifacts.py` (run + _inventory_payload)
- `backend/app/ingest/r2_artifacts_download.py` (optional fallback)
- `backend/tests/test_r2_artifacts.py` (cover the union case)

## Evidence

The macro.parquet incident this morning:

```
$ python -m app.ingest.r2_artifacts_download --keys 'data/ml/features/macro.parquet'
inventory_generated_at=2026-05-17T17:38:51.492491+00:00 inventory_files=314 selected=0 downloaded=0
```

Despite `data/ml/features/macro.parquet` being a 9.4 MB object on R2 (uploaded 2026-05-16 19:01 UTC) — confirmed via direct boto3 head_object.
