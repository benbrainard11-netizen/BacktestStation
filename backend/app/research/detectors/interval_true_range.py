"""Interval true-range detector.

ITR is a completed-interval regime feature. Each event fires only after an
interval closes, so the interval's OHLC/range features are legal inputs for
predicting the next comparable interval.

Modes:
  - daily_itr: full Globex day
  - weekly_itr: full Globex week
  - asia_itr: Asia session inside each Globex day
  - london_itr: London session inside each Globex day
  - ny_itr: NY session inside each Globex day
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from statistics import mean, median
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from app.research.detectors import BarReader, DetectorContext, register
from app.research.sessions import (
    GlobexPeriod,
    globex_day_for,
    globex_week_for,
    session_for,
)
from app.schemas.research_events import ResearchEventCreate

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
log = logging.getLogger(__name__)

HISTORY_WINDOWS = (1, 3, 5, 10)


@dataclass(frozen=True, slots=True)
class ModeConfig:
    interval_kind: str
    timeframe: str
    session_name: str | None = None
    lookback_days: int = 30
    forward_days: int = 30


MODE_CONFIG: dict[str, ModeConfig] = {
    "daily_itr": ModeConfig("globex_day", "1D", lookback_days=30, forward_days=30),
    "weekly_itr": ModeConfig("globex_week", "1W", lookback_days=120, forward_days=45),
    "asia_itr": ModeConfig("session", "session", "asia", lookback_days=30, forward_days=30),
    "london_itr": ModeConfig("session", "session", "london", lookback_days=30, forward_days=30),
    "ny_itr": ModeConfig("session", "session", "ny", lookback_days=30, forward_days=30),
}


class IntervalTrueRangeDetector:
    feature_name: str = "interval_true_range"
    detector_version: str = "v1"
    supported_modes: tuple[str, ...] = tuple(MODE_CONFIG.keys())

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        if ctx.mode is None:
            raise ValueError(
                f"interval_true_range requires --mode {{{ '|'.join(self.supported_modes) }}}"
            )
        if ctx.mode not in MODE_CONFIG:
            raise ValueError(f"unsupported mode: {ctx.mode}")
        if not ctx.symbols:
            raise ValueError("interval_true_range requires at least one symbol")

        cfg = MODE_CONFIG[ctx.mode]
        events: list[ResearchEventCreate] = []
        for symbol in ctx.symbols:
            events.extend(self._scan_symbol(ctx, symbol, cfg))
        return events

    def _scan_symbol(
        self,
        ctx: DetectorContext,
        symbol: str,
        cfg: ModeConfig,
    ) -> list[ResearchEventCreate]:
        scan_start = _date_start(ctx.start)
        scan_end = _date_start(ctx.end) + timedelta(days=1)
        periods = list(
            _iter_periods(
                mode=ctx.mode or "",
                start=scan_start - timedelta(days=cfg.lookback_days),
                end=scan_end + timedelta(days=cfg.forward_days),
            )
        )
        if len(periods) < 2:
            return []

        bars = _safe_load(
            ctx.bar_reader,
            symbol=symbol,
            timeframe="1m",
            start=periods[0].start_utc,
            end=periods[-1].end_utc + timedelta(days=1),
        )
        if bars is None or bars.empty:
            return []
        bars = _ensure_utc_index(bars).sort_index()

        history: list[dict[str, Any]] = []
        events: list[ResearchEventCreate] = []
        for idx, period in enumerate(periods[:-1]):
            metrics = _period_metrics(bars, period)
            if metrics is None:
                continue

            bar_end_utc = metrics["bar_end_utc"]
            should_emit = scan_start <= bar_end_utc < scan_end
            if should_emit:
                event = self._build_event(
                    symbol=symbol,
                    mode=ctx.mode or "",
                    cfg=cfg,
                    period=period,
                    next_period=periods[idx + 1],
                    metrics=metrics,
                    history=history,
                )
                if event is not None:
                    events.append(event)
            history.append(metrics)
        return events

    def _build_event(
        self,
        *,
        symbol: str,
        mode: str,
        cfg: ModeConfig,
        period: GlobexPeriod,
        next_period: GlobexPeriod,
        metrics: dict[str, Any],
        history: list[dict[str, Any]],
    ) -> ResearchEventCreate | None:
        bar_end_utc: datetime = metrics["bar_end_utc"]
        prior = history[-1] if history else None
        rolling = _rolling_features(metrics, history)
        direction = metrics["direction"]

        prev_close = prior["close"] if prior else None
        true_range = _true_range(
            high=metrics["high"],
            low=metrics["low"],
            previous_close=prev_close,
        )
        gap_from_prev_close = (
            float(metrics["open"] - prev_close) if prev_close is not None else None
        )

        event_data: dict[str, Any] = {
            "schema_version": 1,
            "detector_version": self.detector_version,
            "mode": mode,
            "interval_kind": cfg.interval_kind,
            "session_name": cfg.session_name,
            "interval_start_utc": period.start_utc.isoformat(),
            "interval_end_utc": period.end_utc.isoformat(),
            "next_interval_start_utc": next_period.start_utc.isoformat(),
            "next_interval_end_utc": next_period.end_utc.isoformat(),
            "interval_open": metrics["open"],
            "interval_high": metrics["high"],
            "interval_low": metrics["low"],
            "interval_close": metrics["close"],
            "interval_mid": metrics["mid"],
            "interval_range_pts": metrics["range_pts"],
            "interval_body_pts": metrics["body_pts"],
            "interval_upper_wick_pts": metrics["upper_wick_pts"],
            "interval_lower_wick_pts": metrics["lower_wick_pts"],
            "interval_wick_share": metrics["wick_share"],
            "interval_body_share": metrics["body_share"],
            "interval_close_location": metrics["close_location"],
            "interval_direction": direction,
            "interval_return_pts": float(metrics["close"] - metrics["open"]),
            "interval_true_range_pts": true_range,
            "prev_close": prev_close,
            "gap_from_prev_close_pts": gap_from_prev_close,
            "abs_gap_from_prev_close_pts": (
                abs(gap_from_prev_close) if gap_from_prev_close is not None else None
            ),
            "n_1m_bars": metrics["n_bars"],
            "bar_end_utc": bar_end_utc.isoformat(),
            **_previous_interval_features(metrics, prior),
            **rolling,
        }

        et_ts = bar_end_utc.astimezone(ET)
        context: dict[str, Any] = {
            "day_of_week_et": et_ts.weekday(),
            "hour_of_day_et": et_ts.hour,
            "interval_kind": cfg.interval_kind,
            "session_name": cfg.session_name,
        }
        return ResearchEventCreate(
            feature_name=self.feature_name,
            event_type=mode,
            bar_end_utc=bar_end_utc,
            primary_symbol=symbol,
            symbols=[symbol],
            timeframe=cfg.timeframe,
            side=direction,
            event_data=event_data,
            context=context,
            outcomes=None,
            replay_pointer={
                "primary_symbol": symbol,
                "ts_utc": bar_end_utc.isoformat(),
                "interval_high": metrics["high"],
                "interval_low": metrics["low"],
                "interval_range_pts": metrics["range_pts"],
            },
            detector_version=self.detector_version,
        )


def _date_start(value: date_type) -> datetime:
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


def _iter_periods(*, mode: str, start: datetime, end: datetime):
    cfg = MODE_CONFIG[mode]
    if cfg.interval_kind == "globex_week":
        cur = globex_week_for(start)
        while cur.start_utc < end:
            yield cur
            cur = globex_week_for(cur.end_utc + timedelta(days=2, hours=2))
        return

    cur_day = globex_day_for(start)
    while cur_day.start_utc < end:
        if cfg.interval_kind == "globex_day":
            yield cur_day
        else:
            yield session_for(cur_day.start_utc + timedelta(hours=1), cfg.session_name or "")
        cur_day = globex_day_for(cur_day.end_utc + timedelta(hours=1))


def _safe_load(
    bar_reader: BarReader,
    *,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> pd.DataFrame | None:
    try:
        df = bar_reader(symbol=symbol, timeframe=timeframe, start=start, end=end)
    except (FileNotFoundError, ValueError) as exc:
        log.info("interval_true_range: missing bars %s %s: %s", symbol, timeframe, exc)
        return None
    if df is None or len(df) == 0:
        return None
    return df


def _ensure_utc_index(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.index, pd.DatetimeIndex):
        return df.tz_convert("UTC") if df.index.tz else df.tz_localize("UTC")
    if "ts_event" in df.columns:
        out = df.set_index("ts_event")
        return out.tz_convert("UTC") if out.index.tz else out.tz_localize("UTC")
    raise ValueError("bar frame has no usable timestamp")


def _ts_to_utc(ts: Any) -> datetime:
    if isinstance(ts, pd.Timestamp):
        ts = ts.to_pydatetime()
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _period_metrics(bars: pd.DataFrame, period: GlobexPeriod) -> dict[str, Any] | None:
    window = bars[(bars.index >= period.start_utc) & (bars.index < period.end_utc)]
    if window.empty or len(window) < 2:
        return None

    open_v = float(window["open"].iloc[0])
    high_v = float(window["high"].max())
    low_v = float(window["low"].min())
    close_v = float(window["close"].iloc[-1])
    range_pts = high_v - low_v
    if range_pts <= 0:
        return None

    body_pts = abs(close_v - open_v)
    upper_wick = max(0.0, high_v - max(open_v, close_v))
    lower_wick = max(0.0, min(open_v, close_v) - low_v)
    direction = "bullish" if close_v > open_v else ("bearish" if close_v < open_v else "doji")
    return {
        "period_start_utc": period.start_utc,
        "period_end_utc": period.end_utc,
        "bar_end_utc": _ts_to_utc(window.index[-1]),
        "open": open_v,
        "high": high_v,
        "low": low_v,
        "close": close_v,
        "mid": float((high_v + low_v) / 2.0),
        "range_pts": float(range_pts),
        "body_pts": float(body_pts),
        "upper_wick_pts": float(upper_wick),
        "lower_wick_pts": float(lower_wick),
        "wick_share": float((upper_wick + lower_wick) / range_pts),
        "body_share": float(body_pts / range_pts),
        "close_location": float((close_v - low_v) / range_pts),
        "direction": direction,
        "n_bars": int(len(window)),
    }


def _true_range(*, high: float, low: float, previous_close: float | None) -> float:
    if previous_close is None:
        return float(high - low)
    return float(max(high - low, abs(high - previous_close), abs(low - previous_close)))


def _previous_interval_features(
    metrics: dict[str, Any],
    prior: dict[str, Any] | None,
) -> dict[str, Any]:
    if prior is None:
        return {
            "prev_interval_high": None,
            "prev_interval_low": None,
            "prev_interval_mid": None,
            "prev_interval_range_pts": None,
            "range_vs_prev_interval": None,
            "range_delta_vs_prev_interval_pts": None,
            "took_prev_interval_high": None,
            "took_prev_interval_low": None,
            "closed_above_prev_interval_high": None,
            "closed_below_prev_interval_low": None,
            "closed_inside_prev_interval": None,
            "inside_prev_interval_range": None,
            "outside_prev_interval_range": None,
            "overlap_prev_interval_pct": None,
            "close_vs_prev_high_pts": None,
            "close_vs_prev_low_pts": None,
            "close_vs_prev_mid_pts": None,
        }

    cur_range = metrics["range_pts"]
    overlap = max(0.0, min(metrics["high"], prior["high"]) - max(metrics["low"], prior["low"]))
    inside = metrics["high"] <= prior["high"] and metrics["low"] >= prior["low"]
    outside = metrics["high"] >= prior["high"] and metrics["low"] <= prior["low"]
    return {
        "prev_interval_high": prior["high"],
        "prev_interval_low": prior["low"],
        "prev_interval_mid": prior["mid"],
        "prev_interval_range_pts": prior["range_pts"],
        "range_vs_prev_interval": _safe_ratio(cur_range, prior["range_pts"]),
        "range_delta_vs_prev_interval_pts": float(cur_range - prior["range_pts"]),
        "took_prev_interval_high": metrics["high"] > prior["high"],
        "took_prev_interval_low": metrics["low"] < prior["low"],
        "closed_above_prev_interval_high": metrics["close"] > prior["high"],
        "closed_below_prev_interval_low": metrics["close"] < prior["low"],
        "closed_inside_prev_interval": prior["low"] <= metrics["close"] <= prior["high"],
        "inside_prev_interval_range": inside,
        "outside_prev_interval_range": outside,
        "overlap_prev_interval_pct": float(overlap / cur_range) if cur_range > 0 else None,
        "close_vs_prev_high_pts": float(metrics["close"] - prior["high"]),
        "close_vs_prev_low_pts": float(metrics["close"] - prior["low"]),
        "close_vs_prev_mid_pts": float(metrics["close"] - prior["mid"]),
    }


def _rolling_features(
    metrics: dict[str, Any],
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    current_range = float(metrics["range_pts"])
    for n in HISTORY_WINDOWS:
        prior = history[-n:]
        ranges = [float(item["range_pts"]) for item in prior]
        stem = f"prev_{n}_interval"
        if not ranges:
            out[f"{stem}_avg_range_pts"] = None
            out[f"{stem}_median_range_pts"] = None
            out[f"{stem}_max_range_pts"] = None
            out[f"{stem}_min_range_pts"] = None
            out[f"range_vs_{stem}_avg"] = None
            out[f"range_percentile_vs_{stem}s"] = None
            out[f"is_expansion_vs_{stem}s"] = None
            out[f"is_compression_vs_{stem}s"] = None
            continue
        avg_range = float(mean(ranges))
        out[f"{stem}_avg_range_pts"] = avg_range
        out[f"{stem}_median_range_pts"] = float(median(ranges))
        out[f"{stem}_max_range_pts"] = float(max(ranges))
        out[f"{stem}_min_range_pts"] = float(min(ranges))
        out[f"range_vs_{stem}_avg"] = _safe_ratio(current_range, avg_range)
        out[f"range_percentile_vs_{stem}s"] = float(
            sum(1 for value in ranges if value <= current_range) / len(ranges)
        )
        out[f"is_expansion_vs_{stem}s"] = current_range > 1.25 * avg_range
        out[f"is_compression_vs_{stem}s"] = current_range < 0.75 * avg_range
    return out


def _safe_ratio(num: float, den: float | None) -> float | None:
    if den is None or den == 0:
        return None
    return float(num / den)


register("interval_true_range", IntervalTrueRangeDetector())
