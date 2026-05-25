"""Operator monitor endpoint."""

from fastapi import APIRouter

from app.schemas.ops import OpsStatusRead
from app.services.ops_status import get_ops_status

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/status", response_model=OpsStatusRead)
def read_ops_status() -> OpsStatusRead:
    return get_ops_status()
