"""Ensemble predictor combining XGBoost and Bi-LSTM models.

Uses weighted averaging of predictions from both models,
with configurable weights that can be optimized via validation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

from app.core.ml.xgboost_model import XGBoostForecaster
from app.core.ml.bilstm_model import BiLSTMForecaster
from app.utils.logging import get_logger

logger = get_logger(__name__)


class EnsembleForecaster:
    """Weighted ensemble combining XGBoost and Bi-LSTM predictions.

    The ensemble uses a weighted average:
        prediction = w_xgb * xgb_pred + w_lstm * lstm_pred

    Weights can be set manually or optimized on validation data.

    Usage:
        ensemble = EnsembleForecaster(task="classification")
        ensemble.set_models(xgb_model, lstm_model)
        ensemble.optimize_weights(X_val, y_val)
        predictions = ensemble.predict(X_new)
    """

    def __init__(
        self,
        task: str = "classification",
        xgb_weight: float = 0.6,
        lstm_weight: float = 0.4,
    ) -> None:
        self._task = task
        self._xgb_weight = xgb_weight
        self._lstm_weight = lstm_weight
        self._xgb_model: XGBoostForecaster | None = None
        self._lstm_model: BiLSTMForecaster | None = None
        self._optimized = False

    @property
    def task(self) -> str:
        return self._task

    @property
    def weights(self) -> dict[str, float]:
        return {
            "xgboost": round(self._xgb_weight, 4),
            "bilstm": round(self._lstm_weight, 4),
        }

    def set_models(
        self,
        xgb_model: XGBoostForecaster,
        lstm_model: BiLSTMForecaster,
    ) -> None:
        """Set the component models."""
        self._xgb_model = xgb_model
        self._lstm_model = lstm_model
        logger.info("Ensemble models configured.")

    def predict(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        """Generate ensemble predictions.

        Args:
            X: Feature DataFrame/array.

        Returns:
            Weighted ensemble predictions.
        """
        if self._xgb_model is None or self._lstm_model is None:
            raise RuntimeError("Both models must be set before prediction.")

        xgb_preds = self._get_xgb_predictions(X)
        lstm_preds = self._get_lstm_predictions(X)

        # Align lengths (LSTM output is shorter due to sequence windowing)
        min_len = min(len(xgb_preds), len(lstm_preds))
        xgb_aligned = xgb_preds[-min_len:]
        lstm_aligned = lstm_preds[-min_len:]

        ensemble_preds = (
            self._xgb_weight * xgb_aligned + self._lstm_weight * lstm_aligned
        )

        if self._task == "classification":
            ensemble_preds = np.clip(ensemble_preds, 0.0, 1.0)

        return ensemble_preds

    def predict_classes(self, X: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        """Predict binary classes from ensemble probabilities."""
        if self._task != "classification":
            raise ValueError("predict_classes only for classification.")
        probs = self.predict(X)
        return (probs >= threshold).astype(int)

    def optimize_weights(
        self,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        grid_steps: int = 21,
    ) -> dict[str, Any]:
        """Optimize ensemble weights on validation data.

        Performs grid search over weight combinations [0, 1] in steps.

        Args:
            X_val: Validation features.
            y_val: Validation targets.
            grid_steps: Number of weight steps to try.

        Returns:
            Optimization results with best weights and score.
        """
        if self._xgb_model is None or self._lstm_model is None:
            raise RuntimeError("Both models must be set.")

        xgb_preds = self._get_xgb_predictions(X_val)
        lstm_preds = self._get_lstm_predictions(X_val)

        min_len = min(len(xgb_preds), len(lstm_preds))
        xgb_aligned = xgb_preds[-min_len:]
        lstm_aligned = lstm_preds[-min_len:]
        y_aligned = y_val.values[-min_len:] if isinstance(y_val, pd.Series) else y_val[-min_len:]

        best_score = -float("inf")
        best_w = 0.5

        for i in range(grid_steps):
            w = i / (grid_steps - 1)
            combined = w * xgb_aligned + (1 - w) * lstm_aligned

            if self._task == "classification":
                preds = (combined >= 0.5).astype(int)
                from sklearn.metrics import accuracy_score
                score = accuracy_score(y_aligned, preds)
            else:
                from sklearn.metrics import r2_score
                score = r2_score(y_aligned, combined)

            if score > best_score:
                best_score = score
                best_w = w

        self._xgb_weight = best_w
        self._lstm_weight = 1 - best_w
        self._optimized = True

        result = {
            "optimized": True,
            "best_xgb_weight": round(best_w, 4),
            "best_lstm_weight": round(1 - best_w, 4),
            "best_score": round(float(best_score), 6),
            "metric": "accuracy" if self._task == "classification" else "r2",
        }
        logger.info("Ensemble weights optimized: %s", result)
        return result

    def get_model_contributions(
        self, X: pd.DataFrame
    ) -> dict[str, np.ndarray]:
        """Get individual model predictions for analysis."""
        xgb_preds = self._get_xgb_predictions(X)
        lstm_preds = self._get_lstm_predictions(X)
        min_len = min(len(xgb_preds), len(lstm_preds))

        return {
            "xgboost": xgb_preds[-min_len:],
            "bilstm": lstm_preds[-min_len:],
            "ensemble": self.predict(X),
        }

    def _get_xgb_predictions(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        """Get XGBoost predictions (probabilities for classification)."""
        if self._task == "classification":
            probs = self._xgb_model.predict_proba(X if isinstance(X, pd.DataFrame) else pd.DataFrame(X))
            return probs[:, 1]  # P(class=1)
        return self._xgb_model.predict(X if isinstance(X, pd.DataFrame) else pd.DataFrame(X))

    def _get_lstm_predictions(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        """Get Bi-LSTM predictions."""
        return self._lstm_model.predict(X)
