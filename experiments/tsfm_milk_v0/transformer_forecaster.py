"""Small custom Transformer forecaster — pragmatic v0 TSFM-style baseline.

WHY THIS EXISTS:
  Originally planned to fine-tune IBM Granite TTM-r2 in `ttm_forecaster.py`.
  Three environment blockers stopped that path on 2026-05-27:
    1. Python 3.14 has no PyTorch CUDA wheels yet -> CPU only
    2. granite-tsfm not published to PyPI as a real package (Coming soon)
    3. TTM-r2 is pretrained univariate at context_length=512; our data is
       multivariate (32 channels) at lookback 240 — adapter loaded but the
       patcher dimensions don't align without rebuilding the dataset.

  Properly fine-tuning IBM TTM is queued for v0.6 (Python 3.13 downgrade
  OR official TTM-r3 with multivariate-pretrained checkpoints).

  This module is a CUSTOM transformer that fits our exact (240, 32) input
  shape and the Forecaster ABC interface. Same multi-horizon classification
  objective. Trained from scratch — no pretraining benefit — but with the
  right architectural priors (patch embed + self-attention + multi-head
  classification) to give an honest "transformer architecture vs gradient
  boosting" comparison against LightGBM.

ARCHITECTURE:
  Input: (B, 240, 32)
  Patch embedding: 20 non-overlapping patches of 12 timesteps × 32 channels
    -> (B, 20, d_model=128) via Conv1d-equivalent linear projection
  Position embedding: learned, added per patch
  Transformer encoder: 4 layers, 4 heads, d_model=128, ffn=256, GELU
  Pool: mean over patches
  Classification head: 5 horizons × 4 symbols × 3 classes = 60 logits
    -> reshape to (B, 5, 4, 3) -> softmax along last dim per (horizon, symbol)

Loss: cross-entropy summed across horizons (skip -1 ignore-index labels).
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Mapping

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from forecaster import CLASS_CODES, HORIZON_KEYS, SYMBOL_ORDER, ForecastBatch, Forecaster


# ---------------------------------------------------------------------------
# Model components
# ---------------------------------------------------------------------------


class PatchEmbedding(nn.Module):
    """Project (B, T, C) -> (B, num_patches, d_model) via non-overlapping patches."""

    def __init__(self, n_channels: int, lookback: int, patch_size: int, d_model: int):
        super().__init__()
        assert lookback % patch_size == 0, f"lookback ({lookback}) must be divisible by patch_size ({patch_size})"
        self.n_channels = n_channels
        self.lookback = lookback
        self.patch_size = patch_size
        self.num_patches = lookback // patch_size
        self.d_model = d_model
        self.proj = nn.Linear(patch_size * n_channels, d_model)
        self.pos_embed = nn.Parameter(torch.zeros(1, self.num_patches, d_model))
        nn.init.trunc_normal_(self.pos_embed, std=0.02)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, T, C) -> reshape to (B, num_patches, patch_size, C) -> (B, num_patches, patch_size*C)
        B, T, C = x.shape
        x = x.reshape(B, self.num_patches, self.patch_size, C)
        x = x.reshape(B, self.num_patches, self.patch_size * C)
        x = self.proj(x)  # (B, num_patches, d_model)
        x = x + self.pos_embed
        return x


class TransformerEncoder(nn.Module):
    """Standard pre-LN transformer encoder, batched (B, N, d)."""

    def __init__(self, d_model: int, num_heads: int, ffn_dim: int, num_layers: int, dropout: float = 0.1):
        super().__init__()
        layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=num_heads,
            dim_feedforward=ffn_dim,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,  # pre-LN, more stable
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=num_layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)


class MultiHorizonClassificationHead(nn.Module):
    """Pool + MLP that produces (B, n_horizons, n_symbols, n_classes) logits."""

    def __init__(self, d_model: int, n_horizons: int, n_symbols: int, n_classes: int = 3, dropout: float = 0.1):
        super().__init__()
        self.n_horizons = n_horizons
        self.n_symbols = n_symbols
        self.n_classes = n_classes
        out_dim = n_horizons * n_symbols * n_classes
        self.dropout = nn.Dropout(dropout)
        self.fc1 = nn.Linear(d_model, d_model)
        self.fc2 = nn.Linear(d_model, out_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, num_patches, d_model). Pool by mean.
        pooled = x.mean(dim=1)  # (B, d_model)
        h = self.dropout(F.gelu(self.fc1(pooled)))
        logits = self.fc2(h)  # (B, out_dim)
        B = logits.size(0)
        return logits.reshape(B, self.n_horizons, self.n_symbols, self.n_classes)


class TransformerClassifier(nn.Module):
    def __init__(
        self,
        n_channels: int,
        lookback: int,
        patch_size: int,
        d_model: int,
        num_heads: int,
        ffn_dim: int,
        num_layers: int,
        n_horizons: int,
        n_symbols: int,
        n_classes: int = 3,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.patch_embed = PatchEmbedding(n_channels, lookback, patch_size, d_model)
        self.encoder = TransformerEncoder(d_model, num_heads, ffn_dim, num_layers, dropout)
        self.head = MultiHorizonClassificationHead(d_model, n_horizons, n_symbols, n_classes, dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.patch_embed(x)
        x = self.encoder(x)
        return self.head(x)


# ---------------------------------------------------------------------------
# Forecaster ABC implementation
# ---------------------------------------------------------------------------


class TransformerForecaster(Forecaster):
    """Small from-scratch transformer for multi-horizon directional classification."""

    def __init__(
        self,
        *,
        lookback: int = 240,
        n_channels: int = 32,
        patch_size: int = 12,
        d_model: int = 128,
        num_heads: int = 4,
        ffn_dim: int = 256,
        num_layers: int = 4,
        dropout: float = 0.1,
        batch_size: int = 256,
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4,
        max_epochs: int = 8,
        early_stop_patience: int = 2,
        device: str | None = None,
        seed: int = 42,
    ):
        self.lookback = lookback
        self.n_channels = n_channels
        self.patch_size = patch_size
        self.d_model = d_model
        self.num_heads = num_heads
        self.ffn_dim = ffn_dim
        self.num_layers = num_layers
        self.dropout = dropout
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.max_epochs = max_epochs
        self.early_stop_patience = early_stop_patience
        self.seed = seed

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)

        torch.manual_seed(seed)
        np.random.seed(seed)

        self._model: TransformerClassifier | None = None
        self._n_horizons = len(HORIZON_KEYS)
        self._n_symbols = len(SYMBOL_ORDER)
        self._n_classes = len(CLASS_CODES)

    @property
    def name(self) -> str:
        return f"transformer_v0_d{self.d_model}_L{self.num_layers}_p{self.patch_size}"

    def _build_model(self) -> TransformerClassifier:
        m = TransformerClassifier(
            n_channels=self.n_channels,
            lookback=self.lookback,
            patch_size=self.patch_size,
            d_model=self.d_model,
            num_heads=self.num_heads,
            ffn_dim=self.ffn_dim,
            num_layers=self.num_layers,
            n_horizons=self._n_horizons,
            n_symbols=self._n_symbols,
            n_classes=self._n_classes,
            dropout=self.dropout,
        )
        return m.to(self.device)

    def _multi_horizon_loss(self, logits: torch.Tensor, labels_per_h: dict[str, torch.Tensor]) -> torch.Tensor:
        """logits: (B, n_horizons, n_symbols, n_classes); labels_per_h[h_key]: (B, n_symbols) long with -1 = ignore."""
        total = torch.tensor(0.0, device=logits.device)
        for h_idx, h_key in enumerate(HORIZON_KEYS):
            y = labels_per_h[h_key].to(self.device).long()  # (B, n_symbols)
            for s_idx in range(self._n_symbols):
                # CE per (horizon, symbol)
                lo = logits[:, h_idx, s_idx, :]  # (B, n_classes)
                ys = y[:, s_idx]  # (B,)
                loss = F.cross_entropy(lo, ys, ignore_index=-1, reduction="mean")
                if torch.isfinite(loss):
                    total = total + loss
        # average across (horizon * symbol) for scale stability
        return total / float(self._n_horizons * self._n_symbols)

    def _iterate_minibatches(self, inputs: np.ndarray, labels: dict[str, np.ndarray], shuffle: bool):
        n = inputs.shape[0]
        order = np.random.permutation(n) if shuffle else np.arange(n)
        for start in range(0, n, self.batch_size):
            idx = order[start : start + self.batch_size]
            x = torch.from_numpy(inputs[idx]).float()
            y_dict = {h: torch.from_numpy(labels[h][idx]).long() for h in HORIZON_KEYS}
            yield x, y_dict

    def fit(
        self,
        *,
        train_inputs: np.ndarray,
        train_labels: Mapping[str, np.ndarray],
        val_inputs: np.ndarray,
        val_labels: Mapping[str, np.ndarray],
        train_ts: np.ndarray | None = None,
        val_ts: np.ndarray | None = None,
        **kwargs,
    ) -> None:
        # Sanitize: replace NaN inputs with 0 (build_dataset already filters, but defense in depth)
        train_inputs = np.nan_to_num(train_inputs, copy=False)
        val_inputs = np.nan_to_num(val_inputs, copy=False)

        self._model = self._build_model()
        n_params = sum(p.numel() for p in self._model.parameters())
        print(f"    [transformer] params={n_params/1e6:.2f}M  device={self.device}", flush=True)

        optimizer = torch.optim.AdamW(
            self._model.parameters(), lr=self.learning_rate, weight_decay=self.weight_decay,
        )

        best_val = float("inf")
        patience = 0
        best_state = None

        for epoch in range(self.max_epochs):
            t0 = time.time()
            # Train
            self._model.train()
            train_loss_sum, n_train_batches = 0.0, 0
            for x, y_dict in self._iterate_minibatches(train_inputs, dict(train_labels), shuffle=True):
                x = x.to(self.device)
                optimizer.zero_grad()
                logits = self._model(x)
                loss = self._multi_horizon_loss(logits, y_dict)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self._model.parameters(), max_norm=1.0)
                optimizer.step()
                train_loss_sum += float(loss.item())
                n_train_batches += 1
            train_loss = train_loss_sum / max(1, n_train_batches)

            # Val
            self._model.eval()
            val_loss_sum, n_val_batches = 0.0, 0
            with torch.no_grad():
                for x, y_dict in self._iterate_minibatches(val_inputs, dict(val_labels), shuffle=False):
                    x = x.to(self.device)
                    logits = self._model(x)
                    loss = self._multi_horizon_loss(logits, y_dict)
                    val_loss_sum += float(loss.item())
                    n_val_batches += 1
            val_loss = val_loss_sum / max(1, n_val_batches)

            elapsed = time.time() - t0
            print(
                f"    [transformer] epoch {epoch + 1}/{self.max_epochs}: "
                f"train_loss={train_loss:.4f}  val_loss={val_loss:.4f}  ({elapsed:.1f}s)",
                flush=True,
            )

            if val_loss < best_val - 1e-5:
                best_val = val_loss
                patience = 0
                best_state = {k: v.detach().cpu().clone() for k, v in self._model.state_dict().items()}
            else:
                patience += 1
                if patience >= self.early_stop_patience:
                    print(f"    [transformer] early stop at epoch {epoch + 1}", flush=True)
                    break

        if best_state is not None:
            self._model.load_state_dict(best_state)
        self._model.eval()

    def predict_proba(self, inputs: np.ndarray, ts: np.ndarray) -> ForecastBatch:
        if self._model is None:
            raise RuntimeError("TransformerForecaster.predict_proba called before fit()")
        inputs = np.nan_to_num(inputs, copy=False)
        self._model.eval()
        n = inputs.shape[0]
        n_classes = self._n_classes
        n_symbols = self._n_symbols

        all_proba = {h: np.zeros((n, n_symbols, n_classes), dtype=np.float32) for h in HORIZON_KEYS}
        with torch.no_grad():
            for start in range(0, n, self.batch_size):
                end = min(n, start + self.batch_size)
                x = torch.from_numpy(inputs[start:end]).float().to(self.device)
                logits = self._model(x)  # (B, n_horizons, n_symbols, n_classes)
                proba = F.softmax(logits, dim=-1).cpu().numpy()
                for h_idx, h_key in enumerate(HORIZON_KEYS):
                    all_proba[h_key][start:end] = proba[:, h_idx, :, :]

        return ForecastBatch(
            horizons=HORIZON_KEYS,
            symbols=SYMBOL_ORDER,
            proba=all_proba,
            ts=ts,
            metadata={"model_name": self.name, "params": sum(p.numel() for p in self._model.parameters())},
        )

    def save(self, path: Path) -> None:
        if self._model is None:
            raise RuntimeError("Cannot save before fit()")
        path.mkdir(parents=True, exist_ok=True)
        torch.save(self._model.state_dict(), path / "model_state.pt")
        cfg = {
            "lookback": self.lookback,
            "n_channels": self.n_channels,
            "patch_size": self.patch_size,
            "d_model": self.d_model,
            "num_heads": self.num_heads,
            "ffn_dim": self.ffn_dim,
            "num_layers": self.num_layers,
            "dropout": self.dropout,
            "batch_size": self.batch_size,
            "learning_rate": self.learning_rate,
            "weight_decay": self.weight_decay,
            "max_epochs": self.max_epochs,
            "early_stop_patience": self.early_stop_patience,
            "seed": self.seed,
        }
        (path / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "TransformerForecaster":
        cfg = json.loads((path / "config.json").read_text(encoding="utf-8"))
        obj = cls(**cfg)
        obj._model = obj._build_model()
        state = torch.load(path / "model_state.pt", map_location=obj.device)
        obj._model.load_state_dict(state)
        obj._model.eval()
        return obj


def main() -> int:
    """Self-test: train on synthetic data, predict a small batch."""
    rng = np.random.default_rng(7)
    n_train, n_val = 256, 64
    n_channels = 32
    lookback = 240

    train_inputs = rng.standard_normal((n_train, lookback, n_channels)).astype(np.float32)
    val_inputs = rng.standard_normal((n_val, lookback, n_channels)).astype(np.float32)

    def _make_labels(inputs):
        signal = inputs[:, -1, 0]  # last value of channel 0
        labels = {}
        for h in HORIZON_KEYS:
            y = np.zeros((inputs.shape[0], len(SYMBOL_ORDER)), dtype=np.int64)
            for s in range(len(SYMBOL_ORDER)):
                y[:, s] = np.where(signal > 0.3, 1, np.where(signal < -0.3, 2, 0))
            labels[h] = y
        return labels

    train_labels = _make_labels(train_inputs)
    val_labels = _make_labels(val_inputs)
    train_ts = np.arange(n_train)
    val_ts = np.arange(n_val) + n_train

    model = TransformerForecaster(max_epochs=2, batch_size=64)
    model.fit(
        train_inputs=train_inputs,
        train_labels=train_labels,
        val_inputs=val_inputs,
        val_labels=val_labels,
        train_ts=train_ts,
        val_ts=val_ts,
    )
    out = model.predict_proba(val_inputs, val_ts)
    print(f"\nname: {model.name}")
    for h in HORIZON_KEYS:
        dist = out.proba[h][0, 0]
        print(f"  {h}: first-row first-sym dist = {dist.tolist()}, sum = {dist.sum():.3f}")
    print("self-test OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
