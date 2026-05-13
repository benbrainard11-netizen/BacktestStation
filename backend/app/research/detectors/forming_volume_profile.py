"""Live-style forming volume profile detector.

This is intentionally separate from `volume_profile`, which uses completed
daily/weekly/session profiles. A forming VP event is an as-of snapshot inside
the active Globex day. Its event_data only uses 1m bars with timestamps before
the snapshot cutoff.

Modes:
  - daily_vp_asof_1h: every hour after the Globex day has been open 1h
  - daily_vp_asof_4h: every 4h after the Globex day has been open 4h

The final Globex-day close is excluded because completed daily VP already
covers that state.
"""

from __future__ import annotations

import logging
import math
from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from app.research.detectors import BarReader, DetectorContext, register
from app.research.detectors.volume_profile import (
    N_BINS,
    TOP_HVN_LVN,
    VALUE_AREA_PCT,
    _ensure_utc_index,
    _safe_load,
    _value_area,
)
from app.research.sessions import GlobexPeriod, globex_day_for
from app.schemas.research_events import ResearchEventCreate

UTC = timezone.utc
ET = ZoneInfo("America/New_York")
log = logging.getLogger(__name__)


_MODE_CONFIG: dict[str, dict[str, Any]] = {
    "daily_vp_asof_1h": {"cadence_min": 60, "min_elapsed_min": 60, "tf": "ASOF_1H"},
    "daily_vp_asof_4h": {"cadence_min": 240, "min_elapsed_min": 240, "tf": "ASOF_4H"},
}


