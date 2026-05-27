"""TTMForecaster — IBM Granite TinyTimeMixer (TTM-r2), GPU fine-tuning.

This is the v0.6 deliverable (was originally v0 primary, deferred when Python
3.14 env blocked CUDA torch). Now runs on a Python 3.12 venv with PyTorch
nightly + CUDA 12.8 supporting RTX 5080 (sm_120 Blackwell).

ARCHITECTURE:
  Pretrained checkpoint: ibm-granite/granite-timeseries-ttm-r2
  Backbone:              TinyTimeMixerModel
  Config overrides:
    num_input_channels = 32    (was 1; multivariate adapter)
    context_length     = 512   (pretrained native; we pad our 240 → 512)
    decoder_mode       = 'mix_channel'   (cross-channel mixing)
  ignore_mismatched_sizes = True (much of the encoder is re-init for multivariate)

  Input:    (B, 240, 32)
  Pad:      prepend 272 zeros → (B, 512, 32)
  Backbone: TinyTimeMixerModel → last_hidden_state (B, 32, 8, 192)
  Pool:     mean over channels and patches → (B, 192)
  Head:     Linear(192, 256) → GELU → Dropout → Linear(256, 60) → reshape (B, 5, 4, 3)

  Total params: ~0.6-0.8M (depending on backbone size)

CAVEATS:
  - Multivariate config invalidates most encoder pretrained weights — they
    re-initialize. The "pretrained benefit" is real but limited (patcher and
    decoder weights survive; encoder is mostly retrained).
  - 272 leading zeros pollute the early patches of the backbone. The patches
    that are zero-only will be uninformative; the model learns to ignore them
    via the channel-mixer normalization layer (revin).
  - Using LayerNorm-stabilized AdamW with small learning rate to preserve
    pretrained weights where they exist.

Honest comparison target: LightGBM's sum-net-R at h_60m (+39k) and h_90m (+39k).
TTM has to clear those to justify the complexity.
"""

from __future__ import annotations

import json
import time
import warnings
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


class TTMClassificationHead(nn.Module):
    def __init__(self, d_model: int, n_horizons: int, n_symbols: int, n_classes: int = 3, hidden_dim: int = 256, dropout: float = 0.1):
        super().__init__()
        self.n_horizons = n_horizons
        self.n_symbols = n_symbols
        self.n_classes = n_classes
        out_dim = n_horizons * n_symbols * n_classes
        self.fc1 = nn.Linear(d_model, hidden_dim)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(hidden_dim, out_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, d_model) pooled representation
        h = self.dropout(self.act(self.fc1(x)))
        logits = self.fc2(h)
        return logits.reshape(-1, self.n_horizons, self.n_symbols, self.n_classes)


class TTMClassifier(nn.Module):
    """TTM backbone + custom classification head with input padding to 512."""

    def __init__(
        self,
        backbone,
        d_model: int,
        n_horizons: int,
        n_symbols: int,
        n_classes: int,
        hidden_dim: int = 256,
        dropout: float = 0.1,
        target_context_length: int = 512,
        input_lookback: int = 240,
    ):
        super().__init__()
        self.backbone = backbone
        self.target_context_length = target_context_length
        self.input_lookback = input_lookback
        self.pad_amount = target_context_length - input_lookback
        assert self.pad_amount >= 0
        self.head = TTMClassificationHead(d_model, n_horizons, n_symbols, n_classes, hidden_dim, dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, lookback=240, channels=32)
        if self.pad_amount > 0:
            B = x.shape[0]
            pad = torch.zeros(B, self.pad_amount, x.shape[2], device=x.device, dtype=x.dtype)
            x = torch.cat([pad, x], dim=1)
        # Forward through backbone -> (B, n_channels, n_patches, d_model)
        out = self.backbone(past_values=x)
        h = out.last_hidden_state  # (B, n_channels, n_patches, d_model)
        # Pool over channels and patches → (B, d_model)
        pooled = h.mean(dim=(1, 2))
        return self.head(pooled)


# ---------------------------------------------------------------------------
# Forecaster ABC implementation
# ---------------------------------------------------------------------------


