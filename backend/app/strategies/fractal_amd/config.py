"""Fractal AMD strategy parameters.

Source-of-truth values mirror the trusted live bot
(`FractalAMD-/production/live_bot.py`) as of 2026-04-12. When the live
bot changes, update both. The defaults here match the trusted backtest
exactly so a deterministic re-run reproduces the validated results.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FractalAMDConfig:
    # Entry window (ET). The trusted backtest gates entries with
    # `et.hour < 9 or et.hour >= 14`, combined with rth_s = 9:30.
    rth_open_hour: int = 9
    rth_open_min: int = 30
    max_entry_hour: int = 14  # last entry at 13:59

    # Risk / sizing (in points, not dollars).
    min_risk_pts: float = 8.0  # skip if stop is too tight to survive bid/ask noise
    max_risk_pts: float = 150.0  # trusted-backtest cap
    target_r: float = 3.0
    max_trades_per_day: int = 2

    # Aux symbols required for SMT divergence (NQ vs ES vs YM).
    primary_symbol: str = "NQ.c.0"
    aux_symbols: tuple[str, ...] = ("ES.c.0", "YM.c.0")

    # FVG detection runs on resampled LTF bars (5m / 15m), not raw 1m.
    # CandleBuilder buffer in the live bot is ~1500 bars (~25h) so HTF
    # session candles from prior 18:00 ET open survive through RTH scan.
    htf_lookback_bars: int = 1500

    # Setup deduplication: same FVG = one setup per day.
    dedupe_setups: bool = True

    # Stop-buffer in points beyond the FVG far edge. Mirrors live_bot.BUFFER.
    stop_buffer_pts: float = 1.0

    # Minimum continuation-OF score gate. None = disabled (recommended for
    # backtest until OF/delta proxy is implemented). Live bot uses 3.
    min_co_score: int | None = None

    # Touch-to-entry timing window: a touched setup must convert to entry
    # within `entry_max_bars_after_touch` primary bars or it resets to
    # WATCHING. Mirrors live's 30s-150s window applied to bar-level events.
    entry_max_bars_after_touch: int = 3

    # 15-min direction dedup: at most one entry per (direction, 15-min
    # bucket). Mirrors live's `entries_today` set.
    entry_dedup_minutes: int = 15

    @classmethod
    def from_params(cls, params: dict) -> "FractalAMDConfig":
        """Build a config from the loose `RunConfig.params` dict.

        Unknown keys are ignored (forward-compatible with future params).
        """
        known = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: v for k, v in params.items() if k in known}
        # aux_symbols arrives as a list from JSON; normalize to tuple so
        # the dataclass stays hashable + frozen-friendly.
        if "aux_symbols" in kwargs and isinstance(kwargs["aux_symbols"], list):
            kwargs["aux_symbols"] = tuple(kwargs["aux_symbols"])
        return cls(**kwargs)
