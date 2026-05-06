"""Backtest run endpoints: read + light mutations (rename) + engine kickoff."""

import asyncio
import datetime as dt
import threading
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.backtest.engine import RunConfig
from app.backtest.engine import run as engine_run
from app.backtest.instruments import lookup as lookup_instrument
from app.backtest.runner import (
    _data_root,
    _git_sha,
    _resolve_strategy,
    load_aux_bars,
    load_bars,
    make_run_dir,
    persist_run_to_session,
    write_run,
)
from app.db.models import (
    BacktestRun,
    ConfigSnapshot,
    EquityPoint,
    RunMetrics,
    StrategyVersion,
    Trade,
)
from app.db.session import get_session
from app.schemas import (
    AsyncBacktestRunQueued,
    BacktestRunRead,
    BacktestRunRequest,
    BacktestRunTagsUpdate,
    BacktestRunUpdate,
    ConfigSnapshotRead,
    EquityPointRead,
    RunMetricsRead,
    StrategyDefinitionRead,
    TradeRead,
)
from app.services.run_deletion import delete_run as _delete_run_with_cleanup
from app.services.strategy_registry import STRATEGY_DEFINITIONS

router = APIRouter(prefix="/backtests", tags=["backtests"])

_ASYNC_PROGRESS: dict[int, dict[str, float | int | None]] = {}
_ASYNC_PROGRESS_LOCK = threading.RLock()


@router.get("/strategies", response_model=list[StrategyDefinitionRead])
def list_runnable_strategies() -> list[dict]:
    """Strategies the engine resolver knows how to run, with their
    parameter schemas (frontend-friendly JSON Schema-ish) so the
    Run-a-Backtest form can render typed fields per strategy. The
    list is hand-maintained in `app.services.strategy_registry` to
    mirror `runner._resolve_strategy`.
    """
    return STRATEGY_DEFINITIONS


