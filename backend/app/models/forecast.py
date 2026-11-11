"""Pydantic schemas for forecast endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Nested Schemas ───────────────────────────────────────────


class ForecastPoint(BaseModel):
    """A single forecast data point."""

    timestamp: datetime
    predicted_direction: str = Field(..., description="'up' or 'down'")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence.")
    predicted_return: float | None = Field(None, description="Predicted return value (regression).")


class FeatureImportance(BaseModel):
    """Feature importance entry."""

    feature: str
    importance: float


class ModelInfo(BaseModel):
    """Information about a trained model."""

    model_type: str
    version: str
    task: str
    trained_at: str
    metrics: dict[str, Any] = Field(default_factory=dict)


class TrainRequest(BaseModel):
    """Request body for model training."""

    model_config = ConfigDict(strict=True)

    ticker: str = Field(..., min_length=1, max_length=30)
    period: str = Field(default="2y", description="Historical data period.")
    task: str = Field(default="classification", pattern="^(classification|regression)$")
    forecast_horizon: int = Field(default=1, ge=1, le=30)
    train_ratio: float = Field(default=0.8, ge=0.5, le=0.95)


class ResponseMeta(BaseModel):
    """Standard response metadata."""

    timestamp: datetime
    ticker: str
    model_type: str | None = None
    version: str | None = None


# ── Response Schemas ─────────────────────────────────────────


class ForecastData(BaseModel):
    """Forecast response data payload."""

    ticker: str
    signal: str = Field(..., description="Overall signal: Bullish / Bearish / Neutral")
    confidence: float = Field(..., ge=0.0, le=1.0)
    predictions: list[ForecastPoint]
    feature_importance: list[FeatureImportance] | None = None
    model_info: ModelInfo


class ForecastResponse(BaseModel):
    """Full forecast response."""

    status: str = "ok"
    data: ForecastData
    meta: ResponseMeta


class TrainData(BaseModel):
    """Training response data payload."""

    ticker: str
    model_type: str
    version: str
    task: str
    metrics: dict[str, Any]
    feature_importance: list[FeatureImportance] | None = None
    samples_train: int
    samples_val: int


class TrainResponse(BaseModel):
    """Training response."""

    status: str = "ok"
    data: TrainData
    meta: ResponseMeta


class ModelsListData(BaseModel):
    """Data for listing models."""

    models: list[ModelInfo]
    total: int


class ModelsListResponse(BaseModel):
    """Response for listing available models."""

    status: str = "ok"
    data: ModelsListData
    meta: ResponseMeta