class TTMForecaster(Forecaster):
    """IBM Granite TTM-r2 fine-tuned for multi-horizon directional classification."""

    PRETRAINED_NAME = "ibm-granite/granite-timeseries-ttm-r2"

    def __init__(
        self,
        *,
        lookback: int = 240,
        n_channels: int = 32,
        target_context_length: int = 512,
        head_hidden_dim: int = 256,
        head_dropout: float = 0.1,
        batch_size: int = 128,
        learning_rate: float = 5e-4,
        backbone_lr_mult: float = 0.1,  # smaller LR for pretrained backbone
        weight_decay: float = 1e-4,
        max_epochs: int = 6,
        early_stop_patience: int = 2,
        device: str | None = None,
        seed: int = 42,
    ):
        self.lookback = lookback
        self.n_channels = n_channels
        self.target_context_length = target_context_length
        self.head_hidden_dim = head_hidden_dim
        self.head_dropout = head_dropout
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.backbone_lr_mult = backbone_lr_mult
        self.weight_decay = weight_decay
        self.max_epochs = max_epochs
        self.early_stop_patience = early_stop_patience
        self.seed = seed

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)

        torch.manual_seed(seed)
        np.random.seed(seed)

        self._model: TTMClassifier | None = None
        self._n_horizons = len(HORIZON_KEYS)
        self._n_symbols = len(SYMBOL_ORDER)
        self._n_classes = len(CLASS_CODES)

    @property
    def name(self) -> str:
        return "ttm_r2_v0_pad512"

    def _build_model(self) -> TTMClassifier:
        # Lazy import so the rest of the file is importable on CPU-only envs
        from tsfm_public.models.tinytimemixer import TinyTimeMixerModel

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            backbone = TinyTimeMixerModel.from_pretrained(
                self.PRETRAINED_NAME,
                num_input_channels=self.n_channels,
                context_length=self.target_context_length,
                decoder_mode="mix_channel",
                ignore_mismatched_sizes=True,
            )
        d_model = backbone.config.d_model

        model = TTMClassifier(
            backbone=backbone,
            d_model=d_model,
            n_horizons=self._n_horizons,
            n_symbols=self._n_symbols,
            n_classes=self._n_classes,
            hidden_dim=self.head_hidden_dim,
            dropout=self.head_dropout,
            target_context_length=self.target_context_length,
            input_lookback=self.lookback,
        ).to(self.device)
        return model

    def _multi_horizon_loss(self, logits: torch.Tensor, labels_per_h: dict[str, torch.Tensor]) -> torch.Tensor:
        """logits: (B, n_horizons, n_symbols, n_classes); labels_per_h[h_key]: (B, n_symbols) long, -1=ignore."""
        total = torch.tensor(0.0, device=logits.device)
        for h_idx, h_key in enumerate(HORIZON_KEYS):
            y = labels_per_h[h_key].to(self.device).long()
            for s_idx in range(self._n_symbols):
                lo = logits[:, h_idx, s_idx, :]
                ys = y[:, s_idx]
                loss = F.cross_entropy(lo, ys, ignore_index=-1, reduction="mean")
                if torch.isfinite(loss):
                    total = total + loss
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
        train_inputs = np.nan_to_num(train_inputs, copy=False)
        val_inputs = np.nan_to_num(val_inputs, copy=False)

        self._model = self._build_model()
        n_params = sum(p.numel() for p in self._model.parameters())
        n_trainable = sum(p.numel() for p in self._model.parameters() if p.requires_grad)
        print(
            f"    [ttm] params={n_params/1e6:.2f}M  trainable={n_trainable/1e6:.2f}M  device={self.device}",
            flush=True,
        )

        # Param groups: smaller LR for backbone, full LR for head
        backbone_params = list(self._model.backbone.parameters())
        head_params = list(self._model.head.parameters())
        optimizer = torch.optim.AdamW(
            [
                {"params": backbone_params, "lr": self.learning_rate * self.backbone_lr_mult},
                {"params": head_params, "lr": self.learning_rate},
            ],
            weight_decay=self.weight_decay,
        )

        best_val = float("inf")
        patience = 0
        best_state = None

        for epoch in range(self.max_epochs):
            t0 = time.time()
            self._model.train()
            train_loss_sum, n_batches = 0.0, 0
            for x, y_dict in self._iterate_minibatches(train_inputs, dict(train_labels), shuffle=True):
                x = x.to(self.device)
                optimizer.zero_grad()
                logits = self._model(x)
                loss = self._multi_horizon_loss(logits, y_dict)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self._model.parameters(), max_norm=1.0)
                optimizer.step()
                train_loss_sum += float(loss.item())
                n_batches += 1
            train_loss = train_loss_sum / max(1, n_batches)

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
                f"    [ttm] epoch {epoch + 1}/{self.max_epochs}: "
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
                    print(f"    [ttm] early stop at epoch {epoch + 1}", flush=True)
                    break

        if best_state is not None:
            self._model.load_state_dict(best_state)
        self._model.eval()

    def predict_proba(self, inputs: np.ndarray, ts: np.ndarray) -> ForecastBatch:
        if self._model is None:
            raise RuntimeError("TTMForecaster.predict_proba called before fit()")
        inputs = np.nan_to_num(inputs, copy=False)
        self._model.eval()
        n = inputs.shape[0]
        n_symbols = self._n_symbols
        n_classes = self._n_classes

        all_proba = {h: np.zeros((n, n_symbols, n_classes), dtype=np.float32) for h in HORIZON_KEYS}
        with torch.no_grad():
            for start in range(0, n, self.batch_size):
                end = min(n, start + self.batch_size)
                x = torch.from_numpy(inputs[start:end]).float().to(self.device)
                logits = self._model(x)
                proba = F.softmax(logits, dim=-1).cpu().numpy()
                for h_idx, h_key in enumerate(HORIZON_KEYS):
                    all_proba[h_key][start:end] = proba[:, h_idx, :, :]

        return ForecastBatch(
            horizons=HORIZON_KEYS,
            symbols=SYMBOL_ORDER,
            proba=all_proba,
            ts=ts,
            metadata={"model_name": self.name, "pretrained": self.PRETRAINED_NAME},
        )

    def save(self, path: Path) -> None:
        if self._model is None:
            raise RuntimeError("Cannot save before fit()")
        path.mkdir(parents=True, exist_ok=True)
        torch.save(self._model.state_dict(), path / "model_state.pt")
        cfg = {
            "lookback": self.lookback,
            "n_channels": self.n_channels,
            "target_context_length": self.target_context_length,
            "head_hidden_dim": self.head_hidden_dim,
            "head_dropout": self.head_dropout,
            "batch_size": self.batch_size,
            "learning_rate": self.learning_rate,
            "backbone_lr_mult": self.backbone_lr_mult,
            "weight_decay": self.weight_decay,
            "max_epochs": self.max_epochs,
            "early_stop_patience": self.early_stop_patience,
            "seed": self.seed,
        }
        (path / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "TTMForecaster":
        cfg = json.loads((path / "config.json").read_text(encoding="utf-8"))
        obj = cls(**cfg)
        obj._model = obj._build_model()
        state = torch.load(path / "model_state.pt", map_location=obj.device)
        obj._model.load_state_dict(state)
        obj._model.eval()
        return obj


def main() -> int:
    """Self-test: build the model, forward pass, tiny training step."""
    rng = np.random.default_rng(7)
    n_train, n_val = 64, 16
    lookback = 240
    n_channels = 32

    train_inputs = rng.standard_normal((n_train, lookback, n_channels)).astype(np.float32)
    val_inputs = rng.standard_normal((n_val, lookback, n_channels)).astype(np.float32)
    train_labels = {h: rng.choice([0, 1, 2], size=(n_train, len(SYMBOL_ORDER))).astype(np.int64) for h in HORIZON_KEYS}
    val_labels = {h: rng.choice([0, 1, 2], size=(n_val, len(SYMBOL_ORDER))).astype(np.int64) for h in HORIZON_KEYS}

    model = TTMForecaster(max_epochs=1, batch_size=16)
    model.fit(
        train_inputs=train_inputs,
        train_labels=train_labels,
        val_inputs=val_inputs,
        val_labels=val_labels,
        train_ts=np.arange(n_train),
        val_ts=np.arange(n_val) + n_train,
    )
    out = model.predict_proba(val_inputs, np.arange(n_val))
    print(f"\nname: {model.name}")
    for h in HORIZON_KEYS:
        dist = out.proba[h][0, 0]
        print(f"  {h}: first-row first-sym dist = {dist.tolist()}, sum = {dist.sum():.3f}")
    print("self-test OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
