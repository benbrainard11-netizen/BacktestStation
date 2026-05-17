"""Scheduled macro-event pre-release anchors.

This detector turns a curated economic-calendar CSV into research events.
It is deliberately pre-release only: actual/surprise values are never written
to event_data. Those belong in post-release outcomes or offline analysis.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from app.research.detectors import BarReader, DetectorContext, register
from app.research.macro_events import (
    DEFAULT_MACRO_EVENTS_PATH,
    MacroEvent,
    filter_macro_events,
    parse_macro_events_csv,
)
from app.research.macro_taxonomy import classify_macro_event
from app.schemas.research_events import ResearchEventCreate

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
log = logging.getLogger(__name__)

DEFAULT_WINDOWS_MIN = (5, 15, 60)


class MacroEventAnchorDetector:
    feature_name: str = "macro_event_anchor"
    detector_version: str = "v1"
    supported_modes: tuple[str, ...] = ("pre_release",)

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        if ctx.mode != "pre_release":
            raise ValueError("macro_event_anchor requires --mode pre_release")
        if not ctx.symbols:
            raise ValueError("macro_event_anchor requires at least one symbol")

        events_path = Path(str(ctx.params.get("events_path") or DEFAULT_MACRO_EVENTS_PATH))
        currencies = _csv_set(ctx.params.get("currencies", "USD"), upper=True)
        impacts = _csv_set(ctx.params.get("impacts", "high,medium"), upper=False)
        event_groups = _csv_set(ctx.params.get("event_groups", ""), upper=False)
        known_buffer_min = int(ctx.params.get("known_buffer_min", 1))
        pre_context_min = int(ctx.params.get("pre_context_min", 60))
        require_bars = _bool_param(ctx.params.get("require_bars", True))

        macro_events = filter_macro_events(
            parse_macro_events_csv(events_path),
            start=ctx.start,
            end=ctx.end,
            currencies=currencies or None,
            impacts=impacts or None,
            event_groups=event_groups or None,
        )
        schedule_context = _schedule_context(macro_events)

        out: list[ResearchEventCreate] = []
        for event in macro_events:
            for symbol in ctx.symbols:
                payload = self._build_event(
                    ctx,
                    event=event,
                    symbol=symbol,
                    known_buffer_min=known_buffer_min,
                    pre_context_min=pre_context_min,
                    require_bars=require_bars,
                    schedule_context=schedule_context.get(event.event_id, {}),
                )
                if payload is not None:
                    out.append(payload)
        return out

    def _build_event(
        self,
        ctx: DetectorContext,
        *,
        event: MacroEvent,
        symbol: str,
        known_buffer_min: int,
        pre_context_min: int,
        require_bars: bool,
        schedule_context: dict[str, Any],
    ) -> ResearchEventCreate | None:
        release_ts = event.release_ts_utc.astimezone(UTC)
        known_ts = release_ts - timedelta(minutes=known_buffer_min)
        bars = _safe_load(
            ctx.bar_reader,
            symbol=symbol,
            timeframe="1m",
            start=known_ts - timedelta(minutes=pre_context_min + 5),
            end=release_ts + timedelta(minutes=1),
        )
        if bars is None or bars.empty:
            if require_bars:
                return None
            pre_context: dict[str, Any] = {}
        else:
            bars = _ensure_utc_index(bars).sort_index()
            pre_context = _pre_release_context(
                bars,
                known_ts=known_ts,
                windows_min=DEFAULT_WINDOWS_MIN,
            )

        event_type = f"pre_{event.event_group}"
        release_et = release_ts.astimezone(ET)
        taxonomy = classify_macro_event(
            event_group=event.event_group,
            event_name=event.event_name,
            impact=event.impact,
            release_ts_et=release_et,
        )
        event_data: dict[str, Any] = {
            "schema_version": 1,
            "detector_version": self.detector_version,
            "source_event_id": event.event_id,
            "event_name": event.event_name,
            "event_group": event.event_group,
            "country": event.country,
            "currency": event.currency,
            "impact": event.impact,
            "source": event.source,
            "release_ts_utc": release_ts.isoformat(),
            "release_ts_et": release_et.isoformat(),
            "known_ts_utc": known_ts.isoformat(),
            "minutes_until_release": float(known_buffer_min),
            "scheduled_hour_et": int(release_et.hour),
            "scheduled_minute_et": int(release_et.minute),
            "day_of_week_et": int(release_et.weekday()),
            "has_forecast": bool(event.has_forecast),
            "has_previous": bool(event.has_previous),
            "forecast_raw": event.forecast_raw,
            "previous_raw": event.previous_raw,
            "forecast_value": event.forecast_value,
            "previous_value": event.previous_value,
            **taxonomy.as_event_data(),
            **schedule_context,
            **pre_context,
        }
        context = {
            "macro_event_group": event.event_group,
            "macro_family": taxonomy.family,
            "macro_theme": taxonomy.theme,
            "macro_importance_tier": taxonomy.importance_tier,
            "macro_currency": event.currency,
            "macro_impact": event.impact,
            "known_ts_utc": known_ts.isoformat(),
            "release_ts_utc": release_ts.isoformat(),
        }
        return ResearchEventCreate(
            feature_name=self.feature_name,
            event_type=event_type,
            bar_end_utc=known_ts,
            primary_symbol=symbol,
            symbols=[symbol],
            timeframe="macro",
            side=event.impact,
            event_data=event_data,
            context=context,
            outcomes=None,
            replay_pointer={
                "primary_symbol": symbol,
                "ts_utc": release_ts.isoformat(),
                "known_ts_utc": known_ts.isoformat(),
                "source_event_id": event.event_id,
            },
            detector_version=self.detector_version,
        )


def _csv_set(value: Any, *, upper: bool) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, (list, tuple, set)):
        parts = [str(part) for part in value]
    else:
        parts = str(value).split(",")
    out: set[str] = set()
    for part in parts:
        item = part.strip()
        if not item:
            continue
        out.add(item.upper() if upper else item.lower())
    return out


def _schedule_context(events: list[MacroEvent]) -> dict[str, dict[str, Any]]:
    by_currency: dict[str, dict[datetime, list[MacroEvent]]] = defaultdict(lambda: defaultdict(list))
    for event in events:
        by_currency[event.currency.upper()][event.release_ts_utc].append(event)

    out: dict[str, dict[str, Any]] = {}
    for _currency, clusters in by_currency.items():
        release_times = sorted(clusters)
        for idx, release_ts in enumerate(release_times):
            cluster = sorted(clusters[release_ts], key=lambda item: item.event_group)
            groups = [event.event_group for event in cluster]
            impacts = [event.impact for event in cluster]
            previous_ts = release_times[idx - 1] if idx > 0 else None
            next_ts = release_times[idx + 1] if idx + 1 < len(release_times) else None
            payload = {
                "macro_same_ts_event_count": len(cluster),
                "macro_same_ts_high_impact_count": sum(1 for impact in impacts if impact == "high"),
                "macro_same_ts_medium_impact_count": sum(1 for impact in impacts if impact == "medium"),
                "macro_same_ts_event_groups": ",".join(groups),
                "macro_minutes_since_previous_release": (
                    (release_ts - previous_ts).total_seconds() / 60.0 if previous_ts else None
                ),
                "macro_minutes_until_next_release": (
                    (next_ts - release_ts).total_seconds() / 60.0 if next_ts else None
                ),
            }
            for event in cluster:
                out[event.event_id] = dict(payload)
    return out


def _bool_param(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def _pre_release_context(
    bars: pd.DataFrame,
    *,
    known_ts: datetime,
    windows_min: tuple[int, ...],
) -> dict[str, Any]:
    pre = bars[bars.index < known_ts]
    if pre.empty:
        return {}
    out: dict[str, Any] = {}
    reference_close = float(pre["close"].astype(float).iloc[-1])
    out["pre_release_reference_close"] = reference_close
    for minutes in windows_min:
        start = known_ts - timedelta(minutes=minutes)
        window = pre[pre.index >= start]
        prefix = f"pre_{minutes}m"
        if window.empty:
            out[f"{prefix}_n_bars"] = 0
            continue
        metrics = _window_metrics(window, reference_close=reference_close)
        for key, value in metrics.items():
            out[f"{prefix}_{key}"] = value
    return out


def _window_metrics(window: pd.DataFrame, *, reference_close: float) -> dict[str, Any]:
    opens = window["open"].astype(float)
    highs = window["high"].astype(float)
    lows = window["low"].astype(float)
    closes = window["close"].astype(float)
    high = float(highs.max())
    low = float(lows.min())
    close = float(closes.iloc[-1])
    range_pts = high - low
    return {
        "n_bars": int(len(window)),
        "open": float(opens.iloc[0]),
        "high": high,
        "low": low,
        "close": close,
        "range_pts": float(range_pts),
        "return_pts": float(close - float(opens.iloc[0])),
        "return_from_reference_pts": float(close - reference_close),
        "close_location": float((close - low) / range_pts) if range_pts > 0 else None,
    }


def _safe_load(
    bar_reader: BarReader,
    *,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> pd.DataFrame | None:
    try:
        # The warehouse reader is date-partition oriented. Read full dates,
        # then trim to the true intraday window here.
        df = bar_reader(
            symbol=symbol,
            timeframe=timeframe,
            start=start.date(),
            end=end.date() + timedelta(days=1),
        )
    except (FileNotFoundError, ValueError) as exc:
        log.info("macro_event_anchor: bar_reader missing %s %s: %s", symbol, timeframe, exc)
        return None
    if df is None or len(df) == 0:
        return None
    df = _ensure_utc_index(df).sort_index()
    return df[(df.index >= start) & (df.index < end)].copy()


def _ensure_utc_index(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.index, pd.DatetimeIndex):
        return df.tz_convert("UTC") if df.index.tz else df.tz_localize("UTC")
    if "ts_event" in df.columns:
        out = df.set_index("ts_event")
        return out.tz_convert("UTC") if out.index.tz else out.tz_localize("UTC")
    raise ValueError("bar frame has no usable timestamp")


register("macro_event_anchor", MacroEventAnchorDetector())
