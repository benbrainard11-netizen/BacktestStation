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
    BigInteger,
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
    # Engine plugin this strategy uses — matches a key in
    # `app.services.strategy_registry.STRATEGY_DEFINITIONS`. Null = the
    # strategy isn't bound to a plugin yet (legacy / imported-only). The
    # frontend's Build page renders the visual feature builder when
    # plugin === "composable", else the markdown rules editor.
    plugin: Mapped[str | None] = mapped_column(String(64))
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
    # Composable-strategy spec (entry_long / entry_short / stop / target
    # rules over the FEATURES registry). Null for traditional plugins
    # (fractal_amd etc.) which still use entry_md/exit_md/risk_md as the
    # rules source. Set by the visual feature builder on /build.
    spec_json: Mapped[dict | None] = mapped_column(JSON, default=None)

    strategy: Mapped[Strategy] = relationship(back_populates="versions")
    # `runs` is the reverse side of BacktestRun.strategy_version_id. With
    # baseline_run_id now also linking the two tables, the join column
    # must be disambiguated explicitly.
    runs: Mapped[list["BacktestRun"]] = relationship(
        back_populates="strategy_version",
        cascade="all, delete-orphan",
        foreign_keys="BacktestRun.strategy_version_id",
    )
    hypotheses: Mapped[list["Hypothesis"]] = relationship(
        back_populates="parent_strategy_version",
        foreign_keys="Hypothesis.parent_strategy_version_id",
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
    dataset_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("dataset_snapshots.snapshot_id"), index=True, default=None
    )
    code_commit_sha: Mapped[str | None] = mapped_column(String(40))
    seed: Mapped[int | None] = mapped_column(Integer)
    # "imported" — trades.csv/equity.csv/metrics.json bundle from another tool.
    # "engine"   — produced by the in-app backtest engine.
    source: Mapped[str] = mapped_column(
        String(20), default="imported", server_default="imported", index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="imported")
    tags: Mapped[list[str] | None] = mapped_column(JSON)
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
    trials: Mapped[list["Trial"]] = relationship(
        back_populates="backtest_run",
        foreign_keys="Trial.backtest_run_id",
    )
    dataset_snapshot: Mapped["DatasetSnapshot | None"] = relationship(
        back_populates="backtest_runs",
        foreign_keys=[dataset_snapshot_id],
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


class DatasetSnapshot(Base):
    """A durable data-scope and integrity proof for reproducible runs."""

    __tablename__ = "dataset_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(String(80))
    symbols_json: Mapped[list[str]] = mapped_column(JSON)
    date_start: Mapped[datetime] = mapped_column(DateTime)
    date_end: Mapped[datetime] = mapped_column(DateTime)
    schemas_json: Mapped[list[str]] = mapped_column(JSON)
    r2_inventory_hash: Mapped[str | None] = mapped_column(String(64))
    research_events_manifest_sha256: Mapped[str | None] = mapped_column(String(64))
    partition_count: Mapped[int] = mapped_column(Integer)
    total_bytes: Mapped[int | None] = mapped_column(BigInteger)
    roll_map_version: Mapped[str | None] = mapped_column(String(40))
    known_exclusions_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    # draft | active | archived
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft", index=True
    )
    notes: Mapped[str | None] = mapped_column(Text)
    validation_report_id: Mapped[int | None] = mapped_column(Integer)

    partitions: Mapped[list["DatasetSnapshotPartition"]] = relationship(
        back_populates="snapshot",
        cascade="all, delete-orphan",
        foreign_keys="DatasetSnapshotPartition.snapshot_id",
        order_by="DatasetSnapshotPartition.id",
    )
    inputs: Mapped[list["DatasetSnapshotInput"]] = relationship(
        back_populates="snapshot",
        cascade="all, delete-orphan",
        foreign_keys="DatasetSnapshotInput.snapshot_id",
        order_by="DatasetSnapshotInput.id",
    )
    backtest_runs: Mapped[list["BacktestRun"]] = relationship(
        back_populates="dataset_snapshot",
        foreign_keys="BacktestRun.dataset_snapshot_id",
    )


class DatasetSnapshotPartition(Base):
    """One hashed storage object included in a dataset snapshot."""

    __tablename__ = "dataset_snapshot_partitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("dataset_snapshots.snapshot_id"), index=True
    )
    r2_key: Mapped[str] = mapped_column(String(500), index=True)
    size: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64), index=True)

    snapshot: Mapped[DatasetSnapshot] = relationship(
        back_populates="partitions",
        foreign_keys=[snapshot_id],
    )


class DatasetSnapshotInput(Base):
    """A source manifest or data root used to derive a dataset snapshot."""

    __tablename__ = "dataset_snapshot_inputs"

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("dataset_snapshots.snapshot_id"), index=True
    )
    input_kind: Mapped[str] = mapped_column(String(40), index=True)
    input_uri: Mapped[str] = mapped_column(String(500), index=True)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    size: Mapped[int | None] = mapped_column(BigInteger)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    snapshot: Mapped[DatasetSnapshot] = relationship(
        back_populates="inputs",
        foreign_keys=[snapshot_id],
    )


class PartitionValidationReport(Base):
    """Summary of semantic/integrity validation for one dataset snapshot."""

    __tablename__ = "partition_validation_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(String(64), index=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    generator_version: Mapped[str | None] = mapped_column(String(40))
    total_partitions: Mapped[int] = mapped_column(Integer)
    partitions_pass: Mapped[int] = mapped_column(Integer)
    partitions_warn: Mapped[int] = mapped_column(Integer)
    partitions_fail: Mapped[int] = mapped_column(Integer)
    summary_json: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), default="completed", server_default="completed"
    )
    notes: Mapped[str | None] = mapped_column(Text)

    findings: Mapped[list["PartitionValidationFinding"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        foreign_keys="PartitionValidationFinding.report_id",
        order_by="PartitionValidationFinding.id",
    )


class PartitionValidationFinding(Base):
    """One gate finding emitted by a partition validation report."""

    __tablename__ = "partition_validation_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(
        ForeignKey("partition_validation_reports.id"), index=True
    )
    partition_r2_key: Mapped[str] = mapped_column(String(400))
    schema: Mapped[str] = mapped_column(String(40))
    symbol: Mapped[str | None] = mapped_column(String(20))
    date: Mapped[str | None] = mapped_column(String(10))
    gate_name: Mapped[str] = mapped_column(String(60))
    severity: Mapped[str] = mapped_column(String(10), index=True)
    message: Mapped[str | None] = mapped_column(Text)
    details_json: Mapped[str | None] = mapped_column(Text)

    report: Mapped[PartitionValidationReport] = relationship(
        back_populates="findings",
        foreign_keys=[report_id],
    )


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


class Hypothesis(Base):
    """A falsifiable research claim that can own one or more trial groups."""

    __tablename__ = "hypotheses"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    hypothesis_md: Mapped[str] = mapped_column(Text)
    rationale_md: Mapped[str | None] = mapped_column(Text)
    # draft | active | validated | rejected | archived
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft", index=True
    )
    parent_strategy_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategy_versions.id"), index=True, default=None
    )
    tags_json: Mapped[list[str] | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    parent_strategy_version: Mapped["StrategyVersion | None"] = relationship(
        back_populates="hypotheses",
        foreign_keys=[parent_strategy_version_id],
    )
    trial_groups: Mapped[list["TrialGroup"]] = relationship(
        back_populates="hypothesis",
        cascade="all, delete-orphan",
        foreign_keys="TrialGroup.hypothesis_id",
    )


class TrialGroup(Base):
    """A bounded strategy/search batch under one hypothesis."""

    __tablename__ = "trial_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    hypothesis_id: Mapped[int] = mapped_column(ForeignKey("hypotheses.id"), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    search_space_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    selection_rule: Mapped[str | None] = mapped_column(Text)
    selected_trial_id: Mapped[int | None] = mapped_column(
        ForeignKey("trials.id"), index=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    # draft | running | completed | abandoned | archived
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft", index=True
    )
    notes: Mapped[str | None] = mapped_column(Text)

    hypothesis: Mapped[Hypothesis] = relationship(
        back_populates="trial_groups",
        foreign_keys=[hypothesis_id],
    )
    trials: Mapped[list["Trial"]] = relationship(
        back_populates="trial_group",
        cascade="all, delete-orphan",
        foreign_keys="Trial.trial_group_id",
    )
    lock_records: Mapped[list["TrialLockRecord"]] = relationship(
        back_populates="trial_group",
        cascade="all, delete-orphan",
        foreign_keys="TrialLockRecord.trial_group_id",
    )
    selected_trial: Mapped["Trial | None"] = relationship(
        foreign_keys=[selected_trial_id],
        post_update=True,
    )


class Trial(Base):
    """One attempted candidate inside a TrialGroup."""

    __tablename__ = "trials"

    id: Mapped[int] = mapped_column(primary_key=True)
    trial_group_id: Mapped[int] = mapped_column(
        ForeignKey("trial_groups.id"), index=True
    )
    trial_lock_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("trial_lock_records.id"), index=True, default=None
    )
    backtest_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("backtest_runs.id"), index=True, default=None
    )
    candidate_config_id: Mapped[str | None] = mapped_column(String(200), index=True)
    params_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    parent_trial_id: Mapped[int | None] = mapped_column(
        ForeignKey("trials.id"), index=True, default=None
    )
    data_snapshot_sha: Mapped[str | None] = mapped_column(String(64), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    # queued | running | completed | failed | killed | promoted | ignored
    status: Mapped[str] = mapped_column(
        String(20), default="queued", server_default="queued", index=True
    )
    is_selected: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0", index=True
    )
    selection_reason: Mapped[str | None] = mapped_column(Text)
    summary_metrics_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, default=None
    )

    trial_group: Mapped[TrialGroup] = relationship(
        back_populates="trials",
        foreign_keys=[trial_group_id],
    )
    lock_record: Mapped["TrialLockRecord | None"] = relationship(
        back_populates="trials",
        foreign_keys=[trial_lock_record_id],
    )
    backtest_run: Mapped["BacktestRun | None"] = relationship(
        back_populates="trials",
        foreign_keys=[backtest_run_id],
    )
    parent_trial: Mapped["Trial | None"] = relationship(
        remote_side=[id],
        back_populates="child_trials",
        foreign_keys=[parent_trial_id],
    )
    child_trials: Mapped[list["Trial"]] = relationship(
        back_populates="parent_trial",
        foreign_keys=[parent_trial_id],
    )


