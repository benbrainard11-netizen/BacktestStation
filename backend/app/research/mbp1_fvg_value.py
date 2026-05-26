"""MBP-1 assisted FVG value study.

This module answers a research question, not an execution question:

    Which Fair Value Gaps tend to behave like support/resistance when
    price retests them, and what did the top of book look like around
    that retest?

The labels are intentionally bar-based. MBP-1 features are computed only
around the first retest so they can be tested as explanatory/predictive
features without leaking future outcome data.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from typing import Literal

import pandas as pd

Direction = Literal["bullish", "bearish"]
FvgOutcome = Literal["hold", "fail", "neutral", "ambiguous"]
Role = Literal["support", "resistance"]


@dataclass(frozen=True)
class FvgZone:
    """One classic 3-candle Fair Value Gap zone."""

    symbol: str
    timeframe: str
    direction: Direction
    formed_ts: dt.datetime
    fvg_low: float
    fvg_high: float
    c1_ts: dt.datetime
    c3_ts: dt.datetime
    c3_close: float

    @property
    def width_pts(self) -> float:
        return self.fvg_high - self.fvg_low

    @property
    def mid(self) -> float:
        return (self.fvg_high + self.fvg_low) / 2.0

    @property
    def role(self) -> Role:
        return "support" if self.direction == "bullish" else "resistance"

    @property
    def near_edge(self) -> float:
        return self.fvg_high if self.direction == "bullish" else self.fvg_low

    @property
    def far_edge(self) -> float:
        return self.fvg_low if self.direction == "bullish" else self.fvg_high


@dataclass(frozen=True)
class FvgRetest:
    """First bar that overlaps the FVG after formation."""

    zone: FvgZone
    touch_ts: dt.datetime
    touch_index: int
    bars_after_formation: int
    open: float
    high: float
    low: float
    close: float
    touch_depth_frac: float


@dataclass(frozen=True)
class FvgHoldLabel:
    """Support/resistance outcome after first retest."""

    outcome: FvgOutcome
    role: Role
    held: bool
    failed: bool
    reason: str
    first_touch_ts: dt.datetime
    decisive_ts: dt.datetime | None
    horizon_bars: int
    target_pts: float
    failure_buffer_pts: float
    max_favorable_pts: float
    max_adverse_pts: float
    favorable_r: float | None
    adverse_r: float | None


def detect_fvg_zones(
    bars: pd.DataFrame,
    *,
    symbol: str,
    timeframe: str,
    min_width_pts: float = 0.0,
) -> list[FvgZone]:
    """Detect classic 3-candle FVGs from OHLC bars.

    Bullish: candle 1 high < candle 3 low.
    Bearish: candle 1 low > candle 3 high.
    """

    df = _normalize_ohlc_bars(bars)
    if len(df) < 3:
        return []

    zones: list[FvgZone] = []
    highs = pd.to_numeric(df["high"], errors="coerce").to_numpy()
    lows = pd.to_numeric(df["low"], errors="coerce").to_numpy()
    closes = pd.to_numeric(df["close"], errors="coerce").to_numpy()
    idx = df.index

    for i in range(2, len(df)):
        c1_high = float(highs[i - 2])
        c1_low = float(lows[i - 2])
        c3_high = float(highs[i])
        c3_low = float(lows[i])
        if not all(map(math.isfinite, (c1_high, c1_low, c3_high, c3_low))):
            continue

        if c1_high < c3_low:
            direction: Direction = "bullish"
            fvg_low = c1_high
            fvg_high = c3_low
        elif c1_low > c3_high:
            direction = "bearish"
            fvg_low = c3_high
            fvg_high = c1_low
        else:
            continue

        width = fvg_high - fvg_low
        if width <= min_width_pts:
            continue

        c3_ts = _to_utc_datetime(idx[i])
        zones.append(
            FvgZone(
                symbol=symbol,
                timeframe=timeframe,
                direction=direction,
                formed_ts=c3_ts,
                fvg_low=float(fvg_low),
                fvg_high=float(fvg_high),
                c1_ts=_to_utc_datetime(idx[i - 2]),
                c3_ts=c3_ts,
                c3_close=float(closes[i]),
            )
        )
    return zones


def find_first_retest(
    bars: pd.DataFrame,
    zone: FvgZone,
    *,
    max_bars_after_formation: int | None = None,
) -> FvgRetest | None:
    """Return the first later bar whose range overlaps the FVG zone."""

    df = _normalize_ohlc_bars(bars)
    future = df.loc[df.index > pd.Timestamp(zone.formed_ts)]
    if max_bars_after_formation is not None:
        future = future.iloc[:max_bars_after_formation]

    for bars_after, (ts, row) in enumerate(future.iterrows(), start=1):
        high = float(row["high"])
        low = float(row["low"])
        if not _bar_overlaps_zone(high=high, low=low, zone=zone):
            continue

        touch_index = int(df.index.get_indexer([ts])[0])
        return FvgRetest(
            zone=zone,
            touch_ts=_to_utc_datetime(ts),
            touch_index=touch_index,
            bars_after_formation=bars_after,
            open=float(row["open"]),
            high=high,
            low=low,
            close=float(row["close"]),
            touch_depth_frac=_touch_depth_frac(high=high, low=low, zone=zone),
        )
    return None


def label_retest_hold(
    bars: pd.DataFrame,
    retest: FvgRetest,
    *,
    horizon_bars: int = 20,
    reaction_multiple: float = 1.0,
    min_reaction_pts: float = 0.0,
    failure_buffer_pts: float = 0.0,
) -> FvgHoldLabel:
    """Label whether the FVG held after first retest.

    A bullish FVG "holds" when price first moves away above the near
    edge by the target distance before any close through the far edge.
    A bearish FVG is the mirror image. If both happen inside the same
    bar, the label is ambiguous because bar OHLC cannot prove sequence.
    """

    if horizon_bars < 1:
        raise ValueError("horizon_bars must be >= 1")
    if reaction_multiple < 0:
        raise ValueError("reaction_multiple must be >= 0")
    if min_reaction_pts < 0:
        raise ValueError("min_reaction_pts must be >= 0")
    if failure_buffer_pts < 0:
        raise ValueError("failure_buffer_pts must be >= 0")

    zone = retest.zone
    if zone.width_pts <= 0:
        raise ValueError("FVG width must be positive")

    df = _normalize_ohlc_bars(bars)
    window = df.loc[df.index >= pd.Timestamp(retest.touch_ts)].iloc[:horizon_bars]
    if window.empty:
        return _empty_label(retest, horizon_bars=0)

    highs = pd.to_numeric(window["high"], errors="coerce")
    lows = pd.to_numeric(window["low"], errors="coerce")
    if zone.direction == "bullish":
        max_favorable = max(0.0, float(highs.max()) - zone.fvg_high)
        max_adverse = max(0.0, zone.fvg_low - float(lows.min()))
    else:
        max_favorable = max(0.0, zone.fvg_low - float(lows.min()))
        max_adverse = max(0.0, float(highs.max()) - zone.fvg_high)

    target_pts = max(zone.width_pts * reaction_multiple, min_reaction_pts)
    target_pts = float(target_pts)
    max_favorable = float(max_favorable)
    max_adverse = float(max_adverse)
    favorable_r = max_favorable / zone.width_pts
    adverse_r = max_adverse / zone.width_pts

    for ts, row in window.iterrows():
        high = float(row["high"])
        low = float(row["low"])
        close = float(row["close"])
        reaction = _reaction_reached(
            high=high, low=low, zone=zone, target_pts=target_pts,
        )
        failure = _close_through_far_edge(
            close=close, zone=zone, failure_buffer_pts=failure_buffer_pts,
        )

        if reaction and failure:
            return FvgHoldLabel(
                outcome="ambiguous",
                role=zone.role,
                held=False,
                failed=False,
                reason="reaction target and close-through occurred in the same bar",
                first_touch_ts=retest.touch_ts,
                decisive_ts=_to_utc_datetime(ts),
                horizon_bars=int(len(window)),
                target_pts=target_pts,
                failure_buffer_pts=failure_buffer_pts,
                max_favorable_pts=max_favorable,
                max_adverse_pts=max_adverse,
                favorable_r=float(favorable_r),
                adverse_r=float(adverse_r),
            )
        if reaction:
            return FvgHoldLabel(
                outcome="hold",
                role=zone.role,
                held=True,
                failed=False,
                reason="reaction target reached before close-through",
                first_touch_ts=retest.touch_ts,
                decisive_ts=_to_utc_datetime(ts),
                horizon_bars=int(len(window)),
                target_pts=target_pts,
                failure_buffer_pts=failure_buffer_pts,
                max_favorable_pts=max_favorable,
                max_adverse_pts=max_adverse,
                favorable_r=float(favorable_r),
                adverse_r=float(adverse_r),
            )
        if failure:
            return FvgHoldLabel(
                outcome="fail",
                role=zone.role,
                held=False,
                failed=True,
                reason="closed through far edge before reaction target",
                first_touch_ts=retest.touch_ts,
                decisive_ts=_to_utc_datetime(ts),
                horizon_bars=int(len(window)),
                target_pts=target_pts,
                failure_buffer_pts=failure_buffer_pts,
                max_favorable_pts=max_favorable,
                max_adverse_pts=max_adverse,
                favorable_r=float(favorable_r),
                adverse_r=float(adverse_r),
            )

    return FvgHoldLabel(
        outcome="neutral",
        role=zone.role,
        held=False,
        failed=False,
        reason="no reaction target or close-through within horizon",
        first_touch_ts=retest.touch_ts,
        decisive_ts=None,
        horizon_bars=int(len(window)),
        target_pts=target_pts,
        failure_buffer_pts=failure_buffer_pts,
        max_favorable_pts=max_favorable,
        max_adverse_pts=max_adverse,
        favorable_r=float(favorable_r),
        adverse_r=float(adverse_r),
    )


def compute_mbp1_retest_features(
    mbp1: pd.DataFrame,
    retest: FvgRetest,
    *,
    pre_seconds: int = 30,
    post_seconds: int = 30,
    tick_size: float = 0.25,
) -> dict[str, float | int | None]:
    """Compute top-of-book features around the first FVG retest."""

    if pre_seconds < 1:
        raise ValueError("pre_seconds must be >= 1")
    if post_seconds < 1:
        raise ValueError("post_seconds must be >= 1")
    if tick_size <= 0:
        raise ValueError("tick_size must be > 0")

    zone = retest.zone
    df = _normalize_mbp1(mbp1)
    touch_ts = pd.Timestamp(retest.touch_ts)
    pre_start = touch_ts - pd.Timedelta(seconds=pre_seconds)
    post_end = touch_ts + pd.Timedelta(seconds=post_seconds)

    pre = _with_quote_features(
        df.loc[(df.index >= pre_start) & (df.index < touch_ts)],
        direction=zone.direction,
    )
    post = _with_quote_features(
        df.loc[(df.index >= touch_ts) & (df.index <= post_end)],
        direction=zone.direction,
    )

    touch_row = post.iloc[0] if not post.empty else None
    touch_mid = _row_float(touch_row, "mid_px")

    if not post.empty and touch_mid is not None:
        if zone.direction == "bullish":
            micro_favorable = max(0.0, float(post["mid_px"].max()) - touch_mid)
            micro_adverse = max(0.0, touch_mid - float(post["mid_px"].min()))
            far_cross_count = int((post["bid_px"] < zone.fvg_low).sum())
            near_touch_count = int((post["bid_px"] <= zone.fvg_high).sum())
        else:
            micro_favorable = max(0.0, touch_mid - float(post["mid_px"].min()))
            micro_adverse = max(0.0, float(post["mid_px"].max()) - touch_mid)
            far_cross_count = int((post["ask_px"] > zone.fvg_high).sum())
            near_touch_count = int((post["ask_px"] >= zone.fvg_low).sum())
        final_mid_move = (
            float(post["mid_px"].iloc[-1]) - touch_mid
            if zone.direction == "bullish"
            else touch_mid - float(post["mid_px"].iloc[-1])
        )
    else:
        micro_favorable = None
        micro_adverse = None
        final_mid_move = None
        far_cross_count = 0
        near_touch_count = 0

    inside_zone_fraction = (
        _mean(((post["mid_px"] >= zone.fvg_low) & (post["mid_px"] <= zone.fvg_high)).astype(float))
        if not post.empty
        else None
    )

    pre_aligned_size = _mean(pre["aligned_sz"]) if not pre.empty else None
    post_aligned_size = _mean(post["aligned_sz"]) if not post.empty else None
    pre_opposing_size = _mean(pre["opposing_sz"]) if not pre.empty else None
    post_opposing_size = _mean(post["opposing_sz"]) if not post.empty else None
    pre_aligned_imb = _mean(pre["aligned_imbalance"]) if not pre.empty else None
    post_aligned_imb = _mean(post["aligned_imbalance"]) if not post.empty else None

    out: dict[str, float | int | None] = {
        "mbp.pre_seconds": pre_seconds,
        "mbp.post_seconds": post_seconds,
        "mbp.pre_event_count": int(len(pre)),
        "mbp.post_event_count": int(len(post)),
        "mbp.pre_events_per_second": float(len(pre) / pre_seconds),
        "mbp.post_events_per_second": float(len(post) / post_seconds),
        "mbp.touch_mid": touch_mid,
        "mbp.touch_spread_ticks": _divide(_row_float(touch_row, "spread"), tick_size),
        "mbp.pre_mean_spread_ticks": _divide(
            _mean(pre["spread"]) if not pre.empty else None,
            tick_size,
        ),
        "mbp.post_mean_spread_ticks": _divide(
            _mean(post["spread"]) if not post.empty else None,
            tick_size,
        ),
        "mbp.post_max_spread_ticks": _divide(
            _max(post["spread"]) if not post.empty else None,
            tick_size,
        ),
        "mbp.pre_mean_imbalance": _mean(pre["imbalance"]) if not pre.empty else None,
        "mbp.post_mean_imbalance": _mean(post["imbalance"]) if not post.empty else None,
        "mbp.pre_mean_aligned_imbalance": pre_aligned_imb,
        "mbp.post_mean_aligned_imbalance": post_aligned_imb,
        "mbp.aligned_imbalance_change": _diff(post_aligned_imb, pre_aligned_imb),
        "mbp.pre_mean_aligned_size": pre_aligned_size,
        "mbp.post_mean_aligned_size": post_aligned_size,
        "mbp.aligned_size_change_frac": _change_frac(post_aligned_size, pre_aligned_size),
        "mbp.pre_mean_opposing_size": pre_opposing_size,
        "mbp.post_mean_opposing_size": post_opposing_size,
        "mbp.opposing_size_change_frac": _change_frac(post_opposing_size, pre_opposing_size),
        "mbp.post_micro_favorable_pts": micro_favorable,
        "mbp.post_micro_adverse_pts": micro_adverse,
        "mbp.post_micro_final_move_pts": final_mid_move,
        "mbp.post_micro_favorable_to_adverse": _ratio(micro_favorable, micro_adverse),
        "mbp.post_far_edge_cross_count": far_cross_count,
        "mbp.post_near_edge_touch_count": near_touch_count,
        "mbp.post_inside_zone_fraction": inside_zone_fraction,
    }
    out.update(_raw_event_features(post))
    return out


def build_fvg_value_study(
    *,
    bars: pd.DataFrame,
    mbp1: pd.DataFrame,
    symbol: str,
    timeframe: str,
    min_width_pts: float = 0.0,
    max_zones: int | None = None,
    max_bars_after_formation: int | None = None,
    horizon_bars: int = 20,
    reaction_multiple: float = 1.0,
    min_reaction_pts: float = 0.0,
    failure_buffer_pts: float = 0.0,
    pre_seconds: int = 30,
    post_seconds: int = 30,
    tick_size: float = 0.25,
    include_neutral: bool = True,
) -> pd.DataFrame:
    """Build one row per touched FVG with label columns and MBP features."""

    bars_norm = _normalize_ohlc_bars(bars)
    mbp1_norm = _normalize_mbp1(mbp1)
    zones = detect_fvg_zones(
        bars_norm,
        symbol=symbol,
        timeframe=timeframe,
        min_width_pts=min_width_pts,
    )
    if max_zones is not None:
        zones = zones[:max_zones]

    rows: list[dict[str, object]] = []
    for zone in zones:
        retest = find_first_retest(
            bars_norm,
            zone,
            max_bars_after_formation=max_bars_after_formation,
        )
        if retest is None:
            continue
        label = label_retest_hold(
            bars_norm,
            retest,
            horizon_bars=horizon_bars,
            reaction_multiple=reaction_multiple,
            min_reaction_pts=min_reaction_pts,
            failure_buffer_pts=failure_buffer_pts,
        )
        if label.outcome == "neutral" and not include_neutral:
            continue
        features = compute_mbp1_retest_features(
            mbp1_norm,
            retest,
            pre_seconds=pre_seconds,
            post_seconds=post_seconds,
            tick_size=tick_size,
        )
        rows.append(_study_row(zone, retest, label, features))

    return pd.DataFrame(rows)


def summarize_outcomes(study: pd.DataFrame) -> dict[str, object]:
    """Compact summary for CLI output and notebooks."""

    if study.empty:
        return {"rows": 0, "outcomes": {}}
    counts = study["outcome"].value_counts(dropna=False).to_dict()
    total = int(len(study))
    return {
        "rows": total,
        "outcomes": {str(k): int(v) for k, v in counts.items()},
        "hold_rate": float((study["outcome"] == "hold").mean()),
        "fail_rate": float((study["outcome"] == "fail").mean()),
    }


def rank_mbp1_feature_edges(
    study: pd.DataFrame,
    *,
    min_count_per_side: int = 5,
) -> pd.DataFrame:
    """Compare MBP feature means for held vs failed FVGs.

    This is descriptive, not a model. A good feature here is a candidate
    for a later walk-forward test, not a proven edge by itself.
    """

    if study.empty or "outcome" not in study.columns:
        return pd.DataFrame()
    sample = study.loc[study["outcome"].isin(["hold", "fail"])].copy()
    if sample.empty:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    feature_cols = [c for c in sample.columns if c.startswith("mbp.")]
    for col in feature_cols:
        values = pd.to_numeric(sample[col], errors="coerce")
        hold = values.loc[sample["outcome"] == "hold"].dropna()
        fail = values.loc[sample["outcome"] == "fail"].dropna()
        if len(hold) < min_count_per_side or len(fail) < min_count_per_side:
            continue
        hold_mean = float(hold.mean())
        fail_mean = float(fail.mean())
        diff = hold_mean - fail_mean
        pooled = _pooled_std(float(hold.std()), float(fail.std()))
        rows.append(
            {
                "feature": col,
                "hold_count": int(len(hold)),
                "fail_count": int(len(fail)),
                "hold_mean": hold_mean,
                "fail_mean": fail_mean,
                "hold_minus_fail": float(diff),
                "standardized_diff": _divide(diff, pooled),
            }
        )

    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out["_rank"] = out["standardized_diff"].abs().fillna(0.0)
    out = out.sort_values(
        ["_rank", "hold_minus_fail"], ascending=[False, False],
    )
    return out.drop(columns=["_rank"]).reset_index(drop=True)


def _study_row(
    zone: FvgZone,
    retest: FvgRetest,
    label: FvgHoldLabel,
    features: dict[str, float | int | None],
) -> dict[str, object]:
    row: dict[str, object] = {
        "symbol": zone.symbol,
        "timeframe": zone.timeframe,
        "direction": zone.direction,
        "role": zone.role,
        "formed_ts": zone.formed_ts,
        "touch_ts": retest.touch_ts,
        "bars_to_touch": retest.bars_after_formation,
        "fvg_low": zone.fvg_low,
        "fvg_high": zone.fvg_high,
        "fvg_mid": zone.mid,
        "fvg_width_pts": zone.width_pts,
        "touch_depth_frac": retest.touch_depth_frac,
        "outcome": label.outcome,
        "held": label.held,
        "failed": label.failed,
        "label_reason": label.reason,
        "decisive_ts": label.decisive_ts,
        "horizon_bars": label.horizon_bars,
        "target_pts": label.target_pts,
        "failure_buffer_pts": label.failure_buffer_pts,
        "max_favorable_pts": label.max_favorable_pts,
        "max_adverse_pts": label.max_adverse_pts,
        "favorable_r": label.favorable_r,
        "adverse_r": label.adverse_r,
    }
    row.update(features)
    return row


def _normalize_ohlc_bars(df: pd.DataFrame) -> pd.DataFrame:
    out = _normalize_time_index(df, frame_name="bars")
    required = {"open", "high", "low", "close"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"bars missing required columns: {sorted(missing)}")
    return out


def _normalize_mbp1(df: pd.DataFrame) -> pd.DataFrame:
    out = _normalize_time_index(df, frame_name="mbp1")
    required = {"bid_px", "ask_px", "bid_sz", "ask_sz"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"mbp1 missing required columns: {sorted(missing)}")
    return out


def _normalize_time_index(df: pd.DataFrame, *, frame_name: str) -> pd.DataFrame:
    if df is None:
        raise ValueError(f"{frame_name} frame is None")
    out = df.copy(deep=False)
    if isinstance(out.index, pd.DatetimeIndex):
        idx = pd.to_datetime(out.index, utc=True)
    elif "ts_event" in out.columns:
        idx = pd.to_datetime(out["ts_event"], utc=True)
        out = out.set_index(pd.DatetimeIndex(idx))
    else:
        raise ValueError(f"{frame_name} frame needs a DatetimeIndex or ts_event column")
    out.index = pd.DatetimeIndex(idx)
    out = out.loc[~out.index.isna()]
    return out.sort_index()


def _with_quote_features(df: pd.DataFrame, *, direction: Direction) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    out = df.copy(deep=False)
    for col in ("bid_px", "ask_px", "bid_sz", "ask_sz"):
        out[col] = pd.to_numeric(out[col], errors="coerce").astype("float64")
    out = out.loc[
        out["bid_px"].gt(0)
        & out["ask_px"].gt(0)
        & out["ask_px"].ge(out["bid_px"])
        & out["bid_sz"].ge(0)
        & out["ask_sz"].ge(0)
    ].copy()
    if out.empty:
        return out

    out["mid_px"] = (out["bid_px"] + out["ask_px"]) / 2.0
    out["spread"] = out["ask_px"] - out["bid_px"]
    total_size = out["bid_sz"] + out["ask_sz"]
    out["imbalance"] = (out["bid_sz"] - out["ask_sz"]) / total_size.where(total_size > 0)
    if direction == "bullish":
        out["aligned_imbalance"] = out["imbalance"]
        out["aligned_sz"] = out["bid_sz"]
        out["opposing_sz"] = out["ask_sz"]
    else:
        out["aligned_imbalance"] = -out["imbalance"]
        out["aligned_sz"] = out["ask_sz"]
        out["opposing_sz"] = out["bid_sz"]
    return out


def _raw_event_features(post: pd.DataFrame) -> dict[str, float | int | None]:
    out: dict[str, float | int | None] = {
        "mbp.post_trade_event_count": 0,
        "mbp.post_trade_size_sum": 0.0,
        "mbp.post_event_side_a_count": 0,
        "mbp.post_event_side_b_count": 0,
    }
    if post.empty:
        return out

    if "action" in post.columns:
        actions = post["action"].astype(str).str.upper()
        trade_mask = actions.eq("T")
        out["mbp.post_trade_event_count"] = int(trade_mask.sum())
        if "size" in post.columns:
            sizes = pd.to_numeric(post["size"], errors="coerce").fillna(0.0)
            out["mbp.post_trade_size_sum"] = float(sizes.loc[trade_mask].sum())
    if "side" in post.columns:
        sides = post["side"].astype(str).str.upper()
        out["mbp.post_event_side_a_count"] = int(sides.eq("A").sum())
        out["mbp.post_event_side_b_count"] = int(sides.eq("B").sum())
    return out


def _empty_label(retest: FvgRetest, *, horizon_bars: int) -> FvgHoldLabel:
    return FvgHoldLabel(
        outcome="neutral",
        role=retest.zone.role,
        held=False,
        failed=False,
        reason="no bars available after retest",
        first_touch_ts=retest.touch_ts,
        decisive_ts=None,
        horizon_bars=horizon_bars,
        target_pts=0.0,
        failure_buffer_pts=0.0,
        max_favorable_pts=0.0,
        max_adverse_pts=0.0,
        favorable_r=None,
        adverse_r=None,
    )


def _bar_overlaps_zone(*, high: float, low: float, zone: FvgZone) -> bool:
    return low <= zone.fvg_high and high >= zone.fvg_low


def _touch_depth_frac(*, high: float, low: float, zone: FvgZone) -> float:
    if zone.width_pts <= 0:
        return 0.0
    if zone.direction == "bullish":
        depth = max(0.0, zone.fvg_high - low)
    else:
        depth = max(0.0, high - zone.fvg_low)
    return float(depth / zone.width_pts)


def _reaction_reached(
    *,
    high: float,
    low: float,
    zone: FvgZone,
    target_pts: float,
) -> bool:
    if zone.direction == "bullish":
        return high >= zone.fvg_high + target_pts
    return low <= zone.fvg_low - target_pts


def _close_through_far_edge(
    *,
    close: float,
    zone: FvgZone,
    failure_buffer_pts: float,
) -> bool:
    if zone.direction == "bullish":
        return close < zone.fvg_low - failure_buffer_pts
    return close > zone.fvg_high + failure_buffer_pts


def _to_utc_datetime(value) -> dt.datetime:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")
    return ts.to_pydatetime()


def _row_float(row: pd.Series | None, key: str) -> float | None:
    if row is None or key not in row:
        return None
    value = row[key]
    if pd.isna(value):
        return None
    return float(value)


def _mean(series: pd.Series) -> float | None:
    if series.empty:
        return None
    value = series.mean()
    return None if pd.isna(value) else float(value)


def _max(series: pd.Series) -> float | None:
    if series.empty:
        return None
    value = series.max()
    return None if pd.isna(value) else float(value)


def _divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return float(numerator / denominator)


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None:
        return None
    if denominator is None or denominator <= 0:
        return None
    return float(numerator / denominator)


def _diff(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return float(left - right)


def _change_frac(new: float | None, old: float | None) -> float | None:
    if new is None or old is None or old == 0:
        return None
    return float((new - old) / old)


def _pooled_std(left: float, right: float) -> float | None:
    if not math.isfinite(left) or not math.isfinite(right):
        return None
    pooled = math.sqrt((left**2 + right**2) / 2.0)
    return pooled if pooled > 0 else None
