"""Technical indicator library for financial time series.

All indicators operate on pandas DataFrames with standardized OHLCV columns
(open, high, low, close, volume). Computations are fully vectorized using
NumPy/Pandas — no loops, no lookahead bias.

Every indicator uses .shift() or min_periods to ensure only past data
is used in calculation, preventing lookahead bias in backtests.
"""

from __future__ import annotations

from typing import Final

import numpy as np
import pandas as pd

from app.utils.logging import get_logger

logger = get_logger(__name__)

# Default parameters
DEFAULT_RSI_PERIOD: Final[int] = 14
DEFAULT_MACD_FAST: Final[int] = 12
DEFAULT_MACD_SLOW: Final[int] = 26
DEFAULT_MACD_SIGNAL: Final[int] = 9
DEFAULT_BB_PERIOD: Final[int] = 20
DEFAULT_BB_STD: Final[float] = 2.0


# ── Moving Averages ──────────────────────────────────────────


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average.

    Args:
        series: Price series (typically 'close').
        period: Lookback window size.

    Returns:
        SMA series with NaN for first (period-1) values.
    """
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average.

    Args:
        series: Price series.
        period: Span for EMA calculation.

    Returns:
        EMA series.
    """
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def wma(series: pd.Series, period: int) -> pd.Series:
    """Weighted Moving Average.

    Weights increase linearly: [1, 2, ..., period].
    """
    weights = np.arange(1, period + 1, dtype=float)
    return series.rolling(window=period, min_periods=period).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


# ── RSI ──────────────────────────────────────────────────────


def rsi(series: pd.Series, period: int = DEFAULT_RSI_PERIOD) -> pd.Series:
    """Relative Strength Index (Wilder's smoothing).

    Uses the Wilder smoothing method (exponential moving average with
    alpha = 1/period) for consistency with industry standard.

    Args:
        series: Price series (typically 'close').
        period: RSI lookback period.

    Returns:
        RSI values in [0, 100] with NaN for initial values.
    """
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    # Wilder's smoothing (equivalent to EMA with alpha=1/period)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi_values = 100.0 - (100.0 / (1.0 + rs))

    return rsi_values


# ── MACD ─────────────────────────────────────────────────────


def macd(
    series: pd.Series,
    fast: int = DEFAULT_MACD_FAST,
    slow: int = DEFAULT_MACD_SLOW,
    signal_period: int = DEFAULT_MACD_SIGNAL,
) -> pd.DataFrame:
    """Moving Average Convergence Divergence.

    Args:
        series: Price series.
        fast: Fast EMA period.
        slow: Slow EMA period.
        signal_period: Signal line EMA period.

    Returns:
        DataFrame with columns: 'macd', 'macd_signal', 'macd_histogram'.
    """
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
    histogram = macd_line - signal_line

    return pd.DataFrame(
        {
            "macd": macd_line,
            "macd_signal": signal_line,
            "macd_histogram": histogram,
        },
        index=series.index,
    )


# ── Bollinger Bands ──────────────────────────────────────────


def bollinger_bands(
    series: pd.Series,
    period: int = DEFAULT_BB_PERIOD,
    num_std: float = DEFAULT_BB_STD,
) -> pd.DataFrame:
    """Bollinger Bands.

    Args:
        series: Price series.
        period: SMA lookback period.
        num_std: Number of standard deviations for bands.

    Returns:
        DataFrame with columns: 'bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_pct'.
    """
    middle = sma(series, period)
    rolling_std = series.rolling(window=period, min_periods=period).std()

    upper = middle + (rolling_std * num_std)
    lower = middle - (rolling_std * num_std)
    width = (upper - lower) / middle  # Normalized width
    pct_b = (series - lower) / (upper - lower)  # %B indicator

    return pd.DataFrame(
        {
            "bb_upper": upper,
            "bb_middle": middle,
            "bb_lower": lower,
            "bb_width": width,
            "bb_pct": pct_b,
        },
        index=series.index,
    )


