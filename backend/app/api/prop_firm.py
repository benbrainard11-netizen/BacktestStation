"""Prop-firm simulator endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    BacktestRun,
    FirmRuleProfile,
    PropFirmSimulation,
    Strategy,
    StrategyVersion,
    Trade,
)
from app.db.session import get_session
from app.schemas import (
    FirmRuleProfileCreate,
    FirmRuleProfilePatch,
    FirmRuleProfileRead,
    PropFirmConfigIn,
    PropFirmPresetRead,
    PropFirmResultRead,
)
from app.schemas.prop_simulator import (
    SimulationRunDetail,
    SimulationRunListRow,
    SimulationRunRequest,
)
from app.services import prop_firm
from app.services.monte_carlo import run_monte_carlo

router = APIRouter(prefix="/prop-firm", tags=["prop-firm"])


# Fields that, when changed, invalidate verification (force back to
# "unverified" + clear verified_at). Editing notes / source_url /
# verified_by alone keeps a verified profile verified.
_RULE_FIELDS_THAT_INVALIDATE_VERIFICATION = frozenset(
    {
        "firm_name",
        "account_name",
        "account_size",
        "phase_type",
        "profit_target",
        "max_drawdown",
        "daily_loss_limit",
        "trailing_drawdown_enabled",
        "trailing_drawdown_type",
        "consistency_pct",
        "consistency_rule_type",
        "max_trades_per_day",
        "minimum_trading_days",
        "risk_per_trade_dollars",
        "payout_split",
        "payout_min_days",
        "payout_min_profit",
        "eval_fee",
        "activation_fee",
        "reset_fee",
        "monthly_fee",
        "last_known_at",
    }
)


# --- Editable firm rule profiles --------------------------------------


@router.get("/profiles", response_model=list[FirmRuleProfileRead])
def list_firm_profiles(
    include_archived: bool = False,
    db: Session = Depends(get_session),
) -> list[FirmRuleProfile]:
    """List firm rule profiles. Active by default; pass
    `?include_archived=true` to include soft-deleted ones too."""
    stmt = select(FirmRuleProfile)
    if not include_archived:
        stmt = stmt.where(FirmRuleProfile.is_archived.is_(False))
    stmt = stmt.order_by(FirmRuleProfile.firm_name.asc(), FirmRuleProfile.id.asc())
    return list(db.scalars(stmt).all())


@router.get("/profiles/{profile_id}", response_model=FirmRuleProfileRead)
def get_firm_profile(
    profile_id: str, db: Session = Depends(get_session)
) -> FirmRuleProfile:
    profile = _resolve_profile(db, profile_id)
    return profile


@router.post(
    "/profiles", response_model=FirmRuleProfileRead, status_code=201
)
def create_firm_profile(
    payload: FirmRuleProfileCreate, db: Session = Depends(get_session)
) -> FirmRuleProfile:
    """Create a custom firm profile. `is_seed=False` so it's never
    overwritten by the seed-on-empty pass and isn't eligible for
    `/reset`."""
    existing = db.scalars(
        select(FirmRuleProfile).where(
            FirmRuleProfile.profile_id == payload.profile_id
        )
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Profile {payload.profile_id!r} already exists.",
        )
    profile = FirmRuleProfile(
        is_seed=False,
        is_archived=False,
        verification_status="unverified",
        **payload.model_dump(),
    )
    db.add(profile)
    db.flush()
    db.commit()
    db.refresh(profile)
    return profile


@router.patch("/profiles/{profile_id}", response_model=FirmRuleProfileRead)
def patch_firm_profile(
    profile_id: str,
    payload: FirmRuleProfilePatch,
    db: Session = Depends(get_session),
) -> FirmRuleProfile:
    """Partial update. Pydantic v2's `exclude_unset=True` distinguishes
    "field omitted" from "field set to null", which matters for
    nullable rule fields like `daily_loss_limit`."""
    profile = _resolve_profile(db, profile_id)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return profile

    explicit_status_change = "verification_status" in updates
    rule_changed = bool(
        set(updates.keys()) & _RULE_FIELDS_THAT_INVALIDATE_VERIFICATION
    )

    for key, value in updates.items():
        setattr(profile, key, value)

    now = datetime.now(timezone.utc)
    if explicit_status_change:
        if profile.verification_status == "verified":
            profile.verified_at = now
        else:
            profile.verified_at = None
            profile.verified_by = None
    elif rule_changed and profile.verification_status == "verified":
        # Editing a rule field on a verified profile invalidates the
        # verification stamp — the user has to re-verify the new values.
        profile.verification_status = "unverified"
        profile.verified_at = None
        profile.verified_by = None

    db.flush()
    db.commit()
    db.refresh(profile)
    return profile


@router.post(
    "/profiles/{profile_id}/reset", response_model=FirmRuleProfileRead
)
def reset_firm_profile(
    profile_id: str, db: Session = Depends(get_session)
) -> FirmRuleProfile:
    """Restore a seed profile to its `app.services.prop_firm.PRESETS`
    factory values. Returns 404 if the profile isn't a seed (user-
    created profiles have no factory to revert to)."""
    profile = _resolve_profile(db, profile_id)
    if not profile.is_seed:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Profile {profile_id!r} is user-created — no seed values "
                "to restore. Edit fields directly or delete the profile."
            ),
        )
    seed = prop_firm.PRESETS.get(profile_id)
    if seed is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Profile {profile_id!r} is marked is_seed=True but no "
                "PRESETS entry exists. The seed key may have been removed."
            ),
        )
    _apply_seed_to_profile(profile, seed)
    db.flush()
    db.commit()
    db.refresh(profile)
    return profile


@router.post(
    "/profiles/{profile_id}/archive", response_model=FirmRuleProfileRead
)
def archive_firm_profile(
    profile_id: str, db: Session = Depends(get_session)
) -> FirmRuleProfile:
    profile = _resolve_profile(db, profile_id)
    profile.is_archived = True
    db.commit()
    db.refresh(profile)
    return profile


@router.post(
    "/profiles/{profile_id}/unarchive", response_model=FirmRuleProfileRead
)
def unarchive_firm_profile(
    profile_id: str, db: Session = Depends(get_session)
) -> FirmRuleProfile:
    profile = _resolve_profile(db, profile_id)
    profile.is_archived = False
    db.commit()
    db.refresh(profile)
    return profile


def _resolve_profile(db: Session, profile_id: str) -> FirmRuleProfile:
    profile = db.scalars(
        select(FirmRuleProfile).where(FirmRuleProfile.profile_id == profile_id)
    ).first()
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Firm profile {profile_id!r} not found.",
        )
    return profile


def _apply_seed_to_profile(
    profile: FirmRuleProfile, seed: "prop_firm.PropFirmPreset"
) -> None:
    """Overwrite every editable field on `profile` with the values from
    `seed`. Preserves identity (id, profile_id, created_at, is_seed)."""
    firm_name = seed.name.split(" ")[0] or seed.name
    trailing_type = seed.trailing_drawdown_type
    if seed.trailing_drawdown and trailing_type == "none":
        trailing_type = "intraday"
    profile.firm_name = firm_name
    profile.account_name = seed.name
    profile.account_size = seed.starting_balance
    profile.phase_type = "evaluation"
    profile.profit_target = seed.profit_target
    profile.max_drawdown = seed.max_drawdown
    profile.daily_loss_limit = seed.daily_loss_limit
    profile.trailing_drawdown_enabled = seed.trailing_drawdown
    profile.trailing_drawdown_type = trailing_type
    profile.consistency_pct = seed.consistency_pct
    profile.consistency_rule_type = (
        "best_day_pct_of_total"
        if seed.consistency_pct is not None
        else "none"
    )
    profile.max_trades_per_day = seed.max_trades_per_day
    profile.minimum_trading_days = seed.minimum_trading_days
    profile.risk_per_trade_dollars = seed.risk_per_trade_dollars
    profile.payout_split = seed.payout_split
    profile.payout_min_days = seed.payout_min_days
    profile.payout_min_profit = seed.payout_min_profit
    profile.eval_fee = seed.eval_fee
    profile.activation_fee = seed.activation_fee
    profile.reset_fee = seed.reset_fee
    profile.monthly_fee = seed.monthly_fee
    profile.source_url = seed.source_url
    profile.last_known_at = seed.last_known_at
    profile.notes = seed.notes
    profile.verification_status = "unverified"
    profile.verified_at = None
    profile.verified_by = None
    profile.is_archived = False


# --- Backwards-compat presets endpoint ---------------------------------


@router.get("/presets", response_model=list[PropFirmPresetRead])
def list_presets(db: Session = Depends(get_session)) -> list[dict]:
    """Legacy shape for the deterministic single-path checker embedded
    on /backtests/[id]. Reads from the DB now (so user edits flow
    through), maps each row to the lean PropFirmPreset shape."""
    rows = db.scalars(
        select(FirmRuleProfile).where(FirmRuleProfile.is_archived.is_(False))
        .order_by(FirmRuleProfile.firm_name.asc(), FirmRuleProfile.id.asc())
    ).all()
    return [
        {
            "key": row.profile_id,
            "name": row.account_name,
            "notes": row.notes or "",
            "starting_balance": row.account_size,
            "profit_target": row.profit_target,
            "max_drawdown": row.max_drawdown,
            "trailing_drawdown": row.trailing_drawdown_enabled,
            "daily_loss_limit": row.daily_loss_limit,
            "consistency_pct": row.consistency_pct,
            "max_trades_per_day": row.max_trades_per_day,
            "risk_per_trade_dollars": row.risk_per_trade_dollars,
            "trailing_drawdown_type": row.trailing_drawdown_type,
            "minimum_trading_days": row.minimum_trading_days,
            "payout_split": row.payout_split,
            "payout_min_days": row.payout_min_days,
            "payout_min_profit": row.payout_min_profit,
            "eval_fee": row.eval_fee,
            "activation_fee": row.activation_fee,
            "reset_fee": row.reset_fee,
            "monthly_fee": row.monthly_fee,
            "source_url": row.source_url,
            "last_known_at": row.last_known_at,
        }
        for row in rows
    ]


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

    # 3. Resolve firm profile from the editable DB table (the user can
    # edit any field on the /prop-simulator/firms page; those edits flow
    # through here on the next simulation). Falls back to the static
    # PRESETS dict only when a profile_id matches a seed key but the
    # row hasn't been created yet (rare — seed-on-empty handles new DBs).
    profile_row = db.scalars(
        select(FirmRuleProfile).where(
            FirmRuleProfile.profile_id == payload.firm_profile_id,
            FirmRuleProfile.is_archived.is_(False),
        )
    ).first()
    if profile_row is not None:
        firm_profile = _row_to_firm_rule_profile(profile_row)
    else:
        legacy_preset = prop_firm.PRESETS.get(payload.firm_profile_id)
        if legacy_preset is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Firm profile {payload.firm_profile_id!r} not found. "
                    "Edit available profiles at /prop-simulator/firms."
                ),
            )
        firm_profile = _preset_to_firm_rule_profile(legacy_preset, payload)

    # 4. Resolve per-run strategy + version metadata. Codex review
    # 2026-04-29 finding #8: previously only the FIRST run's metadata
    # was looked up and copy-pasted across every pool_backtests row,
    # silently mis-labelling runs from different strategies/versions/
    # symbols when the user picked a multi-strategy pool.
    version_ids = {r.strategy_version_id for r in runs}
    versions_by_id: dict[int, StrategyVersion] = {
        v.id: v
        for v in db.scalars(
            select(StrategyVersion).where(StrategyVersion.id.in_(version_ids))
        )
    }
    strategy_ids = {v.strategy_id for v in versions_by_id.values()}
    strategies_by_id: dict[int, Strategy] = {
        s.id: s
        for s in db.scalars(
            select(Strategy).where(Strategy.id.in_(strategy_ids))
        )
    }

    def _meta_for(run: BacktestRun) -> tuple[StrategyVersion | None, Strategy | None]:
        version = versions_by_id.get(run.strategy_version_id)
        strategy = (
            strategies_by_id.get(version.strategy_id)
            if version is not None
            else None
        )
        return version, strategy

    # Top-level strategy_name: single name when the pool is
    # homogeneous, "Mixed pool (N strategies)" otherwise. The Monte
    # Carlo result row shows this; using "Mixed" instead of misleading
    # the user with the first run's name is the honest choice.
    unique_strategy_names = sorted(
        {s.name for _, s in (_meta_for(r) for r in runs) if s is not None}
    )
    if len(unique_strategy_names) == 1:
        strategy_name = unique_strategy_names[0]
    elif len(unique_strategy_names) == 0:
        strategy_name = "Unknown strategy"
    else:
        strategy_name = f"Mixed pool ({len(unique_strategy_names)} strategies)"

    # 5. Build pool_backtests + daily_pnl side data. Each row carries
    # its OWN run's strategy/version metadata.
    pool_backtests = []
    for r in runs:
        v, s = _meta_for(r)
        pool_backtests.append(
            _pool_backtest_summary(r, v, s, len(trades), trades)
        )
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

    # 7. Persist. The denormalized `source_backtest_run_id` is the
    # primary anchor for the per-run detail page; for multi-run pools
    # we use the first run as the anchor (the others appear in the
    # pool_backtests JSON column with their own metadata).
    risk_label = _format_risk_label(payload)
    sim = PropFirmSimulation(
        name=payload.name,
        source_backtest_run_id=runs[0].id,
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


def _row_to_firm_rule_profile(row: FirmRuleProfile) -> dict:
    """Convert a FirmRuleProfile row to the FirmRuleProfile dict shape
    the simulator + frontend expect. Mirrors `_preset_to_firm_rule_profile`
    field-for-field but reads from the editable DB row."""
    return {
        "profile_id": row.profile_id,
        "firm_name": row.firm_name,
        "account_name": row.account_name,
        "account_size": row.account_size,
        "phase_type": row.phase_type,
        "profit_target": row.profit_target,
        "max_drawdown": row.max_drawdown,
        "daily_loss_limit": row.daily_loss_limit,
        "trailing_drawdown_enabled": row.trailing_drawdown_enabled,
        "trailing_drawdown_type": row.trailing_drawdown_type,
        "trailing_drawdown_stop_level": None,
        "minimum_trading_days": row.minimum_trading_days,
        "maximum_trading_days": None,
        "max_contracts": row.max_trades_per_day,
        "scaling_plan_enabled": False,
        "scaling_plan_rules": [],
        "consistency_rule_enabled": row.consistency_pct is not None,
        "consistency_rule_type": row.consistency_rule_type,
        "consistency_rule_value": row.consistency_pct,
        "news_trading_allowed": True,
        "overnight_holding_allowed": False,
        "weekend_holding_allowed": False,
        "copy_trading_allowed": True,
        "payout_min_days": row.payout_min_days,
        "payout_min_profit": row.payout_min_profit,
        "payout_cap": None,
        "payout_split": row.payout_split,
        "first_payout_rules": None,
        "recurring_payout_rules": None,
        "eval_fee": row.eval_fee,
        "activation_fee": row.activation_fee,
        "reset_fee": row.reset_fee,
        "monthly_fee": row.monthly_fee,
        "refund_rules": None,
        "rule_source_url": row.source_url,
        "rule_last_verified_at": (
            row.verified_at.isoformat() if row.verified_at else row.last_known_at
        ),
        "verification_status": row.verification_status,
        "notes": row.notes or "",
        "version": 1,
        "active": not row.is_archived,
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
