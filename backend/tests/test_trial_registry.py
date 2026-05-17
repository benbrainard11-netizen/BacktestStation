from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, text

from app.db import models
from app.db.session import create_all, make_engine, make_session_factory


def test_trial_registry_locked_walk_forward_roundtrip(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'trial_registry.sqlite'}")
    create_all(engine)
    SessionLocal = make_session_factory(engine)

    with SessionLocal() as session:
        strategy = models.Strategy(name="Type B Candidate", slug="type-b-candidate")
        version = models.StrategyVersion(version="v13-v19-frozen", strategy=strategy)
        run = models.BacktestRun(
            symbol="NQ",
            timeframe="1m",
            import_source="locked_2018_2019_holdout",
            strategy_version=version,
            tags=["locked-walk-forward", "primary-test"],
        )
        run.metrics = models.RunMetrics(
            net_r=42.5,
            win_rate=0.51,
            trade_count=120,
            max_drawdown=-8.0,
        )
        hypothesis = models.Hypothesis(
            title="Frozen Type-B candidate survives untouched holdouts",
            hypothesis_md=(
                "The frozen v13-v19 deploy candidate keeps comparable "
                "per-trade R on 2018-2019 and 2026 YTD."
            ),
            rationale_md="2020-2025 is exploratory; 2018-2019 and 2026 YTD are untouched.",
            status="active",
            parent_strategy_version=version,
            tags_json=["type-b", "locked-validation"],
        )
        group = models.TrialGroup(
            hypothesis=hypothesis,
            name="two-lock holdout validation",
            search_space_json={
                "frozen_candidate": "v13-v19 Type-B deploy candidate",
                "slippage_ticks": 2,
                "concurrency_cap": 10,
            },
            selection_rule="No new selection after lock; run frozen candidate once per holdout.",
            status="running",
        )
        pre_validation = models.TrialLockRecord(
            trial_group=group,
            lock_type="pre_validation",
            locked_at=datetime(2026, 5, 17, 12, 10),
            candidate_set_yaml="- type_b_deploy_candidate_v13_v19\n",
            candidate_set_hash="b" * 64,
            dataset_snapshot_id="expanded-universe-v1:2015-2026",
            code_commit_sha="6727c90307c0f60768fac1eb5d4af5e1075dd3a1",
            pre_registration_md="Pass if 2018-2019 remains positive with comparable avg_R.",
            window_train="2020-01-01:2025-12-31",
            window_validation="2018-01-01:2019-12-31",
            status="active",
            bug_exceptions_after_lock_json=[],
        )
        pre_test = models.TrialLockRecord(
            trial_group=group,
            lock_type="pre_test",
            locked_at=datetime(2026, 5, 17, 12, 20),
            candidate_set_yaml="- type_b_deploy_candidate_v13_v19\n",
            candidate_set_hash="c" * 64,
            dataset_snapshot_id="expanded-universe-v1:2015-2026",
            code_commit_sha="6727c90307c0f60768fac1eb5d4af5e1075dd3a1",
            pre_registration_md="Pass if 2026 YTD remains pro-rated positive.",
            window_test="2026-01-01:2026-05-17",
            status="active",
            bug_exceptions_after_lock_json=[
                {"ref": "BUG-2026-05-17-inventory", "reason": "R2 inventory only"}
            ],
        )
        trial = models.Trial(
            trial_group=group,
            lock_record=pre_validation,
            backtest_run=run,
            candidate_config_id="type_b_deploy_candidate_v13_v19",
            params_json={"cap": 10, "slippage_ticks": 2},
            data_snapshot_sha="a" * 64,
            started_at=datetime(2026, 5, 17, 12, 30),
            completed_at=datetime(2026, 5, 17, 12, 40),
            status="completed",
            is_selected=True,
            selection_reason="frozen candidate selected before locked holdout",
            summary_metrics_json={"net_r": 42.5, "win_rate": 0.51},
        )
        group.selected_trial = trial
        session.add(strategy)
        session.commit()
        hypothesis_id = hypothesis.id
        group_id = group.id
        trial_id = trial.id
        lock_id = pre_validation.id
        pre_test_id = pre_test.id

    with SessionLocal() as session:
        loaded_hypothesis = session.get(models.Hypothesis, hypothesis_id)
        loaded_group = session.get(models.TrialGroup, group_id)
        loaded_trial = session.get(models.Trial, trial_id)
        loaded_lock = session.get(models.TrialLockRecord, lock_id)
        loaded_pre_test = session.get(models.TrialLockRecord, pre_test_id)

        assert loaded_hypothesis is not None
        assert loaded_group is not None
        assert loaded_trial is not None
        assert loaded_lock is not None
        assert loaded_pre_test is not None
        assert loaded_hypothesis.parent_strategy_version.strategy.slug == "type-b-candidate"
        assert loaded_group.hypothesis.title == (
            "Frozen Type-B candidate survives untouched holdouts"
        )
        assert loaded_group.selected_trial_id == trial_id
        assert loaded_group.selected_trial.candidate_config_id == (
            "type_b_deploy_candidate_v13_v19"
        )
        assert loaded_trial.trial_lock_record_id == lock_id
        assert loaded_trial.lock_record.lock_type == "pre_validation"
        assert loaded_trial.backtest_run.metrics.net_r == 42.5
        assert loaded_lock.dataset_snapshot_id == "expanded-universe-v1:2015-2026"
        assert loaded_pre_test.bug_exceptions_after_lock_json == [
            {"ref": "BUG-2026-05-17-inventory", "reason": "R2 inventory only"}
        ]


