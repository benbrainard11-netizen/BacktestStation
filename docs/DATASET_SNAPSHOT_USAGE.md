# Dataset Snapshot Usage

Dataset snapshots are the durable proof of what data produced a run. The
snapshot-creation utility computes partition hashes; the database stores the
result and lets runs/locks reference it.

## Create A Snapshot

```python
from datetime import datetime

from app.db import models


snapshot = models.DatasetSnapshot(
    snapshot_id="5ad286d2..."[:64],
    name="expanded-universe-v1 through 2026 YTD",
    created_by="benpc",
    symbols_json=["NQ.c.0", "ES.c.0", "YM.c.0", "RTY.c.0"],
    date_start=datetime(2015, 1, 1),
    date_end=datetime(2026, 5, 17),
    schemas_json=["ohlcv-1m", "research_events"],
    r2_inventory_hash="<sha256-of-_research_inventory.json>",
    research_events_manifest_sha256="<sha256-of-data/research_events/manifest.json>",
    partition_count=2,
    total_bytes=3000,
    roll_map_version="continuous-v1",
    known_exclusions_json=[
        {"date": "2016-01-01", "symbol": "NQ.c.0", "reason": "holiday"}
    ],
    status="active",
)
```

## Add Partitions

Use one `DatasetSnapshotPartition` row per hashed object.

```python
snapshot.partitions.append(
    models.DatasetSnapshotPartition(
        r2_key="data/research_events/symbol=NQ.c.0/part-000.parquet",
        size=123456789,
        sha256="<partition-sha256>",
    )
)
```

## Attach Snapshot To A Backtest Run

Historical runs can stay null. Locked walk-forward and production-grade runs
should set `dataset_snapshot_id`, `code_commit_sha`, and `seed`.

```python
run = models.BacktestRun(
    strategy_version_id=strategy_version_id,
    symbol="NQ",
    timeframe="1m",
    dataset_snapshot_id=snapshot.snapshot_id,
    code_commit_sha="<git-sha-that-produced-run>",
    seed=247,
)
```

## Reference Snapshot From A Lock Record

`trial_lock_records.dataset_snapshot_id` is a soft string reference in v1. By
convention, set it to the same `dataset_snapshots.snapshot_id`.

```python
lock = models.TrialLockRecord(
    trial_group_id=trial_group_id,
    lock_type="pre_validation",
    candidate_set_hash="<sha256-of-candidate-config>",
    dataset_snapshot_id=snapshot.snapshot_id,
    code_commit_sha="<git-sha-at-lock-time>",
    window_train="2020-01-01:2025-12-31",
    window_validation="2018-01-01:2019-12-31",
    status="active",
)
```

## Query Snapshots By Partition

```python
snapshots = (
    session.query(models.DatasetSnapshot)
    .join(models.DatasetSnapshotPartition)
    .filter(
        models.DatasetSnapshotPartition.r2_key
        == "data/research_events/symbol=NQ.c.0/part-000.parquet"
    )
    .all()
)
```

This answers: "which snapshots included this exact data object?"