class TrialLockRecord(Base):
    """A protocol lock proving when candidates, data, and code were frozen."""

    __tablename__ = "trial_lock_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    trial_group_id: Mapped[int] = mapped_column(
        ForeignKey("trial_groups.id"), index=True
    )
    # pre_validation | pre_test | final
    lock_type: Mapped[str] = mapped_column(String(20), index=True)
    locked_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    candidate_set_yaml: Mapped[str | None] = mapped_column(Text)
    candidate_set_hash: Mapped[str] = mapped_column(String(64), index=True)
    # Soft v1 reference to dataset_snapshots.snapshot_id; no hard FK yet.
    dataset_snapshot_id: Mapped[str] = mapped_column(String(160), index=True)
    code_commit_sha: Mapped[str] = mapped_column(String(40), index=True)
    pre_registration_md: Mapped[str | None] = mapped_column(Text)
    window_train: Mapped[str | None] = mapped_column(String(80))
    window_validation: Mapped[str | None] = mapped_column(String(80))
    window_test: Mapped[str | None] = mapped_column(String(80))
    window_final: Mapped[str | None] = mapped_column(String(80))
    # active | superseded | abandoned | completed
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default="active", index=True
    )
    bug_exceptions_after_lock_json: Mapped[list[dict[str, Any]] | None] = (
        mapped_column(JSON)
    )
    superseded_by_lock_id: Mapped[int | None] = mapped_column(
        ForeignKey("trial_lock_records.id"), index=True, default=None
    )
    notes: Mapped[str | None] = mapped_column(Text)

    trial_group: Mapped[TrialGroup] = relationship(
        back_populates="lock_records",
        foreign_keys=[trial_group_id],
    )
    trials: Mapped[list[Trial]] = relationship(
        back_populates="lock_record",
        foreign_keys="Trial.trial_lock_record_id",
    )
    superseded_by: Mapped["TrialLockRecord | None"] = relationship(
        remote_side=[id],
        back_populates="superseded_locks",
        foreign_keys=[superseded_by_lock_id],
    )
    superseded_locks: Mapped[list["TrialLockRecord"]] = relationship(
        back_populates="superseded_by",
        foreign_keys=[superseded_by_lock_id],
    )


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