def test_trial_registry_tables_and_indexes_exist(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'trial_registry_schema.sqlite'}")
    create_all(engine)
    inspector = inspect(engine)

    assert {"hypotheses", "trial_groups", "trials", "trial_lock_records"}.issubset(
        set(inspector.get_table_names())
    )
    hypothesis_columns = {c["name"] for c in inspector.get_columns("hypotheses")}
    trial_group_columns = {c["name"] for c in inspector.get_columns("trial_groups")}
    trial_columns = {c["name"] for c in inspector.get_columns("trials")}
    lock_columns = {c["name"] for c in inspector.get_columns("trial_lock_records")}

    assert {
        "title",
        "hypothesis_md",
        "rationale_md",
        "status",
        "parent_strategy_version_id",
        "tags_json",
    }.issubset(hypothesis_columns)
    assert {
        "hypothesis_id",
        "name",
        "search_space_json",
        "selection_rule",
        "selected_trial_id",
        "status",
    }.issubset(trial_group_columns)
    assert {
        "trial_group_id",
        "trial_lock_record_id",
        "backtest_run_id",
        "candidate_config_id",
        "params_json",
        "parent_trial_id",
        "data_snapshot_sha",
        "status",
        "is_selected",
        "summary_metrics_json",
    }.issubset(trial_columns)
    assert {
        "id",
        "trial_group_id",
        "lock_type",
        "locked_at",
        "candidate_set_yaml",
        "candidate_set_hash",
        "dataset_snapshot_id",
        "code_commit_sha",
        "pre_registration_md",
        "window_train",
        "window_validation",
        "window_test",
        "window_final",
        "status",
        "bug_exceptions_after_lock_json",
        "superseded_by_lock_id",
        "notes",
    }.issubset(lock_columns)

    index_names = {
        index["name"]
        for table_name in ("hypotheses", "trial_groups", "trials", "trial_lock_records")
        for index in inspector.get_indexes(table_name)
    }
    assert {
        "ix_hypotheses_status",
        "ix_hypotheses_parent_strategy_version_id",
        "ix_trial_groups_hypothesis_id",
        "ix_trial_groups_status",
        "ix_trials_trial_group_id",
        "ix_trials_trial_lock_record_id",
        "ix_trials_backtest_run_id",
        "ix_trials_status",
        "ix_trials_is_selected",
        "ix_trial_lock_records_trial_group_id",
        "ix_trial_lock_records_lock_type",
        "ix_trial_lock_records_candidate_set_hash",
        "ix_trial_lock_records_dataset_snapshot_id",
        "ix_trial_lock_records_code_commit_sha",
        "ix_trial_lock_records_status",
        "ix_trial_lock_records_superseded_by_lock_id",
    }.issubset(index_names)


def test_trial_registry_migration_is_idempotent(tmp_path: Path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'trial_registry_idempotent.sqlite'}")
    create_all(engine)
    create_all(engine)

    with engine.begin() as connection:
        hypothesis_count = connection.execute(text("SELECT COUNT(*) FROM hypotheses")).scalar_one()
        group_count = connection.execute(text("SELECT COUNT(*) FROM trial_groups")).scalar_one()
        trial_count = connection.execute(text("SELECT COUNT(*) FROM trials")).scalar_one()
        lock_count = connection.execute(
            text("SELECT COUNT(*) FROM trial_lock_records")
        ).scalar_one()

    assert hypothesis_count == 0
    assert group_count == 0
    assert trial_count == 0
    assert lock_count == 0
