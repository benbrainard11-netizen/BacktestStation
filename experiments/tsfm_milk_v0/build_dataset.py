"""Build the multivariate dataset for tsfm_milk_v0.

Pipeline:
  1. Load 1m OHLCV bars for ES/NQ/YM/RTY across the universe
  2. Time-align bars at the 1-minute grid (intersect index, drop unaligned)
  3. Compute 28 per-symbol channels + 4 cross-asset channels = 32 channels
  4. Compute sigma_h per (symbol, horizon) on a rolling 30-trading-day window
  5. Compute Option A labels: up/down/flat at 5 horizons per symbol
  6. For each fold + phase + final holdout:
       - Sample RTH weekday anchor minutes (stride = --anchor-stride, default 5)
       - Drop anchors with invalid lookback or invalid labels
       - Apply purge: drop training anchors whose label window crosses into val/test
       - Apply 1-hour embargo between train/val and val/test
       - Assemble (N, lookback=240, 32) input tensor
       - Write meta.parquet + inputs.npy to out/dataset/fold_{fid}_{phase}/

Outputs:
  out/dataset/fold_{fid}_{phase}/meta.parquet
  out/dataset/fold_{fid}_{phase}/inputs.npy
  out/dataset/holdout/meta.parquet
  out/dataset/holdout/inputs.npy
  out/dataset/build_summary.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time as time_mod
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

THIS_FILE = Path(__file__).resolve()
EXPERIMENT_DIR = THIS_FILE.parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.data.reader import read_bars  # noqa: E402

SYMBOLS = ("ES.c.0", "NQ.c.0", "YM.c.0", "RTY.c.0")
SYMBOL_SHORT = {"ES.c.0": "ES", "NQ.c.0": "NQ", "YM.c.0": "YM", "RTY.c.0": "RTY"}

PER_SYMBOL_CHANNELS = (
    "log_return_1m",
    "high_minus_low_pct",
    "close_minus_open_pct",
    "log_volume",
    "log_trade_count",
    "close_vs_typical_pct",   # was close_vs_vwap_pct; vwap is null in bars before 2025-01.
                              # typical = (h+l+c)/3 is a deterministic proxy from each bar.
    "realized_vol_60",
)
CROSS_ASSET_CHANNELS = (
    "nq_over_es_log_ratio_z",
    "rty_over_es_log_ratio_z",
    "equity_basket_mean_return",
    "equity_basket_dispersion",
)

CHANNEL_ORDER: list[str] = []
for sym in SYMBOLS:
    for ch in PER_SYMBOL_CHANNELS:
        CHANNEL_ORDER.append(f"{SYMBOL_SHORT[sym]}__{ch}")
CHANNEL_ORDER.extend(CROSS_ASSET_CHANNELS)
# 7 per-sym × 4 symbols + 4 cross-asset = 32 channels.
assert len(CHANNEL_ORDER) == 32, f"got {len(CHANNEL_ORDER)} channels, expected 32"

CLASS_FLAT = 0
CLASS_UP = 1
CLASS_DOWN = 2

RTH_START_UTC = dt.time(13, 30)
RTH_END_UTC = dt.time(20, 0)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_universe_bars(symbols: tuple[str, ...], start: dt.date, end: dt.date) -> dict[str, pd.DataFrame]:
    """Load 1m bars per symbol over [start, end). Returns dict keyed by symbol."""
    out: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        t0 = time_mod.time()
        df = read_bars(symbol=sym, timeframe="1m", start=start, end=end + dt.timedelta(days=1))
        if len(df) == 0:
            print(f"  {sym}: 0 bars in [{start}, {end}]", flush=True)
            continue
        df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
        df = df.sort_values("ts_event").drop_duplicates(subset=["ts_event"]).reset_index(drop=True)
        out[sym] = df
        print(f"  loaded {sym}: {len(df):,} bars in {time_mod.time()-t0:.1f}s", flush=True)
    return out


def align_bars_on_minute_grid(bars_dict: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Inner-join all symbols on ts_event. Returns a wide DataFrame with
    columns like `ES__close`, `NQ__close`, etc. Rows are minutes where ALL
    symbols have a bar."""
    if not bars_dict:
        return pd.DataFrame()
    merged: pd.DataFrame | None = None
    for sym in SYMBOLS:
        if sym not in bars_dict:
            continue
        sub = bars_dict[sym][["ts_event", "open", "high", "low", "close", "volume", "trade_count", "vwap"]].copy()
        sub.columns = ["ts_event"] + [f"{SYMBOL_SHORT[sym]}__{c}" for c in ["open", "high", "low", "close", "volume", "trade_count", "vwap"]]
        if merged is None:
            merged = sub
        else:
            merged = merged.merge(sub, on="ts_event", how="inner")
    return merged if merged is not None else pd.DataFrame()


