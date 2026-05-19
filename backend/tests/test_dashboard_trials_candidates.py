"""Tests for dashboard Trials + Candidates endpoints."""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app

ARTIFACT_ROOT = Path(__file__).parent / "_artifacts" / "dashboard_trials_candidates"


@pytest.fixture
def session_factory() -> Generator[sessionmaker[Session], None, None]:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    db_path = ARTIFACT_ROOT / f"{uuid.uuid4().hex}.sqlite"
    engine = make_engine(f"sqlite:///{db_path}")
    create_all(engine)
    try:
        yield make_session_factory(engine)
    finally:
        engine.dispose()
        db_path.unlink(missing_ok=True)


@pytest.fixture
def client(
    session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)


def _seed_dashboard_fixture(
    factory: sessionmaker[Session],
) -> dict[str, int]:
    with factory() as session:
        strategy = models.Strategy(
            name="Strict Sweep Core",
            slug="strict-sweep-core",
            status="testing",
        )
        version = models.StrategyVersion(strategy=strategy, version="v6")
        run = models.BacktestRun(
            strategy_version=version,
            symbol="NQ",
            timeframe="1m",
            import_source="gpu-walk-forward",
        )
        hypothesis = models.Hypothesis(
            title="Strict sweep survives locked validation",
            hypothesis_md="Sweep failure + recovery remains positive OOS.",
            rationale_md="Consensus filtering was the dominant PnL lever.",
            status="active",
            parent_strategy_version=version,
            tags_json=["sweep", "strict-label"],
        )
        group = models.TrialGroup(
            hypothesis=hypothesis,
            name="strict sweep lock chain",
            search_space_json={"candidate": "sweep_failed_recovered_v1"},
            selection_rule="Freeze candidate before validation.",
            status="running",
        )
        pre_validation = models.TrialLockRecord(
            trial_group=group,
            lock_type="pre_validation",
            locked_at=dt.datetime(2026, 5, 17, 12, 0),
            candidate_set_hash="a" * 64,
            dataset_snapshot_id="expanded-universe-v1:2015-2026",
            code_commit_sha="1" * 40,
            status="active",
        )
        pre_test = models.TrialLockRecord(
            trial_group=group,
            lock_type="pre_test",
            locked_at=dt.datetime(2026, 5, 17, 12, 30),
            candidate_set_hash="b" * 64,
            dataset_snapshot_id="expanded-universe-v1:2015-2026",
            code_commit_sha="2" * 40,
            status="completed",
        )
        selected_trial = models.Trial(
            trial_group=group,
            lock_record=pre_validation,
            backtest_run=run,
            candidate_config_id="sweep_failed_recovered_v1",
            params_json={"stop_atr": 2.0, "target_atr": 4.0},
            data_snapshot_sha="c" * 64,
            started_at=dt.datetime(2026, 5, 17, 13, 0),
            completed_at=dt.datetime(2026, 5, 17, 13, 5),
            status="completed",
            is_selected=True,
            selection_reason="best locked top-bucket lift",
            summary_metrics_json={"net_r": 110.0, "win_rate": 0.49},
        )
        queued_trial = models.Trial(
            trial_group=group,
            lock_record=pre_test,
            candidate_config_id="sweep_alt_v1",
            status="running",
            started_at=dt.datetime(2026, 5, 17, 13, 10),
        )
        group.selected_trial = selected_trial
        session.add_all([strategy, queued_trial])
        session.flush()
        paper_candidate = models.StrategyPromotionCheck(
            strategy_id=strategy.id,
            strategy_version_id=version.id,
            backtest_run_id=run.id,
            candidate_name="Sweep Failed Recovered",
            candidate_config_id="sweep_failed_recovered_v1",
            findings_path="docs/ML_SWEEP_RELEASE.md",
            status="pass_paper",
            final_verdict="paper-ready after consensus filtering",
            pass_reasons=["positive 5/6 years"],
            fail_reasons=[],
            metrics_json={"cum_r": 110.0},
            robustness_json={"jaccard_overlap": 0.03},
            evidence_paths_json={"scoreboard": "docs/ML_FULL_SCOREBOARD.md"},
            next_actions=["paper start"],
            updated_at=dt.datetime(2026, 5, 18, 9, 0),
        )
        killed_candidate = models.StrategyPromotionCheck(
            candidate_name="Dead Variant",
            candidate_config_id="dead_v1",
            status="killed",
            final_verdict="regime artifact",
        )
        session.add_all([paper_candidate, killed_candidate])
        session.commit()
        return {
            "group_id": group.id,
            "run_id": run.id,
            "selected_trial_id": selected_trial.id,
            "paper_candidate_id": paper_candidate.id,
            "killed_candidate_id": killed_candidate.id,
        }