def _require_run(db: Session, backtest_id: int) -> BacktestRun:
    run = db.get(BacktestRun, backtest_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return run


def _iso_to_utc(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value).replace(tzinfo=dt.UTC)


def _set_progress(
    run_id: int,
    *,
    progress_pct: float | None = None,
    eta_seconds: int | None = None,
) -> None:
    with _ASYNC_PROGRESS_LOCK:
        current = _ASYNC_PROGRESS.setdefault(
            run_id,
            {"progress_pct": None, "eta_seconds": None, "started_at": None},
        )
        current["progress_pct"] = progress_pct
        current["eta_seconds"] = eta_seconds


def _mark_progress_started(run_id: int) -> None:
    with _ASYNC_PROGRESS_LOCK:
        _ASYNC_PROGRESS[run_id] = {
            "progress_pct": 0.0,
            "eta_seconds": None,
            "started_at": time.monotonic(),
        }


def _attach_async_progress(run: BacktestRun) -> BacktestRun:
    with _ASYNC_PROGRESS_LOCK:
        progress = dict(_ASYNC_PROGRESS.get(run.id, {}))
    if run.status == "complete":
        run.progress_pct = 100.0
        run.eta_seconds = 0
    elif run.status in {"queued", "running"}:
        run.progress_pct = progress.get("progress_pct")
        run.eta_seconds = progress.get("eta_seconds")
    else:
        run.progress_pct = None
        run.eta_seconds = None
    return run


def _build_run_config_and_inputs(
    payload: BacktestRunRequest, db: Session
) -> tuple[RunConfig, object, list, dict]:
    version = db.get(StrategyVersion, payload.strategy_version_id)
    if version is None:
        raise HTTPException(
            status_code=404,
            detail=f"strategy version {payload.strategy_version_id} not found",
        )

    spec = lookup_instrument(payload.symbol)
    instrument_kwargs: dict = {}
    if spec is not None:
        instrument_kwargs = {
            "tick_size": spec.tick_size,
            "contract_value": spec.contract_value,
            "commission_per_contract": spec.commission_per_contract,
        }

    run_params = dict(payload.params or {})
    if (
        payload.strategy_name == "composable"
        and not run_params.get("entry_long")
        and not run_params.get("entry_short")
    ):
        if version.spec_json:
            run_params = {**version.spec_json, **run_params}

    config = RunConfig(
        strategy_name=payload.strategy_name,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        start=payload.start,
        end=payload.end,
        initial_equity=payload.initial_equity,
        qty=payload.qty,
        aux_symbols=payload.aux_symbols,
        params=run_params,
        slippage_ticks=payload.slippage_ticks,
        session_start_hour=payload.session_start_hour,
        session_end_hour=payload.session_end_hour,
        session_tz=payload.session_tz,
        **instrument_kwargs,
    )

    try:
        strategy = _resolve_strategy(config.strategy_name, config.params, config)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    bars = load_bars(config)
    if not bars:
        raise HTTPException(
            status_code=422,
            detail=(
                f"no bars found for {config.symbol} {config.timeframe} "
                f"{config.start}..{config.end} -- check the warehouse"
            ),
        )
    aux_bars = load_aux_bars(config)
    return config, strategy, bars, aux_bars


def _execute_engine_backtest(
    payload: BacktestRunRequest,
    db: Session,
    *,
    existing_run_id: int | None = None,
    progress_callback=None,
) -> int:
    config, strategy, bars, aux_bars = _build_run_config_and_inputs(payload, db)

    started_at = dt.datetime.now(dt.UTC)
    result = engine_run(
        strategy,
        bars,
        config,
        aux_bars=aux_bars,
        progress_callback=progress_callback,
    )
    completed_at = dt.datetime.now(dt.UTC)

    out_dir, _ = make_run_dir(_data_root(), config.strategy_name, started_at)
    write_run(out_dir, result, started_at, completed_at, _git_sha())

    return persist_run_to_session(
        db,
        config,
        result,
        out_dir,
        payload.strategy_version_id,
        run_id=existing_run_id,
    )


def _run_async_backtest_worker(
    payload: BacktestRunRequest,
    session_factory: sessionmaker[Session],
    run_id: int,
) -> None:
    _mark_progress_started(run_id)
    with session_factory() as session:
        run = session.get(BacktestRun, run_id)
        if run is None:
            return
        run.status = "running"
        session.commit()

        started_at = time.monotonic()

        def progress_callback(done: int, total: int) -> None:
            if total <= 0:
                return
            pct = min(100.0, max(0.0, (done / total) * 100.0))
            eta = None
            if done > 0 and done < total:
                elapsed = time.monotonic() - started_at
                eta = int(max(0.0, (elapsed / done) * (total - done)))
            _set_progress(run_id, progress_pct=pct, eta_seconds=eta)

        try:
            _execute_engine_backtest(
                payload,
                session,
                existing_run_id=run_id,
                progress_callback=progress_callback,
            )
            _set_progress(run_id, progress_pct=100.0, eta_seconds=0)
            session.commit()
        except Exception:
            session.rollback()
            failed = session.get(BacktestRun, run_id)
            if failed is not None:
                failed.status = "failed"
                session.commit()
            _set_progress(run_id, progress_pct=None, eta_seconds=None)
            raise


@router.post("/run", response_model=BacktestRunRead, status_code=201)
def run_engine_backtest(
    payload: BacktestRunRequest, db: Session = Depends(get_session)
) -> BacktestRun:
    """Kick off a synchronous engine backtest. Loads bars, runs the strategy,
    writes outputs to disk, persists the BacktestRun row, returns it."""
    run_id = _execute_engine_backtest(payload, db)

    # Mirror the async handler's idea-origin tag so sync-driven runs from
    # /inbox are also traceable back to the originating sidecar idea.
    if payload.idea_id is not None:
        run = _require_run(db, run_id)
        idea_tag = f"idea:{payload.idea_id}"
        existing_tags = list(run.tags or [])
        if idea_tag not in existing_tags:
            run.tags = [*existing_tags, idea_tag]

    db.commit()
    return _attach_async_progress(_require_run(db, run_id))


@router.post("/run-async", response_model=AsyncBacktestRunQueued, status_code=202)
async def run_engine_backtest_async(
    payload: BacktestRunRequest, db: Session = Depends(get_session)
) -> AsyncBacktestRunQueued:
    """Queue an engine backtest for bot/programmatic callers."""
    version = db.get(StrategyVersion, payload.strategy_version_id)
    if version is None:
        raise HTTPException(
            status_code=404,
            detail=f"strategy version {payload.strategy_version_id} not found",
        )
    run = BacktestRun(
        strategy_version_id=payload.strategy_version_id,
        name=f"{payload.strategy_name} {payload.start}..{payload.end}",
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        start_ts=_iso_to_utc(payload.start),
        end_ts=_iso_to_utc(payload.end),
        source="engine",
        status="queued",
        tags=[f"idea:{payload.idea_id}"] if payload.idea_id is not None else None,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    _set_progress(run.id, progress_pct=0.0, eta_seconds=None)

    factory: sessionmaker[Session] = sessionmaker(
        bind=db.get_bind(), autoflush=False, autocommit=False
    )
    asyncio.create_task(
        asyncio.to_thread(_run_async_backtest_worker, payload, factory, run.id)
    )
    return AsyncBacktestRunQueued(run_id=run.id)


@router.get("", response_model=list[BacktestRunRead])
def list_backtests(db: Session = Depends(get_session)) -> list[BacktestRun]:
    statement = select(BacktestRun).order_by(
        BacktestRun.created_at.desc(), BacktestRun.id.desc()
    )
    return [_attach_async_progress(run) for run in db.scalars(statement).all()]


@router.get("/{backtest_id}", response_model=BacktestRunRead)
def get_backtest(backtest_id: int, db: Session = Depends(get_session)) -> BacktestRun:
    return _attach_async_progress(_require_run(db, backtest_id))


@router.get("/{backtest_id}/trades", response_model=list[TradeRead])
def list_backtest_trades(
    backtest_id: int, db: Session = Depends(get_session)
) -> list[Trade]:
    _require_run(db, backtest_id)
    statement = (
        select(Trade)
        .where(Trade.backtest_run_id == backtest_id)
        .order_by(Trade.entry_ts.asc(), Trade.id.asc())
    )
    return list(db.scalars(statement).all())


@router.get("/{backtest_id}/equity", response_model=list[EquityPointRead])
def list_backtest_equity(
    backtest_id: int, db: Session = Depends(get_session)
) -> list[EquityPoint]:
    _require_run(db, backtest_id)
    statement = (
        select(EquityPoint)
        .where(EquityPoint.backtest_run_id == backtest_id)
        .order_by(EquityPoint.ts.asc(), EquityPoint.id.asc())
    )
    return list(db.scalars(statement).all())


@router.get("/{backtest_id}/metrics", response_model=RunMetricsRead)
def get_backtest_metrics(
    backtest_id: int, db: Session = Depends(get_session)
) -> RunMetrics:
    _require_run(db, backtest_id)
    statement = select(RunMetrics).where(RunMetrics.backtest_run_id == backtest_id)
    metrics = db.scalars(statement).first()
    if metrics is None:
        raise HTTPException(status_code=404, detail="Backtest metrics not found")
    return metrics


@router.get("/{backtest_id}/config", response_model=ConfigSnapshotRead)
def get_backtest_config(
    backtest_id: int, db: Session = Depends(get_session)
) -> ConfigSnapshot:
    _require_run(db, backtest_id)
    snapshot = db.scalars(
        select(ConfigSnapshot).where(ConfigSnapshot.backtest_run_id == backtest_id)
    ).first()
    if snapshot is None:
        raise HTTPException(
            status_code=404, detail="Backtest config snapshot not found"
        )
    return snapshot


@router.patch("/{backtest_id}", response_model=BacktestRunRead)
def update_backtest(
    backtest_id: int,
    payload: BacktestRunUpdate,
    db: Session = Depends(get_session),
) -> BacktestRun:
    run = _require_run(db, backtest_id)
    run.name = payload.name
    db.commit()
    db.refresh(run)
    return run


@router.delete("/{backtest_id}", status_code=204)
def delete_backtest(
    backtest_id: int, db: Session = Depends(get_session)
) -> None:
    """Delete a run and all its children.

    Routed through `app.services.run_deletion.delete_run` so the live-
    trades ingester (which replaces a prior live run for the same JSONL)
    can share the exact cleanup logic. See that module for the full set
    of cross-table references that get NULL'd or cascade-deleted before
    the row is removed.
    """
    run = _require_run(db, backtest_id)
    _delete_run_with_cleanup(db, run)
    db.commit()
    return None


@router.put("/{backtest_id}/tags", response_model=BacktestRunRead)
def set_backtest_tags(
    backtest_id: int,
    payload: BacktestRunTagsUpdate,
    db: Session = Depends(get_session),
) -> BacktestRun:
    """Replace the full tag list on a run. Empty list clears all tags."""
    run = _require_run(db, backtest_id)
    run.tags = payload.tags or None
    db.commit()
    db.refresh(run)
    return run
