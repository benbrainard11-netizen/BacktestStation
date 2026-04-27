"""Repo-relative paths used by the backend.

Anything that needs to read or write to the local filesystem (the metadata
SQLite DB, raw market data, derived parquet, results) should resolve its
location through this module so paths stay consistent across CLI tools,
the FastAPI app, and tests.
"""

import os
from pathlib import Path

# backend/app/core/paths.py -> parents[3] is the repo root.
REPO_ROOT: Path = Path(__file__).resolve().parents[3]

DATA_DIR: Path = REPO_ROOT / "data"
META_DB_PATH: Path = DATA_DIR / "meta.sqlite"
LIVE_STATUS_PATH: Path = DATA_DIR / "live_status.json"
LIVE_INBOX_DIR: Path = DATA_DIR / "live_inbox"
LIVE_INBOX_JSONL_PATH: Path = LIVE_INBOX_DIR / "trades.jsonl"
LIVE_INBOX_LOG_PATH: Path = LIVE_INBOX_DIR / "import.log"

# External market-data sources (Fractal AMD local parquet archive).
# Read-only — BacktestStation never writes here.
_DEFAULT_FRACTAL_ROOT = Path("C:/Fractal-AMD/data")


def fractal_data_root() -> Path:
    """Root of the Fractal-AMD local data archive.

    Override with env var `FRACTAL_DATA_ROOT` to point at a different
    local mirror. Read-only for BacktestStation.
    """
    override = os.getenv("FRACTAL_DATA_ROOT")
    return Path(override) if override else _DEFAULT_FRACTAL_ROOT


def fractal_ohlcv_dir() -> Path:
    return fractal_data_root() / "raw"


def fractal_tbbo_dir() -> Path:
    return fractal_data_root() / "l2"


def ensure_data_dir() -> Path:
    """Create the local data directory if it does not exist; return it."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def warehouse_root() -> Path:
    """Root of the on-disk data warehouse (raw DBN, parquet mirror, heartbeats).

    Configured via the BS_DATA_ROOT env var — same pattern the ingester
    daemons use. Defaults to C:/data on Windows, ./data elsewhere. This
    is DIFFERENT from DATA_DIR which is the repo-relative metadata
    directory; the warehouse lives outside the repo on a 24/7 collection
    node and is mounted/synced separately.
    """
    default = "C:/data" if os.name == "nt" else "./data"
    return Path(os.environ.get("BS_DATA_ROOT", default))


def ingester_heartbeat_path() -> Path:
    """Path to the live ingester's heartbeat JSON. Read by /api/monitor/ingester."""
    return warehouse_root() / "heartbeat" / "live_ingester.json"
