"""Discover what's available in the R2 warehouse without recursive LIST.

Fetches `_inventory.json` from the R2 bucket root. Cached in-process per
session so repeat calls are free. Use to surface coverage to users
("here's the symbol/date matrix") and to validate requested ranges
before the loader hits R2.
"""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from typing import Any

from bsdata.cache import make_s3_client

INVENTORY_KEY = "_inventory.json"

_cached_inventory: "Inventory | None" = None


@dataclass(frozen=True)
class InventoryPartition:
    kind: str               # "raw" | "bars"
    schema: str             # tbbo | mbp-1 | ohlcv-1m
    symbol: str
    date: dt.date
    timeframe: str | None   # bars only
    size: int
    r2_key: str


@dataclass(frozen=True)
class Inventory:
    generated_at: dt.datetime
    schema_version: str
    generator_version: str
    partitions: tuple[InventoryPartition, ...]

    def symbols(self) -> list[str]:
        return sorted({p.symbol for p in self.partitions})

    def date_range(self, *, schema: str, symbol: str) -> tuple[dt.date, dt.date] | None:
        """Return (min_date, max_date) for the (schema, symbol) pair, or None."""
        dates = sorted(
            p.date for p in self.partitions
            if p.schema == schema and p.symbol == symbol
        )
        if not dates:
            return None
        return dates[0], dates[-1]


def get_inventory(*, force_refresh: bool = False) -> Inventory:
    """Fetch and parse the R2 inventory. Cached for the process lifetime."""
    global _cached_inventory
    if _cached_inventory is not None and not force_refresh:
        return _cached_inventory

    client, bucket = make_s3_client()
    obj = client.get_object(Bucket=bucket, Key=INVENTORY_KEY)
    raw = obj["Body"].read().decode("utf-8")
    payload = json.loads(raw)
    _cached_inventory = _parse_inventory(payload)
    return _cached_inventory


def _parse_inventory(payload: dict[str, Any]) -> Inventory:
    parts = []
    for p in payload.get("partitions", []):
        parts.append(
            InventoryPartition(
                kind=p["kind"],
                schema=p["schema"],
                symbol=p["symbol"],
                date=dt.date.fromisoformat(p["date"]),
                timeframe=p.get("timeframe"),
                size=int(p["size"]),
                r2_key=p["r2_key"],
            )
        )
    return Inventory(
        generated_at=dt.datetime.fromisoformat(payload["generated_at"]),
        schema_version=payload["schema_version"],
        generator_version=payload["generator_version"],
        partitions=tuple(parts),
    )
