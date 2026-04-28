"""Settings endpoint — read-only system inspection (v1).

Editable user prefs land in a later PR with its own table + CRUD.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas import SystemSettingsRead
from app.services.system_info import get_system_info

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/system", response_model=SystemSettingsRead)
def read_system_settings() -> SystemSettingsRead:
    """Snapshot of how the app is currently configured.

    No persistence yet — every field is derived from process state at
    request time. Frontend polls or fetches once at page load.
    """
    return get_system_info()