class ChatMessage(Base):
    """One turn of a per-strategy AI chat thread.

    Messages are appended in order (user → assistant → user → ...). The
    `cli_session_id` on assistant messages records Claude Code CLI's
    session UUID so subsequent turns can pass `--resume <id>` to keep
    conversation context. Codex is stateless in v1, so its messages
    leave `cli_session_id` null.

    `cost_usd` is what the CLI reported for this turn (Claude only —
    Codex CLI doesn't emit a cost field). Audit trail; not enforced.
    """

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("strategies.id"), index=True
    )
    # "user" | "assistant"
    role: Mapped[str] = mapped_column(String(16), index=True)
    content: Mapped[str] = mapped_column(Text)
    # "claude" | "codex"
    model: Mapped[str] = mapped_column(String(16), default="claude", index=True)
    # Optional Stage-3 scope tag. When per-section AI agents land,
    # this records which workspace tab the conversation belongs to
    # (e.g. "build", "backtest", "replay") so each tab can render
    # its own thread with its own system prompt + context. Null
    # for legacy single-thread messages and for unsectioned chat.
    section: Mapped[str | None] = mapped_column(String(32), index=True)
    # Claude Code's session UUID; populated on assistant messages from
    # the CLI's JSON output. Reused as `--resume <id>` on the next user
    # turn to keep context. Null on user messages and on Codex turns.
    cli_session_id: Mapped[str | None] = mapped_column(String(64))
    # USD cost reported by the CLI for this turn. Claude emits it via
    # `total_cost_usd`; Codex doesn't, leave null.
    cost_usd: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class ResearchEntry(Base):
    """One entry in the per-strategy research workspace.

    Three kinds of entries:
      - "hypothesis": "I think X. Tested by run Y." status: open / running /
        confirmed / rejected
      - "decision":   "I changed Z because of run Y." status: done
      - "question":   "Should I check W?" status: open / done

    All scoped to a single strategy. The body is markdown (rendered in
    the UI). Optional links: `linked_run_id` ties a hypothesis to the
    backtest run that tested it; `linked_version_id` ties a decision to
    the version it changed.

    Lives alongside Notes — Notes are floating research artifacts
    (kept across strategy/version deletes); ResearchEntries are tightly
    bound to the strategy and cascade with it.
    """

    __tablename__ = "research_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("strategies.id"), index=True
    )
    # "hypothesis" | "decision" | "question"
    kind: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(Text)
    # Hypotheses: open | running | confirmed | rejected
    # Decisions: done (immutable record)
    # Questions: open | done
    status: Mapped[str] = mapped_column(
        String(20), default="open", server_default="open", index=True
    )
    linked_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("backtest_runs.id"), index=True
    )
    linked_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategy_versions.id"), index=True
    )
    # Optional links to KnowledgeCard rows. Stored as a JSON id list so
    # one hypothesis/question can point at multiple formulas/concepts.
    # API validation keeps ids real and same-strategy/global.
    knowledge_card_ids: Mapped[list[int] | None] = mapped_column(JSON)
    tags: Mapped[list[str] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)


class KnowledgeCard(Base):
    """Reusable quant memory for formulas, concepts, and research process.

    Knowledge cards are broader than per-strategy research entries:
    a card can define an orderflow formula, a market concept, a setup
    archetype, or a research playbook. Cards are global by default and
    may optionally point at a strategy when the knowledge is strategy-
    specific. They are intentionally structured enough for retrieval
    while still keeping the actual explanation in markdown.
    """

    __tablename__ = "knowledge_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategies.id"), index=True
    )
    kind: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    formula: Mapped[str | None] = mapped_column(Text)
    inputs: Mapped[list[str] | None] = mapped_column(JSON)
    use_cases: Mapped[list[str] | None] = mapped_column(JSON)
    failure_modes: Mapped[list[str] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft", index=True
    )
    source: Mapped[str | None] = mapped_column(Text)
    # Optional structured pointers to the evidence behind a card. A card
    # can be marked `trusted` only honestly if the supporting run /
    # version / research entry is recorded here. `source` keeps the
    # freeform string marker; these fields keep the structured pointer
    # so the UI can render chips and validate scope.
    linked_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("backtest_runs.id"), index=True
    )
    linked_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategy_versions.id"), index=True
    )
    linked_research_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("research_entries.id"), index=True
    )
    tags: Mapped[list[str] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)


