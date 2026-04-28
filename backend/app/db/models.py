"""ORM models for the Phase 1 metadata DB.

These tables back the "Imported Results Command Center": strategies, the
runs/trades/equity/metrics imported from existing result files, run config
snapshots, live monitor signals/heartbeats, and research notes.

Phase 1 only stores imported data; the engine that produces fresh runs
comes later. See `docs/PHASE_1_SCOPE.md`.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    # idea | testing | live | retired
    status: Mapped[str] = mapped_column(String(20), default="idea")
    tags: Mapped[list[str] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    versions: Mapped[list["StrategyVersion"]] = relationship(
        back_populates="strategy", cascade="all, delete-orphan"
    )


class StrategyVersion(Base):
    __tablename__ = "strategy_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("strategies.id"), index=True
    )
    version: Mapped[str] = mapped_column(String(40))
    entry_md: Mapped[str | None] = mapped_column(Text)
    exit_md: Mapped[str | None] = mapped_column(Text)
    risk_md: Mapped[str | None] = mapped_column(Text)
    git_commit_sha: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    # The run that represents the live-trading expectation for this version.
    # Forward Drift Monitor compares live runs against this baseline. Nullable
    # because most versions never go to live trading. SET NULL on baseline-run
    # delete so the version isn't orphaned.
    baseline_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("backtest_runs.id", ondelete="SET NULL"), default=None
    )

    strategy: Mapped[Strategy] = relationship(back_populates="versions")
    # `runs` is the reverse side of BacktestRun.strategy_version_id. With
    # baseline_run_id now also linking the two tables, the join column
    # must be disambiguated explicitly.
    runs: Mapped[list["BacktestRun"]] = relationship(
        back_populates="strategy_version",
        cascade="all, delete-orphan",
        foreign_keys="BacktestRun.strategy_version_id",
    )


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_version_id: Mapped[int] = mapped_column(
        ForeignKey("strategy_versions.id"), index=True
    )
    name: Mapped[str | None] = mapped_column(String(200))
    symbol: Mapped[str] = mapped_column(String(40), index=True)
    timeframe: Mapped[str | None] = mapped_column(String(20))
    session_label: Mapped[str | None] = mapped_column(String(40))
    start_ts: Mapped[datetime | None] = mapped_column(DateTime)
    end_ts: Mapped[datetime | None] = mapped_column(DateTime)
    # File path or short tag describing where the run was imported from.
    import_source: Mapped[str | None] = mapped_column(Text)
    # "imported" — trades.csv/equity.csv/metrics.json bundle from another tool.
    # "engine"   — produced by the in-app backtest engine.
    source: Mapped[str] = mapped_column(
        String(20), default="imported", server_default="imported", index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="imported")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    strategy_version: Mapped[StrategyVersion] = relationship(
        back_populates="runs",
        foreign_keys=[strategy_version_id],
    )
    trades: Mapped[list["Trade"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    equity_points: Mapped[list["EquityPoint"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    metrics: Mapped["RunMetrics | None"] = relationship(
        back_populates="run", cascade="all, delete-orphan", uselist=False
    )
    config_snapshot: Mapped["ConfigSnapshot | None"] = relationship(
        back_populates="run", cascade="all, delete-orphan", uselist=False
    )


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    backtest_run_id: Mapped[int] = mapped_column(
        ForeignKey("backtest_runs.id"), index=True
    )
    entry_ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    exit_ts: Mapped[datetime | None] = mapped_column(DateTime)
    symbol: Mapped[str] = mapped_column(String(40))
    # "long" | "short"
    side: Mapped[str] = mapped_column(String(8))
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float | None] = mapped_column(Float)
    stop_price: Mapped[float | None] = mapped_column(Float)
    target_price: Mapped[float | None] = mapped_column(Float)
    size: Mapped[float] = mapped_column(Float)
    pnl: Mapped[float | None] = mapped_column(Float)
    r_multiple: Mapped[float | None] = mapped_column(Float)
    # stop | target | eod | manual | other
    exit_reason: Mapped[str | None] = mapped_column(String(20))
    tags: Mapped[list[str] | None] = mapped_column(JSON)

    run: Mapped[BacktestRun] = relationship(back_populates="trades")


class EquityPoint(Base):
    __tablename__ = "equity_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    backtest_run_id: Mapped[int] = mapped_column(
        ForeignKey("backtest_runs.id"), index=True
    )
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    equity: Mapped[float] = mapped_column(Float)
    drawdown: Mapped[float | None] = mapped_column(Float)

    run: Mapped[BacktestRun] = relationship(back_populates="equity_points")


class RunMetrics(Base):
    __tablename__ = "run_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    backtest_run_id: Mapped[int] = mapped_column(
        ForeignKey("backtest_runs.id"), unique=True
    )
    net_pnl: Mapped[float | None] = mapped_column(Float)
    net_r: Mapped[float | None] = mapped_column(Float)
    win_rate: Mapped[float | None] = mapped_column(Float)
    profit_factor: Mapped[float | None] = mapped_column(Float)
    max_drawdown: Mapped[float | None] = mapped_column(Float)
    avg_r: Mapped[float | None] = mapped_column(Float)
    avg_win: Mapped[float | None] = mapped_column(Float)
    avg_loss: Mapped[float | None] = mapped_column(Float)
    trade_count: Mapped[int | None] = mapped_column(Integer)
    longest_losing_streak: Mapped[int | None] = mapped_column(Integer)
    best_trade: Mapped[float | None] = mapped_column(Float)
    worst_trade: Mapped[float | None] = mapped_column(Float)

    run: Mapped[BacktestRun] = relationship(back_populates="metrics")


class ConfigSnapshot(Base):
    __tablename__ = "config_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    backtest_run_id: Mapped[int] = mapped_column(
        ForeignKey("backtest_runs.id"), unique=True
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    run: Mapped[BacktestRun] = relationship(back_populates="config_snapshot")


class LiveSignal(Base):
    __tablename__ = "live_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategy_versions.id"), index=True
    )
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    side: Mapped[str] = mapped_column(String(8))
    price: Mapped[float] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(Text)
    executed: Mapped[bool] = mapped_column(Boolean, default=False)


class LiveHeartbeat(Base):
    __tablename__ = "live_heartbeats"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    source: Mapped[str] = mapped_column(String(80))
    # running | stopped | error | unknown
    status: Mapped[str] = mapped_column(String(20))
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class Dataset(Base):
    """A market-data file BacktestStation knows about.

    The on-disk file is the source of truth. This row is a queryable
    cache: where the file is, what it contains, when it was last seen.
    Repopulated by `POST /api/datasets/scan` which walks the warehouse.

    `source` distinguishes how the data got here:
      - "live"        — written by app.ingest.live (continuous TBBO stream)
      - "historical"  — pulled by app.ingest.historical (monthly batch)
      - "imported"    — manually imported result/replay data

    `kind` distinguishes the storage format:
      - "dbn"     — Databento native, immutable raw archive
      - "parquet" — derived, queryable, can be regenerated from DBN
    """

    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_path: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    dataset_code: Mapped[str] = mapped_column(String(40), index=True)  # e.g. GLBX.MDP3
    schema: Mapped[str] = mapped_column(String(20), index=True)  # tbbo, mbp-1, ohlcv-1m, ...
    symbol: Mapped[str | None] = mapped_column(String(40), index=True)  # None for multi-symbol DBN
    source: Mapped[str] = mapped_column(String(20), index=True)  # live | historical | imported
    kind: Mapped[str] = mapped_column(String(10), index=True)  # dbn | parquet
    start_ts: Mapped[datetime | None] = mapped_column(DateTime)
    end_ts: Mapped[datetime | None] = mapped_column(DateTime)
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    row_count: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64))
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Experiment(Base):
    """A unit of structured research: hypothesis + baseline + variant + decision.

    The Experiment Ledger sits between freeform notes (which live on the
    `Note` table) and runnable backtests (`BacktestRun`). It records
    *what* you were testing, *why*, *how it shook out*, and *what you
    decided* — independent of any future in-app strategy engine.

    `change_description` is freeform markdown on purpose. Once the shape
    of "what changed between baseline and variant" stabilizes through
    real use, structured sub-fields can replace it.
    """

    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_version_id: Mapped[int] = mapped_column(
        ForeignKey("strategy_versions.id"), index=True
    )
    hypothesis: Mapped[str] = mapped_column(Text)
    baseline_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("backtest_runs.id"), index=True
    )
    variant_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("backtest_runs.id"), index=True
    )
    change_description: Mapped[str | None] = mapped_column(Text)
    # pending | promote | reject | retest | forward_test | archive
    decision: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending", index=True
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)


class PropFirmSimulation(Base):
    """One Monte Carlo prop-firm simulation run.

    `aggregated_json` and `selected_paths_json` cache the heavy
    payload (fan_bands, distributions, paths) so repeated GETs of the
    same run don't re-aggregate. `summary_*` columns are denormalized
    for fast list-page queries.
    """

    __tablename__ = "prop_firm_simulations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    source_backtest_run_id: Mapped[int] = mapped_column(
        ForeignKey("backtest_runs.id"), index=True
    )
    firm_profile_id: Mapped[str] = mapped_column(String(60), index=True)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    firm_profile_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    aggregated_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    selected_paths_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    fan_bands_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    confidence_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    rule_violation_counts_json: Mapped[dict[str, int]] = mapped_column(JSON)
    daily_pnl_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    risk_sweep_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    pool_backtests_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON)

    # Denormalized scalars for the list page (avoid hydrating JSON blobs).
    summary_pass_rate: Mapped[float] = mapped_column(Float)
    summary_fail_rate: Mapped[float] = mapped_column(Float)
    summary_payout_rate: Mapped[float] = mapped_column(Float)
    summary_ev_after_fees: Mapped[float] = mapped_column(Float)
    summary_confidence: Mapped[float] = mapped_column(Float)
    sampling_mode: Mapped[str] = mapped_column(String(40))
    simulation_count: Mapped[int] = mapped_column(Integer)
    risk_label: Mapped[str] = mapped_column(String(40))
    strategy_name: Mapped[str] = mapped_column(String(120))
    firm_name: Mapped[str] = mapped_column(String(120))
    account_size: Mapped[float] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategies.id"), index=True
    )
    strategy_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategy_versions.id"), index=True
    )
    backtest_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("backtest_runs.id"), index=True
    )
    trade_id: Mapped[int | None] = mapped_column(ForeignKey("trades.id"), index=True)
    # One of: observation | hypothesis | question | decision | bug | risk_note
    note_type: Mapped[str] = mapped_column(
        String(20), default="observation", server_default="observation", index=True
    )
    tags: Mapped[list[str] | None] = mapped_column(JSON)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)


class RiskProfile(Base):
    """A named bundle of risk caps applied retroactively to a run.

    Lets you ask "if I'd been running profile X (max_daily_loss_r=5,
    max_drawdown_r=20, allowed_hours [13,14,15]), would strategy Y
    have hit any cap on day Z?". Evaluation is computed by
    `app.services.risk_evaluator.evaluate_profile`; profiles
    themselves are pure metadata and can be freely created, archived,
    and deleted without touching trade data.

    Caps in R-multiples; None = no cap. allowed_hours_json is a JSON
    list of ints (UTC hours of day) or null = any hour allowed.
    """

    __tablename__ = "risk_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    # "active" | "archived"
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default="active", index=True
    )
    max_daily_loss_r: Mapped[float | None] = mapped_column(Float)
    max_drawdown_r: Mapped[float | None] = mapped_column(Float)
    max_consecutive_losses: Mapped[int | None] = mapped_column(Integer)
    max_position_size: Mapped[int | None] = mapped_column(Integer)
    allowed_hours_json: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    # Default strategy params this profile prefills on the Run-a-Backtest
    # form. Stored as a free-form dict so each strategy's keys can vary;
    # only keys recognized by the chosen strategy are honored. None means
    # "this profile has no opinion on strategy params; only enforces the
    # post-run rule caps above."
    strategy_params: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class FirmRuleProfile(Base):
    """Editable firm rule profile — the source of truth for prop-firm
    rules consumed by the Monte Carlo simulator and shown on the firms
    page.

    Seeded from `app.services.prop_firm.PRESETS` on first boot (any row
    with `is_seed=True`). After that, the dict is just the factory-reset
    reference for the `reset` endpoint; live state lives here.

    Verification semantics:
    - Editing any rule field on a "verified" profile flips the status
      back to "unverified" and clears `verified_at` / `verified_by`.
    - Setting `verification_status="verified"` explicitly stamps
      `verified_at = now()`.
    """

    __tablename__ = "firm_rule_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stable string key — used in URLs + by the simulator's firm_profile_id.
    profile_id: Mapped[str] = mapped_column(String(60), unique=True, index=True)

    # Identity
    firm_name: Mapped[str] = mapped_column(String(120))
    account_name: Mapped[str] = mapped_column(String(120))
    account_size: Mapped[float] = mapped_column(Float)
    phase_type: Mapped[str] = mapped_column(
        String(40), default="evaluation", server_default="evaluation"
    )

    # Sim-relevant rule fields
    profit_target: Mapped[float] = mapped_column(Float)
    max_drawdown: Mapped[float] = mapped_column(Float)
    daily_loss_limit: Mapped[float | None] = mapped_column(Float)
    trailing_drawdown_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1"
    )
    # "intraday" | "end_of_day" | "static" | "none"
    trailing_drawdown_type: Mapped[str] = mapped_column(
        String(20), default="none", server_default="none"
    )
    consistency_pct: Mapped[float | None] = mapped_column(Float)
    consistency_rule_type: Mapped[str] = mapped_column(
        String(40), default="none", server_default="none"
    )
    max_trades_per_day: Mapped[int | None] = mapped_column(Integer)
    minimum_trading_days: Mapped[int | None] = mapped_column(Integer)
    risk_per_trade_dollars: Mapped[float] = mapped_column(
        Float, default=200.0, server_default="200"
    )

    # Payout
    payout_split: Mapped[float] = mapped_column(
        Float, default=0.9, server_default="0.9"
    )
    payout_min_days: Mapped[int | None] = mapped_column(Integer)
    payout_min_profit: Mapped[float | None] = mapped_column(Float)

    # Fees
    eval_fee: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    activation_fee: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0"
    )
    reset_fee: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    monthly_fee: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0"
    )

    # Provenance
    source_url: Mapped[str | None] = mapped_column(String(255))
    last_known_at: Mapped[str | None] = mapped_column(String(20))  # ISO yyyy-mm-dd
    notes: Mapped[str | None] = mapped_column(Text)

    # Verification
    # "unverified" | "verified" | "demo"
    verification_status: Mapped[str] = mapped_column(
        String(20), default="unverified", server_default="unverified", index=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    verified_by: Mapped[str | None] = mapped_column(String(60))

    # Bookkeeping
    is_seed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", index=True
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