# ---------------------------------------------------------------------------
# Channel computation
# ---------------------------------------------------------------------------


def compute_per_symbol_channels(df: pd.DataFrame) -> pd.DataFrame:
    """Add 7 per-symbol channels in place. Expects wide DataFrame from align_bars_on_minute_grid()."""
    out = df.copy()
    for sym in SYMBOLS:
        s = SYMBOL_SHORT[sym]
        close = out[f"{s}__close"]
        # Returns (1m log)
        out[f"{s}__log_return_1m"] = np.log(close / close.shift(1))
        # High-Low pct
        out[f"{s}__high_minus_low_pct"] = (out[f"{s}__high"] - out[f"{s}__low"]) / close
        # Close-Open pct
        out[f"{s}__close_minus_open_pct"] = (close - out[f"{s}__open"]) / out[f"{s}__open"]
        # Log volume
        out[f"{s}__log_volume"] = np.log1p(out[f"{s}__volume"])
        # Log trade count
        out[f"{s}__log_trade_count"] = np.log1p(out[f"{s}__trade_count"])
        # Close vs typical-price pct (vwap is null in 2018-2024 bars)
        typical = (out[f"{s}__high"] + out[f"{s}__low"] + close) / 3.0
        out[f"{s}__close_vs_typical_pct"] = (close - typical) / typical
        # Realized vol over last 60 1m returns
        out[f"{s}__realized_vol_60"] = out[f"{s}__log_return_1m"].rolling(60, min_periods=30).std()
    return out


