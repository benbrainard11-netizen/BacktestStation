"""Read-only aggregators for the dashboard Live Monitor endpoints."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import LiveSignal, Strategy, StrategyPromotionCheck
from app.db.models import StrategyVersion
from app.schemas.dashboard_live import (
    DashboardLiveActiveCandidates,
    DashboardLiveCandidate,
    DashboardLiveDriftReport,
    DashboardLivePosition,
    DashboardLivePositions,
    DashboardLiveSignal,
    DashboardLiveSignals,
)


PAPER_READY_STATUSES = ("pass_paper", "paper_ready")


def get_active_candidates(db: Session) -> DashboardLiveActiveCandidates:
    paper_ready = db.scalars(
        select(StrategyPromotionCheck)
        .where(StrategyPromotionCheck.status.in_(PAPER_READY_STATUSES))
        .order_by(
            StrategyPromotionCheck.created_at.desc(),
            StrategyPromotionCheck.id.desc(),
        )
        .limit(25)
    ).all()
    strategies, versions = _load_strategy_maps(db, paper_ready)
    candidates = [
        _candidate(check, strategies=strategies, versions=versions)
        for check in paper_ready
    ]
    return DashboardLiveActiveCandidates(
        paper_trade_active=False,
        active_count=0,
        candidates=[],
        paper_ready_candidates=candidates,
        message=(
            "No paper trade active. Start one via "
            "`bs paper start <candidate_id>`."
        ),
    )


def get_signals(
    db: Session, *, since: dt.datetime | None, limit: int
) -> DashboardLiveSignals:
    statement = select(LiveSignal)
    if since is not None:
        statement = statement.where(LiveSignal.ts >= since)
    rows = db.scalars(
        statement.order_by(LiveSignal.ts.desc(), LiveSignal.id.desc()).limit(limit)
    ).all()
    signals = [
        DashboardLiveSignal(
            id=row.id,
            strategy_version_id=row.strategy_version_id,
            ts=row.ts,
            side=row.side,
            price=row.price,
            reason=row.reason,
            executed=row.executed,
        )
        for row in rows
    ]
    return DashboardLiveSignals(since=since, count=len(signals), signals=signals)


def get_drift_report() -> DashboardLiveDriftReport:
    return DashboardLiveDriftReport(
        generated_at=_utc_now(),
        message=(
            "No drift report yet because paper trading has not started. "
            "This endpoint is a typed v1 placeholder."
        ),
    )


def get_positions() -> DashboardLivePositions:
    positions: list[DashboardLivePosition] = []
    return DashboardLivePositions(
        count=0,
        positions=positions,
        message="No active paper/live positions.",
    )


def _load_strategy_maps(
    db: Session, checks: list[StrategyPromotionCheck]
) -> tuple[dict[int, Strategy], dict[int, StrategyVersion]]:
    version_ids = {
        check.strategy_version_id
        for check in checks
        if check.strategy_version_id is not None
    }
    versions = _versions_by_id(db, version_ids)
    strategy_ids = {
        check.strategy_id for check in checks if check.strategy_id is not None
    }
    strategy_ids.update(version.strategy_id for version in versions.values())
    strategies = _strategies_by_id(db, strategy_ids)
    return strategies, versions


def _candidate(
    check: StrategyPromotionCheck,
    *,
    strategies: dict[int, Strategy],
    versions: dict[int, StrategyVersion],
) -> DashboardLiveCandidate:
    version = versions.get(check.strategy_version_id)
    strategy_id = check.strategy_id or (version.strategy_id if version else None)
    strategy = strategies.get(strategy_id) if strategy_id is not None else None
    return DashboardLiveCandidate(
        candidate_id=check.id,
        candidate_name=check.candidate_name,
        candidate_config_id=check.candidate_config_id,
        lifecycle_status=_lifecycle_status(check.status),
        strategy_id=strategy_id,
        strategy_name=strategy.name if strategy else None,
        strategy_version_id=check.strategy_version_id,
        strategy_version=version.version if version else None,
        start_command=f"bs paper start {check.id}",
    )


def _versions_by_id(
    db: Session, version_ids: set[int | None]
) -> dict[int, StrategyVersion]:
    ids = {int(value) for value in version_ids if value is not None}
    if not ids:
        return {}
    rows = db.scalars(
        select(StrategyVersion).where(StrategyVersion.id.in_(ids))
    ).all()
    return {row.id: row for row in rows}


def _strategies_by_id(
    db: Session, strategy_ids: set[int | None]
) -> dict[int, Strategy]:
    ids = {int(value) for value in strategy_ids if value is not None}
    if not ids:
        return {}
    rows = db.scalars(select(Strategy).where(Strategy.id.in_(ids))).all()
    return {row.id: row for row in rows}


def _lifecycle_status(status: str) -> str:
    if status == "pass_paper":
        return "paper_ready"
    return status


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)
