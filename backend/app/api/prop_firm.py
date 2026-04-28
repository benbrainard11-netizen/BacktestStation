"""Prop-firm simulator endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    BacktestRun,
    PropFirmSimulation,
    Strategy,
    StrategyVersion,
    Trade,
)
from app.db.session import get_session
from app.schemas import PropFirmConfigIn, PropFirmPresetRead, PropFirmResultRead
from app.schemas.prop_simulator import (
    SimulationRunDetail,
    SimulationRunListRow,
    SimulationRunRequest,
)
from app.services import prop_firm
from app.services.monte_carlo import run_monte_carlo

router = APIRouter(prefix="/prop-firm", tags=["prop-firm"])


@router.get("/presets", response_model=list[PropFirmPresetRead])
def list_presets() -> list[dict]:
    return [preset.as_dict() for preset in prop_firm.PRESETS.values()]


# --- Monte Carlo simulator: list / detail / create ---------------------


@router.get("/simulations", response_model=list[SimulationRunListRow])
def list_simulations(
    db: Session = Depends(get_session),
) -> list[dict]:
    rows = db.scalars(
        select(PropFirmSimulation).order_by(
            PropFirmSimulation.created_at.desc(), PropFirmSimulation.id.desc()
        )
    ).all()
    return [
        {
            "simulation_id": str(r.id),
            "name": r.name,
            "strategy_name": r.strategy_name,
            "backtests_used": len(
                (r.config_json or {}).get("selected_backtest_ids", [])
            ),
            "firm_name": r.firm_name,
            "account_size": r.account_size,
            "sampling_mode": r.sampling_mode,
            "simulation_count": r.simulation_count,
            "risk_label": r.risk_label,
            "pass_rate": r.summary_pass_rate,
            "fail_rate": r.summary_fail_rate,
            "payout_rate": r.summary_payout_rate,
            "ev_after_fees": r.summary_ev_after_fees,
            "confidence": r.summary_confidence,
            "created_at": r.created_at.isoformat(timespec="seconds")
            if r.created_at
            else "",
        }
        for r in rows
    ]


@router.get("/simulations/{sim_id}", response_model=SimulationRunDetail)
def get_simulation(
    sim_id: int, db: Session = Depends(get_session)
) -> dict:
    row = db.get(PropFirmSimulation, sim_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    config = dict(row.config_json or {})
    # `simulation_id` in the config_json is a uuid; replace with the int
    # primary key the frontend uses for routing.
    config["simulation_id"] = str(row.id)
    return {
        "config": config,
        "firm": row.firm_profile_json,
        "pool_backtests": row.pool_backtests_json,
        "aggregated": row.aggregated_json,
        "risk_sweep": row.risk_sweep_json,
        "selected_paths": row.selected_paths_json,
        "fan_bands": row.fan_bands_json,
        "rule_violation_counts": row.rule_violation_counts_json,
        "confidence": row.confidence_json,
        "daily_pnl": row.daily_pnl_json,
    }


@router.post(
    "/simulations", response_model=SimulationRunDetail, status_code=201
)
def create_simulation(
    payload: SimulationRunRequest, db: Session = Depends(get_session)
) -> dict:
    """Run a Monte Carlo prop-firm simulation against one or more backtests."""
    # 1. Resolve backtest pool + strategy info.
    runs = list(
        db.scalars(
            select(BacktestRun).where(
                BacktestRun.id.in_(payload.selected_backtest_ids)
            )
        ).all()
    )
    if not runs:
        raise HTTPException(
            status_code=404,
            detail=(
                "No matching BacktestRuns for selected_backtest_ids "
                f"{payload.selected_backtest_ids}"
            ),
        )
    found_ids = {r.id for r in runs}
    missing = [i for i in payload.selected_backtest_ids if i not in found_ids]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"BacktestRuns not found: {missing}",
        )

    # 2. Load all trades from those runs.
    trades = list(
        db.scalars(
            select(Trade)
            .where(Trade.backtest_run_id.in_(payload.selected_backtest_ids))
            .order_by(Trade.entry_ts.asc(), Trade.id.asc())
        )
    )
    if not trades:
        raise HTTPException(
            status_code=422,
            detail="Selected backtests have no trades to bootstrap from.",
        )

    # 3. Resolve firm profile from preset key (v1: presets only;
    # custom-rule UI is a follow-up).
    preset = prop_firm.PRESETS.get(payload.firm_profile_id)
    if preset is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Firm profile {payload.firm_profile_id!r} not found. "
                f"Available: {list(prop_firm.PRESETS.keys())}"
            ),
        )
    firm_profile = _preset_to_firm_rule_profile(preset, payload)

    # 4. Resolve strategy name (use the first run's strategy).
    first_run = runs[0]
    version = db.get(StrategyVersion, first_run.strategy_version_id)
    strategy = (
        db.get(Strategy, version.strategy_id) if version is not None else None
    )
    strategy_name = strategy.name if strategy else "Unknown strategy"

    # 5. Build pool_backtests + daily_pnl side data.
    pool_backtests = [
        _pool_backtest_summary(r, version, strategy, len(trades), trades)
        for r in runs
    ]
    daily_pnl = _build_daily_pnl(trades, payload.risk_per_trade or 200.0)

    # 6. Run the Monte Carlo.
    result = run_monte_carlo(
        trades=trades,
        request=payload.model_dump(),
        firm_profile=firm_profile,
        strategy_name=strategy_name,
        pool_backtests=pool_backtests,
        daily_pnl=daily_pnl,
    )

    # 7. Persist.
    risk_label = _format_risk_label(payload)
    sim = PropFirmSimulation(
        name=payload.name,
        source_backtest_run_id=first_run.id,
        firm_profile_id=payload.firm_profile_id,
        config_json=result["config"],
        firm_profile_json=result["firm"],
        aggregated_json=result["aggregated"],
        selected_paths_json=result["selected_paths"],
        fan_bands_json=result["fan_bands"],
        confidence_json=result["confidence"],
        rule_violation_counts_json=result["rule_violation_counts"],
        daily_pnl_json=result["daily_pnl"],
        risk_sweep_json=result["risk_sweep"],
        pool_backtests_json=result["pool_backtests"],
        summary_pass_rate=result["_summary"]["pass_rate"],
        summary_fail_rate=result["_summary"]["fail_rate"],
        summary_payout_rate=result["_summary"]["payout_rate"],
        summary_ev_after_fees=result["_summary"]["ev_after_fees"],
        summary_confidence=result["_summary"]["confidence"],
        sampling_mode=payload.sampling_mode,
        simulation_count=payload.simulation_count,
        risk_label=risk_label,
        strategy_name=strategy_name,
        firm_name=firm_profile["firm_name"],
        account_size=payload.account_size,
    )
    db.add(sim)
    db.flush()
    db.commit()

    # Re-issue config with the int simulation_id for the frontend.
    out = {
        "config": {**result["config"], "simulation_id": str(sim.id)},
        "firm": result["firm"],
        "pool_backtests": result["pool_backtests"],
        "aggregated": result["aggregated"],
        "risk_sweep": result["risk_sweep"],
        "selected_paths": result["selected_paths"],
        "fan_bands": result["fan_bands"],
        "rule_violation_counts": result["rule_violation_counts"],
        "confidence": result["confidence"],
        "daily_pnl": result["daily_pnl"],
    }
    return out


def _format_risk_label(payload: SimulationRunRequest) -> str:
    if payload.risk_mode == "fixed_dollar" and payload.risk_per_trade is not None:
        return f"${int(payload.risk_per_trade)}"
    if payload.risk_mode == "fixed_contracts":
        return "fixed contracts"
    if payload.risk_mode == "percent_balance":
        return "% balance"
    if payload.risk_mode == "risk_sweep":
        return "sweep"
    return ""


def _preset_to_firm_rule_profile(
    preset, payload: SimulationRunRequest
) -> dict:
    """Convert a PropFirmPreset to the FirmRuleProfile shape the
    frontend expects. Reads display metadata (fees, payout, min days,
    trailing type) directly from the preset rather than hardcoding
    defaults — falls back to safe defaults only when the preset omits
    a field."""
    # Firm name = everything before the first space-separated number/size
    # in the preset name. Falls back to the full name if no split point.
    firm_name = preset.name.split(" ")[0] or preset.name
    # Heuristic: "intraday" trailing if preset trailing is on but type
    # field is "none" (legacy presets that don't set the new field).
    trailing_type = preset.trailing_drawdown_type
    if preset.trailing_drawdown and trailing_type == "none":
        trailing_type = "intraday"
    return {
        "profile_id": preset.key,
        "firm_name": firm_name,
        "account_name": preset.name,
        "account_size": preset.starting_balance,
        "phase_type": "evaluation",
        "profit_target": preset.profit_target,
        "max_drawdown": preset.max_drawdown,
        "daily_loss_limit": preset.daily_loss_limit,
        "trailing_drawdown_enabled": preset.trailing_drawdown,
        "trailing_drawdown_type": trailing_type,
        "trailing_drawdown_stop_level": None,
        "minimum_trading_days": preset.minimum_trading_days,
        "maximum_trading_days": None,
        "max_contracts": preset.max_trades_per_day,
        "scaling_plan_enabled": False,
        "scaling_plan_rules": [],
        "consistency_rule_enabled": preset.consistency_pct is not None,
        "consistency_rule_type": (
            "best_day_pct_of_total"
            if preset.consistency_pct is not None
            else "none"
        ),
        "consistency_rule_value": preset.consistency_pct,
        "news_trading_allowed": True,
        "overnight_holding_allowed": False,
        "weekend_holding_allowed": False,
        "copy_trading_allowed": True,
        "payout_min_days": preset.payout_min_days,
        "payout_min_profit": preset.payout_min_profit,
        "payout_cap": None,
        "payout_split": preset.payout_split,
        "first_payout_rules": None,
        "recurring_payout_rules": None,
        "eval_fee": preset.eval_fee,
        "activation_fee": preset.activation_fee,
        "reset_fee": preset.reset_fee,
        "monthly_fee": preset.monthly_fee,
        "refund_rules": None,
        "rule_source_url": preset.source_url,
        "rule_last_verified_at": preset.last_known_at,
        # All seeded presets are honest approximations — flag accordingly so
        # the firm-rule status badge in the UI never shows "Verified".
        "verification_status": "unverified",
        "notes": preset.notes,
        "version": 1,
        "active": True,
    }


def _pool_backtest_summary(
    run: BacktestRun,
    version: StrategyVersion | None,
    strategy: Strategy | None,
    total_trade_count: int,
    trades: list[Trade],
) -> dict:
    """Summary for the pool_backtests panel on the run-detail page."""
    run_trades = [t for t in trades if t.backtest_run_id == run.id]
    days = {t.entry_ts.date() for t in run_trades if t.entry_ts}
    return {
        "backtest_id": run.id,
        "strategy_id": strategy.id if strategy else 0,
        "strategy_name": strategy.name if strategy else "Unknown",
        "strategy_version": version.version if version else "",
        "symbol": run.symbol,
        "market": "futures",
        "timeframe": run.timeframe or "",
        "start_date": (
            run.start_ts.date().isoformat() if run.start_ts else ""
        ),
        "end_date": run.end_ts.date().isoformat() if run.end_ts else "",
        "data_source": run.import_source or run.source or "",
        "commission_model": "default",
        "slippage_model": "default",
        "initial_balance": 25_000.0,
        "confidence_score": 50.0,
        "trade_count": len(run_trades),
        "day_count": len(days),
    }


def _build_daily_pnl(trades: list[Trade], risk_per_trade: float) -> list[dict]:
    """Daily P&L for the calendar heatmap on the dashboard / detail page."""
    by_day: dict = {}
    for t in trades:
        if t.entry_ts is None or t.r_multiple is None:
            continue
        day = t.entry_ts.date().isoformat()
        by_day.setdefault(day, {"date": day, "pnl": 0.0, "trades": 0})
        by_day[day]["pnl"] += t.r_multiple * risk_per_trade
        by_day[day]["trades"] += 1
    return [by_day[k] for k in sorted(by_day.keys())]


# --- Backwards-compat single-path endpoint -----------------------------


backtest_router = APIRouter(prefix="/backtests", tags=["prop-firm"])


@backtest_router.post(
    "/{backtest_id}/prop-firm-sim", response_model=PropFirmResultRead
)
def simulate_prop_firm(
    backtest_id: int,
    config: PropFirmConfigIn,
    db: Session = Depends(get_session),
) -> dict:
    run = db.get(BacktestRun, backtest_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    trades = list(
        db.scalars(select(Trade).where(Trade.backtest_run_id == backtest_id))
    )
    sim_config = prop_firm.PropFirmConfig(
        starting_balance=config.starting_balance,
        profit_target=config.profit_target,
        max_drawdown=config.max_drawdown,
        trailing_drawdown=config.trailing_drawdown,
        daily_loss_limit=config.daily_loss_limit,
        consistency_pct=config.consistency_pct,
        max_trades_per_day=config.max_trades_per_day,
        risk_per_trade_dollars=config.risk_per_trade_dollars,
    )
    result = prop_firm.simulate(trades, sim_config)
    return result.as_dict()
