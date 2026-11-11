"""Sentiment analysis API endpoints.

Provides:
  - GET  /analyze/{ticker}  — fetch news & score sentiment for a ticker
  - POST /analyze/headlines — score user-provided headlines
  - GET  /health            — sentiment engine health check
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from app.config import Settings, get_settings
from app.core.sentiment.aggregator import aggregate_sentiment, compute_current_sentiment
from app.core.sentiment.finbert import FinBERTAnalyzer
from app.core.sentiment.news_fetcher import NewsFetcher
from app.core.sentiment.preprocessor import preprocess_headlines
from app.models.sentiment import (
    HeadlineScore,
    HeadlineSentimentResponse,
    ResponseMeta,
    SentimentAggregation,
    SentimentRequest,
    TickerSentimentData,
    TickerSentimentResponse,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _get_finbert(request: Request) -> FinBERTAnalyzer:
    """Extract FinBERT analyzer from app state; lazy-load model on first use."""
    analyzer: FinBERTAnalyzer | None = getattr(request.app.state, "finbert", None)
    if analyzer is None:
        raise HTTPException(status_code=503, detail="FinBERT analyzer not initialized.")
    if not analyzer.is_loaded:
        logger.info("Lazy-loading FinBERT model on first sentiment request...")
        try:
            analyzer.load_model()
        except Exception as exc:
            logger.error("Failed to load FinBERT model: %s", exc)
            raise HTTPException(status_code=503, detail=f"FinBERT model loading failed: {exc}")
    return analyzer


def _compound_to_signal(score: float) -> str:
    """Map compound score to a discrete trading signal."""
    if score >= 0.15:
        return "Bullish"
    elif score <= -0.15:
        return "Bearish"
    return "Neutral"


@router.get(
    "/analyze/{ticker:path}",
    response_model=TickerSentimentResponse,
    summary="Analyze sentiment for a ticker",
)
async def analyze_ticker(
    request: Request,
    ticker: Annotated[str, Path(min_length=1, max_length=20, description="Stock or crypto ticker symbol")],
    lookback_days: Annotated[int, Query(ge=1, le=30, description="Days to look back")] = 7,
    settings: Settings = Depends(get_settings),
) -> TickerSentimentResponse:
    """Fetch recent news for a ticker and return scored sentiment analysis."""
    analyzer = _get_finbert(request)
    ticker = ticker.upper()

    # 1. Fetch news
    fetcher = NewsFetcher(settings)
    articles = await fetcher.fetch(ticker, lookback_days=lookback_days)

    if not articles:
        # No news is not an error — return neutral sentiment
        logger.info("No articles found for %s — returning neutral sentiment.", ticker)
        return TickerSentimentResponse(
            status="ok",
            data=TickerSentimentData(
                ticker=ticker,
                current_score=0.0,
                signal="Neutral",
                headline_scores=[],
                rolling_sentiment=[],
                total_articles=0,
            ),
            meta=ResponseMeta(
                timestamp=datetime.now(tz=timezone.utc),
                ticker=ticker,
                cached_items=0,
            ),
        )

    # 2. Preprocess & pair with source articles
    from app.core.sentiment.preprocessor import clean_headline, is_valid_headline
    valid_articles: list[NewsArticle] = []
    cleaned: list[str] = []
    for art in articles:
        c = clean_headline(art.title)
        if is_valid_headline(c):
            valid_articles.append(art)
            cleaned.append(c)

    if not cleaned:
        # All headlines filtered out — return neutral sentiment
        logger.info("No valid headlines after preprocessing for %s — returning neutral sentiment.", ticker)
        return TickerSentimentResponse(
            status="ok",
            data=TickerSentimentData(
                ticker=ticker,
                current_score=0.0,
                signal="Neutral",
                headline_scores=[],
                rolling_sentiment=[],
                total_articles=0,
            ),
            meta=ResponseMeta(
                timestamp=datetime.now(tz=timezone.utc),
                ticker=ticker,
                cached_items=0,
            ),
        )

    # 3. Score with FinBERT
    scores = analyzer.predict(cleaned)
    score_dicts = [s.to_dict() for s in scores]

    # 4. Map article metadata (source, tier, weight, url, timestamp)
    timestamps: list[datetime] = []
    enriched_score_dicts: list[dict[str, Any]] = []

    for i, sd in enumerate(score_dicts):
        item = dict(sd)
        art = valid_articles[i]
        item["headline"] = art.title  # Keep original readable headline
        item["source"] = art.source
        item["source_tier"] = art.source_tier
        item["trust_label"] = art.trust_label
        item["tier_weight"] = art.tier_weight
        item["url"] = art.url
        timestamps.append(art.published_at)
        enriched_score_dicts.append(item)

    # 5. Aggregate with domain reputation tier weights
    rolling = aggregate_sentiment(enriched_score_dicts, timestamps)
    current = compute_current_sentiment(enriched_score_dicts, timestamps)

    # 6. Build response
    headline_scores = [HeadlineScore(**sd) for sd in enriched_score_dicts]

    return TickerSentimentResponse(
        status="ok",
        data=TickerSentimentData(
            ticker=ticker,
            current_score=current,
            signal=_compound_to_signal(current),
            headline_scores=headline_scores,
            rolling_sentiment=[
                SentimentAggregation(timestamp=dp.timestamp, compound_score=dp.compound_score, headline_count=dp.headline_count)
                for dp in rolling
            ],
            total_articles=len(cleaned),
        ),
        meta=ResponseMeta(
            timestamp=datetime.now(tz=timezone.utc),
            ticker=ticker,
            cached_items=analyzer.cache_stats["cached_items"],
        ),
    )


@router.post(
    "/analyze/headlines",
    response_model=HeadlineSentimentResponse,
    summary="Analyze custom headlines",
)
async def analyze_headlines(
    body: SentimentRequest,
    request: Request,
) -> HeadlineSentimentResponse:
    """Score a list of user-provided financial headlines."""
    analyzer = _get_finbert(request)

    # Preprocess
    cleaned = preprocess_headlines(body.headlines, deduplicate=True)
    if not cleaned:
        raise HTTPException(status_code=422, detail="No valid headlines after preprocessing.")

    # Score
    scores = analyzer.predict(cleaned)
    headline_scores = [HeadlineScore(**s.to_dict()) for s in scores]

    return HeadlineSentimentResponse(
        status="ok",
        data=headline_scores,
        meta=ResponseMeta(
            timestamp=datetime.now(tz=timezone.utc),
            cached_items=analyzer.cache_stats["cached_items"],
        ),
    )


@router.get("/health", summary="Sentiment engine health")
async def sentiment_health(request: Request) -> dict[str, object]:
    """Check FinBERT model status and cache stats."""
    analyzer = _get_finbert(request)
    return {
        "status": "ok",
        "model_loaded": analyzer.is_loaded,
        "cache": analyzer.cache_stats,
    }
