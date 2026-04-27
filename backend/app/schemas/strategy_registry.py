"""API schemas for the strategy-registry endpoint."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class StrategyParamFieldSchema(BaseModel):
    """One field of a strategy's params, in a frontend-friendly shape.

    `type` mirrors JSON Schema's primitive types we actually use today;
    `label` is the form-row title; `min`/`max`/`step` are optional UI
    hints for number inputs; `description` is a one-line hint shown
    under the field. `enum` lets a strategy expose dropdown choices in
    the future (unused so far).
    """

    type: str  # "number" | "integer" | "string" | "boolean"
    label: str
    description: str | None = None
    min: float | int | None = None
    max: float | int | None = None
    step: float | int | None = None
    enum: list[Any] | None = None


class StrategyParamSchema(BaseModel):
    type: str = "object"
    properties: dict[str, StrategyParamFieldSchema] = Field(default_factory=dict)


class StrategyDefinitionRead(BaseModel):
    """One runnable strategy + the metadata the form needs to render."""

    name: str
    label: str
    description: str | None = None
    default_params: dict[str, Any] = Field(default_factory=dict)
    param_schema: StrategyParamSchema