class ResearchEvent(Base):
    """One per-detector observation in market data.

    Distinct from `Trade` (filled trades), `LiveSignal` (trade-decision-
    shaped, side+price+executed), and the JSONL `LiveSignalLog` stream
    (trade-signal-shaped, ref_price/stop/target/contracts). A research
    event captures "this detector fired on this bar with this context"
    — most events never become trades. See
    `docs/RESEARCH_KNOWLEDGE_LAYER.md` for the surrounding taxonomy.

    Identity: `event_id` is a stable hash of
    (feature_name, primary_symbol, bar_end_utc, event_type), produced
    by `app.services.research_events.make_event_id`. Insert is
    idempotent on `event_id` so re-running a detector scan over the
    same bars is a no-op.
    """

    __tablename__ = "research_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Stable, collision-resistant hash; unique across the table.
    event_id: Mapped[str] = mapped_column(
        String(80), unique=True, index=True
    )
    # String reference to the FEATURES registry
    # (`backend/app/features/__init__.py`). Not an FK — features are
    # code modules, not DB rows.
    feature_name: Mapped[str] = mapped_column(String(80), index=True)
    # Optional FK to the concept (KnowledgeCard with kind=market_concept).
    knowledge_card_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_cards.id"), index=True, default=None
    )
    # Detector-defined sub-type, e.g. "smt_high", "fvg_creation",
    # "sweep_pdh". Free-form string by design — detectors own their
    # own vocabulary.
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    bar_end_utc: Mapped[datetime] = mapped_column(DateTime, index=True)
    primary_symbol: Mapped[str] = mapped_column(String(40), index=True)
    # All symbols involved (for cross-asset events like SMT). Includes
    # primary_symbol redundantly for query simplicity.
    symbols: Mapped[list[str]] = mapped_column(JSON)
    timeframe: Mapped[str] = mapped_column(String(20))
    # "bullish" | "bearish" | "high" | "low" | None — detector-defined.
    side: Mapped[str | None] = mapped_column(String(20), default=None)
    # Detector-specific decision context at event time. Schema owned
    # by the detector; consumers read it as a free-form dict.
    event_data: Mapped[dict[str, Any]] = mapped_column(JSON)
    # Universal context: session, regime, vol bucket, news proximity.
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    # Forward-window observations recorded after the event (5m/15m/
    # 30m/60m MFE/MAE etc.). Detector or post-processor populates.
    outcomes: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    # Replay pointer: {run_id, dataset, ts_range} or similar — enough
    # to open this moment in the trade-replay UI.
    replay_pointer: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, default=None
    )
    source_dataset: Mapped[str | None] = mapped_column(Text, default=None)
    source_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("backtest_runs.id"), index=True, default=None
    )
    # Detector code version — e.g. git SHA or semver. Lets us segment
    # results by detector revision.
    detector_version: Mapped[str | None] = mapped_column(String(40), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class StrategyPromotionCheck(Base):
    """Per-candidate promotion verdict — paper-ready / research-only / killed.

    Distinct from `Experiment.decision`: an Experiment is a per-A/B-test
    verdict, a PromotionCheck is the per-candidate full-robustness verdict
    aggregating all evidence (walk-forward, LOO, slippage, prop sim,
    sample size, findings docs). Both coexist; FK columns are present so
    a check can optionally point at the strategy/version/run that backed
    the decision, but none are required — many candidates start outside
    the Strategy registry (e.g. raw FractalAMD CSV outputs) and are
    promoted into it later.

    `candidate_config_id` is the soft idempotency key for seed scripts
    that re-import a fixed list of candidates. `findings_path` and the
    `*_paths_json` columns point at the on-disk evidence; the row stores
    pointers, not parsed CSV content (CSV parsing is a future pass).
    """

    __tablename__ = "strategy_promotion_checks"

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
    candidate_name: Mapped[str] = mapped_column(String(200), index=True)
    candidate_config_id: Mapped[str | None] = mapped_column(
        String(200), index=True
    )
    source_repo: Mapped[str | None] = mapped_column(String(120))
    source_dir: Mapped[str | None] = mapped_column(Text)
    findings_path: Mapped[str | None] = mapped_column(Text)
    # draft | pass_paper | research_only | killed | archived
    status: Mapped[str] = mapped_column(
        String(20), default="draft", server_default="draft", index=True
    )
    final_verdict: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    fail_reasons: Mapped[list[str] | None] = mapped_column(JSON)
    pass_reasons: Mapped[list[str] | None] = mapped_column(JSON)
    metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    robustness_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    evidence_paths_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    next_actions: Mapped[list[str] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)
