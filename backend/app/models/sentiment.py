"""Pydantic schemas for sentiment analysis endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Request Schemas ──────────────────────────────────────────


class SentimentRequest(BaseModel):
    """Request body for analyzing custom headlines."""

    model_config = ConfigDict(strict=True)

    headlines: list[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of headlines to analyze (1-100).",
    )


# ── Response Schemas ─────────────────────────────────────────


class HeadlineScore(BaseModel):
    """Sentiment score for a single headline with domain reputation tiering."""

    headline: str
    positive: float = Field(..., ge=0.0, le=1.0)
    negative: float = Field(..., ge=0.0, le=1.0)
    neutral: float = Field(..., ge=0.0, le=1.0)
    compound: float = Field(..., ge=-1.0, le=1.0)
    label: str = Field(..., pattern="^(positive|negative|neutral)$")
    source: str = "Financial Wire"
    source_tier: int = 1
    trust_label: str = "Tier 1: High Trust"
    tier_weight: float = 1.0
    url: str = ""


class SentimentAggregation(BaseModel):
    """Aggregated sentiment for a time bucket."""

    timestamp: datetime
    compound_score: float = Field(..., ge=-1.0, le=1.0)
    headline_count: int = Field(..., ge=0)


class ResponseMeta(BaseModel):
    """Standard response metadata."""

    timestamp: datetime
    ticker: str | None = None
    model: str = "ProsusAI/finbert"
    cached_items: int | None = None


class TickerSentimentData(BaseModel):
    """Data payload for ticker sentiment."""

    ticker: str
    current_score: float = Field(..., ge=-1.0, le=1.0, description="Current weighted sentiment.")
    signal: str = Field(..., description="Bullish / Bearish / Neutral signal.")
    headline_scores: list[HeadlineScore]
    rolling_sentiment: list[SentimentAggregation]
    total_articles: int = Field(..., ge=0)


class TickerSentimentResponse(BaseModel):
    """Full sentiment analysis response for a ticker."""

    model_config = ConfigDict(populate_by_name=True)

    status: str = "ok"
    data: TickerSentimentData
    meta: ResponseMeta


class HeadlineSentimentResponse(BaseModel):
    """Response for custom headline analysis."""

    status: str = "ok"
    data: list[HeadlineScore]
    meta: ResponseMeta
