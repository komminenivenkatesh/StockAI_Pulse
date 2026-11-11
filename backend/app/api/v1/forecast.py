"""Forecast API endpoints.

Provides:
  - POST /train           — train XGBoost model for a ticker
  - GET  /predict/{ticker} — generate forecast predictions
  - GET  /models           — list available trained models
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Path as FastAPIPath, Query

from app.config import Settings, get_settings
from app.core.market.data_fetcher import MarketDataFetcher
from app.core.market.feature_eng import (
    build_feature_matrix,
    create_classification_target,
    train_test_split_temporal,
)
from app.core.ml.registry import ModelRegistry
from app.core.ml.xgboost_model import XGBoostForecaster
from app.models.forecast import (
    FeatureImportance,
    ForecastData,
    ForecastPoint,
    ForecastResponse,
    ModelInfo,
    ModelsListData,
    ModelsListResponse,
    ResponseMeta,
    TrainData,
    TrainRequest,
    TrainResponse,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _get_registry(settings: Settings = Depends(get_settings)) -> ModelRegistry:
    """Get the model registry."""
    return ModelRegistry(base_dir=settings.ml_artifacts_dir)


@router.post(
    "/train",
    response_model=TrainResponse,
    summary="Train a forecast model",
)
async def train_model(
    body: TrainRequest,
    settings: Settings = Depends(get_settings),
) -> TrainResponse:
    """Train an XGBoost model on historical data for a ticker."""
    ticker = body.ticker.upper()
    logger.info("Training model for %s (task=%s, period=%s)", ticker, body.task, body.period)

    # 1. Fetch market data
    fetcher = MarketDataFetcher()
    market_data = await fetcher.fetch(ticker, period=body.period, interval="1d")

    if len(market_data.df) < 100:
        raise HTTPException(
            status_code=422,
            detail=f"Insufficient data for {ticker}: {len(market_data.df)} bars (need >=100).",
        )

    # 2. Build feature matrix
    features, target = build_feature_matrix(
        market_data.df,
        forecast_horizon=body.forecast_horizon,
    )

    # 3. Convert target for classification
    if body.task == "classification":
        target = create_classification_target(target)

    # 4. Temporal split
    X_train, X_val, y_train, y_val = train_test_split_temporal(
        features, target, body.train_ratio
    )

    # 5. Train XGBoost
    model = XGBoostForecaster(task=body.task)
    metrics = model.train(X_train, y_train, X_val, y_val)

    # 6. Save model
    registry = ModelRegistry(base_dir=settings.ml_artifacts_dir)
    model_dir = registry.get_model_dir("xgboost", ticker)
    version_str = registry._next_version("xgboost", ticker)
    model_path = model_dir / f"{version_str}.json"
    model.save(model_path)

    # 7. Register
    version = registry.register(
        model_name=f"XGBoost-{ticker}",
        model_type="xgboost",
        task=body.task,
        ticker=ticker,
        file_path=model_path,
        metrics={
            k: v for k, v in metrics.items()
            if isinstance(v, (int, float, str))
        },
    )

    # 8. Feature importance
    importance = model.get_feature_importance()
    top_features = [
        FeatureImportance(feature=k, importance=round(v, 6))
        for k, v in list(importance.items())[:15]
    ]

    return TrainResponse(
        status="ok",
        data=TrainData(
            ticker=ticker,
            model_type="xgboost",
            version=version.version,
            task=body.task,
            metrics={k: v for k, v in metrics.items() if isinstance(v, (int, float, str))},
            feature_importance=top_features,
            samples_train=len(X_train),
            samples_val=len(X_val),
        ),
        meta=ResponseMeta(
            timestamp=datetime.now(tz=timezone.utc),
            ticker=ticker,
            model_type="xgboost",
            version=version.version,
        ),
    )


@router.get(
    "/predict/{ticker:path}",
    response_model=ForecastResponse,
    summary="Generate forecast predictions",
)
async def predict(
    ticker: Annotated[str, FastAPIPath(min_length=1, max_length=20, description="Ticker symbol")],
    days: Annotated[int, Query(ge=1, le=30, description="Number of days to forecast")] = 5,
    settings: Settings = Depends(get_settings),
) -> ForecastResponse:
    """Generate forecast predictions using a trained model (auto-trains if needed)."""
    ticker = ticker.upper()

    # 1. Load model from registry
    registry = ModelRegistry(base_dir=settings.ml_artifacts_dir)
    model_version = registry.get_latest("xgboost", ticker)

    if model_version is None:
        logger.info("No trained model found for %s; auto-training XGBoost on the fly...", ticker)
        try:
            await train_model(
                TrainRequest(ticker=ticker, period="2y", task="classification"),
                settings=settings,
            )
            # Re-read registry from disk after training saves a new version
            registry = ModelRegistry(base_dir=settings.ml_artifacts_dir)
            model_version = registry.get_latest("xgboost", ticker)
        except Exception as exc:
            logger.warning("Auto-training failed for %s: %s", ticker, exc)
            raise HTTPException(
                status_code=404,
                detail=f"Could not generate forecast for {ticker}: {exc}",
            )

    if model_version is None:
        raise HTTPException(
            status_code=404,
            detail=f"No trained model could be found or created for {ticker}.",
        )

    model = XGBoostForecaster(task=model_version.task)
    model.load(Path(model_version.file_path))

    # 2. Fetch recent market data (use 2y to ensure 200-day SMA has enough bars)
    fetcher = MarketDataFetcher()
    market_data = await fetcher.fetch(ticker, period="2y", interval="1d")

    # 3. Build features using build_feature_matrix to match training features exactly
    features, _ = build_feature_matrix(market_data.df)

    if features.empty:
        raise HTTPException(status_code=422, detail="Insufficient data to generate features.")

    # 4. Generate predictions on recent data
    recent_features = features.tail(days)
    predictions_raw = model.predict(recent_features)

    # 5. Build forecast points
    forecast_points: list[ForecastPoint] = []
    if model_version.task == "classification":
        probs = model.predict_proba(recent_features)
        for i, (idx, _) in enumerate(recent_features.iterrows()):
            direction = "up" if predictions_raw[i] == 1 else "down"
            confidence = float(max(probs[i]))
            forecast_points.append(
                ForecastPoint(
                    timestamp=idx.to_pydatetime(),
                    predicted_direction=direction,
                    confidence=round(confidence, 4),
                )
            )
    else:
        for i, (idx, _) in enumerate(recent_features.iterrows()):
            direction = "up" if predictions_raw[i] > 0 else "down"
            forecast_points.append(
                ForecastPoint(
                    timestamp=idx.to_pydatetime(),
                    predicted_direction=direction,
                    confidence=0.5,
                    predicted_return=round(float(predictions_raw[i]), 6),
                )
            )

    # 6. Overall signal
    up_count = sum(1 for p in forecast_points if p.predicted_direction == "up")
    ratio = up_count / len(forecast_points) if forecast_points else 0.5
    if ratio >= 0.6:
        signal = "Bullish"
    elif ratio <= 0.4:
        signal = "Bearish"
    else:
        signal = "Neutral"

    avg_confidence = float(np.mean([p.confidence for p in forecast_points]))

    # Feature importance
    importance = model.get_feature_importance()
    top_features = [
        FeatureImportance(feature=k, importance=round(v, 6))
        for k, v in list(importance.items())[:10]
    ]

    return ForecastResponse(
        status="ok",
        data=ForecastData(
            ticker=ticker,
            signal=signal,
            confidence=round(avg_confidence, 4),
            predictions=forecast_points,
            feature_importance=top_features,
            model_info=ModelInfo(
                model_type=model_version.model_type,
                version=model_version.version,
                task=model_version.task,
                trained_at=model_version.created_at,
                metrics=model_version.metrics,
            ),
        ),
        meta=ResponseMeta(
            timestamp=datetime.now(tz=timezone.utc),
            ticker=ticker,
            model_type=model_version.model_type,
            version=model_version.version,
        ),
    )


@router.get(
    "/models",
    response_model=ModelsListResponse,
    summary="List trained models",
)
async def list_models(
    ticker: Annotated[str | None, Query(description="Filter by ticker")] = None,
    model_type: Annotated[str | None, Query(description="Filter by model type")] = None,
    settings: Settings = Depends(get_settings),
) -> ModelsListResponse:
    """List all trained models with optional filtering."""
    registry = ModelRegistry(base_dir=settings.ml_artifacts_dir)
    versions = registry.get_all(model_type=model_type, ticker=ticker)

    models = [
        ModelInfo(
            model_type=v.model_type,
            version=v.version,
            task=v.task,
            trained_at=v.created_at,
            metrics=v.metrics,
        )
        for v in versions
    ]

    return ModelsListResponse(
        status="ok",
        data=ModelsListData(models=models, total=len(models)),
        meta=ResponseMeta(
            timestamp=datetime.now(tz=timezone.utc),
            ticker=ticker or "all",
        ),
    )