class FormingVolumeProfileDetector:
    feature_name: str = "forming_volume_profile"
    detector_version: str = "v1"
    supported_modes: tuple[str, ...] = tuple(_MODE_CONFIG.keys())

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        if ctx.mode is None:
            raise ValueError(
                f"forming_volume_profile requires --mode {{{ '|'.join(self.supported_modes) }}}"
            )
        if ctx.mode not in _MODE_CONFIG:
            raise ValueError(f"unsupported mode: {ctx.mode}")
        if not ctx.symbols:
            raise ValueError("forming_volume_profile requires at least one symbol")

        events: list[ResearchEventCreate] = []
        for symbol in ctx.symbols:
            events.extend(self._scan_symbol(ctx, symbol))
        return events

    def _scan_symbol(
        self,
        ctx: DetectorContext,
        symbol: str,
    ) -> list[ResearchEventCreate]:
        events: list[ResearchEventCreate] = []
        for parent in _iter_globex_days(ctx.start, ctx.end):
            events.extend(self._scan_one_parent(ctx, symbol, parent))
        return events

    def _scan_one_parent(
        self,
        ctx: DetectorContext,
        symbol: str,
        parent: GlobexPeriod,
    ) -> list[ResearchEventCreate]:
        cfg = _MODE_CONFIG[ctx.mode or ""]
        bars = _safe_load(
            ctx.bar_reader,
            symbol=symbol,
            timeframe="1m",
            start=parent.start_utc,
            end=parent.end_utc + timedelta(days=1),
        )
        if bars is None or bars.empty:
            return []

        bars = _ensure_utc_index(bars).sort_index()
        bars = bars[(bars.index >= parent.start_utc) & (bars.index < parent.end_utc)]
        if bars.empty:
            return []

        out: list[ResearchEventCreate] = []
        cadence = int(cfg["cadence_min"])
        min_elapsed = int(cfg["min_elapsed_min"])
        cutoff = parent.start_utc + timedelta(minutes=min_elapsed)
        while cutoff < parent.end_utc:
            snapshot_bars = bars[bars.index < cutoff]
            if len(snapshot_bars) >= 5:
                ev = self._build_event(
                    ctx=ctx,
                    symbol=symbol,
                    parent=parent,
                    asof_ts=cutoff,
                    bars=snapshot_bars,
                )
                if ev is not None:
                    out.append(ev)
            cutoff += timedelta(minutes=cadence)
        return out

    def _build_event(
        self,
        *,
        ctx: DetectorContext,
        symbol: str,
        parent: GlobexPeriod,
        asof_ts: datetime,
        bars: pd.DataFrame,
    ) -> ResearchEventCreate | None:
        profile = _compute_profile(bars)
        if profile is None:
            return None

        period_open = float(bars["open"].iloc[0])
        asof_close = float(bars["close"].iloc[-1])
        profile_high = float(bars["high"].max())
        profile_low = float(bars["low"].min())
        profile_range = profile_high - profile_low
        if profile_range <= 0:
            return None

        close_vs_vwap_pts = asof_close - profile["vwap"]
        close_vs_vwap_sd = (
            close_vs_vwap_pts / profile["vwap_sd"]
            if profile["vwap_sd"] > 0
            else 0.0
        )
        close_band = _close_band(close_vs_vwap_sd)
        side = (
            "buying"
            if profile["profile_shape"] == "buying_P"
            else ("selling" if profile["profile_shape"] == "selling_b" else "balanced")
        )

        elapsed_min = int((asof_ts - parent.start_utc).total_seconds() // 60)
        remaining_min = int((parent.end_utc - asof_ts).total_seconds() // 60)
        et_ts = asof_ts.astimezone(ET)
        cfg = _MODE_CONFIG[ctx.mode or ""]

        event_data: dict[str, Any] = {
            "schema_version": 1,
            "detector_version": self.detector_version,
            "mode": ctx.mode,
            "parent_period_label": parent.label,
            "parent_period_start_utc": parent.start_utc.isoformat(),
            "parent_period_end_utc": parent.end_utc.isoformat(),
            "asof_ts_utc": asof_ts.isoformat(),
            "cadence_min": int(cfg["cadence_min"]),
            "elapsed_min": elapsed_min,
            "remaining_min": remaining_min,
            "progress_pct": float(elapsed_min / max(elapsed_min + remaining_min, 1)),
            "period_open": period_open,
            "asof_close": asof_close,
            "profile_high_so_far": profile_high,
            "profile_low_so_far": profile_low,
            "profile_range_pts": profile_range,
            "total_volume_so_far": profile["total_volume"],
            "n_bars": int(len(bars)),
            "n_bins": N_BINS,
            "bin_width_pts": profile["bin_width_pts"],
            "bins": profile["bins"],
            "poc_price": profile["poc_price"],
            "poc_volume": profile["poc_volume"],
            "poc_bin_idx": profile["poc_bin_idx"],
            "poc_pct_in_range": profile["poc_pct_in_range"],
            "vah_price": profile["vah_price"],
            "val_price": profile["val_price"],
            "value_area_volume_pct": profile["value_area_volume_pct"],
            "value_area_range_pts": profile["value_area_range_pts"],
            "top_hvn": profile["top_hvn"],
            "top_lvn": profile["top_lvn"],
            "profile_shape": profile["profile_shape"],
            "vwap": profile["vwap"],
            "vwap_sd": profile["vwap_sd"],
            "vwap_1sd_high": profile["vwap_1sd_high"],
            "vwap_1sd_low": profile["vwap_1sd_low"],
            "vwap_2sd_high": profile["vwap_2sd_high"],
            "vwap_2sd_low": profile["vwap_2sd_low"],
            "vwap_3sd_high": profile["vwap_3sd_high"],
            "vwap_3sd_low": profile["vwap_3sd_low"],
            "close_vs_vwap_pts": float(close_vs_vwap_pts),
            "close_vs_vwap_sd": float(close_vs_vwap_sd),
            "close_band": close_band,
            "close_vs_poc_pts": float(asof_close - profile["poc_price"]),
            "close_above_vwap": asof_close > profile["vwap"],
            "close_above_poc": asof_close > profile["poc_price"],
            "close_in_value_area": profile["val_price"] <= asof_close <= profile["vah_price"],
        }
        context: dict[str, Any] = {
            "day_of_week_et": et_ts.weekday(),
            "hour_of_day_et": et_ts.hour,
            "parent_period_label": parent.label,
        }
        return ResearchEventCreate(
            feature_name=self.feature_name,
            event_type=ctx.mode or "",
            bar_end_utc=asof_ts,
            primary_symbol=symbol,
            symbols=[symbol],
            timeframe=str(cfg["tf"]),
            side=side,
            event_data=event_data,
            context=context,
            outcomes=None,
            replay_pointer={
                "primary_symbol": symbol,
                "ts_utc": asof_ts.isoformat(),
                "poc_price": profile["poc_price"],
                "vwap": profile["vwap"],
            },
            detector_version=self.detector_version,
        )


def _compute_profile(bars: pd.DataFrame) -> dict[str, Any] | None:
    profile_high = float(bars["high"].max())
    profile_low = float(bars["low"].min())
    profile_range = profile_high - profile_low
    if profile_range <= 0:
        return None

    typical = ((bars["open"] + bars["high"] + bars["low"] + bars["close"]) / 4.0).to_numpy()
    volume = bars["volume"].fillna(0).to_numpy()
    total_volume = float(volume.sum())
    if total_volume <= 0:
        return None

    bin_width = profile_range / N_BINS
    bin_edges = np.linspace(profile_low, profile_high, N_BINS + 1)
    bin_volumes, _ = np.histogram(typical, bins=bin_edges, weights=volume)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0

    poc_bin_idx = int(np.argmax(bin_volumes))
    poc_price = float(bin_centers[poc_bin_idx])
    poc_volume = float(bin_volumes[poc_bin_idx])
    vah_idx, val_idx = _value_area(bin_volumes, poc_bin_idx, total_volume, VALUE_AREA_PCT)
    vah_price = float(bin_edges[vah_idx + 1])
    val_price = float(bin_edges[val_idx])
    va_volume = float(bin_volumes[val_idx:vah_idx + 1].sum())

    sorted_by_vol_desc = np.argsort(-bin_volumes)
    sorted_by_vol_asc = np.argsort(bin_volumes)
    top_hvn = [
        {"price": float(bin_centers[i]), "volume": float(bin_volumes[i]), "bin_idx": int(i)}
        for i in sorted_by_vol_desc[:TOP_HVN_LVN]
    ]
    top_lvn = [
        {"price": float(bin_centers[i]), "volume": float(bin_volumes[i]), "bin_idx": int(i)}
        for i in sorted_by_vol_asc[:TOP_HVN_LVN]
    ]

    poc_pct_in_range = (poc_price - profile_low) / profile_range
    if poc_pct_in_range >= 0.70:
        shape = "buying_P"
    elif poc_pct_in_range <= 0.30:
        shape = "selling_b"
    else:
        shape = "balanced_D"

    vwap = float((typical * volume).sum() / total_volume)
    var = float((volume * (typical - vwap) ** 2).sum() / total_volume)
    sd = math.sqrt(var) if var > 0 else 0.0

    bins_data = [
        {"price_lo": float(bin_edges[i]), "price_hi": float(bin_edges[i + 1]), "volume": float(bin_volumes[i])}
        for i in range(N_BINS)
    ]
    return {
        "total_volume": total_volume,
        "bin_width_pts": float(bin_width),
        "bins": bins_data,
        "poc_price": poc_price,
        "poc_volume": poc_volume,
        "poc_bin_idx": poc_bin_idx,
        "poc_pct_in_range": float(poc_pct_in_range),
        "vah_price": vah_price,
        "val_price": val_price,
        "value_area_volume_pct": float(va_volume / total_volume),
        "value_area_range_pts": float(vah_price - val_price),
        "top_hvn": top_hvn,
        "top_lvn": top_lvn,
        "profile_shape": shape,
        "vwap": vwap,
        "vwap_sd": sd,
        "vwap_1sd_high": vwap + sd,
        "vwap_1sd_low": vwap - sd,
        "vwap_2sd_high": vwap + 2 * sd,
        "vwap_2sd_low": vwap - 2 * sd,
        "vwap_3sd_high": vwap + 3 * sd,
        "vwap_3sd_low": vwap - 3 * sd,
    }


def _close_band(close_vs_vwap_sd: float) -> str:
    if close_vs_vwap_sd >= 3:
        return "above_3sd"
    if close_vs_vwap_sd >= 2:
        return "2sd_3sd_above"
    if close_vs_vwap_sd >= 1:
        return "1sd_2sd_above"
    if close_vs_vwap_sd >= 0:
        return "vwap_to_1sd_above"
    if close_vs_vwap_sd >= -1:
        return "vwap_to_1sd_below"
    if close_vs_vwap_sd >= -2:
        return "1sd_2sd_below"
    if close_vs_vwap_sd >= -3:
        return "2sd_3sd_below"
    return "below_3sd"


def _iter_globex_days(start_d: date_type, end_d: date_type):
    start_dt = datetime(start_d.year, start_d.month, start_d.day, tzinfo=UTC)
    end_dt = datetime(end_d.year, end_d.month, end_d.day, tzinfo=UTC) + timedelta(days=1)
    cur = globex_day_for(start_dt)
    while cur.start_utc < end_dt:
        yield cur
        cur = globex_day_for(cur.end_utc + timedelta(seconds=1))


register("forming_volume_profile", FormingVolumeProfileDetector())
