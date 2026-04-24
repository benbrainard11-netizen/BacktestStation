"""SQLAlchemy engine, session factory, and table-creation helper.

Production callers go through `get_session()` which lazily binds to the
default SQLite metadata DB at `data/meta.sqlite`. Tests should build their
own engine with `make_engine("sqlite:///<tmp>/test.sqlite")` and call
`create_all(engine)` so they never touch the real DB.
"""

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


# Lazily-initialised module globals for the running FastAPI app.
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a Session bound to the default DB."""
    global _engine, _session_factory
    if _session_factory is None:
        _engine = make_engine()
        create_all(_engine)
        _session_factory = make_session_factory(_engine)
    db = _session_factory()
    try:
        yield db
    finally:
        db.close()
