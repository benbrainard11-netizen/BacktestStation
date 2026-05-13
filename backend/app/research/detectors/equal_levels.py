"""Equal Levels detector — find liquidity pools (clusters of swing pivots).

When two or more swing pivots fall within X points of each other (on
the same side — both highs or both lows), that price level becomes
a "liquidity pool" — orders likely sit there. ICT folks use these as
TARGETS (where price is drawn).

Detection joins to existing `swing_pivot` events. Fires AFTER the
SECOND pivot (the one that confirms the cluster is valid). bar_end_utc
= the timestamp of the SECOND pivot.

Modes pair pivot-N + tolerance-pts:
  - eq_pivot_5_1h_5pts    (5-bar swing on 1h, within 5 NQ pts)
  - eq_pivot_5_1h_15pts   (looser tolerance)
  - eq_pivot_5_4h_15pts   (4h pivots, 15pts)
  - eq_pivot_5_daily_30pts

Side = "high" (equal highs = sell-side liquidity above) or "low".
Wide-reach data: all member pivot timestamps + prices, cluster mid,
cluster spread (max - min).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ResearchEvent
from app.db.session import make_engine, make_session_factory
from app.research.detectors import BarReader, DetectorContext, register
from app.schemas.research_events import ResearchEventCreate

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
log = logging.getLogger(__name__)


# Mode → (parent swing_pivot mode, tolerance_pts).
_MODE_CONFIG: dict[str, dict[str, Any]] = {
    "eq_pivot_5_1h_5pts":    {"parent": "pivot_5_1h",   "tol_pts": 5.0},
    "eq_pivot_5_1h_15pts":   {"parent": "pivot_5_1h",   "tol_pts": 15.0},
    "eq_pivot_5_4h_15pts":   {"parent": "pivot_5_4h",   "tol_pts": 15.0},
    "eq_pivot_5_daily_30pts": {"parent": "pivot_5_daily", "tol_pts": 30.0},
    "eq_pivot_3_1h_5pts":    {"parent": "pivot_3_1h",   "tol_pts": 5.0},
    "eq_pivot_3_1h_15pts":   {"parent": "pivot_3_1h",   "tol_pts": 15.0},
    "eq_pivot_3_4h_15pts":   {"parent": "pivot_3_4h",   "tol_pts": 15.0},
}


class EqualLevelsDetector:
    feature_name: str = "equal_levels"
    detector_version: str = "v1"
    supported_modes: tuple[str, ...] = tuple(_MODE_CONFIG.keys())

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        if ctx.mode is None:
            raise ValueError(
                f"equal_levels requires --mode {{{ '|'.join(self.supported_modes) }}}"
            )
        if ctx.mode not in _MODE_CONFIG:
            raise ValueError(f"unsupported mode: {ctx.mode}")
        if not ctx.symbols:
            raise ValueError("equal_levels requires at least one symbol")

        cfg = _MODE_CONFIG[ctx.mode]
        # Open a fresh DB session to read the parent swing_pivot events.
        engine = make_engine()
        session_factory = make_session_factory(engine)
        events: list[ResearchEventCreate] = []
        with session_factory() as db:
            for symbol in ctx.symbols:
                events.extend(self._scan_symbol(ctx, symbol, cfg, db))
        return events

    def _scan_symbol(
        self,
        ctx: DetectorContext, symbol: str,
        cfg: dict[str, Any], db: Session,
    ) -> list[ResearchEventCreate]:
        # Load all swing_pivot events of the parent mode for this symbol.
        # Filter by event_data side (not the row's side which is already there).
        start_dt = datetime(ctx.start.year, ctx.start.month, ctx.start.day, tzinfo=UTC)
        end_dt = datetime(ctx.end.year, ctx.end.month, ctx.end.day, tzinfo=UTC) + timedelta(days=1)
        # Pad start by 60 days so we can detect equal levels with prior pivots.
        load_start = start_dt - timedelta(days=60)

        stmt = (
            select(ResearchEvent)
            .where(ResearchEvent.feature_name == "swing_pivot")
            .where(ResearchEvent.event_type == cfg["parent"])
            .where(ResearchEvent.primary_symbol == symbol)
            .where(ResearchEvent.bar_end_utc >= load_start.replace(tzinfo=None))
            .where(ResearchEvent.bar_end_utc < end_dt.replace(tzinfo=None))
            .order_by(ResearchEvent.bar_end_utc)
        )
        pivots = list(db.scalars(stmt))
        if len(pivots) < 2:
            return []

        # Process highs and lows separately.
        high_pivots = [p for p in pivots if p.side == "high"]
        low_pivots = [p for p in pivots if p.side == "low"]

        events: list[ResearchEventCreate] = []
        events.extend(self._find_equal_clusters(
            high_pivots, side="high", cfg=cfg, mode=ctx.mode,
            symbol=symbol, scan_start=start_dt, scan_end=end_dt,
        ))
        events.extend(self._find_equal_clusters(
            low_pivots, side="low", cfg=cfg, mode=ctx.mode,
            symbol=symbol, scan_start=start_dt, scan_end=end_dt,
        ))
        return events

    def _find_equal_clusters(
        self,
        pivots: list[ResearchEvent],
        *, side: str, cfg: dict[str, Any], mode: str, symbol: str,
        scan_start: datetime, scan_end: datetime,
    ) -> list[ResearchEventCreate]:
        """Walk through pivots in chronological order. For each pivot,
        check the LOOKBACK pivots (default last 10) within tolerance.
        Fire on second-or-more match. The "cluster" is all matched pivots
        plus the current one.
        """
        tol_pts = cfg["tol_pts"]
        events: list[ResearchEventCreate] = []
        max_lookback = 10  # only consider the last N prior pivots for clustering

        for i, p in enumerate(pivots):
            p_price = float((p.event_data or {}).get("pivot_price", 0.0))
            if p_price == 0.0:
                continue
            # Find prior pivots within tol_pts.
            cluster: list[ResearchEvent] = []
            for j in range(max(0, i - max_lookback), i):
                q = pivots[j]
                q_price = float((q.event_data or {}).get("pivot_price", 0.0))
                if q_price == 0.0:
                    continue
                if abs(p_price - q_price) <= tol_pts:
                    cluster.append(q)
            if not cluster:
                continue
            cluster.append(p)  # include the current pivot
            # bar_end_utc = current pivot's bar_end (when cluster is "knowable")
            ts = p.bar_end_utc
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if ts < scan_start or ts >= scan_end:
                continue
            # Member descriptions
            members = []
            prices: list[float] = []
            for m in cluster:
                m_price = float((m.event_data or {}).get("pivot_price", 0.0))
                m_ts = m.bar_end_utc
                if m_ts.tzinfo is None:
                    m_ts = m_ts.replace(tzinfo=UTC)
                members.append({
                    "ts_utc": m_ts.isoformat(),
                    "price": m_price,
                    "pivot_event_id": m.event_id,
                    "pivot_n": (m.event_data or {}).get("n"),
                })
                prices.append(m_price)
            cluster_mid = (max(prices) + min(prices)) / 2.0
            cluster_spread = max(prices) - min(prices)
            # Use the EXTREME of the cluster as the level price (most
            # likely target). For equal highs → max. For equal lows → min.
            level_price = max(prices) if side == "high" else min(prices)
            et_ts = ts.astimezone(ET)
            event_data: dict[str, Any] = {
                "schema_version": 1,
                "detector_version": self.detector_version,
                "mode": mode,
                "side": side,
                "tolerance_pts": tol_pts,
                "parent_pivot_mode": cfg["parent"],
                "n_members": len(cluster),
                "members": members,
                "level_price": level_price,
                "cluster_mid": cluster_mid,
                "cluster_spread_pts": cluster_spread,
                "cluster_min_price": min(prices),
                "cluster_max_price": max(prices),
            }
            context: dict[str, Any] = {
                "day_of_week_et": et_ts.weekday(),
                "hour_of_day_et": et_ts.hour,
                "n_members": len(cluster),
                "tolerance_pts": tol_pts,
            }
            events.append(ResearchEventCreate(
                feature_name=self.feature_name,
                event_type=mode,
                bar_end_utc=ts,
                primary_symbol=symbol,
                symbols=[symbol],
                timeframe="LEVEL",
                side=side,
                event_data=event_data,
                context=context,
                outcomes=None,
                replay_pointer={
                    "primary_symbol": symbol,
                    "ts_utc": ts.isoformat(),
                    "level_price": level_price,
                    "side": side,
                },
                detector_version=self.detector_version,
            ))
        return events


# ---------- registration ----------

register("equal_levels", EqualLevelsDetector())
