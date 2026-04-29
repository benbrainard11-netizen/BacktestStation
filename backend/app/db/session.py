"""SQLAlchemy engine, session factory, and table-creation helper.

Production callers go through `get_session()` which lazily binds to the
default SQLite metadata DB at `data/meta.sqlite`. Tests should build their
own engine with `make_engine("sqlite:///<tmp>/test.sqlite")` and call
`create_all(engine)` so they never touch the real DB.
"""

import threading
from collections.abc import Generator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.paths import META_DB_PATH, ensure_data_dir


class Base(DeclarativeBase):
    """Base class every ORM model inherits from."""


def make_engine(database_url: str | None = None) -> Engine:
    """Build a SQLAlchemy engine. Defaults to the local SQLite metadata DB.

    SQLite engines get a `PRAGMA foreign_keys=ON` connect listener so the
    FK relationships declared on the ORM models are actually enforced. SQLite
    ships with FK enforcement OFF by default — without this, `ON DELETE`
    cascades and orphan-row protections silently no-op.
    """
    if database_url is None:
        ensure_data_dir()
        database_url = f"sqlite:///{META_DB_PATH}"
    is_sqlite = database_url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    engine = create_engine(database_url, connect_args=connect_args, future=True)
    if is_sqlite:
        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Build a Session factory bound to the given engine."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def create_all(engine: Engine) -> None:
    """Create every table registered on `Base` against the given engine.

    Used by tests for a fresh DB and by first-run setup against the default DB.
    """
    # Importing models registers their classes on Base.metadata.
    from app.db import models  # noqa: F401

    Base.metadata.create_all(engine)
    _run_data_migrations(engine)


def _run_data_migrations(engine: Engine) -> None:
    """Idempotent data migrations that run every time the app starts.

    Kept tiny and explicit — when there are more than a few, we'll switch
    to Alembic. For now each migration is a guarded UPDATE.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    with engine.begin() as connection:
        # 2026-04-24: "testing" was the legacy auto-registered status for
        # imported strategies before the lifecycle vocabulary shipped. Map
        # any leftover rows to "building" so they show up in the right
        # pipeline column. Safe to re-run: the UPDATE is a no-op once
        # nothing matches.
        connection.execute(
            text(
                "UPDATE strategies SET status = 'building' "
                "WHERE status = 'testing'"
            )
        )

        # 2026-04-24: StrategyVersion.archived_at added so versions can be
        # archived instead of cascade-deleting their runs/trades/metrics.
        # SQLite's create_all() won't add columns to existing tables, so
        # check and ALTER explicitly. Guard is idempotent.
        sv_columns = {c["name"] for c in inspector.get_columns("strategy_versions")}
        if "archived_at" not in sv_columns:
            connection.execute(
                text("ALTER TABLE strategy_versions ADD COLUMN archived_at DATETIME")
            )

        # 2026-04-24: Notes extended for the Research Workspace —
        # attach to strategy/version, typed (observation/hypothesis/...),
        # tagged, with an updated_at. Existing rows get note_type
        # backfilled to 'observation' via the column DEFAULT.
        notes_columns = {c["name"] for c in inspector.get_columns("notes")}
        if "strategy_id" not in notes_columns:
            connection.execute(
                text("ALTER TABLE notes ADD COLUMN strategy_id INTEGER")
            )
        if "strategy_version_id" not in notes_columns:
            connection.execute(
                text(
                    "ALTER TABLE notes ADD COLUMN strategy_version_id INTEGER"
                )
            )
        if "note_type" not in notes_columns:
            connection.execute(
                text(
                    "ALTER TABLE notes ADD COLUMN note_type VARCHAR(20) "
                    "NOT NULL DEFAULT 'observation'"
                )
            )
        if "tags" not in notes_columns:
            connection.execute(text("ALTER TABLE notes ADD COLUMN tags JSON"))
        if "updated_at" not in notes_columns:
            connection.execute(
                text("ALTER TABLE notes ADD COLUMN updated_at DATETIME")
            )

        # 2026-04-25: BacktestRun gains `source` to distinguish imported
        # vs engine-produced runs. Existing rows backfill to "imported".
        run_columns = {c["name"] for c in inspector.get_columns("backtest_runs")}
        if "source" not in run_columns:
            connection.execute(
                text(
                    "ALTER TABLE backtest_runs ADD COLUMN source VARCHAR(20) "
                    "NOT NULL DEFAULT 'imported'"
                )
            )

        # 2026-04-29: BacktestRun gains `tags` (JSON list) — the API at
        # PUT /api/backtests/{id}/tags has been writing to this attribute,
        # but the underlying column was missing so values silently dropped
        # on commit. Existing rows backfill to NULL.
        if "tags" not in run_columns:
            connection.execute(
                text("ALTER TABLE backtest_runs ADD COLUMN tags JSON")
            )

        # 2026-04-25: StrategyVersion.baseline_run_id added for the Forward
        # Drift Monitor — points at the run we expect live behavior to track.
        # Nullable; existing rows have no baseline until the user picks one.
        if "baseline_run_id" not in sv_columns:
            connection.execute(
                text(
                    "ALTER TABLE strategy_versions ADD COLUMN "
                    "baseline_run_id INTEGER REFERENCES backtest_runs(id)"
                )
            )

        # 2026-04-26: RiskProfile.strategy_params added so a profile can
        # prefill the Run-a-Backtest form with default strategy params.
        # Nullable; existing rows have no opinion on params and only
        # enforce the post-run caps already on the row.
        if inspector.has_table("risk_profiles"):
            rp_columns = {
                c["name"] for c in inspector.get_columns("risk_profiles")
            }
            if "strategy_params" not in rp_columns:
                connection.execute(
                    text("ALTER TABLE risk_profiles ADD COLUMN strategy_params JSON")
                )

            # Seed default profiles once. Idempotent — INSERT only when
            # no row with the same name already exists, so the user can
            # rename / delete / edit them freely without us re-creating
            # the originals on every app restart.
            _seed_default_risk_profiles(connection)

        # 2026-04-25: FirmRuleProfile table added — DB now owns the
        # editable firm presets. Seed from the static PRESETS dict if
        # any profile_id is missing. Idempotent — never overwrites a
        # row the user has edited.
        if inspector.has_table("firm_rule_profiles"):
            _seed_default_firm_rule_profiles(connection)

        # 2026-04-29: Strategy.plugin — engine-plugin key (composable /
        # fractal_amd / moving_average_crossover). Lets the workspace
        # render the right Build-tab UI (visual feature builder vs
        # markdown rules) without name-matching tricks.
        s_columns = {c["name"] for c in inspector.get_columns("strategies")}
        if "plugin" not in s_columns:
            connection.execute(
                text("ALTER TABLE strategies ADD COLUMN plugin VARCHAR(64)")
            )

        # 2026-04-29: StrategyVersion.spec_json — composable-strategy
        # recipe (entry_long / entry_short / stop / target). Null for
        # traditional plugins.
        if "spec_json" not in sv_columns:
            connection.execute(
                text("ALTER TABLE strategy_versions ADD COLUMN spec_json JSON")
            )

        # 2026-04-29: ChatMessage table for per-strategy AI chat threads.
        # `Base.metadata.create_all()` already handles fresh DBs; this
        # guarded CREATE catches existing sqlite files that predate the
        # model.
        if not inspector.has_table("chat_messages"):
            connection.execute(
                text(
                    "CREATE TABLE chat_messages ("
                    " id INTEGER PRIMARY KEY,"
                    " strategy_id INTEGER NOT NULL REFERENCES strategies(id),"
                    " role VARCHAR(16) NOT NULL,"
                    " content TEXT NOT NULL,"
                    " model VARCHAR(16) NOT NULL DEFAULT 'claude',"
                    " cli_session_id VARCHAR(64),"
                    " cost_usd FLOAT,"
                    " created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"
                    ")"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX ix_chat_messages_strategy_id "
                    "ON chat_messages(strategy_id)"
                )
            )


def _seed_default_risk_profiles(connection) -> None:
    """Insert Conservative / Live-mirror / Aggressive defaults if missing.

    Profiles are user-editable; we only seed names that don't already
    exist. Caps are R-multiples (so size-independent); strategy_params
    are fractal_amd-specific (the only strategy we trade today).
    """
    import json as _json
    from sqlalchemy import text as _text

    defaults = [
        {
            "name": "Conservative",
            "status": "active",
            "max_daily_loss_r": 2.0,
            "max_drawdown_r": 5.0,
            "max_consecutive_losses": 2,
            "max_position_size": 1,
            "allowed_hours_json": _json.dumps([13, 14, 15, 16, 17]),  # UTC
            "notes": (
                "Tight per-trade risk, single contract, RTH only. Caps a "
                "drawdown at 5R."
            ),
            "strategy_params": _json.dumps(
                {
                    "max_risk_dollars": 300.0,
                    "max_trades_per_day": 1,
                    "target_r": 2.0,
                }
            ),
        },
        {
            "name": "Live-mirror",
            "status": "active",
            "max_daily_loss_r": 4.0,
            "max_drawdown_r": 10.0,
            "max_consecutive_losses": 3,
            "max_position_size": 1,
            "allowed_hours_json": _json.dumps([13, 14, 15, 16, 17]),
            "notes": (
                "Mirrors the live bot's risk gates: $300 dollar cap, "
                "max 2 trades/day, 3R target."
            ),
            "strategy_params": _json.dumps(
                {
                    "max_risk_dollars": 300.0,
                    "max_trades_per_day": 2,
                    "target_r": 3.0,
                }
            ),
        },
        {
            "name": "Aggressive",
            "status": "active",
            "max_daily_loss_r": 8.0,
            "max_drawdown_r": 20.0,
            "max_consecutive_losses": 4,
            "max_position_size": 1,
            "allowed_hours_json": None,
            "notes": (
                "$500 dollar cap, up to 3 trades/day, 3R target. Wider "
                "caps; intended for stress-testing the strategy."
            ),
            "strategy_params": _json.dumps(
                {
                    "max_risk_dollars": 500.0,
                    "max_trades_per_day": 3,
                    "target_r": 3.0,
                }
            ),
        },
    ]
    for profile in defaults:
        existing = connection.execute(
            _text("SELECT id FROM risk_profiles WHERE name = :name"),
            {"name": profile["name"]},
        ).first()
        if existing:
            continue
        connection.execute(
            _text(
                "INSERT INTO risk_profiles "
                "(name, status, max_daily_loss_r, max_drawdown_r, "
                " max_consecutive_losses, max_position_size, "
                " allowed_hours_json, notes, strategy_params) "
                "VALUES (:name, :status, :max_daily_loss_r, :max_drawdown_r, "
                " :max_consecutive_losses, :max_position_size, "
                " :allowed_hours_json, :notes, :strategy_params)"
            ),
            profile,
        )


def _seed_default_firm_rule_profiles(connection) -> None:
    """Seed firm rule profiles from `app.services.prop_firm.PRESETS` for
    any `profile_id` not already in the DB. Existing rows are NEVER
    overwritten — `is_seed=True` is the marker that a row was originally
    seeded (and so eligible for the /reset endpoint), but once the user
    edits it the row stays editable; reset is the only way to restore.
    """
    from sqlalchemy import text as _text

    # Local import — services/prop_firm.py imports from app.db.models,
    # so a top-level import would cycle.
    from app.services.prop_firm import PRESETS

    for key, preset in PRESETS.items():
        existing = connection.execute(
            _text("SELECT id FROM firm_rule_profiles WHERE profile_id = :pid"),
            {"pid": key},
        ).first()
        if existing:
            continue
        firm_name = preset.name.split(" ")[0] or preset.name
        trailing_type = preset.trailing_drawdown_type
        if preset.trailing_drawdown and trailing_type == "none":
            trailing_type = "intraday"
        connection.execute(
            _text(
                "INSERT INTO firm_rule_profiles ("
                " profile_id, firm_name, account_name, account_size, "
                " phase_type, profit_target, max_drawdown, daily_loss_limit, "
                " trailing_drawdown_enabled, trailing_drawdown_type, "
                " consistency_pct, consistency_rule_type, max_trades_per_day, "
                " minimum_trading_days, risk_per_trade_dollars, "
                " payout_split, payout_min_days, payout_min_profit, "
                " eval_fee, activation_fee, reset_fee, monthly_fee, "
                " source_url, last_known_at, notes, "
                " verification_status, is_seed, is_archived"
                ") VALUES ("
                " :profile_id, :firm_name, :account_name, :account_size, "
                " :phase_type, :profit_target, :max_drawdown, :daily_loss_limit, "
                " :trailing_drawdown_enabled, :trailing_drawdown_type, "
                " :consistency_pct, :consistency_rule_type, :max_trades_per_day, "
                " :minimum_trading_days, :risk_per_trade_dollars, "
                " :payout_split, :payout_min_days, :payout_min_profit, "
                " :eval_fee, :activation_fee, :reset_fee, :monthly_fee, "
                " :source_url, :last_known_at, :notes, "
                " :verification_status, :is_seed, :is_archived"
                ")"
            ),
            {
                "profile_id": key,
                "firm_name": firm_name,
                "account_name": preset.name,
                "account_size": preset.starting_balance,
                "phase_type": "evaluation",
                "profit_target": preset.profit_target,
                "max_drawdown": preset.max_drawdown,
                "daily_loss_limit": preset.daily_loss_limit,
                "trailing_drawdown_enabled": preset.trailing_drawdown,
                "trailing_drawdown_type": trailing_type,
                "consistency_pct": preset.consistency_pct,
                "consistency_rule_type": (
                    "best_day_pct_of_total"
                    if preset.consistency_pct is not None
                    else "none"
                ),
                "max_trades_per_day": preset.max_trades_per_day,
                "minimum_trading_days": preset.minimum_trading_days,
                "risk_per_trade_dollars": preset.risk_per_trade_dollars,
                "payout_split": preset.payout_split,
                "payout_min_days": preset.payout_min_days,
                "payout_min_profit": preset.payout_min_profit,
                "eval_fee": preset.eval_fee,
                "activation_fee": preset.activation_fee,
                "reset_fee": preset.reset_fee,
                "monthly_fee": preset.monthly_fee,
                "source_url": preset.source_url,
                "last_known_at": preset.last_known_at,
                "notes": preset.notes,
                "verification_status": "unverified",
                "is_seed": True,
                "is_archived": False,
            },
        )


# Lazily-initialised module globals for the running FastAPI app.
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
# Guards the lazy init — FastAPI serves sync endpoints on a thread pool,
# so parallel requests on first load could race through `create_all` and
# collide on CREATE TABLE. A single lock keeps init atomic.
_init_lock = threading.Lock()


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a Session bound to the default DB."""
    global _engine, _session_factory
    if _session_factory is None:
        with _init_lock:
            if _session_factory is None:
                _engine = make_engine()
                create_all(_engine)
                _session_factory = make_session_factory(_engine)
    assert _session_factory is not None  # narrow for type checker
    db = _session_factory()
    try:
        yield db
    finally:
        db.close()
