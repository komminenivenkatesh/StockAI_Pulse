"""Pydantic schemas for market data endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Nested Schemas ───────────────────────────────────────────


class OHLCVBar(BaseModel):
    """Single OHLCV bar."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class IndicatorValues(BaseModel):
    """Technical indicator values for a single bar."""

    timestamp: datetime
    rsi: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    ema_12: float | None = None
    ema_26: float | None = None
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    atr: float | None = None
    stoch_k: float | None = None
    stoch_d: float | None = None


class MarketSummary(BaseModel):
    """Summary statistics for market data."""

    current_price: float
    change_pct: float = Field(..., description="Percentage change from previous close.")
    high_52w: float | None = None
    low_52w: float | None = None
    avg_volume: float | None = None
    volatility_20d: float | None = None


class ResponseMeta(BaseModel):
    """Standard response metadata."""

    timestamp: datetime
    ticker: str
    asset_type: str
    exchange: str
    currency: str
    bars: int
    period: str | None = None
    interval: str | None = None


# ── Response Schemas ─────────────────────────────────────────


class MarketDataPayload(BaseModel):
    """Data payload for market data response."""

    ticker: str
    summary: MarketSummary
    ohlcv: list[OHLCVBar]
    indicators: list[IndicatorValues] | None = None


class MarketDataResponse(BaseModel):
    """Full market data response with OHLCV bars."""

    model_config = ConfigDict(populate_by_name=True)

    status: str = "ok"
    data: MarketDataPayload
    meta: ResponseMeta


class IndicatorsPayload(BaseModel):
    """Data payload for indicators response."""

    ticker: str
    indicators: list[IndicatorValues]


class IndicatorsResponse(BaseModel):
    """Response for technical indicators only."""

    status: str = "ok"
    data: IndicatorsPayload
    meta: ResponseMeta


class SearchItem(BaseModel):
    """Single search suggestion."""

    symbol: str
    name: str
    exchange: str
    type: str


class SearchResponse(BaseModel):
    """Response for market search suggestions."""

    status: str = "ok"
    data: list[SearchItem]
