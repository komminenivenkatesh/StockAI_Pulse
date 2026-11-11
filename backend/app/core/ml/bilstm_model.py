"""Bi-LSTM model for financial time series forecasting.

Uses PyTorch to build a Bidirectional LSTM that operates on
sequential windows of features for direction/return prediction.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

from app.utils.logging import get_logger

logger = get_logger(__name__)

# Defaults
DEFAULT_HIDDEN_SIZE: Final[int] = 128
DEFAULT_NUM_LAYERS: Final[int] = 2
DEFAULT_DROPOUT: Final[float] = 0.3
DEFAULT_SEQUENCE_LENGTH: Final[int] = 30
DEFAULT_LEARNING_RATE: Final[float] = 1e-3
DEFAULT_EPOCHS: Final[int] = 50
DEFAULT_BATCH_SIZE: Final[int] = 64


# ── Dataset ──────────────────────────────────────────────────


class TimeSeriesDataset(Dataset):
    """PyTorch Dataset for sequential time series windows."""

    def __init__(
        self,
        features: np.ndarray,
        targets: np.ndarray,
        sequence_length: int = DEFAULT_SEQUENCE_LENGTH,
    ) -> None:
        self._features = features
        self._targets = targets
        self._seq_len = sequence_length

    def __len__(self) -> int:
        return len(self._features) - self._seq_len

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        x = self._features[idx : idx + self._seq_len]
        y = self._targets[idx + self._seq_len]
        return (
            torch.tensor(x, dtype=torch.float32),
            torch.tensor(y, dtype=torch.float32),
        )


# ── Model Architecture ───────────────────────────────────────


class BiLSTMNetwork(nn.Module):
    """Bidirectional LSTM network for sequence prediction."""

    def __init__(
        self,
        input_size: int,
        hidden_size: int = DEFAULT_HIDDEN_SIZE,
        num_layers: int = DEFAULT_NUM_LAYERS,
        dropout: float = DEFAULT_DROPOUT,
        task: str = "classification",
    ) -> None:
        super().__init__()
        self.task = task

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
            bidirectional=True,
        )

        self.attention = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.Tanh(),
            nn.Linear(hidden_size, 1),
        )

        self.fc = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout / 2),
            nn.Linear(hidden_size // 2, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Args:
            x: Input tensor of shape (batch, seq_len, input_size).

        Returns:
            Output tensor of shape (batch, 1).
        """
        lstm_out, _ = self.lstm(x)  # (batch, seq_len, hidden*2)

        # Attention mechanism
        attn_weights = self.attention(lstm_out)  # (batch, seq_len, 1)
        attn_weights = torch.softmax(attn_weights, dim=1)
        context = (lstm_out * attn_weights).sum(dim=1)  # (batch, hidden*2)

        output = self.fc(context)  # (batch, 1)

        if self.task == "classification":
            output = torch.sigmoid(output)

        return output.squeeze(-1)


# ── Trainer ──────────────────────────────────────────────────


