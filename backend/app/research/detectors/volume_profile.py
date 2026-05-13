"""Volume profile + VWAP detector.

For each period (daily / weekly / asia / london / ny session), computes
both a volume-by-price histogram AND VWAP statistics:

  Volume profile:
    - POC (price with highest volume)
    - VAH / VAL (top/bottom of Value Area = contiguous 70% of volume around POC)
    - Top 5 HVN (highest-volume bins)
    - Top 5 LVN (lowest-volume bins inside period range, excludes range edges)
    - Profile shape: balanced_D / buying_P / selling_b
    - 50-bin distribution stored as `bins` (for downstream re-analysis)

  VWAP:
    - vwap = Σ(typical_price × volume) / Σ(volume)
    - σ-bands at ±1σ, ±2σ, ±3σ from VWAP
    - close_vs_vwap_pts and band-bucket flags

Detection: load 1m bars over the period; weight by `(open+high+low+close)/4`
typical price. Auto-binning: bin_width = period_range / 50.

bar_end_utc = period.start_utc
knowable_ts = period.end_utc  (computed by analyses)
side = "buying" | "selling" | "balanced" based on POC position in range
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
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


_MODE_CONFIG: dict[str, dict[str, Any]] = {
    "daily_volume_profile":   {"parent": "globex_day"},
    "weekly_volume_profile":  {"parent": "globex_week"},
    "asia_volume_profile":    {"parent": "session_asia"},
    "london_volume_profile":  {"parent": "session_london"},
    "ny_volume_profile":      {"parent": "session_ny"},
}

N_BINS: int = 50
VALUE_AREA_PCT: float = 0.70
TOP_HVN_LVN: int = 5


class VolumeProfileDetector:
    feature_name: str = "volume_profile"
    detector_version: str = "v1"
    supported_modes: tuple[str, ...] = tuple(_MODE_CONFIG.keys())

    def scan(self, ctx: DetectorContext) -> list[ResearchEventCreate]:
        if ctx.mode is None:
            raise ValueError(
                f"volume_profile requires --mode {{{ '|'.join(self.supported_modes) }}}"
            )
        if ctx.mode not in _MODE_CONFIG:
            raise ValueError(f"unsupported mode: {ctx.mode}")
        if not ctx.symbols:
            raise ValueError("volume_profile requires at least one symbol")
        events: list[ResearchEventCreate] = []
        for symbol in ctx.symbols:
            events.extend(self._scan_symbol(ctx, symbol))
        return events

    def _scan_symbol(
        self, ctx: DetectorContext, symbol: str,
    ) -> list[ResearchEventCreate]:
        events: list[ResearchEventCreate] = []
        for parent in _iter_parent_periods(ctx.start, ctx.end, ctx.mode):
            ev = self._scan_one_parent(ctx, symbol, parent)
            if ev is not None:
                events.append(ev)
        return events

    def _scan_one_parent(
        self, ctx: DetectorContext, symbol: str, parent: GlobexPeriod,
    ) -> ResearchEventCreate | None:
        bars = _safe_load(
            ctx.bar_reader,
            symbol=symbol, timeframe="1m",
            start=parent.start_utc,
            end=parent.end_utc + timedelta(days=1),
        )
        if bars is None or bars.empty:
            return None
        bars = _ensure_utc_index(bars)
        bars = bars[(bars.index >= parent.start_utc) & (bars.index < parent.end_utc)]
        if bars.empty or len(bars) < 5:
            return None

        period_high = float(bars["high"].max())
        period_low = float(bars["low"].min())
        period_open = float(bars["open"].iloc[0])
        period_close = float(bars["close"].iloc[-1])
        period_range = period_high - period_low
        if period_range <= 0:
            return None

        # Typical price weighting.
        typical = ((bars["open"] + bars["high"] + bars["low"] + bars["close"]) / 4.0).to_numpy()
        volume = bars["volume"].fillna(0).to_numpy()
        total_volume = float(volume.sum())
        if total_volume <= 0:
            return None

        # ---- Volume profile binning ----
        bin_width = period_range / N_BINS
        bin_edges = np.linspace(period_low, period_high, N_BINS + 1)
        bin_volumes, _ = np.histogram(typical, bins=bin_edges, weights=volume)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0

        poc_bin_idx = int(np.argmax(bin_volumes))
        poc_price = float(bin_centers[poc_bin_idx])
        poc_volume = float(bin_volumes[poc_bin_idx])

        # Value Area: expand from POC bin until 70% of total volume.
        vah_idx, val_idx = _value_area(bin_volumes, poc_bin_idx, total_volume, VALUE_AREA_PCT)
        vah_price = float(bin_edges[vah_idx + 1])  # top edge of VAH bin
        val_price = float(bin_edges[val_idx])      # bottom edge of VAL bin
        va_volume = float(bin_volumes[val_idx:vah_idx + 1].sum())

        # Top HVN and LVN.
        sorted_by_vol_desc = np.argsort(-bin_volumes)
        sorted_by_vol_asc = np.argsort(bin_volumes)
        top_hvn = [
            {"price": float(bin_centers[i]), "volume": float(bin_volumes[i]),
             "bin_idx": int(i)}
            for i in sorted_by_vol_desc[:TOP_HVN_LVN]
        ]
        top_lvn = [
            {"price": float(bin_centers[i]), "volume": float(bin_volumes[i]),
             "bin_idx": int(i)}
            for i in sorted_by_vol_asc[:TOP_HVN_LVN]
        ]

        # Profile shape based on POC position within range.
        poc_pct_in_range = (poc_price - period_low) / period_range
        if poc_pct_in_range >= 0.70:
            shape = "buying_P"
        elif poc_pct_in_range <= 0.30:
            shape = "selling_b"
        else:
            shape = "balanced_D"

        # ---- VWAP and SD bands ----
        vwap = float((typical * volume).sum() / total_volume)
        # Variance: Σ(volume × (typical - vwap)^2) / Σ(volume)
        var = float((volume * (typical - vwap) ** 2).sum() / total_volume)
        sd = math.sqrt(var) if var > 0 else 0.0
        vwap_1sd_high = vwap + sd
        vwap_1sd_low = vwap - sd
        vwap_2sd_high = vwap + 2 * sd
        vwap_2sd_low = vwap - 2 * sd
        vwap_3sd_high = vwap + 3 * sd
        vwap_3sd_low = vwap - 3 * sd

        close_vs_vwap_pts = period_close - vwap
        if sd > 0:
            close_vs_vwap_sd = close_vs_vwap_pts / sd
        else:
            close_vs_vwap_sd = 0.0

        if close_vs_vwap_sd >= 3:
            close_band = "above_3sd"
        elif close_vs_vwap_sd >= 2:
            close_band = "2sd_3sd_above"
        elif close_vs_vwap_sd >= 1:
            close_band = "1sd_2sd_above"
        elif close_vs_vwap_sd >= 0:
            close_band = "vwap_to_1sd_above"
        elif close_vs_vwap_sd >= -1:
            close_band = "vwap_to_1sd_below"
        elif close_vs_vwap_sd >= -2:
            close_band = "1sd_2sd_below"
        elif close_vs_vwap_sd >= -3:
            close_band = "2sd_3sd_below"
        else:
            close_band = "below_3sd"

        # Bin distribution (for downstream re-bucketing).
        bins_data = [
            {"price_lo": float(bin_edges[i]),
             "price_hi": float(bin_edges[i + 1]),
             "volume": float(bin_volumes[i])}
            for i in range(N_BINS)
        ]

        side = (
            "buying" if shape == "buying_P"
            else ("selling" if shape == "selling_b" else "balanced")
        )

        bar_end_utc = parent.start_utc
        et_ts = bar_end_utc.astimezone(ET)
        event_data: dict[str, Any] = {
            "schema_version": 1,
            "detector_version": self.detector_version,
            "mode": ctx.mode,
            "parent_period_label": parent.label,
            "parent_period_start_utc": parent.start_utc.isoformat(),
            "parent_period_end_utc": parent.end_utc.isoformat(),
            "period_open": period_open,
            "period_close": period_close,
            "period_high": period_high,
            "period_low": period_low,
            "period_range_pts": period_range,
            "total_volume": total_volume,
            "n_bars": int(len(bars)),
            # Volume profile
            "n_bins": N_BINS,
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
            # VWAP
            "vwap": vwap,
            "vwap_sd": sd,
            "vwap_1sd_high": vwap_1sd_high,
            "vwap_1sd_low": vwap_1sd_low,
            "vwap_2sd_high": vwap_2sd_high,
            "vwap_2sd_low": vwap_2sd_low,
            "vwap_3sd_high": vwap_3sd_high,
            "vwap_3sd_low": vwap_3sd_low,
            "close_vs_vwap_pts": float(close_vs_vwap_pts),
            "close_vs_vwap_sd": float(close_vs_vwap_sd),
            "close_band": close_band,
            "close_vs_poc_pts": float(period_close - poc_price),
            "close_above_vwap": period_close > vwap,
            "close_above_poc": period_close > poc_price,
            "close_in_value_area": val_price <= period_close <= vah_price,
        }
        context: dict[str, Any] = {
            "day_of_week_et": et_ts.weekday(),
            "hour_of_day_et": et_ts.hour,
            "parent_period_label": parent.label,
        }
        return ResearchEventCreate(
            feature_name=self.feature_name,
            event_type=ctx.mode,
            bar_end_utc=bar_end_utc,
            primary_symbol=symbol,
            symbols=[symbol],
            timeframe=_TF_LABEL[ctx.mode],
            side=side,
            event_data=event_data,
            context=context,
            outcomes=None,
            replay_pointer={
                "primary_symbol": symbol,
                "ts_utc": bar_end_utc.isoformat(),
                "poc_price": poc_price,
                "vwap": vwap,
            },
            detector_version=self.detector_version,
        )


_TF_LABEL: dict[str, str] = {
    "daily_volume_profile": "1D",
    "weekly_volume_profile": "1W",
    "asia_volume_profile": "ASIA",
    "london_volume_profile": "LONDON",
    "ny_volume_profile": "NY",
}


# ---------- value area expansion ----------


def _value_area(
    bin_volumes: np.ndarray,
    poc_idx: int,
    total_volume: float,
    target_pct: float,
) -> tuple[int, int]:
    """Classic VA expansion: start at POC, iteratively expand to the
    neighbor with higher volume until cumulative_volume >= target_pct.

    Returns (val_idx, vah_idx) inclusive bin indices.
    """
    val_idx = poc_idx
    vah_idx = poc_idx
    cumulative = bin_volumes[poc_idx]
    target = target_pct * total_volume
    while cumulative < target and (val_idx > 0 or vah_idx < len(bin_volumes) - 1):
        # Look at two candidates: one bin below val_idx, one above vah_idx.
        below = bin_volumes[val_idx - 1] if val_idx > 0 else -1
        above = bin_volumes[vah_idx + 1] if vah_idx < len(bin_volumes) - 1 else -1
        if below < 0 and above < 0:
            break
        if above >= below:
            vah_idx += 1
            cumulative += bin_volumes[vah_idx]
        else:
            val_idx -= 1
            cumulative += bin_volumes[val_idx]
    return val_idx, vah_idx


# ---------- parent iterators ----------


def _iter_parent_periods(start_d, end_d, mode: str):
    start_dt = datetime(start_d.year, start_d.month, start_d.day, tzinfo=UTC)
    end_dt = datetime(end_d.year, end_d.month, end_d.day, tzinfo=UTC) + timedelta(days=1)
    parent_type = _MODE_CONFIG[mode]["parent"]
    if parent_type == "globex_day":
        cur = globex_day_for(start_dt)
        while cur.start_utc < end_dt:
            yield cur
            cur = globex_day_for(cur.end_utc + timedelta(seconds=1))
    elif parent_type == "globex_week":
        cur = globex_week_for(start_dt)
        while cur.start_utc < end_dt:
            yield cur
            cur = globex_week_for(cur.end_utc + timedelta(seconds=1))
    elif parent_type.startswith("session_"):
        session_name = parent_type.split("_", 1)[1]
        cur_day = globex_day_for(start_dt)
        while cur_day.start_utc < end_dt:
            sess = session_for(cur_day.start_utc + timedelta(hours=1), session_name)
            if sess.end_utc > start_dt and sess.start_utc < end_dt:
                yield sess
            cur_day = globex_day_for(cur_day.end_utc + timedelta(seconds=1))
    else:
        raise ValueError(f"unknown parent type: {parent_type}")


# ---------- helpers ----------


def _safe_load(
    bar_reader: BarReader,
    *, symbol: str, timeframe: str, start: datetime, end: datetime,
) -> pd.DataFrame | None:
    try:
        df = bar_reader(symbol=symbol, timeframe=timeframe, start=start, end=end)
    except (FileNotFoundError, ValueError) as exc:
        log.info("volume_profile: bar_reader missing %s %s: %s", symbol, timeframe, exc)
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


# ---------- registration ----------

register("volume_profile", VolumeProfileDetector())
