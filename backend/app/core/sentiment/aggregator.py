"""Rolling sentiment score aggregation.

Computes time-weighted sentiment scores over configurable windows,
using exponentially weighted means to emphasize recency.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Final

import numpy as np
import pandas as pd

from app.utils.logging import get_logger

logger = get_logger(__name__)

# Default rolling window parameters
DEFAULT_WINDOW: Final[str] = "24h"
DEFAULT_HALFLIFE: Final[str] = "6h"


class SentimentDataPoint:
    """A single timestamped sentiment measurement."""

    __slots__ = ("timestamp", "compound_score", "headline_count")

    def __init__(
        self,
        timestamp: datetime,
        compound_score: float,
        headline_count: int = 1,
    ) -> None:
        self.timestamp = timestamp
        self.compound_score = compound_score
        self.headline_count = headline_count

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "compound_score": self.compound_score,
            "headline_count": self.headline_count,
        }


def aggregate_sentiment(
    scores: list[dict[str, object]],
    timestamps: list[datetime],
    window: str = DEFAULT_WINDOW,
    halflife: str = DEFAULT_HALFLIFE,
) -> list[SentimentDataPoint]:
    """Aggregate headline-level sentiment into rolling time-bucketed scores.

    Args:
        scores: List of dicts with at least a 'compound' key (from SentimentScore.to_dict()).
        timestamps: Corresponding publication timestamps (must be same length as scores).
        window: Pandas-compatible frequency string for time bucketing (e.g., '24h', '1D').
        halflife: Halflife for exponential weighting within the window.

    Returns:
        List of SentimentDataPoint, one per time bucket, sorted chronologically.

    Raises:
        ValueError: If scores and timestamps have different lengths.
    """
    if len(scores) != len(timestamps):
        raise ValueError(
            f"Length mismatch: {len(scores)} scores vs {len(timestamps)} timestamps."
        )

    if not scores:
        logger.debug("No scores to aggregate.")
        return []

    # Build DataFrame
    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(timestamps, utc=True),
            "compound": [float(s.get("compound", 0.0)) for s in scores],
        }
    )
    df = df.set_index("timestamp").sort_index()

    # Resample into time buckets
    resampled = df.resample(window).agg(
        compound_mean=("compound", "mean"),
        headline_count=("compound", "count"),
    )

    # Drop empty buckets
    resampled = resampled[resampled["headline_count"] > 0]

    if resampled.empty:
        return []

    # Apply exponential weighting for recency bias
    resampled["ewm_score"] = (
        resampled["compound_mean"]
        .ewm(halflife=halflife, times=resampled.index)
        .mean()
    )

    # Build output
    data_points: list[SentimentDataPoint] = []
    for idx, row in resampled.iterrows():
        data_points.append(
            SentimentDataPoint(
                timestamp=idx.to_pydatetime().replace(tzinfo=timezone.utc),  # type: ignore[union-attr]
                compound_score=round(float(row["ewm_score"]), 6),
                headline_count=int(row["headline_count"]),
            )
        )

    logger.debug("Aggregated %d time buckets from %d headlines.", len(data_points), len(scores))
    return data_points


def compute_current_sentiment(
    scores: list[dict[str, object]],
    timestamps: list[datetime],
    halflife: str = DEFAULT_HALFLIFE,
) -> float:
    """Compute a single current sentiment score from recent headlines.

    Uses exponential weighting where more recent headlines have
    stronger influence on the final score.

    Args:
        scores: Scored headline dicts with 'compound' key.
        timestamps: Publication timestamps.
        halflife: Halflife for decay weighting.

    Returns:
        Weighted sentiment in [-1.0, 1.0], or 0.0 if no data.
    """
    if not scores:
        return 0.0

    compounds = np.array([float(s.get("compound", 0.0)) for s in scores])
    tier_weights = np.array([float(s.get("tier_weight", 1.0)) for s in scores])
    ts = pd.to_datetime(timestamps, utc=True)
    now = pd.Timestamp.now(tz="UTC")

    # Compute exponential decay weights based on age
    ages_seconds = np.maximum(0.0, (now - ts).total_seconds().values.astype(float))
    halflife_seconds = pd.Timedelta(halflife).total_seconds()
    recency_weights = np.exp(-np.log(2) * ages_seconds / halflife_seconds)

    # Combine recency decay with domain trust tier weight
    weights = recency_weights * tier_weights

    # Weighted average
    if weights.sum() == 0:
        return 0.0

    weighted_score = float(np.average(compounds, weights=weights))
    return round(float(np.clip(weighted_score, -1.0, 1.0)), 6)
