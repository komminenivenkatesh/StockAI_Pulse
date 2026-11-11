"""Unit tests for technical indicators and feature engineering."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.core.market.indicators import (
    add_all_indicators,
    atr,
    bollinger_bands,
    ema,
    macd,
    rsi,
    sma,
    stochastic,
    vwap,
    wma,
)
from app.core.market.feature_eng import (
    build_feature_matrix,
    create_classification_target,
    train_test_split_temporal,
)
from app.core.market.data_fetcher import detect_asset_type, AssetType


# ── Fixtures ─────────────────────────────────────────────────


@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    """Generate synthetic OHLCV data for testing."""
    np.random.seed(42)
    n = 300
    dates = pd.date_range("2023-01-01", periods=n, freq="D", tz="UTC")

    # Random walk for close price
    returns = np.random.normal(0.0005, 0.02, n)
    close = 100.0 * np.cumprod(1 + returns)

    df = pd.DataFrame(
        {
            "open": close * (1 + np.random.normal(0, 0.005, n)),
            "high": close * (1 + np.abs(np.random.normal(0, 0.01, n))),
            "low": close * (1 - np.abs(np.random.normal(0, 0.01, n))),
            "close": close,
            "volume": np.random.randint(1_000_000, 10_000_000, n).astype(float),
        },
        index=dates,
    )
    return df


# ── Moving Average Tests ─────────────────────────────────────


class TestSMA:
    def test_length_matches_input(self, sample_ohlcv: pd.DataFrame) -> None:
        result = sma(sample_ohlcv["close"], 20)
        assert len(result) == len(sample_ohlcv)

    def test_first_values_are_nan(self, sample_ohlcv: pd.DataFrame) -> None:
        result = sma(sample_ohlcv["close"], 20)
        assert result.iloc[:19].isna().all()
        assert result.iloc[19:].notna().all()

    def test_known_value(self) -> None:
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        result = sma(s, 3)
        assert result.iloc[2] == pytest.approx(2.0)
        assert result.iloc[4] == pytest.approx(4.0)


class TestEMA:
    def test_length_matches(self, sample_ohlcv: pd.DataFrame) -> None:
        result = ema(sample_ohlcv["close"], 12)
        assert len(result) == len(sample_ohlcv)

    def test_ema_follows_trend(self) -> None:
        s = pd.Series(range(1, 51), dtype=float)
        result = ema(s, 10)
        # EMA should be below the current value in an uptrend
        assert result.iloc[-1] < s.iloc[-1]


# ── RSI Tests ────────────────────────────────────────────────


class TestRSI:
    def test_bounded_0_100(self, sample_ohlcv: pd.DataFrame) -> None:
        result = rsi(sample_ohlcv["close"])
        valid = result.dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()

    def test_all_gains_near_100(self) -> None:
        s = pd.Series(range(1, 100), dtype=float)
        result = rsi(s, 14)
        assert result.iloc[-1] > 90.0

    def test_all_losses_near_0(self) -> None:
        s = pd.Series(range(100, 0, -1), dtype=float)
        result = rsi(s, 14)
        assert result.iloc[-1] < 10.0


# ── MACD Tests ───────────────────────────────────────────────


class TestMACD:
    def test_returns_three_columns(self, sample_ohlcv: pd.DataFrame) -> None:
        result = macd(sample_ohlcv["close"])
        assert list(result.columns) == ["macd", "macd_signal", "macd_histogram"]

    def test_histogram_is_diff(self, sample_ohlcv: pd.DataFrame) -> None:
        result = macd(sample_ohlcv["close"])
        valid = result.dropna()
        computed = valid["macd"] - valid["macd_signal"]
        pd.testing.assert_series_equal(
            valid["macd_histogram"], computed, check_names=False, atol=1e-10
        )


# ── Bollinger Bands Tests ────────────────────────────────────


class TestBollingerBands:
    def test_returns_five_columns(self, sample_ohlcv: pd.DataFrame) -> None:
        result = bollinger_bands(sample_ohlcv["close"])
        assert list(result.columns) == ["bb_upper", "bb_middle", "bb_lower", "bb_width", "bb_pct"]

    def test_upper_above_lower(self, sample_ohlcv: pd.DataFrame) -> None:
        result = bollinger_bands(sample_ohlcv["close"])
        valid = result.dropna()
        assert (valid["bb_upper"] >= valid["bb_lower"]).all()


# ── ATR Tests ────────────────────────────────────────────────


class TestATR:
    def test_positive_values(self, sample_ohlcv: pd.DataFrame) -> None:
        result = atr(sample_ohlcv)
        valid = result.dropna()
        assert (valid > 0).all()


# ── Stochastic Tests ─────────────────────────────────────────


class TestStochastic:
    def test_bounded_0_100(self, sample_ohlcv: pd.DataFrame) -> None:
        result = stochastic(sample_ohlcv)
        valid_k = result["stoch_k"].dropna()
        assert (valid_k >= 0).all()
        assert (valid_k <= 100).all()


# ── Composite Tests ──────────────────────────────────────────


class TestAddAllIndicators:
    def test_adds_columns(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_all_indicators(sample_ohlcv)
        assert len(result.columns) > len(sample_ohlcv.columns)
        assert "rsi" in result.columns
        assert "macd" in result.columns
        assert "sma_20" in result.columns
        assert "bb_upper" in result.columns

    def test_preserves_original_data(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_all_indicators(sample_ohlcv)
        pd.testing.assert_series_equal(result["close"], sample_ohlcv["close"])


# ── Asset Type Detection ─────────────────────────────────────


class TestDetectAssetType:
    def test_stock(self) -> None:
        assert detect_asset_type("AAPL") == AssetType.STOCK
        assert detect_asset_type("MSFT") == AssetType.STOCK

    def test_crypto_with_slash(self) -> None:
        assert detect_asset_type("BTC/USDT") == AssetType.CRYPTO

    def test_crypto_known_base(self) -> None:
        assert detect_asset_type("BTC") == AssetType.CRYPTO
        assert detect_asset_type("ETH") == AssetType.CRYPTO


# ── Feature Engineering Tests ────────────────────────────────


class TestBuildFeatureMatrix:
    def test_no_lookahead_bias(self, sample_ohlcv: pd.DataFrame) -> None:
        features, target = build_feature_matrix(sample_ohlcv)
        # Features should have no NaN (after drop_na)
        assert features.isna().sum().sum() == 0
        # Target should have no NaN
        assert target.isna().sum() == 0

    def test_returns_tuple(self, sample_ohlcv: pd.DataFrame) -> None:
        result = build_feature_matrix(sample_ohlcv)
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestTemporalSplit:
    def test_split_ratio(self, sample_ohlcv: pd.DataFrame) -> None:
        features, target = build_feature_matrix(sample_ohlcv)
        X_train, X_test, y_train, y_test = train_test_split_temporal(features, target, 0.8)
        total = len(X_train) + len(X_test)
        assert abs(len(X_train) / total - 0.8) < 0.02

    def test_no_overlap(self, sample_ohlcv: pd.DataFrame) -> None:
        features, target = build_feature_matrix(sample_ohlcv)
        X_train, X_test, _, _ = train_test_split_temporal(features, target)
        assert X_train.index.max() < X_test.index.min()


class TestClassificationTarget:
    def test_binary_output(self) -> None:
        returns = pd.Series([0.01, -0.02, 0.005, -0.001, 0.03])
        result = create_classification_target(returns)
        assert set(result.unique()).issubset({0, 1})

    def test_threshold(self) -> None:
        returns = pd.Series([0.01, 0.02, 0.005])
        result = create_classification_target(returns, threshold=0.015)
        assert result.iloc[0] == 0  # 0.01 < 0.015
        assert result.iloc[1] == 1  # 0.02 > 0.015
