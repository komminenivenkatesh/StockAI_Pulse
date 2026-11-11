"""Feature engineering pipeline for ML models.

Combines technical indicators with rolling sentiment scores into
a unified feature matrix. Strict time-alignment ensures no lookahead bias.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.core.market.indicators import add_all_indicators
from app.utils.logging import get_logger

logger = get_logger(__name__)


def build_feature_matrix(
    ohlcv: pd.DataFrame,
    sentiment_scores: pd.DataFrame | None = None,
    target_col: str = "close",
    forecast_horizon: int = 1,
    drop_na: bool = True,
) -> tuple[pd.DataFrame, pd.Series]:
    """Build a feature matrix from OHLCV + sentiment data.

    Creates a comprehensive feature set combining:
      - Technical indicators (RSI, MACD, Bollinger, MA, etc.)
      - Price-derived features (returns, volatility)
      - Sentiment features (if provided)
      - Lagged target for supervised learning

    IMPORTANT: All features use .shift(1) to prevent lookahead bias.
    The target is the forward return over the forecast horizon.

    Args:
        ohlcv: OHLCV DataFrame with columns: open, high, low, close, volume.
        sentiment_scores: Optional DataFrame with 'compound_score' column,
            indexed by datetime. Will be time-aligned via merge_asof.
        target_col: Column to use for target variable.
        forecast_horizon: Number of bars ahead for the target variable.
        drop_na: Whether to drop rows with NaN values.

    Returns:
        Tuple of (features DataFrame, target Series).
        Features are shifted by 1 bar to prevent lookahead.
        Target is the forward return over forecast_horizon.
    """
    # 1. Add technical indicators
    df = add_all_indicators(ohlcv)

    # 2. Merge sentiment if provided
    if sentiment_scores is not None and not sentiment_scores.empty:
        df = _merge_sentiment(df, sentiment_scores)

    # 3. Create target: forward return
    target = (
        df[target_col].shift(-forecast_horizon) / df[target_col] - 1.0
    )
    target.name = "target_return"

    # 4. Shift ALL features by 1 to prevent lookahead bias
    # At time t, we can only use features computed from data up to t-1
    feature_cols = [c for c in df.columns if c not in ["open", "high", "low", "close", "volume", "adj_close"]]
    features = df[feature_cols].shift(1)

    # 5. Add lagged price features (safe because they're already shifted)
    features["price_to_sma_20"] = (df["close"] / df["sma_20"]).shift(1) if "sma_20" in df.columns else np.nan
    features["price_to_sma_50"] = (df["close"] / df["sma_50"]).shift(1) if "sma_50" in df.columns else np.nan
    features["high_low_range"] = ((df["high"] - df["low"]) / df["close"]).shift(1)
    features["close_to_open"] = ((df["close"] - df["open"]) / df["open"]).shift(1)

    # 6. Volume features
    if "volume" in df.columns:
        features["volume_sma_ratio"] = (
            df["volume"] / df["volume"].rolling(20, min_periods=1).mean()
        ).shift(1)
        features["volume_change"] = df["volume"].pct_change().shift(1)

    # 7. Clean infinities and drop NaN rows
    features = features.replace([np.inf, -np.inf], np.nan)
    target = target.replace([np.inf, -np.inf], np.nan)
    if drop_na:
        valid_mask = features.notna().all(axis=1) & target.notna()
        features = features[valid_mask]
        target = target[valid_mask]

    logger.info(
        "Feature matrix: %d samples, %d features. Horizon: %d bar(s).",
        len(features), len(features.columns), forecast_horizon,
    )

    return features, target


def _merge_sentiment(
    df: pd.DataFrame,
    sentiment: pd.DataFrame,
) -> pd.DataFrame:
    """Merge sentiment scores into the OHLCV DataFrame via time-alignment.

    Uses merge_asof to align sentiment timestamps with market data bars,
    carrying the most recent sentiment score forward (no future data).

    Args:
        df: OHLCV + indicators DataFrame.
        sentiment: DataFrame with datetime index and 'compound_score' column.

    Returns:
        DataFrame with sentiment columns merged in.
    """
    df = df.copy()
    df_reset = df.reset_index()
    df_reset = df_reset.rename(columns={df_reset.columns[0]: "datetime"})

    sent = sentiment.copy()
    if not isinstance(sent.index, pd.DatetimeIndex):
        sent.index = pd.to_datetime(sent.index, utc=True)
    sent = sent.reset_index()
    sent = sent.rename(columns={sent.columns[0]: "datetime"})

    # Ensure both are tz-aware UTC
    df_reset["datetime"] = pd.to_datetime(df_reset["datetime"], utc=True)
    sent["datetime"] = pd.to_datetime(sent["datetime"], utc=True)

    # Sort for merge_asof
    df_reset = df_reset.sort_values("datetime")
    sent = sent.sort_values("datetime")

    merged = pd.merge_asof(
        df_reset,
        sent,
        on="datetime",
        direction="backward",  # Only use past sentiment
    )
    merged = merged.set_index("datetime")

    # Fill missing sentiment with 0 (neutral)
    sentiment_cols = [c for c in sentiment.columns if c != "datetime"]
    for col in sentiment_cols:
        if col in merged.columns:
            merged[col] = merged[col].fillna(0.0)

    # Add rolling sentiment features
    if "compound_score" in merged.columns:
        merged["sentiment_sma_3"] = merged["compound_score"].rolling(3, min_periods=1).mean()
        merged["sentiment_sma_7"] = merged["compound_score"].rolling(7, min_periods=1).mean()
        merged["sentiment_std_7"] = merged["compound_score"].rolling(7, min_periods=1).std().fillna(0.0)
        merged["sentiment_momentum"] = merged["compound_score"] - merged["compound_score"].shift(1)

    logger.debug("Merged %d sentiment columns into feature matrix.", len(sentiment_cols))
    return merged


def create_classification_target(
    target_returns: pd.Series,
    threshold: float = 0.0,
) -> pd.Series:
    """Convert continuous return target to binary classification labels.

    Args:
        target_returns: Forward return series.
        threshold: Return threshold for positive class.

    Returns:
        Binary series: 1 = return > threshold, 0 = return <= threshold.
    """
    return (target_returns > threshold).astype(int)


def train_test_split_temporal(
    features: pd.DataFrame,
    target: pd.Series,
    train_ratio: float = 0.8,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Time-series aware train/test split (no shuffling).

    Args:
        features: Feature DataFrame.
        target: Target Series.
        train_ratio: Fraction of data for training.

    Returns:
        (X_train, X_test, y_train, y_test) — chronologically split.
    """
    split_idx = int(len(features) * train_ratio)

    X_train = features.iloc[:split_idx]
    X_test = features.iloc[split_idx:]
    y_train = target.iloc[:split_idx]
    y_test = target.iloc[split_idx:]

    logger.info(
        "Temporal split: train=%d samples (%s to %s), test=%d samples (%s to %s).",
        len(X_train), X_train.index.min(), X_train.index.max(),
        len(X_test), X_test.index.min(), X_test.index.max(),
    )

    return X_train, X_test, y_train, y_test
