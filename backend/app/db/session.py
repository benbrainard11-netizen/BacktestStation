"""SQLAlchemy engine, session factory, and table-creation helper.

Production callers go through `get_session()` which lazily binds to the
default SQLite metadata DB at `data/meta.sqlite`. Tests should build their
own engine with `make_engine("sqlite:///<tmp>/test.sqlite")` and call
`create_all(engine)` so they never touch the real DB.
"""

import threading
from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.paths import META_DB_PATH, ensure_data_dir


class Base(DeclarativeBase):
    """Base class every ORM model inherits from."""


def make_engine(database_url: str | None = None) -> Engine:
    """Build a SQLAlchemy engine. Defaults to the local SQLite metadata DB."""
    if database_url is None:
        ensure_data_dir()
        database_url = f"sqlite:///{META_DB_PATH}"
    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    return create_engine(database_url, connect_args=connect_args, future=True)


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
