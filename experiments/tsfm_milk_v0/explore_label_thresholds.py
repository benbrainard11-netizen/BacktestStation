"""One-off: compare class balance under 3 label thresholding options.

Resolves the open question raised by qa.py --audit §4 (k=0.5σ_60 collapses
flat class at long horizons).

Options compared:
  A — horizon-specific σ: threshold = k × σ_h(t) where σ_h(t) = stddev of
       h-minute log-returns over last ~30 trading days (~6240 bars).
  B — random-walk-scaled: threshold = k × sqrt(h) × σ_60(t).
  C — per-horizon k: threshold = k_h × σ_60(t) where k_h is hand-tuned
       to roughly equalize the flat fraction at ~35% across horizons.

Output:
  out/explore/label_threshold_comparison.parquet
  appended to report/STATUS_FOR_BEN.md
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

THIS_FILE = Path(__file__).resolve()
EXPERIMENT_DIR = THIS_FILE.parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.data.reader import read_bars  # noqa: E402

SYMBOLS = ("ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0")
HORIZONS = (15, 30, 60, 90, 240)
K_DEFAULT = 0.5

# Hand-tuned per-horizon k for Option C (rough guesses; refine after seeing data)
K_PER_HORIZON_C: dict[int, float] = {
    15: 0.5,
    30: 0.8,
    60: 1.2,
    90: 1.4,
    240: 2.0,
}

# Representative months (sample, not full universe)
SAMPLE_MONTHS = [
    (2021, 6),   # low vol
    (2022, 6),   # bear / high vol
    (2024, 10),  # recent recovery
]

RTH_START_UTC = dt.time(13, 30)
RTH_END_UTC = dt.time(20, 0)


def load_month(symbol: str, year: int, month: int, padding_days: int = 35) -> pd.DataFrame:
    """Load a month of 1m bars plus padding for rolling computation."""
    start = dt.date(year, month, 1) - dt.timedelta(days=padding_days)
    if month == 12:
        end = dt.date(year + 1, 1, 1)
    else:
        end = dt.date(year, month + 1, 1)
    df = read_bars(symbol=symbol, timeframe="1m", start=start, end=end)
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    df = df.sort_values("ts_event").reset_index(drop=True)
    return df


def classify(forward_ret: np.ndarray, threshold: np.ndarray) -> np.ndarray:
    """Map (forward_return, threshold) → class code. flat=0, up=1, down=2."""
    cls = np.full(len(forward_ret), 0, dtype=np.int8)
    cls[forward_ret > threshold] = 1
    cls[forward_ret < -threshold] = 2
    return cls


def balance(cls: np.ndarray) -> tuple[float, float, float]:
    """Return (frac_flat, frac_up, frac_down)."""
    cls = cls[~np.isnan(cls)] if np.issubdtype(cls.dtype, np.floating) else cls
    if len(cls) == 0:
        return float("nan"), float("nan"), float("nan")
    return (
        float((cls == 0).mean()),
        float((cls == 1).mean()),
        float((cls == 2).mean()),
    )


def main() -> int:
    out_dir = EXPERIMENT_DIR / "out" / "explore"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []

    for symbol in SYMBOLS:
        for (year, month) in SAMPLE_MONTHS:
            try:
                df = load_month(symbol, year, month)
            except Exception as e:
                print(f"  {symbol} {year}-{month:02d}: load failed — {e}")
                continue
            if len(df) == 0:
                continue

            df["log_return_1m"] = np.log(df["close"] / df["close"].shift(1))
            # σ_60 rolling
            df["sigma_60"] = df["log_return_1m"].rolling(60).std()

            for h in HORIZONS:
                # Forward h-minute log return
                df[f"fwd_h{h}"] = np.log(df["close"].shift(-h) / df["close"])

                # Option A: rolling stddev of h-step returns over last ~30 days = 30 * 1380 = 41400 1m bars
                # But h-step returns are coarse — actually want rolling std of overlapping h-min log returns
                df[f"sigma_h{h}"] = df[f"fwd_h{h}"].rolling(min_periods=200, window=6240).std()

            in_rth = (df["ts_event"].dt.time >= RTH_START_UTC) & (df["ts_event"].dt.time <= RTH_END_UTC)
            month_mask = (df["ts_event"].dt.year == year) & (df["ts_event"].dt.month == month)
            sub = df[in_rth & month_mask].copy()

            for h in HORIZONS:
                fwd = sub[f"fwd_h{h}"].to_numpy()
                sig60 = sub["sigma_60"].to_numpy()
                sigh = sub[f"sigma_h{h}"].to_numpy()

                # All three options
                valid = ~(np.isnan(fwd) | np.isnan(sig60) | np.isnan(sigh)) & (sig60 > 0) & (sigh > 0)
                if valid.sum() < 100:
                    continue
                fwd_v = fwd[valid]
                sig60_v = sig60[valid]
                sigh_v = sigh[valid]

                # Option A: k * sigma_h
                th_a = K_DEFAULT * sigh_v
                cls_a = classify(fwd_v, th_a)
                ba = balance(cls_a)

                # Option B: k * sqrt(h) * sigma_60
                th_b = K_DEFAULT * np.sqrt(h) * sig60_v
                cls_b = classify(fwd_v, th_b)
                bb = balance(cls_b)

                # Option C: k_h * sigma_60
                k_c = K_PER_HORIZON_C[h]
                th_c = k_c * sig60_v
                cls_c = classify(fwd_v, th_c)
                bc = balance(cls_c)

                for opt, b in [("A_sigma_h", ba), ("B_sqrt_h_x_sigma_60", bb), ("C_per_horizon_k", bc)]:
                    rows.append({
                        "symbol": symbol,
                        "sample_year": year,
                        "sample_month": month,
                        "horizon_min": h,
                        "option": opt,
                        "n_samples": int(valid.sum()),
                        "frac_flat": round(b[0], 4),
                        "frac_up": round(b[1], 4),
                        "frac_down": round(b[2], 4),
                        "k_used": K_PER_HORIZON_C[h] if opt == "C_per_horizon_k" else K_DEFAULT,
                    })
                print(f"  {symbol} {year}-{month:02d} h={h}: A flat={ba[0]:.2%} | B flat={bb[0]:.2%} | C flat={bc[0]:.2%}", flush=True)

    df_out = pd.DataFrame(rows)
    pq_path = out_dir / "label_threshold_comparison.parquet"
    df_out.to_parquet(pq_path, index=False)
    print(f"\nWrote {pq_path}")

    # Per-option mean class balance across months/symbols
    summary = df_out.groupby(["option", "horizon_min"]).agg(
        n_cells=("n_samples", "count"),
        mean_flat=("frac_flat", "mean"),
        mean_up=("frac_up", "mean"),
        mean_down=("frac_down", "mean"),
    ).reset_index()
    summary.to_parquet(out_dir / "label_threshold_summary.parquet", index=False)
    print("\nPooled class balance per (option × horizon):")
    print(summary.to_string(index=False))

    # Append a section to STATUS_FOR_BEN.md
    status_path = EXPERIMENT_DIR / "report" / "STATUS_FOR_BEN.md"
    if status_path.exists():
        lines_to_append = [
            "",
            "---",
            "",
            "## Addendum — Empirical comparison of label-fix options",
            "",
            f"Generated: {dt.datetime.now(dt.timezone.utc).isoformat()}",
            "",
            "Computed the class balance each option would give us, on 3 representative",
            f"sample months ({', '.join(f'{y}-{m:02d}' for y,m in SAMPLE_MONTHS)}) × 4 symbols.",
            "Pooled across symbols + months:",
            "",
            "| option | horizon (min) | mean flat | mean up | mean down |",
            "|---|---|---|---|---|",
        ]
        order = ["A_sigma_h", "B_sqrt_h_x_sigma_60", "C_per_horizon_k"]
        for opt in order:
            for h in HORIZONS:
                sub = summary[(summary["option"] == opt) & (summary["horizon_min"] == h)]
                if len(sub) == 0:
                    continue
                r = sub.iloc[0]
                lines_to_append.append(
                    f"| {opt} | {h} | {r['mean_flat']:.2%} | {r['mean_up']:.2%} | {r['mean_down']:.2%} |"
                )
            lines_to_append.append("")
        lines_to_append.extend([
            "**Read:** an option keeps the model trainable when the flat fraction stays",
            "roughly between 25% and 50% at every horizon. Up/down should be roughly",
            "balanced and similar across horizons. Use this table to pick a labelling",
            "fix.",
            "",
        ])
        existing = status_path.read_text(encoding="utf-8")
        if "## Addendum — Empirical comparison of label-fix options" not in existing:
            status_path.write_text(existing + "\n".join(lines_to_append), encoding="utf-8")
            print(f"Appended addendum to {status_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
