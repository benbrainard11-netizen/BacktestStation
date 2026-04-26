"""Setup-lifecycle dump for the Fractal AMD port.

Runs the engine over a date range with a tracing subclass that
records (a) every WATCHING -> TOUCHED transition and (b) every
validation rejection (with the gate that failed). Writes a CSV to
`backend/tests/_artifacts/setup_lifecycle_{start}_{end}.csv`.

The point: today the strategy port emits 0 trades against 188
detected setups. This script answers "for the 178 setups stuck
WATCHING, what specifically blocked them?" — a per-setup table is
much faster to scan than re-reading bar logs.

Usage:
    cd backend
    .venv/Scripts/python.exe debug_fractal_setup_lifecycle.py \\
        --start 2026-04-14 --end 2026-04-22

The script is OBSERVATION ONLY — no strategy code change. It works
by subclassing FractalAMD at runtime and wrapping
_validate_and_build_intent.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from app.backtest.engine import RunConfig, run as engine_run
from app.backtest.runner import load_aux_bars, load_bars
from app.strategies.fractal_amd import FractalAMD
from app.strategies.fractal_amd.config import FractalAMDConfig
from app.strategies.fractal_amd.signals import ET, Setup, is_in_entry_window

if TYPE_CHECKING:
    from app.backtest.orders import OrderIntent
    from app.backtest.strategy import Bar, Context


# --- Rejection classifier ------------------------------------------------


def _classify_validation_outcome(
    setup: Setup, bar: "Bar", cfg: FractalAMDConfig
) -> str:
    """Reproduce the gates inside _validate_and_build_intent and report
    the first non-passing one. Mirrors strategy.py — KEEP IN SYNC.

    Returns one of: "wait_same_bar", "touch_too_old (...)",
    "risk_negative_or_zero (...)", "risk_too_high (...)",
    "risk_too_low (...)", "dedup_collision (...)", or "would_fire".
    "wait_same_bar" is *transient* in the strategy (setup stays
    TOUCHED); the others are terminal (setup resets to WATCHING).
    """
    if setup.touch_bar_time is None:
        return "no_touch_time"

    bars_since_touch = max(
        0, int((bar.ts_event - setup.touch_bar_time).total_seconds() // 60)
    )
    if bars_since_touch < 1:
        return "wait_same_bar"
    if bars_since_touch > cfg.entry_max_bars_after_touch:
        return f"touch_too_old ({bars_since_touch} > {cfg.entry_max_bars_after_touch})"

    if setup.direction == "BEARISH":
        entry = bar.open
        stop = setup.fvg_high + cfg.stop_buffer_pts
        risk = stop - entry
    else:
        entry = bar.open
        stop = setup.fvg_low - cfg.stop_buffer_pts
        risk = entry - stop

    if risk <= 0:
        return f"risk_negative_or_zero ({risk:.2f})"
    if risk > cfg.max_risk_pts:
        return f"risk_too_high ({risk:.2f} > {cfg.max_risk_pts})"
    if risk < cfg.min_risk_pts:
        return f"risk_too_low ({risk:.2f} < {cfg.min_risk_pts})"

    bar_et = bar.ts_event.astimezone(ET)
    bucket_minute = (
        bar_et.minute // cfg.entry_dedup_minutes
    ) * cfg.entry_dedup_minutes
    bucket = bar_et.replace(minute=bucket_minute, second=0, microsecond=0)
    return f"dedup_collision (bucket={bucket.isoformat()})"


# --- Tracing subclass ----------------------------------------------------


class TracingFractalAMD(FractalAMD):
    """FractalAMD with per-setup transition + rejection capture.

    `setup_records` is keyed by id(setup) so that even setups whose
    status gets reset (TOUCHED -> WATCHING after a validation failure)
    keep their touch + rejection history visible.
    """

    def __init__(self, config: FractalAMDConfig):
        super().__init__(config)
        self.setup_records: dict[int, dict] = {}
        self.rejection_log: list[dict] = []

    def _record_setup(self, s: Setup, bar_ts: dt.datetime) -> None:
        rec = self.setup_records.setdefault(
            id(s),
            {
                "direction": s.direction,
                "htf_tf": s.htf_tf,
                "ltf_tf": s.ltf_tf,
                "fvg_low": s.fvg_low,
                "fvg_high": s.fvg_high,
                "fvg_mid": s.fvg_mid,
                "htf_candle_start": s.htf_candle_start.isoformat(),
                "ltf_candle_end": s.ltf_candle_end.isoformat(),
                "created_at_bar": bar_ts.isoformat(),
                "first_touch_ts": None,
                "last_touch_ts": None,
                "filled_at_bar_ts": None,
                "n_touches": 0,
                "first_touch_in_window": None,
                "n_validation_attempts": 0,
                "n_transient_waits": 0,
                "n_terminal_rejections": 0,
                "rejection_reasons": [],
                "final_status": s.status,
            },
        )
        rec["final_status"] = s.status

    def on_bar(self, bar: "Bar", context: "Context") -> "list[OrderIntent]":
        pre_status = {id(s): s.status for s in self.setups}
        intents = super().on_bar(bar, context)
        # Newly created setups
        for s in self.setups:
            if id(s) not in self.setup_records:
                self._record_setup(s, bar.ts_event)
        # Detect transitions from this bar
        for s in self.setups:
            rec = self.setup_records.get(id(s))
            if rec is None:
                continue
            old = pre_status.get(id(s), s.status)
            if old != "TOUCHED" and s.status == "TOUCHED":
                rec["n_touches"] += 1
                rec["last_touch_ts"] = bar.ts_event.isoformat()
                if rec["first_touch_ts"] is None:
                    rec["first_touch_ts"] = bar.ts_event.isoformat()
                    bar_et = bar.ts_event.astimezone(ET)
                    rec["first_touch_in_window"] = is_in_entry_window(
                        bar_et,
                        open_hour=self.config.rth_open_hour,
                        open_min=self.config.rth_open_min,
                        close_hour=self.config.max_entry_hour,
                    )
            if old != "FILLED" and s.status == "FILLED":
                rec["filled_at_bar_ts"] = bar.ts_event.isoformat()
            rec["final_status"] = s.status
        return intents

    def _validate_and_build_intent(self, setup: Setup, bar: "Bar"):
        result = super()._validate_and_build_intent(setup, bar)
        rec = self.setup_records.get(id(setup))
        if rec is not None:
            rec["n_validation_attempts"] += 1
            if result.action == "wait":
                rec["n_transient_waits"] += 1
            elif result.action == "reject":
                rec["n_terminal_rejections"] += 1
        if result.action != "fire":
            reason = _classify_validation_outcome(setup, bar, self.config)
            if rec is not None:
                rec["rejection_reasons"].append(f"{result.action}:{reason}")
            self.rejection_log.append(
                {
                    "ts": bar.ts_event.isoformat(),
                    "direction": setup.direction,
                    "htf_tf": setup.htf_tf,
                    "ltf_tf": setup.ltf_tf,
                    "fvg_low": setup.fvg_low,
                    "fvg_high": setup.fvg_high,
                    "reason": f"{result.action}:{reason}",
                }
            )
        return result


# --- Driver --------------------------------------------------------------


_ARTIFACT_DIR = Path(__file__).parent / "tests" / "_artifacts"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Dump Fractal AMD setup lifecycle to CSV."
    )
    p.add_argument("--start", required=True, help="YYYY-MM-DD")
    p.add_argument("--end", required=True, help="YYYY-MM-DD")
    p.add_argument(
        "--symbol", default="NQ.c.0", help="primary symbol (default NQ.c.0)"
    )
    p.add_argument(
        "--aux",
        default="ES.c.0,YM.c.0",
        help="comma-separated aux symbols (default ES.c.0,YM.c.0)",
    )
    p.add_argument(
        "--out-dir",
        default=str(_ARTIFACT_DIR),
        help=f"output directory (default {_ARTIFACT_DIR})",
    )
    args = p.parse_args(argv)

    aux_symbols = [s.strip() for s in args.aux.split(",") if s.strip()]
    config = RunConfig(
        strategy_name="fractal_amd",
        symbol=args.symbol,
        timeframe="1m",
        start=args.start,
        end=args.end,
        history_max=2000,
        aux_symbols=aux_symbols,
        commission_per_contract=0.0,
        slippage_ticks=1,
        flatten_on_last_bar=False,
    )

    print(f"loading bars: {args.symbol} + {aux_symbols} {args.start}..{args.end}")
    bars = load_bars(config)
    aux_bars = load_aux_bars(config)
    print(f"  primary={len(bars)} bars; aux: " + ", ".join(
        f"{sym}={len(b)} bars" for sym, b in aux_bars.items()
    ))
    if not bars:
        sys.stderr.write(
            "no primary bars found in warehouse; check BS_DATA_ROOT.\n"
        )
        return 1

    strat = TracingFractalAMD(FractalAMDConfig())
    print("running engine...")
    result = engine_run(strat, bars, config, aux_bars=aux_bars)
    print(f"  trades emitted: {len(result.trades)}")
    print(f"  setups recorded: {len(strat.setup_records)}")
    print(f"  validation rejections: {len(strat.rejection_log)}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = f"{args.start}_{args.end}"
    setup_csv = out_dir / f"setup_lifecycle_{stamp}.csv"
    reject_csv = out_dir / f"setup_rejections_{stamp}.csv"

    with open(setup_csv, "w", newline="", encoding="utf-8") as f:
        cols = [
            "direction",
            "htf_tf",
            "ltf_tf",
            "fvg_low",
            "fvg_high",
            "fvg_mid",
            "htf_candle_start",
            "ltf_candle_end",
            "created_at_bar",
            "first_touch_ts",
            "last_touch_ts",
            "filled_at_bar_ts",
            "first_touch_in_window",
            "n_touches",
            "n_validation_attempts",
            "n_transient_waits",
            "n_terminal_rejections",
            "rejection_reasons",
            "final_status",
        ]
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for rec in strat.setup_records.values():
            row = dict(rec)
            row["rejection_reasons"] = "|".join(row["rejection_reasons"])
            writer.writerow(row)

    with open(reject_csv, "w", newline="", encoding="utf-8") as f:
        cols = [
            "ts",
            "direction",
            "htf_tf",
            "ltf_tf",
            "fvg_low",
            "fvg_high",
            "reason",
        ]
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for ev in strat.rejection_log:
            writer.writerow(ev)

    # Status summary, easy to eyeball.
    from collections import Counter

    statuses = Counter(rec["final_status"] for rec in strat.setup_records.values())
    print(f"final-status counts: {dict(statuses)}")
    if strat.rejection_log:
        reasons = Counter(ev["reason"].split(" ")[0] for ev in strat.rejection_log)
        print(f"rejection reason counts: {dict(reasons)}")
    print(f"wrote {setup_csv}")
    print(f"wrote {reject_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
