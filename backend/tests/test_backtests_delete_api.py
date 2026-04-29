"""DELETE /api/backtests/{id} tests."""

from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db import models
from app.db.session import create_all, get_session, make_engine, make_session_factory
from app.main import app


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'delete.sqlite'}")
    create_all(engine)
    return make_session_factory(engine)


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _seed_full_run(
    factory: sessionmaker[Session], slug: str = "test"
) -> tuple[int, int]:
    """Insert strategy + version + run with trade + equity + metrics + config + note.
    Returns (run_id, trade_id)."""
    with factory() as session:
        strategy = models.Strategy(name="Test", slug=slug, status="testing")
        version = models.StrategyVersion(strategy=strategy, version="v1")
        run = models.BacktestRun(
            strategy_version=version,
            symbol="NQ",
            import_source="fixture",
            start_ts=datetime(2026, 1, 2),
            end_ts=datetime(2026, 1, 3),
        )
        trade = models.Trade(
            entry_ts=datetime(2026, 1, 2, 10, 0),
            symbol="NQ",
            side="long",
            entry_price=21000.0,
            size=1.0,
        )
        equity = models.EquityPoint(ts=datetime(2026, 1, 2, 10, 5), equity=500.0)
        metrics = models.RunMetrics(net_pnl=500.0, trade_count=1)
        config = models.ConfigSnapshot(payload={"symbol": "NQ"})
        run.trades.append(trade)
        run.equity_points.append(equity)
        run.metrics = metrics
        run.config_snapshot = config
        session.add(strategy)
        session.commit()
        note = models.Note(
            body="survives deletion", backtest_run_id=run.id, trade_id=trade.id
        )
        session.add(note)
        session.commit()
        return run.id, trade.id


