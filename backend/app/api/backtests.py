"""Backtest run endpoints: read + light mutations (rename) + engine kickoff."""

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backtest.engine import RunConfig, run as engine_run
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


@router.post("/run", response_model=BacktestRunRead, status_code=201)
def run_engine_backtest(
    payload: BacktestRunRequest, db: Session = Depends(get_session)
) -> BacktestRun:
    """Kick off a synchronous engine backtest. Loads bars, runs the strategy,
    writes outputs to disk, persists the BacktestRun row, returns it."""
    version = db.get(StrategyVersion, payload.strategy_version_id)
    if version is None:
        raise HTTPException(
            status_code=404,
            detail=f"strategy version {payload.strategy_version_id} not found",
        )

    # Instrument-aware defaults — pull tick_size, contract_value, and
    # commission from the per-instrument table keyed by the symbol's
    # alpha prefix. Falls back to the RunConfig dataclass defaults
    # (NQ values) when the prefix is unknown.
    spec = lookup_instrument(payload.symbol)
    instrument_kwargs: dict = {}
    if spec is not None:
        instrument_kwargs = {
            "tick_size": spec.tick_size,
            "contract_value": spec.contract_value,
            "commission_per_contract": spec.commission_per_contract,
        }

    # Composable strategies: if the run params are empty (or missing the
    # entry lists), fall back to the version's saved spec_json. Lets the
    # /build visual builder save the recipe once and the /backtest tab
    # use it without re-pasting the spec on every run. Per-run overrides
    # still win when the caller passes an explicit params dict.
    run_params = dict(payload.params or {})
    if (
        payload.strategy_name == "composable"
        and not run_params.get("entry_long")
        and not run_params.get("entry_short")
    ):
        if version.spec_json:
            run_params = {**version.spec_json, **run_params}

    # Aux symbols: if the run didn't supply any, inherit from the saved
    # spec_json. Per-run aux_symbols still wins (lets you do ablation
    # testing — strip ES from a strategy that nominally needs it). The
    # spec lists what the strategy was DESIGNED to read; the run config
    # is what it ACTUALLY reads on this invocation.
    effective_aux_symbols = list(payload.aux_symbols)
    if (
        not effective_aux_symbols
        and payload.strategy_name == "composable"
        and version.spec_json
    ):
        spec_aux = version.spec_json.get("aux_symbols")
        if isinstance(spec_aux, list):
            effective_aux_symbols = [s for s in spec_aux if isinstance(s, str)]

    config = RunConfig(
        strategy_name=payload.strategy_name,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        start=payload.start,
        end=payload.end,
        initial_equity=payload.initial_equity,
        qty=payload.qty,
        aux_symbols=effective_aux_symbols,
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

    started_at = dt.datetime.now(dt.timezone.utc)
    result = engine_run(strategy, bars, config, aux_bars=aux_bars)
    completed_at = dt.datetime.now(dt.timezone.utc)

    out_dir, _ = make_run_dir(_data_root(), config.strategy_name, started_at)
    write_run(out_dir, result, started_at, completed_at, _git_sha())

    run_id = persist_run_to_session(
        db, config, result, out_dir, payload.strategy_version_id
    )
    db.commit()
    return _require_run(db, run_id)


@router.get("", response_model=list[BacktestRunRead])
def list_backtests(db: Session = Depends(get_session)) -> list[BacktestRun]:
    statement = select(BacktestRun).order_by(
        BacktestRun.created_at.desc(), BacktestRun.id.desc()
    )
    return list(db.scalars(statement).all())


@router.get("/{backtest_id}", response_model=BacktestRunRead)
def get_backtest(backtest_id: int, db: Session = Depends(get_session)) -> BacktestRun:
    return _require_run(db, backtest_id)


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
