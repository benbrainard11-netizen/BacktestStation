"""API shapes for /settings — read-only system info v1.

Editable user prefs (theme, contract specs, session hours, keyboard
shortcuts) need their own table + CRUD; that's a separate PR scoped
explicitly.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SystemSettingsRead(BaseModel):
    """Read-only inspection of how the app is currently configured.

    Everything here is derived from process state at request time —
    no DB persistence yet. When editable settings ship, this stays as
    the "system facts" view; new endpoints will handle the user prefs.
    """

    # Where the warehouse lives.
    bs_data_root: str
    bs_data_root_exists: bool

    # Whether the bot can pull historical data — never the actual key.
    databento_api_key_set: bool

    # Backend identity.
    version: str
    git_sha: str | None
    git_dirty: bool

    # Runtime.
    platform: str
    python_version: str

    # Storage.
    free_disk_bytes: int

    # Wall clocks.
    server_time_utc: datetime
    server_time_et: datetime