def test_trials_dashboard_lists_and_detail(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    ids = _seed_dashboard_fixture(session_factory)

    hypotheses = client.get("/api/dashboard/trials/hypotheses")
    assert hypotheses.status_code == 200, hypotheses.text
    hypothesis_body = hypotheses.json()
    assert hypothesis_body["count"] == 1
    assert hypothesis_body["hypotheses"][0]["active_trial_group_count"] == 1

    groups = client.get("/api/dashboard/trials/groups")
    assert groups.status_code == 200, groups.text
    group_body = groups.json()["groups"][0]
    assert group_body["trial_count"] == 2
    assert group_body["completed_trial_count"] == 1
    assert group_body["selected_trial_id"] == ids["selected_trial_id"]

    locks = client.get("/api/dashboard/trials/locks/recent")
    assert locks.status_code == 200, locks.text
    lock_body = locks.json()
    assert lock_body["count"] == 2
    assert lock_body["locks"][0]["lock_type"] == "pre_test"
    assert lock_body["locks"][0]["dataset_snapshot_id"].startswith("expanded")

    detail = client.get(f"/api/dashboard/trials/group/{ids['group_id']}")
    assert detail.status_code == 200, detail.text
    detail_body = detail.json()
    assert detail_body["hypothesis"]["title"].startswith("Strict sweep")
    assert detail_body["search_space_json"]["candidate"] == (
        "sweep_failed_recovered_v1"
    )
    assert len(detail_body["trials"]) == 2
    assert len(detail_body["locks"]) == 2


def test_trials_dashboard_group_detail_404(client: TestClient) -> None:
    response = client.get("/api/dashboard/trials/group/999999")
    assert response.status_code == 404


def test_candidates_dashboard_board_detail_and_action_stubs(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    ids = _seed_dashboard_fixture(session_factory)

    listing = client.get("/api/dashboard/candidates/list")
    assert listing.status_code == 200, listing.text
    body = listing.json()
    assert body["count"] == 2
    columns = {column["status"]: column for column in body["columns"]}
    assert columns["paper_ready"]["count"] == 1
    assert columns["killed"]["count"] == 1
    paper_card = columns["paper_ready"]["candidates"][0]
    assert paper_card["strategy_name"] == "Strict Sweep Core"
    assert paper_card["strategy_version"] == "v6"

    detail = client.get(f"/api/dashboard/candidates/{ids['paper_candidate_id']}")
    assert detail.status_code == 200, detail.text
    detail_body = detail.json()
    assert detail_body["lifecycle_status"] == "paper_ready"
    assert detail_body["linked_backtest_run_ids"] == [ids["run_id"]]
    assert detail_body["linked_trials"][0]["id"] == ids["selected_trial_id"]
    assert detail_body["metrics_json"]["cum_r"] == 110.0

    promote = client.post(
        f"/api/dashboard/candidates/{ids['paper_candidate_id']}/promote"
    )
    assert promote.status_code == 200, promote.text
    promote_body = promote.json()
    assert promote_body["accepted"] is False
    assert promote_body["current_status"] == "pass_paper"
    assert promote_body["lifecycle_status"] == "paper_ready"

    kill_missing = client.post("/api/dashboard/candidates/999999/kill")
    assert kill_missing.status_code == 404
