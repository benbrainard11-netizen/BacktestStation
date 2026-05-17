# Trial Registry Usage

The trial registry records research lineage so later reviews can see what was
tested, what was selected, and which results were actually locked before the
holdout was run.

## Current Locked Walk-Forward Shape

Use this for the 2026-05-17 Type-B validation run:

| Step | Purpose |
|---|---|
| `Hypothesis` | The falsifiable claim being tested |
| `TrialGroup` | The frozen candidate/search batch under that hypothesis |
| `TrialLockRecord` | The lock proving candidates, data, and code were frozen first |
| `Trial` | The actual run/result, linked back to the lock that governed it |

`dataset_snapshot_id` is a free-form v1 string/hash. There is no
`dataset_snapshots` table yet.

## Example: Frozen Type-B Holdout

```python
from datetime import datetime

from app.db import models


hypothesis = models.Hypothesis(
    title="Frozen Type-B candidate survives untouched holdouts",
    hypothesis_md=(
        "The frozen v13-v19 deploy candidate keeps comparable per-trade R "
        "on 2018-2019 and 2026 YTD."
    ),
    rationale_md=(
        "2020-2025 is exploratory/contaminated. The untouched evidence is "
        "2018-2019 plus 2026 YTD."
    ),
    status="active",
    parent_strategy_version_id=strategy_version_id,
    tags_json=["type-b", "locked-validation"],
)

group = models.TrialGroup(
    hypothesis=hypothesis,
    name="two-lock holdout validation",
    search_space_json={
        "frozen_candidate": "v13-v19 Type-B deploy candidate",
        "slippage_ticks": 2,
        "concurrency_cap": 10,
        "sweep_hour_filter": "drop 22-06 UTC",
    },
    selection_rule=(
        "No new selection after lock; run the frozen candidate once per "
        "untouched holdout."
    ),
    status="running",
)

pre_validation_lock = models.TrialLockRecord(
    trial_group=group,
    lock_type="pre_validation",
    locked_at=datetime.utcnow(),
    candidate_set_yaml="- type_b_deploy_candidate_v13_v19\n",
    candidate_set_hash="<sha256-of-candidate-yaml-or-config>",
    dataset_snapshot_id="expanded-universe-v1:2015-2026",
    code_commit_sha="<git-sha-at-lock-time>",
    pre_registration_md=(
        "Pass if 2018-2019 remains positive with comparable avg_R and no "
        "obvious single-day dependence."
    ),
    window_train="2020-01-01:2025-12-31",
    window_validation="2018-01-01:2019-12-31",
    status="active",
    bug_exceptions_after_lock_json=[],
)

trial = models.Trial(
    trial_group=group,
    lock_record=pre_validation_lock,
    backtest_run_id=backtest_run_id,
    candidate_config_id="type_b_deploy_candidate_v13_v19",
    params_json={
        "slippage_ticks": 2,
        "concurrency_cap": 10,
        "sweep_hour_filter": "drop 22-06 UTC",
    },
    data_snapshot_sha="<optional-data-snapshot-sha>",
    started_at=datetime.utcnow(),
    status="running",
    is_selected=True,
    selection_reason="Candidate was frozen before untouched holdout execution.",
)
group.selected_trial = trial
```

## Lock Rules

- Create the `TrialLockRecord` before starting the holdout run.
- Link every locked `Trial` to `trial_lock_record_id`.
- Historical exploratory audits can be backfilled as hypotheses/groups/trials
  without lock records.
- If a bug fix is allowed after a lock, append a structured object to
  `bug_exceptions_after_lock_json`, for example:

```json
[
  {
    "ref": "BUG-2026-05-17-inventory",
    "reason": "R2 inventory discoverability only; no simulator math changed",
    "approved_by": "ben",
    "approved_at": "2026-05-17T20:30:00Z"
  }
]
```

## Second Lock And Final Run

For the 2026 YTD secondary holdout, add another lock:

```python
pre_test_lock = models.TrialLockRecord(
    trial_group=group,
    lock_type="pre_test",
    locked_at=datetime.utcnow(),
    candidate_set_yaml="- type_b_deploy_candidate_v13_v19\n",
    candidate_set_hash="<sha256-of-final-candidate-config>",
    dataset_snapshot_id="expanded-universe-v1:2015-2026",
    code_commit_sha="<git-sha-at-lock-time>",
    pre_registration_md="Pass if 2026 YTD is pro-rated positive.",
    window_test="2026-01-01:2026-05-17",
    status="active",
    bug_exceptions_after_lock_json=[],
)
```

Then link the 2026 YTD `Trial` to `pre_test_lock`.
