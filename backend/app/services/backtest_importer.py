"""Persist normalized imported backtest results."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.services.import_parsing import (
    first_text,
    load_optional_json,
    normalize_metrics,
    parse_equity_points,
    parse_trades,
    slugify,
)
from app.services.import_types import (
    BacktestImportPayload,
    ImportResult,
    ImportValidationError,
)


def import_backtest_payload(db: Session, payload: BacktestImportPayload) -> ImportResult:
    config_payload = load_optional_json(payload.config_file)
    metrics_payload = load_optional_json(payload.metrics_file)
    config = config_payload if isinstance(config_payload, dict) else {}

    trades = parse_trades(payload.trades_file)
    equity_points = parse_equity_points(payload.equity_file)
    if not trades:
        raise ImportValidationError("trades.csv did not contain any trades")
    if not equity_points:
        raise ImportValidationError("equity.csv did not contain any equity points")

    strategy_name = _resolve_strategy_name(payload, config)
    strategy_slug = first_text(payload.strategy_slug, config.get("strategy_slug"))
    strategy_slug = strategy_slug or slugify(strategy_name)
    version_name = first_text(payload.version, config.get("version"), default="imported")
    if version_name is None:
        raise ImportValidationError("Strategy version could not be resolved")

    strategy = _get_or_create_strategy(db, strategy_name, strategy_slug)
    strategy_version = _get_or_create_strategy_version(db, strategy, version_name)
    run = _build_run(payload, config, strategy_version, trades, equity_points)

    run.trades.extend(models.Trade(**trade) for trade in trades)
    run.equity_points.extend(models.EquityPoint(**point) for point in equity_points)

    metrics = normalize_metrics(metrics_payload)
    if metrics is not None:
        run.metrics = models.RunMetrics(**metrics)
    if config_payload is not None:
        run.config_snapshot = models.ConfigSnapshot(payload=config_payload)

    db.add(run)
    db.commit()
    db.refresh(run)

    return ImportResult(
        backtest_id=run.id,
        strategy_id=strategy.id,
        strategy_version_id=strategy_version.id,
        trades_imported=len(trades),
        equity_points_imported=len(equity_points),
        metrics_imported=metrics is not None,
        config_imported=config_payload is not None,
    )


def _resolve_strategy_name(
    payload: BacktestImportPayload, config: dict[str, Any]
) -> str:
    strategy_name = first_text(
        payload.strategy_name,
        config.get("strategy_name"),
        config.get("name"),
        default="Imported Strategy",
    )
    if strategy_name is None:
        raise ImportValidationError("Strategy name could not be resolved")
    return strategy_name


def _get_or_create_strategy(
    db: Session, strategy_name: str, strategy_slug: str
) -> models.Strategy:
    strategy = db.scalars(
        select(models.Strategy).where(models.Strategy.slug == strategy_slug)
    ).first()
    if strategy is not None:
        return strategy
    strategy = models.Strategy(name=strategy_name, slug=strategy_slug, status="testing")
    db.add(strategy)
    db.flush()
    return strategy


def _get_or_create_strategy_version(
    db: Session, strategy: models.Strategy, version_name: str
) -> models.StrategyVersion:
    version = db.scalars(
        select(models.StrategyVersion).where(
            models.StrategyVersion.strategy_id == strategy.id,
            models.StrategyVersion.version == version_name,
        )
    ).first()
    if version is not None:
        return version
    version = models.StrategyVersion(strategy=strategy, version=version_name)
    db.add(version)
    db.flush()
    return version


def _build_run(
    payload: BacktestImportPayload,
    config: dict[str, Any],
    strategy_version: models.StrategyVersion,
    trades: list[dict[str, Any]],
    equity_points: list[dict[str, Any]],
) -> models.BacktestRun:
    return models.BacktestRun(
        strategy_version=strategy_version,
        name=first_text(payload.run_name, config.get("run_name")),
        symbol=_infer_symbol(payload, config, trades),
        timeframe=first_text(payload.timeframe, config.get("timeframe")),
        session_label=first_text(
            payload.session_label,
            config.get("session_label"),
            config.get("session"),
        ),
        start_ts=_infer_start_ts(trades, equity_points),
        end_ts=_infer_end_ts(trades, equity_points),
        import_source=_build_import_source(payload),
        status="imported",
    )


def _infer_symbol(
    payload: BacktestImportPayload,
    config: dict[str, Any],
    trades: list[dict[str, Any]],
) -> str:
    symbol = first_text(payload.symbol, config.get("symbol"))
    if symbol:
        return symbol.upper()
    return str(trades[0]["symbol"]).upper()


def _infer_start_ts(
    trades: list[dict[str, Any]], equity_points: list[dict[str, Any]]
) -> datetime:
    timestamps = [trade["entry_ts"] for trade in trades]
    timestamps.extend(point["ts"] for point in equity_points)
    return min(timestamps)


def _infer_end_ts(
    trades: list[dict[str, Any]], equity_points: list[dict[str, Any]]
) -> datetime:
    timestamps = [trade.get("exit_ts") or trade["entry_ts"] for trade in trades]
    timestamps.extend(point["ts"] for point in equity_points)
    return max(timestamps)


def _build_import_source(payload: BacktestImportPayload) -> str:
    if payload.import_source:
        return payload.import_source
    filenames = [payload.trades_file.filename, payload.equity_file.filename]
    if payload.metrics_file is not None:
        filenames.append(payload.metrics_file.filename)
    if payload.config_file is not None:
        filenames.append(payload.config_file.filename)
    return ", ".join(filenames)
