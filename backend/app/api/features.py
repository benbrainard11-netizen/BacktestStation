"""Read-only feature-library endpoint.

Exposes the in-process FEATURES registry so the frontend's visual
feature builder (Phase C) can render a pantry of available primitives
+ each one's editable param schema.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.features import FEATURES

router = APIRouter(prefix="/features", tags=["features"])


@router.get("", response_model=list[dict[str, Any]])
def list_features() -> list[dict[str, Any]]:
    """Return the FEATURES registry as a flat list.

    Each entry: { name, label, description, param_schema }. Frontend
    renders one card per entry in the feature pantry; clicking "+ Add"
    instantiates a `{feature: name, params: {}}` block in the strategy
    spec.
    """
    out: list[dict[str, Any]] = []
    for name, spec in FEATURES.items():
        out.append(
            {
                "name": name,
                "label": spec.label,
                "description": spec.description,
                "param_schema": spec.param_schema,
            }
        )
    out.sort(key=lambda x: str(x["name"]))
    return out