def test_delete_existing_run_cascades(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_id, trade_id = _seed_full_run(session_factory)

    response = client.delete(f"/api/backtests/{run_id}")
    assert response.status_code == 204
    assert response.content == b""

    # Follow-up GET is 404.
    assert client.get(f"/api/backtests/{run_id}").status_code == 404

    # Verify the children are gone at the DB level too.
    with session_factory() as session:
        assert session.get(models.BacktestRun, run_id) is None
        assert session.get(models.Trade, trade_id) is None
        trades = list(
            session.scalars(
                select(models.Trade).where(models.Trade.backtest_run_id == run_id)
            )
        )
        assert trades == []
        equity = list(
            session.scalars(
                select(models.EquityPoint).where(
                    models.EquityPoint.backtest_run_id == run_id
                )
            )
        )
        assert equity == []
        metrics = list(
            session.scalars(
                select(models.RunMetrics).where(
                    models.RunMetrics.backtest_run_id == run_id
                )
            )
        )
        assert metrics == []
        config = list(
            session.scalars(
                select(models.ConfigSnapshot).where(
                    models.ConfigSnapshot.backtest_run_id == run_id
                )
            )
        )
        assert config == []


def test_delete_leaves_notes_as_floating(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Notes are not cascade-deleted; their run_id/trade_id go to null is NOT the
    current policy — they stay with dangling FKs. This test pins that behavior
    so future changes are deliberate."""
    run_id, _ = _seed_full_run(session_factory)

    client.delete(f"/api/backtests/{run_id}")

    # Note body still accessible via /api/notes (floats without its parent).
    notes = client.get("/api/notes").json()
    assert len(notes) == 1
    assert notes[0]["body"] == "survives deletion"


def test_delete_missing_run_404(client: TestClient) -> None:
    response = client.delete("/api/backtests/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Backtest run not found"


def test_delete_only_removes_target_run(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_a_id, _ = _seed_full_run(session_factory, slug="strategy-a")
    run_b_id, _ = _seed_full_run(session_factory, slug="strategy-b")
    assert run_a_id != run_b_id

    client.delete(f"/api/backtests/{run_a_id}")

    assert client.get(f"/api/backtests/{run_a_id}").status_code == 404
    assert client.get(f"/api/backtests/{run_b_id}").status_code == 200


def test_delete_clears_baseline_run_id_on_strategy_versions(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Pin the 2026-04-28 fix: deleting a run that's a Forward Drift baseline
    must NULL out StrategyVersion.baseline_run_id, otherwise /drift/latest
    renders an empty panel because the FK is stale (SQLite FK cascades are
    off in this app)."""
    run_id, _ = _seed_full_run(session_factory, slug="baseline-deleter")

    with session_factory() as session:
        version = session.scalars(select(models.StrategyVersion)).one()
        version.baseline_run_id = run_id
        session.commit()
        version_id = version.id

    response = client.delete(f"/api/backtests/{run_id}")
    assert response.status_code == 204

    with session_factory() as session:
        version = session.get(models.StrategyVersion, version_id)
        assert version is not None
        assert version.baseline_run_id is None


def test_delete_clears_experiment_baseline_and_variant_run_ids(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Same fix for Experiment.baseline_run_id and Experiment.variant_run_id.
    Both columns FK to backtest_runs.id without ON DELETE SET NULL in SQLite,
    so we have to clear them explicitly in the delete handler."""
    baseline_id, _ = _seed_full_run(session_factory, slug="exp-baseline")
    variant_id, _ = _seed_full_run(session_factory, slug="exp-variant")

    with session_factory() as session:
        version = session.scalars(
            select(models.StrategyVersion).where(
                models.StrategyVersion.id == 1
            )
        ).one()
        exp = models.Experiment(
            strategy_version_id=version.id,
            hypothesis="does X help?",
            baseline_run_id=baseline_id,
            variant_run_id=variant_id,
        )
        session.add(exp)
        session.commit()
        exp_id = exp.id

    client.delete(f"/api/backtests/{baseline_id}")
    with session_factory() as session:
        exp = session.get(models.Experiment, exp_id)
        assert exp is not None
        assert exp.baseline_run_id is None
        assert exp.variant_run_id == variant_id

    client.delete(f"/api/backtests/{variant_id}")
    with session_factory() as session:
        exp = session.get(models.Experiment, exp_id)
        assert exp is not None
        assert exp.variant_run_id is None


def test_delete_doesnt_clear_unrelated_baselines(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Deleting run A must NOT clear baseline_run_id on a version pointing at
    run B."""
    run_a_id, _ = _seed_full_run(session_factory, slug="a")
    run_b_id, _ = _seed_full_run(session_factory, slug="b")

    with session_factory() as session:
        version_b = session.scalars(
            select(models.StrategyVersion).join(models.Strategy).where(
                models.Strategy.slug == "b"
            )
        ).one()
        version_b.baseline_run_id = run_b_id
        session.commit()
        version_b_id = version_b.id

    client.delete(f"/api/backtests/{run_a_id}")

    with session_factory() as session:
        version_b = session.get(models.StrategyVersion, version_b_id)
        assert version_b is not None
        assert version_b.baseline_run_id == run_b_id


def test_delete_run_removes_prop_firm_simulations(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Codex review 2026-04-29: PropFirmSimulation has a non-null FK to
    backtest_runs. With FK enforcement on, deleting a run with a sim
    pointing at it would 500 unless the sim is cascade-deleted first."""
    run_id, _ = _seed_full_run(session_factory, slug="prop")
    with session_factory() as session:
        sim = models.PropFirmSimulation(
            name="test sim",
            source_backtest_run_id=run_id,
            firm_profile_id="apex_50k",
            config_json={"k": 1},
            firm_profile_json={"name": "apex"},
            aggregated_json={"pass_rate": 0.5},
            selected_paths_json=[],
            fan_bands_json={},
            confidence_json={},
            rule_violation_counts_json={},
            daily_pnl_json=[],
            pool_backtests_json=[],
            summary_pass_rate=0.5,
            summary_fail_rate=0.5,
            summary_payout_rate=0.0,
            summary_ev_after_fees=0.0,
            summary_confidence=0.95,
            sampling_mode="bootstrap",
            simulation_count=1000,
            risk_label="conservative",
            strategy_name="test",
            firm_name="apex",
            account_size=50_000.0,
        )
        session.add(sim)
        session.commit()
        sim_id = sim.id

    response = client.delete(f"/api/backtests/{run_id}")
    assert response.status_code == 204

    with session_factory() as session:
        assert session.get(models.PropFirmSimulation, sim_id) is None