def compute_cross_asset_channels(df: pd.DataFrame, z_window: int = 60) -> pd.DataFrame:
    """Add 4 cross-asset channels. Z-scoring over a rolling window."""
    out = df.copy()
    close_es = out["ES__close"]
    close_nq = out["NQ__close"]
    close_ym = out["YM__close"]
    close_rty = out["RTY__close"]

    nq_over_es = np.log(close_nq / close_es)
    rty_over_es = np.log(close_rty / close_es)

    def _z(s: pd.Series, w: int) -> pd.Series:
        m = s.rolling(w, min_periods=w // 2).mean()
        sd = s.rolling(w, min_periods=w // 2).std()
        return (s - m) / sd

    out["nq_over_es_log_ratio_z"] = _z(nq_over_es, z_window)
    out["rty_over_es_log_ratio_z"] = _z(rty_over_es, z_window)

    # Equity basket: mean and std of 4 syms' 1m log returns
    returns_4 = pd.concat(
        [out[f"{SYMBOL_SHORT[s]}__log_return_1m"].rename(SYMBOL_SHORT[s]) for s in SYMBOLS],
        axis=1,
    )
    out["equity_basket_mean_return"] = returns_4.mean(axis=1)
    out["equity_basket_dispersion"] = returns_4.std(axis=1)

    return out


# ---------------------------------------------------------------------------
# Sigma_h (rolling per-horizon volatility — Option A)
# ---------------------------------------------------------------------------


def compute_sigma_h(df: pd.DataFrame, horizon_min: int, window_bars: int, min_obs: int) -> pd.DataFrame:
    """Compute sigma_h(t) per symbol: rolling stddev of h-minute log returns over `window_bars`."""
    out = df.copy()
    for sym in SYMBOLS:
        s = SYMBOL_SHORT[sym]
        close = out[f"{s}__close"]
        fwd_logret_h = np.log(close.shift(-horizon_min) / close)
        sigma = fwd_logret_h.rolling(window_bars, min_periods=min_obs).std()
        out[f"{s}__sigma_h{horizon_min}"] = sigma
    return out


# ---------------------------------------------------------------------------
# Label computation (Option A: k * sigma_h)
# ---------------------------------------------------------------------------


def compute_labels(df: pd.DataFrame, horizons: list[int], k: float) -> pd.DataFrame:
    """Compute up/down/flat labels at each (symbol, horizon).

    Adds columns:
      {symshort}__future_logret_h{h}
      {symshort}__label_h{h}        (int: 0=flat, 1=up, 2=down)
    Expects `compute_sigma_h` already applied for each horizon.
    """
    out = df.copy()
    for h in horizons:
        for sym in SYMBOLS:
            s = SYMBOL_SHORT[sym]
            close = out[f"{s}__close"]
            fwd = np.log(close.shift(-h) / close)
            sigma = out[f"{s}__sigma_h{h}"]
            threshold = k * sigma

            label = np.full(len(out), CLASS_FLAT, dtype=np.int8)
            up_mask = (fwd > threshold).fillna(False)
            down_mask = (fwd < -threshold).fillna(False)
            label[up_mask] = CLASS_UP
            label[down_mask] = CLASS_DOWN

            # Mark invalid labels (NaN fwd or NaN sigma) with -1 sentinel
            invalid = fwd.isna() | sigma.isna() | (sigma <= 0)
            label[invalid] = -1

            out[f"{s}__future_logret_h{h}"] = fwd.to_numpy()
            out[f"{s}__label_h{h}"] = label
    return out


# ---------------------------------------------------------------------------
# Anchor sampling + tensor assembly
# ---------------------------------------------------------------------------


def filter_anchor_rows(
    df: pd.DataFrame,
    horizons: list[int],
    lookback: int,
    max_missing_fraction: float,
    min_bars_in_lookback: int,
) -> pd.Series:
    """Return boolean mask of valid anchor rows in `df`.

    Conditions:
      - inside RTH (Mon-Fri, 13:30-20:00 UTC)
      - has at least `min_bars_in_lookback` of the prior `lookback` bars present
      - all 32 channels are valid (not NaN) at row t
      - all horizon labels are valid (not -1)
    """
    ts = df["ts_event"]
    in_rth = (ts.dt.dayofweek < 5) & (ts.dt.time >= RTH_START_UTC) & (ts.dt.time <= RTH_END_UTC)

    # Channel validity at row t
    channel_valid = pd.Series(True, index=df.index)
    for ch in CHANNEL_ORDER:
        channel_valid &= df[ch].notna()

    # All labels valid
    label_valid = pd.Series(True, index=df.index)
    for h in horizons:
        for sym in SYMBOLS:
            s = SYMBOL_SHORT[sym]
            label_valid &= df[f"{s}__label_h{h}"] != -1

    # Anchor must have at least min_bars_in_lookback of the prior `lookback` bars
    # Approximation: use rolling count of non-NaN log_return_1m on ES (proxy for bar presence)
    sample_present = df["ES__log_return_1m"].notna().astype(int)
    bars_in_lookback = sample_present.rolling(lookback, min_periods=1).sum()
    enough_history = bars_in_lookback >= min_bars_in_lookback

    return in_rth & channel_valid & label_valid & enough_history


def assemble_inputs_tensor(
    df: pd.DataFrame,
    anchor_indices: np.ndarray,
    lookback: int,
) -> np.ndarray:
    """Build the (N, lookback, n_channels) tensor for the given anchor indices.

    Assumes `df` is row-indexed contiguously and `anchor_indices` are row positions.
    """
    n = len(anchor_indices)
    n_channels = len(CHANNEL_ORDER)
    out = np.full((n, lookback, n_channels), np.nan, dtype=np.float32)
    channel_arr = df[CHANNEL_ORDER].to_numpy(dtype=np.float32, copy=False)

    for i, idx in enumerate(anchor_indices):
        start_row = idx - lookback + 1
        if start_row < 0:
            # Insufficient lookback — pad with NaN at front (caller should have filtered these out)
            pad = -start_row
            out[i, pad:, :] = channel_arr[0 : idx + 1, :]
        else:
            out[i, :, :] = channel_arr[start_row : idx + 1, :]
    return out


# ---------------------------------------------------------------------------
# Walk-forward fold + holdout enumeration
# ---------------------------------------------------------------------------


def enumerate_phases(folds_cfg: dict) -> list[dict]:
    """Return list of dicts: {fold_id, phase, start_date, end_date, kind}.

    kind ∈ {'fold_phase', 'holdout_refit', 'holdout_test'}.
    """
    out: list[dict] = []
    for fold in folds_cfg.get("folds", []):
        for phase in ("train", "val", "test"):
            out.append({
                "fold_id": fold["id"],
                "phase": phase,
                "kind": "fold_phase",
                "start_date": dt.date.fromisoformat(str(fold[f"{phase}_start"])),
                "end_date": dt.date.fromisoformat(str(fold[f"{phase}_end"])),
            })
    hold = folds_cfg.get("final_holdout", {})
    if hold:
        out.append({
            "fold_id": "refit",
            "phase": "refit",
            "kind": "holdout_refit",
            "start_date": dt.date.fromisoformat(str(hold["refit_start"])),
            "end_date": dt.date.fromisoformat(str(hold["refit_end"])),
        })
        out.append({
            "fold_id": "holdout",
            "phase": "holdout",
            "kind": "holdout_test",
            "start_date": dt.date.fromisoformat(str(hold["holdout_start"])),
            "end_date": dt.date.fromisoformat(str(hold["holdout_end"])),
        })
    return out


def select_phase_anchors(
    df: pd.DataFrame,
    valid_mask: pd.Series,
    phase_start: dt.date,
    phase_end: dt.date,
    stride: int,
) -> np.ndarray:
    """Return row indices of valid anchors falling in [phase_start, phase_end] at given stride."""
    ts = df["ts_event"]
    in_phase = (ts.dt.date >= phase_start) & (ts.dt.date <= phase_end)
    full_mask = valid_mask & in_phase
    candidate_idx = np.flatnonzero(full_mask.to_numpy())
    if stride > 1:
        candidate_idx = candidate_idx[::stride]
    return candidate_idx


def apply_purge_and_embargo(
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    test_idx: np.ndarray,
    df: pd.DataFrame,
    max_horizon_min: int,
    embargo_hours: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Return purged_train_idx, purged_val_idx after applying purge + embargo.

    Purge: drop training anchors whose [ts, ts + max_horizon] crosses into val/test ranges.
    Embargo: extend val/test ranges by ±embargo_hours before purging.
    """
    # Convert tz-aware datetime to tz-naive numpy datetime64 for arithmetic.
    ts = df["ts_event"].dt.tz_convert("UTC").dt.tz_localize(None).to_numpy()
    max_h_delta = np.timedelta64(max_horizon_min, "m")
    embargo_delta = np.timedelta64(embargo_hours, "h")

    val_ts = ts[val_idx] if len(val_idx) > 0 else np.array([], dtype="datetime64[ns]")
    test_ts = ts[test_idx] if len(test_idx) > 0 else np.array([], dtype="datetime64[ns]")

    val_min = val_ts.min() - embargo_delta if len(val_ts) else None
    val_max = val_ts.max() + embargo_delta if len(val_ts) else None
    test_min = test_ts.min() - embargo_delta if len(test_ts) else None
    test_max = test_ts.max() + embargo_delta if len(test_ts) else None

    train_ts = ts[train_idx]
    train_label_end = train_ts + max_h_delta

    drop_mask = np.zeros(len(train_idx), dtype=bool)
    if val_min is not None:
        drop_mask |= (train_label_end >= val_min) & (train_ts <= val_max)
    if test_min is not None:
        drop_mask |= (train_label_end >= test_min) & (train_ts <= test_max)

    purged_train_idx = train_idx[~drop_mask]

    # Same logic for val w.r.t. test
    if test_min is not None:
        val_ts_arr = ts[val_idx]
        val_label_end = val_ts_arr + max_h_delta
        val_drop = (val_label_end >= test_min) & (val_ts_arr <= test_max)
        purged_val_idx = val_idx[~val_drop]
    else:
        purged_val_idx = val_idx

    return purged_train_idx, purged_val_idx


# ---------------------------------------------------------------------------
# Per-phase output writer
# ---------------------------------------------------------------------------


def write_phase_output(
    out_dir: Path,
    fold_id,
    phase: str,
    df: pd.DataFrame,
    anchor_idx: np.ndarray,
    inputs_tensor: np.ndarray,
    horizons: list[int],
) -> dict:
    """Write meta.parquet + inputs.npy for one (fold, phase). Returns a summary dict."""
    sub_dir = out_dir / f"fold_{fold_id}_{phase}"
    sub_dir.mkdir(parents=True, exist_ok=True)

    # Build meta DataFrame
    meta_cols: dict = {"ts_event": df["ts_event"].iloc[anchor_idx].to_numpy()}
    for h in horizons:
        for sym in SYMBOLS:
            s = SYMBOL_SHORT[sym]
            meta_cols[f"{s}_label_h{h}"] = df[f"{s}__label_h{h}"].iloc[anchor_idx].to_numpy()
            meta_cols[f"{s}_fwd_logret_h{h}"] = df[f"{s}__future_logret_h{h}"].iloc[anchor_idx].to_numpy()
            # Entry price = next-bar open (for slippage modeling). Use the bar at index i+1.
            # Where i+1 doesn't exist, fall back to current row's close.
            n = len(df)
            next_idx = np.minimum(anchor_idx + 1, n - 1)
            meta_cols[f"{s}_entry_price"] = df[f"{s}__open"].iloc[next_idx].to_numpy()
    meta_cols["fold_id"] = [fold_id] * len(anchor_idx)
    meta_cols["phase"] = [phase] * len(anchor_idx)

    meta = pd.DataFrame(meta_cols)
    meta_path = sub_dir / "meta.parquet"
    meta.to_parquet(meta_path, index=False)

    inputs_path = sub_dir / "inputs.npy"
    np.save(inputs_path, inputs_tensor)

    return {
        "fold_id": str(fold_id),
        "phase": phase,
        "n_anchors": int(len(anchor_idx)),
        "tensor_shape": list(inputs_tensor.shape),
        "meta_path": str(meta_path.relative_to(EXPERIMENT_DIR)),
        "inputs_path": str(inputs_path.relative_to(EXPERIMENT_DIR)),
        "meta_bytes": int(meta_path.stat().st_size),
        "inputs_bytes": int(inputs_path.stat().st_size),
    }


# ---------------------------------------------------------------------------
# Main driver
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--folds", nargs="+", help="Fold IDs to build. Defaults to all.")
    p.add_argument("--anchor-stride", type=int, default=5, help="Sample every Nth RTH minute")
    p.add_argument("--out-dir", default=str(EXPERIMENT_DIR / "out" / "dataset"))
    p.add_argument("--lookback", type=int, default=240)
    p.add_argument("--smoke-test", action="store_true",
                   help="Tiny run: only fold 1, only first 2 months of each phase.")
    args = p.parse_args(argv)

    feature_cfg = yaml.safe_load((EXPERIMENT_DIR / "feature_schema.yaml").read_text(encoding="utf-8"))
    labels_cfg = yaml.safe_load((EXPERIMENT_DIR / "labels_and_horizons.yaml").read_text(encoding="utf-8"))
    folds_cfg = yaml.safe_load((EXPERIMENT_DIR / "walk_forward.yaml").read_text(encoding="utf-8"))

    horizons = list(labels_cfg["horizons_minutes"])
    k = float(labels_cfg["thresholding"]["k"])
    sigma_window_bars = int(labels_cfg["thresholding"]["sigma_h_window_bars"])
    sigma_min_obs = int(labels_cfg["thresholding"]["sigma_h_min_observations"])

    lookback = int(args.lookback)
    max_missing = float(feature_cfg.get("max_missing_fraction_in_lookback", 0.05))
    min_bars_lb = int(feature_cfg.get("min_bars_in_lookback", lookback - 10))

    phases = enumerate_phases(folds_cfg)
    if args.folds:
        wanted = set(args.folds)
        phases = [p for p in phases if str(p["fold_id"]) in wanted]
    if args.smoke_test:
        phases = [p for p in phases if str(p["fold_id"]) == "1"]
        # Compress each phase window to 2 months
        new_phases = []
        for p in phases:
            end_compressed = p["start_date"] + dt.timedelta(days=60)
            new_phases.append({**p, "end_date": min(end_compressed, p["end_date"])})
        phases = new_phases

    # Universe date range = earliest phase start - sigma window (for warmup) ... latest end + max horizon (for label)
    if not phases:
        print("no phases selected")
        return 1

    earliest = min(p["start_date"] for p in phases)
    latest = max(p["end_date"] for p in phases)
    max_h = max(horizons)

    # Approximate calendar days for sigma window: 41,400 bars / 1380 bars/day ≈ 30 trading days ≈ 45 calendar days
    warmup_days = int(sigma_window_bars / 1380 * 1.5) + 5
    universe_start = earliest - dt.timedelta(days=warmup_days)
    universe_end = latest + dt.timedelta(days=max(2, max_h // 60 + 1))

    print(f"Universe: {universe_start} -> {universe_end}  ({len(phases)} phases)")

    t_load = time_mod.time()
    bars_dict = load_universe_bars(SYMBOLS, universe_start, universe_end)
    print(f"  loaded universe in {time_mod.time()-t_load:.1f}s")

    if len(bars_dict) < len(SYMBOLS):
        print(f"WARN: only loaded {len(bars_dict)}/{len(SYMBOLS)} symbols")

    t = time_mod.time()
    df = align_bars_on_minute_grid(bars_dict)
    print(f"  aligned grid: {len(df):,} rows in {time_mod.time()-t:.1f}s")
    if len(df) == 0:
        print("ERROR: aligned grid is empty")
        return 1

    t = time_mod.time()
    df = compute_per_symbol_channels(df)
    df = compute_cross_asset_channels(df)
    print(f"  computed 32 channels in {time_mod.time()-t:.1f}s")

    t = time_mod.time()
    for h in horizons:
        df = compute_sigma_h(df, horizon_min=h, window_bars=sigma_window_bars, min_obs=sigma_min_obs)
    print(f"  computed sigma_h for {len(horizons)} horizons in {time_mod.time()-t:.1f}s")

    t = time_mod.time()
    df = compute_labels(df, horizons=horizons, k=k)
    print(f"  computed labels in {time_mod.time()-t:.1f}s")

    t = time_mod.time()
    valid_mask = filter_anchor_rows(
        df,
        horizons=horizons,
        lookback=lookback,
        max_missing_fraction=max_missing,
        min_bars_in_lookback=min_bars_lb,
    )
    n_valid = int(valid_mask.sum())
    print(f"  valid anchor rows: {n_valid:,} / {len(df):,} ({100*n_valid/len(df):.1f}%)")
    print(f"  validity filter in {time_mod.time()-t:.1f}s")

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Group phases by fold for purging
    fold_groups: dict = {}
    for p in phases:
        fold_groups.setdefault(p["fold_id"], []).append(p)

    summary: list[dict] = []
    embargo_hours = int(folds_cfg.get("embargo", {}).get("value", 1))

    for fold_id, fold_phases in fold_groups.items():
        train_p = next((p for p in fold_phases if p["phase"] == "train"), None)
        val_p = next((p for p in fold_phases if p["phase"] == "val"), None)
        test_p = next((p for p in fold_phases if p["phase"] == "test"), None)
        refit_p = next((p for p in fold_phases if p["phase"] == "refit"), None)
        holdout_p = next((p for p in fold_phases if p["phase"] == "holdout"), None)

        print(f"\n=== fold {fold_id} ===")

        if train_p and val_p and test_p:
            train_idx = select_phase_anchors(df, valid_mask, train_p["start_date"], train_p["end_date"], args.anchor_stride)
            val_idx = select_phase_anchors(df, valid_mask, val_p["start_date"], val_p["end_date"], args.anchor_stride)
            test_idx = select_phase_anchors(df, valid_mask, test_p["start_date"], test_p["end_date"], args.anchor_stride)

            train_idx_pre = len(train_idx)
            val_idx_pre = len(val_idx)
            train_idx, val_idx = apply_purge_and_embargo(
                train_idx, val_idx, test_idx, df, max_horizon_min=max_h, embargo_hours=embargo_hours
            )
            print(f"  train  {train_idx_pre:,} -> {len(train_idx):,} (purged)")
            print(f"  val    {val_idx_pre:,} -> {len(val_idx):,} (purged)")
            print(f"  test   {len(test_idx):,}")

            for phase_name, phase_idx in [("train", train_idx), ("val", val_idx), ("test", test_idx)]:
                if len(phase_idx) == 0:
                    print(f"  {phase_name}: 0 anchors, skipping")
                    continue
                t = time_mod.time()
                inputs = assemble_inputs_tensor(df, phase_idx, lookback)
                s = write_phase_output(out_dir, fold_id, phase_name, df, phase_idx, inputs, horizons)
                print(f"  wrote {phase_name}: {s['n_anchors']:,} anchors, "
                      f"tensor {s['tensor_shape']}, "
                      f"{(s['meta_bytes'] + s['inputs_bytes']) / 1e6:.1f}MB, "
                      f"{time_mod.time()-t:.1f}s")
                summary.append(s)
        elif refit_p or holdout_p:
            # refit and holdout are in separate fold_groups in enumerate_phases
            # (one phase each). When holdout_p is None, only refit is present, and
            # vice versa. We need to look up the OTHER phase from the original folds_cfg
            # so we can purge refit against holdout properly.
            if refit_p and not holdout_p:
                hold_cfg = folds_cfg.get("final_holdout", {})
                if hold_cfg:
                    holdout_p_resolved = {
                        "phase": "holdout",
                        "start_date": dt.date.fromisoformat(str(hold_cfg["holdout_start"])),
                        "end_date": dt.date.fromisoformat(str(hold_cfg["holdout_end"])),
                    }
                else:
                    holdout_p_resolved = None
                refit_idx = select_phase_anchors(df, valid_mask, refit_p["start_date"], refit_p["end_date"], args.anchor_stride)
                holdout_idx_for_purge = (
                    select_phase_anchors(df, valid_mask, holdout_p_resolved["start_date"], holdout_p_resolved["end_date"], args.anchor_stride)
                    if holdout_p_resolved else np.array([], dtype=int)
                )
                refit_pre = len(refit_idx)
                if len(holdout_idx_for_purge) > 0:
                    refit_idx, _ = apply_purge_and_embargo(
                        refit_idx, np.array([], dtype=int), holdout_idx_for_purge,
                        df, max_horizon_min=max_h, embargo_hours=embargo_hours,
                    )
                print(f"  refit  {refit_pre:,} -> {len(refit_idx):,} (purged)")
                if len(refit_idx) > 0:
                    t = time_mod.time()
                    inputs = assemble_inputs_tensor(df, refit_idx, lookback)
                    s = write_phase_output(out_dir, "refit", "refit", df, refit_idx, inputs, horizons)
                    print(f"  wrote refit: {s['n_anchors']:,} anchors, "
                          f"tensor {s['tensor_shape']}, "
                          f"{(s['meta_bytes'] + s['inputs_bytes']) / 1e6:.1f}MB, "
                          f"{time_mod.time()-t:.1f}s")
                    summary.append(s)
            elif holdout_p:
                holdout_idx = select_phase_anchors(
                    df, valid_mask, holdout_p["start_date"], holdout_p["end_date"], args.anchor_stride,
                )
                print(f"  holdout  {len(holdout_idx):,} anchors")
                if len(holdout_idx) > 0:
                    t = time_mod.time()
                    inputs = assemble_inputs_tensor(df, holdout_idx, lookback)
                    s = write_phase_output(out_dir, "holdout", "holdout", df, holdout_idx, inputs, horizons)
                    print(f"  wrote holdout: {s['n_anchors']:,} anchors, "
                          f"tensor {s['tensor_shape']}, "
                          f"{(s['meta_bytes'] + s['inputs_bytes']) / 1e6:.1f}MB, "
                          f"{time_mod.time()-t:.1f}s")
                    summary.append(s)

    # Final summary
    summary_path = out_dir / "build_summary.json"
    summary_obj = {
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "anchor_stride": args.anchor_stride,
        "lookback": lookback,
        "horizons": horizons,
        "k": k,
        "sigma_window_bars": sigma_window_bars,
        "channel_count": len(CHANNEL_ORDER),
        "channel_order": CHANNEL_ORDER,
        "phases": summary,
    }
    summary_path.write_text(json.dumps(summary_obj, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {summary_path.relative_to(EXPERIMENT_DIR)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
