"""Repo-relative paths used by the backend.

Anything that needs to read or write to the local filesystem (the metadata
SQLite DB, raw market data, derived parquet, results) should resolve its
location through this module so paths stay consistent across CLI tools,
the FastAPI app, and tests.
"""

from pathlib import Path

# backend/app/core/paths.py -> parents[3] is the repo root.
REPO_ROOT: Path = Path(__file__).resolve().parents[3]

DATA_DIR: Path = REPO_ROOT / "data"
META_DB_PATH: Path = DATA_DIR / "meta.sqlite"
LIVE_STATUS_PATH: Path = DATA_DIR / "live_status.json"


def ensure_data_dir() -> Path:
    """Create the local data directory if it does not exist; return it."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR
