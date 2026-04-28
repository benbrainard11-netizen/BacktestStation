"""Fractal AMD trusted-strategy plugin parameters.

Defaults mirror `C:/Fractal-AMD/scripts/trusted_multiyear_bt.py` line for line
so a vanilla `FractalAMDTrustedConfig()` reproduces the +274R / 586 trades /
40.8% WR backtest exactly. Live deployments add a non-zero `min_risk_pts`
(live bot uses 8) to filter unfillable tight-stop trades.

Source-of-truth literal values (do not change without re-running the
regression test):
  BUFFER     = 5          stop-buffer in points beyond the FVG far edge
  MAX_HOLD   = 120        max bars (=minutes for 1m) to hold before timeout
  TARGET_R   = 3          take-profit at 3R
  MAX_RISK   = 150        reject setups with stops > 150pt (huge stops)
  MIN_CO     = 3          continuation_of >= 3 required to fire entry
  RTH_OPEN   = (9, 30)    entry window opens 09:30 ET
  RTH_CLOSE  = 14         entry window closes 14:00 ET (et.hour >= 14 rejects)
  MAX_TRADES = 2          per ET trading day
  DEDUP_MIN  = 15         no two entries in same direction within 15-min bucket
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FractalAMDTrustedConfig:
    # Data symbols. Trusted runs NQ as primary with ES/YM as aux for SMT
    # divergence detection.
    primary_symbol: str = "NQ.c.0"
    aux_symbols: tuple[str, ...] = ("ES.c.0", "YM.c.0")

    # Stop / target geometry.
    stop_buffer_pts: float = 5.0  # BUFFER = 5
    target_r: float = 3.0  # TARGET_R = 3
    max_hold_bars: int = 120  # MAX_HOLD = 120

    # Risk gates.
    max_risk_pts: float = 150.0  # reject if stop > 150pts away
    # Trusted backtest has NO min_risk filter. Live bot deployments should
    # set this to 8 (live's MIN_RISK constant) to drop unfillable setups.
    # Backtest regression target uses 0 to faithfully reproduce trusted.
    min_risk_pts: float = 0.0

    # Continuation-OF gate (line 178-181 of trusted_multiyear_bt.py).
    # Skip entries where the OHLCV-derived continuation score is < this.
    min_co_score: int = 3
    co_lookback: int = 15  # bars
    co_atr: float = 40.0  # passed but unused by compute_continuation_of

    # Entry window (ET). Trusted gates entries with `et.hour < 9 or et.hour
    # >= 14` AND `ess = max(le, rth_s)` where rth_s = 9:30. The combined
    # effect is 09:30-13:59 (close exclusive).
    rth_open_hour: int = 9
    rth_open_min: int = 30
    rth_close_hour: int = 14  # 14:00 closes the window (>= 14 rejects)

    # Per-day caps.
    max_trades_per_day: int = 2  # n_today >= 2 rejects further entries
    entry_dedup_minutes: int = 15  # (direction, et.floor("15min"))

    # HTF stages to scan: trusted iterates session + 1H, both directions,
    # accepting either SMT or rejection signals.
    htf_timeframes: tuple[str, ...] = ("session", "1H")

    # LTF SMT search inside each HTF stage's expansion window. Trusted's
    # find_ltf_smt iterates 15m -> 5m and returns the FIRST match (early
    # return). Order matters.
    ltf_timeframes: tuple[tuple[str, int], ...] = (("15m", 15), ("5m", 5))

    # FVG detection on resampled LTF bars.
    fvg_min_gap_pct: float = 0.3  # detect_fvgs(min_gap_pct=0.3)
    fvg_expiry_bars: int = 60  # detect_fvgs(expiry_bars=60)
    # find_nearest_unfilled_fvg's max-bar-age argument (60 in trusted).
    fvg_nearest_max_bar_age: int = 60

    @classmethod
    def from_params(cls, params: dict) -> "FractalAMDTrustedConfig":
        """Build a config from the loose `RunConfig.params` dict.

        Unknown keys are ignored. List → tuple normalization for the
        nested config fields.
        """
        known = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in params.items() if k in known}
        if "aux_symbols" in kwargs and isinstance(kwargs["aux_symbols"], list):
            kwargs["aux_symbols"] = tuple(kwargs["aux_symbols"])
        if "htf_timeframes" in kwargs and isinstance(kwargs["htf_timeframes"], list):
            kwargs["htf_timeframes"] = tuple(kwargs["htf_timeframes"])
        if "ltf_timeframes" in kwargs and isinstance(kwargs["ltf_timeframes"], list):
            kwargs["ltf_timeframes"] = tuple(
                tuple(item) for item in kwargs["ltf_timeframes"]
            )
        return cls(**kwargs)
