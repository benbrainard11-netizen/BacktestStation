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


# Lazily-initialised module globals for the running FastAPI app.
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a Session bound to the default DB."""
    global _engine, _session_factory
    if _session_factory is None:
        _engine = make_engine()
        _session_factory = make_session_factory(_engine)
    db = _session_factory()
    try:
        yield db
    finally:
        db.close()
