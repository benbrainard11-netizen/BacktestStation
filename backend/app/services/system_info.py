"""System-info aggregator for /api/settings/system.

Pure read of process state — no DB writes, no shell-outs except the
git rev-parse for the SHA (cheap, ~10ms). Falls back gracefully when
git isn't available (e.g. shipped artifact, CI without .git).
"""

from __future__ import annotations

import datetime as dt
import os
import shutil
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from app import __version__
from app.core.paths import warehouse_root
from app.schemas.settings import SystemSettingsRead

ET = ZoneInfo("America/New_York")


def get_system_info() -> SystemSettingsRead:
    root = warehouse_root()
    sha, dirty = _git_state()
    free_bytes = _free_disk(root)
    now_utc = dt.datetime.now(dt.timezone.utc)
    return SystemSettingsRead(
        bs_data_root=str(root),
        bs_data_root_exists=root.exists(),
        databento_api_key_set=bool(os.environ.get("DATABENTO_API_KEY")),
        version=__version__,
        git_sha=sha,
        git_dirty=dirty,
        platform=sys.platform,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        free_disk_bytes=free_bytes,
        server_time_utc=now_utc,
        server_time_et=now_utc.astimezone(ET),
    )


def _free_disk(path: Path) -> int:
    try:
        return shutil.disk_usage(path).free
    except (FileNotFoundError, OSError):
        return 0


def _git_state(*, timeout_sec: float = 2.0) -> tuple[str | None, bool]:
    """Best-effort: SHA + dirty flag. Returns (None, False) if git
    isn't available or this isn't a repo."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        if sha.returncode != 0:
            return None, False
        sha_value = sha.stdout.strip() or None

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        dirty = status.returncode == 0 and bool(status.stdout.strip())
        return sha_value, dirty
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None, False