class BiLSTMForecaster:
    """High-level wrapper for training and inference with the Bi-LSTM model.

    Usage:
        model = BiLSTMForecaster(input_size=30, task="classification")
        metrics = model.train(X_train, y_train, X_val, y_val)
        preds = model.predict(X_new)
    """

    def __init__(
        self,
        input_size: int,
        task: str = "classification",
        hidden_size: int = DEFAULT_HIDDEN_SIZE,
        num_layers: int = DEFAULT_NUM_LAYERS,
        dropout: float = DEFAULT_DROPOUT,
        sequence_length: int = DEFAULT_SEQUENCE_LENGTH,
        learning_rate: float = DEFAULT_LEARNING_RATE,
        epochs: int = DEFAULT_EPOCHS,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self._task = task
        self._seq_len = sequence_length
        self._epochs = epochs
        self._batch_size = batch_size
        self._lr = learning_rate
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._trained_at: datetime | None = None
        self._input_size = input_size
        self._train_losses: list[float] = []
        self._val_losses: list[float] = []

        self._network = BiLSTMNetwork(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            task=task,
        ).to(self._device)

        if task == "classification":
            self._criterion = nn.BCELoss()
        else:
            self._criterion = nn.MSELoss()

        self._optimizer = torch.optim.Adam(
            self._network.parameters(), lr=learning_rate, weight_decay=1e-5
        )
        self._scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self._optimizer, mode="min", factor=0.5, patience=5, verbose=False
        )

    @property
    def is_trained(self) -> bool:
        return self._trained_at is not None

    @property
    def task(self) -> str:
        return self._task

    def train(
        self,
        X_train: pd.DataFrame | np.ndarray,
        y_train: pd.Series | np.ndarray,
        X_val: pd.DataFrame | np.ndarray | None = None,
        y_val: pd.Series | np.ndarray | None = None,
        patience: int = 10,
    ) -> dict[str, Any]:
        """Train the Bi-LSTM model.

        Args:
            X_train: Training features (will be windowed into sequences).
            y_train: Training targets.
            X_val: Validation features.
            y_val: Validation targets.
            patience: Early stopping patience.

        Returns:
            Dictionary with training metrics and loss curves.
        """
        X_train_np = X_train.values if isinstance(X_train, pd.DataFrame) else X_train
        y_train_np = y_train.values if isinstance(y_train, pd.Series) else y_train

        # Normalize features
        self._mean = X_train_np.mean(axis=0)
        self._std = X_train_np.std(axis=0)
        self._std[self._std == 0] = 1.0  # Avoid division by zero
        X_train_norm = (X_train_np - self._mean) / self._std

        train_dataset = TimeSeriesDataset(X_train_norm, y_train_np, self._seq_len)
        train_loader = DataLoader(
            train_dataset, batch_size=self._batch_size, shuffle=False  # Keep temporal order
        )

        val_loader = None
        if X_val is not None and y_val is not None:
            X_val_np = X_val.values if isinstance(X_val, pd.DataFrame) else X_val
            y_val_np = y_val.values if isinstance(y_val, pd.Series) else y_val
            X_val_norm = (X_val_np - self._mean) / self._std
            val_dataset = TimeSeriesDataset(X_val_norm, y_val_np, self._seq_len)
            val_loader = DataLoader(val_dataset, batch_size=self._batch_size, shuffle=False)

        logger.info(
            "Training Bi-LSTM (%s) — %d epochs, seq_len=%d, device=%s",
            self._task, self._epochs, self._seq_len, self._device,
        )

        best_val_loss = float("inf")
        patience_counter = 0
        best_state = None

        self._network.train()
        for epoch in range(self._epochs):
            epoch_loss = self._train_epoch(train_loader)
            self._train_losses.append(epoch_loss)

            val_loss = None
            if val_loader is not None:
                val_loss = self._validate_epoch(val_loader)
                self._val_losses.append(val_loss)
                self._scheduler.step(val_loss)

                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    best_state = self._network.state_dict().copy()
                else:
                    patience_counter += 1
                    if patience_counter >= patience:
                        logger.info("Early stopping at epoch %d.", epoch + 1)
                        break

            if (epoch + 1) % 10 == 0:
                msg = f"Epoch {epoch+1}/{self._epochs} — train_loss: {epoch_loss:.6f}"
                if val_loss is not None:
                    msg += f", val_loss: {val_loss:.6f}"
                logger.info(msg)

        # Restore best weights
        if best_state is not None:
            self._network.load_state_dict(best_state)

        self._trained_at = datetime.now(tz=timezone.utc)

        metrics: dict[str, Any] = {
            "task": self._task,
            "epochs_trained": len(self._train_losses),
            "final_train_loss": self._train_losses[-1],
            "train_losses": self._train_losses,
            "trained_at": self._trained_at.isoformat(),
        }
        if self._val_losses:
            metrics["best_val_loss"] = best_val_loss
            metrics["val_losses"] = self._val_losses

        logger.info("Bi-LSTM training complete.")
        return metrics

    def predict(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        """Generate predictions on new data.

        Args:
            X: Feature array/DataFrame (will be windowed).

        Returns:
            Predictions array. For classification: probabilities.
        """
        if not self.is_trained:
            raise RuntimeError("Model has not been trained.")

        X_np = X.values if isinstance(X, pd.DataFrame) else X
        X_norm = (X_np - self._mean) / self._std

        self._network.eval()
        predictions: list[float] = []

        with torch.no_grad():
            for i in range(len(X_norm) - self._seq_len):
                seq = X_norm[i : i + self._seq_len]
                tensor = torch.tensor(seq, dtype=torch.float32).unsqueeze(0).to(self._device)
                pred = self._network(tensor)
                predictions.append(pred.cpu().item())

        return np.array(predictions)

    def predict_classes(self, X: pd.DataFrame | np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Predict binary classes (classification only)."""
        if self._task != "classification":
            raise ValueError("predict_classes only available for classification.")
        probs = self.predict(X)
        return (probs >= threshold).astype(int)

    def save(self, path: Path) -> None:
        """Save model weights and normalization parameters."""
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "state_dict": self._network.state_dict(),
                "mean": self._mean,
                "std": self._std,
                "input_size": self._input_size,
                "task": self._task,
                "seq_len": self._seq_len,
            },
            str(path),
        )
        logger.info("Bi-LSTM model saved to %s.", path)

    def load(self, path: Path) -> None:
        """Load model weights and normalization parameters."""
        checkpoint = torch.load(str(path), map_location=self._device)
        self._network.load_state_dict(checkpoint["state_dict"])
        self._mean = checkpoint["mean"]
        self._std = checkpoint["std"]
        self._trained_at = datetime.now(tz=timezone.utc)
        logger.info("Bi-LSTM model loaded from %s.", path)

    def _train_epoch(self, loader: DataLoader) -> float:
        """Train for one epoch."""
        self._network.train()
        total_loss = 0.0
        n_batches = 0

        for X_batch, y_batch in loader:
            X_batch = X_batch.to(self._device)
            y_batch = y_batch.to(self._device)

            self._optimizer.zero_grad()
            output = self._network(X_batch)
            loss = self._criterion(output, y_batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self._network.parameters(), max_norm=1.0)
            self._optimizer.step()

            total_loss += loss.item()
            n_batches += 1

        return total_loss / max(n_batches, 1)

    def _validate_epoch(self, loader: DataLoader) -> float:
        """Validate for one epoch."""
        self._network.eval()
        total_loss = 0.0
        n_batches = 0

        with torch.no_grad():
            for X_batch, y_batch in loader:
                X_batch = X_batch.to(self._device)
                y_batch = y_batch.to(self._device)
                output = self._network(X_batch)
                loss = self._criterion(output, y_batch)
                total_loss += loss.item()
                n_batches += 1

        return total_loss / max(n_batches, 1)