# ── ATR (Average True Range) ─────────────────────────────────


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range — volatility indicator.

    Args:
        df: OHLCV DataFrame with 'high', 'low', 'close' columns.
        period: Smoothing period.

    Returns:
        ATR series.
    """
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()


# ── VWAP ─────────────────────────────────────────────────────


def vwap(df: pd.DataFrame) -> pd.Series:
    """Volume Weighted Average Price (intraday cumulative).

    Args:
        df: OHLCV DataFrame with 'high', 'low', 'close', 'volume' columns.

    Returns:
        VWAP series.
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    cumulative_tp_volume = (typical_price * df["volume"]).cumsum()
    cumulative_volume = df["volume"].cumsum()

    return cumulative_tp_volume / cumulative_volume


# ── Stochastic Oscillator ────────────────────────────────────


def stochastic(
    df: pd.DataFrame,
    k_period: int = 14,
    d_period: int = 3,
) -> pd.DataFrame:
    """Stochastic Oscillator (%K and %D).

    Args:
        df: OHLCV DataFrame.
        k_period: Lookback for %K.
        d_period: Smoothing for %D (SMA of %K).

    Returns:
        DataFrame with columns: 'stoch_k', 'stoch_d'.
    """
    low_min = df["low"].rolling(window=k_period, min_periods=k_period).min()
    high_max = df["high"].rolling(window=k_period, min_periods=k_period).max()

    stoch_k = 100.0 * (df["close"] - low_min) / (high_max - low_min)
    stoch_d = stoch_k.rolling(window=d_period, min_periods=d_period).mean()

    return pd.DataFrame(
        {"stoch_k": stoch_k, "stoch_d": stoch_d},
        index=df.index,
    )


# ── Composite: Add All Indicators ────────────────────────────


def add_all_indicators(
    df: pd.DataFrame,
    rsi_period: int = DEFAULT_RSI_PERIOD,
    macd_fast: int = DEFAULT_MACD_FAST,
    macd_slow: int = DEFAULT_MACD_SLOW,
    macd_signal: int = DEFAULT_MACD_SIGNAL,
    bb_period: int = DEFAULT_BB_PERIOD,
    bb_std: float = DEFAULT_BB_STD,
    sma_periods: tuple[int, ...] = (20, 50, 200),
    ema_periods: tuple[int, ...] = (12, 26),
) -> pd.DataFrame:
    """Add a comprehensive set of technical indicators to an OHLCV DataFrame.

    All indicators use only past data (no lookahead bias).

    Args:
        df: OHLCV DataFrame with columns: open, high, low, close, volume.
        rsi_period: RSI lookback.
        macd_fast: MACD fast EMA period.
        macd_slow: MACD slow EMA period.
        macd_signal: MACD signal line period.
        bb_period: Bollinger Bands period.
        bb_std: Bollinger Bands standard deviation multiplier.
        sma_periods: Tuple of SMA periods to compute.
        ema_periods: Tuple of EMA periods to compute.

    Returns:
        DataFrame with all original columns plus indicator columns.
    """
    result = df.copy()
    close = result["close"]

    # Moving averages
    for p in sma_periods:
        result[f"sma_{p}"] = sma(close, p)
    for p in ema_periods:
        result[f"ema_{p}"] = ema(close, p)

    # RSI
    result["rsi"] = rsi(close, rsi_period)

    # MACD
    macd_df = macd(close, macd_fast, macd_slow, macd_signal)
    result = pd.concat([result, macd_df], axis=1)

    # Bollinger Bands
    bb_df = bollinger_bands(close, bb_period, bb_std)
    result = pd.concat([result, bb_df], axis=1)

    # ATR
    result["atr"] = atr(result)

    # VWAP
    if "volume" in result.columns and result["volume"].sum() > 0:
        result["vwap"] = vwap(result)

    # Stochastic
    stoch_df = stochastic(result)
    result = pd.concat([result, stoch_df], axis=1)

    # Price-derived features
    result["returns"] = close.pct_change()
    result["log_returns"] = np.log(close / close.shift(1))
    result["volatility_20"] = result["returns"].rolling(20, min_periods=20).std()

    logger.debug("Added %d indicator columns to %d-row DataFrame.", len(result.columns) - len(df.columns), len(result))
    return result
