"""XGBoost model for financial return prediction.

Provides training, validation, prediction, and feature importance
for tabular feature sets combining technical indicators and sentiment.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import TimeSeriesSplit

from app.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_PARAMS: Final[dict[str, Any]] = {
    "n_estimators": 500,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 3,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "random_state": 42,
    "n_jobs": -1,
    "verbosity": 0,
}


class XGBoostForecaster:
    """XGBoost-based forecaster for financial time series.

    Supports both regression (return prediction) and classification
    (direction prediction) modes.

    Usage:
        model = XGBoostForecaster(task="classification")
        metrics = model.train(X_train, y_train, X_val, y_val)
        predictions = model.predict(X_new)
    """

    def __init__(
        self,
        task: str = "classification",
        params: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the XGBoost forecaster.

        Args:
            task: 'classification' for direction prediction, 'regression' for return prediction.
            params: XGBoost hyperparameters. Defaults to DEFAULT_PARAMS.
        """
        import xgboost as xgb

        self._task = task
        self._params = {**DEFAULT_PARAMS, **(params or {})}
        self._feature_names: list[str] = []
        self._trained_at: datetime | None = None

        if task == "classification":
            self._params["objective"] = "binary:logistic"
            self._params["eval_metric"] = "logloss"
            self._model = xgb.XGBClassifier(**self._params)
        else:
            self._params["objective"] = "reg:squarederror"
            self._params["eval_metric"] = "rmse"
            self._model = xgb.XGBRegressor(**self._params)

    @property
    def is_trained(self) -> bool:
        """Check if the model has been trained."""
        return self._trained_at is not None

    @property
    def task(self) -> str:
        return self._task

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame | None = None,
        y_val: pd.Series | None = None,
        early_stopping_rounds: int = 50,
    ) -> dict[str, Any]:
        """Train the XGBoost model.

        Args:
            X_train: Training features.
            y_train: Training target.
            X_val: Validation features (optional).
            y_val: Validation target (optional).
            early_stopping_rounds: Rounds for early stopping.

        Returns:
            Dictionary with training metrics.
        """
        self._feature_names = list(X_train.columns)
        logger.info(
            "Training XGBoost (%s) on %d samples, %d features.",
            self._task, len(X_train), len(self._feature_names),
        )

        fit_kwargs: dict[str, Any] = {}
        if X_val is not None and y_val is not None:
            fit_kwargs["eval_set"] = [(X_val, y_val)]
            fit_kwargs["verbose"] = False

        self._model.fit(X_train, y_train, **fit_kwargs)
        self._trained_at = datetime.now(tz=timezone.utc)

        # Compute metrics
        metrics = self._compute_metrics(X_train, y_train, prefix="train")
        if X_val is not None and y_val is not None:
            val_metrics = self._compute_metrics(X_val, y_val, prefix="val")
            metrics.update(val_metrics)

        metrics["trained_at"] = self._trained_at.isoformat()
        metrics["n_features"] = len(self._feature_names)
        metrics["n_train_samples"] = len(X_train)

        logger.info("XGBoost training complete. Metrics: %s", json.dumps({k: v for k, v in metrics.items() if isinstance(v, (int, float, str))}, indent=2))
        return metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generate predictions.

        Args:
            X: Feature DataFrame.

        Returns:
            Predicted values (probabilities for classification, values for regression).
        """
        if not self.is_trained:
            raise RuntimeError("Model has not been trained. Call train() first.")
        return self._model.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Get prediction probabilities (classification only).

        Args:
            X: Feature DataFrame.

        Returns:
            Array of shape (n_samples, 2) with [P(class_0), P(class_1)].
        """
        if self._task != "classification":
            raise ValueError("predict_proba is only available for classification tasks.")
        if not self.is_trained:
            raise RuntimeError("Model has not been trained.")
        return self._model.predict_proba(X)

    def get_feature_importance(self, importance_type: str = "gain") -> dict[str, float]:
        """Get feature importance scores.

        Args:
            importance_type: Type of importance ('gain', 'weight', 'cover').

        Returns:
            Dictionary mapping feature names to importance scores, sorted descending.
        """
        if not self.is_trained:
            raise RuntimeError("Model has not been trained.")

        importance = self._model.feature_importances_
        importance_dict = dict(zip(self._feature_names, importance.tolist()))
        return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))

    def cross_validate(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_splits: int = 5,
    ) -> dict[str, Any]:
        """Time-series cross-validation.

        Uses TimeSeriesSplit to respect temporal ordering.

        Args:
            X: Feature DataFrame.
            y: Target Series.
            n_splits: Number of CV folds.

        Returns:
            Dictionary with per-fold and aggregate metrics.
        """
        tscv = TimeSeriesSplit(n_splits=n_splits)
        fold_metrics: list[dict[str, Any]] = []

        for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(X)):
            X_train_fold = X.iloc[train_idx]
            y_train_fold = y.iloc[train_idx]
            X_val_fold = X.iloc[val_idx]
            y_val_fold = y.iloc[val_idx]

            # Clone model for this fold
            fold_model = XGBoostForecaster(task=self._task, params=self._params)
            metrics = fold_model.train(X_train_fold, y_train_fold, X_val_fold, y_val_fold)
            metrics["fold"] = fold_idx
            fold_metrics.append(metrics)

        # Aggregate
        result: dict[str, Any] = {"n_splits": n_splits, "folds": fold_metrics}
        if self._task == "classification":
            val_accs = [m.get("val_accuracy", 0) for m in fold_metrics]
            result["mean_val_accuracy"] = float(np.mean(val_accs))
            result["std_val_accuracy"] = float(np.std(val_accs))
        else:
            val_r2s = [m.get("val_r2", 0) for m in fold_metrics]
            result["mean_val_r2"] = float(np.mean(val_r2s))
            result["std_val_r2"] = float(np.std(val_r2s))

        logger.info("Cross-validation complete: %d folds.", n_splits)
        return result

    def save(self, path: Path) -> None:
        """Save model to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        self._model.save_model(str(path))
        logger.info("XGBoost model saved to %s.", path)

    def load(self, path: Path) -> None:
        """Load model from disk."""
        self._model.load_model(str(path))
        self._feature_names = self._model.get_booster().feature_names or []
        self._trained_at = datetime.now(tz=timezone.utc)
        logger.info("XGBoost model loaded from %s.", path)

    def _compute_metrics(
        self, X: pd.DataFrame, y: pd.Series, prefix: str = ""
    ) -> dict[str, Any]:
        """Compute evaluation metrics."""
        preds = self.predict(X)
        metrics: dict[str, Any] = {}
        p = f"{prefix}_" if prefix else ""

        if self._task == "classification":
            metrics[f"{p}accuracy"] = round(float(accuracy_score(y, preds)), 6)
        else:
            metrics[f"{p}mse"] = round(float(mean_squared_error(y, preds)), 8)
            metrics[f"{p}rmse"] = round(float(np.sqrt(mean_squared_error(y, preds))), 8)
            metrics[f"{p}mae"] = round(float(mean_absolute_error(y, preds)), 8)
            metrics[f"{p}r2"] = round(float(r2_score(y, preds)), 6)

        return metrics
