"""Unified market data fetcher for stocks (yfinance) and crypto (CCXT).

Provides a single interface to fetch OHLCV data from multiple sources
with automatic source detection based on ticker format.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Final

import numpy as np
import pandas as pd
import yfinance as yf

from app.utils.errors import ExternalAPIError, TickerNotFoundError
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Common crypto tickers that should route to CCXT
_CRYPTO_SUFFIXES: Final[set[str]] = {
    "USD", "USDT", "USDC", "BTC", "ETH", "BNB", "BUSD",
}
_CRYPTO_BASES: Final[set[str]] = {
    "BTC", "ETH", "SOL", "ADA", "DOT", "AVAX", "MATIC", "LINK",
    "DOGE", "XRP", "BNB", "LTC", "UNI", "AAVE", "ATOM",
}


class AssetType(str, Enum):
    """Enumeration of supported asset types."""
    STOCK = "stock"
    CRYPTO = "crypto"


class MarketDataResult:
    """Container for fetched market data."""

    __slots__ = ("ticker", "asset_type", "df", "currency", "exchange")

    def __init__(
        self,
        ticker: str,
        asset_type: AssetType,
        df: pd.DataFrame,
        currency: str = "USD",
        exchange: str = "unknown",
    ) -> None:
        self.ticker = ticker
        self.asset_type = asset_type
        self.df = df
        self.currency = currency
        self.exchange = exchange

    @property
    def is_empty(self) -> bool:
        return self.df.empty

    @property
    def date_range(self) -> tuple[str, str]:
        if self.is_empty:
            return ("", "")
        return (
            str(self.df.index.min().date()),
            str(self.df.index.max().date()),
        )


def detect_asset_type(ticker: str) -> AssetType:
    """Detect whether a ticker is a stock or crypto asset.

    Rules:
      - Contains '/' (e.g., BTC/USD) → crypto
      - Base is a known crypto symbol → crypto
      - Ends with a known crypto quote currency → crypto
      - Otherwise → stock
    """
    upper = ticker.upper().strip()

    if "/" in upper:
        return AssetType.CRYPTO

    # Check if it's a known crypto base
    base = upper.split("-")[0] if "-" in upper else upper
    if base in _CRYPTO_BASES:
        return AssetType.CRYPTO

    # Check for crypto quote suffix (e.g., BTCUSDT)
    for suffix in _CRYPTO_SUFFIXES:
        if upper.endswith(suffix) and len(upper) > len(suffix):
            potential_base = upper[: -len(suffix)]
            if potential_base in _CRYPTO_BASES:
                return AssetType.CRYPTO

    return AssetType.STOCK


class MarketDataFetcher:
    """Unified fetcher for stock and crypto OHLCV data.

    Usage:
        fetcher = MarketDataFetcher()
        result = await fetcher.fetch("AAPL", period="1y", interval="1d")
        result = await fetcher.fetch("BTC/USDT", period="6mo", interval="1d")
    """

    # Valid yfinance periods and intervals
    VALID_PERIODS: Final[set[str]] = {
        "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max",
    }
    VALID_INTERVALS: Final[set[str]] = {
        "1m", "2m", "5m", "15m", "30m", "60m", "90m",
        "1h", "1d", "5d", "1wk", "1mo", "3mo",
    }

    async def fetch(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d",
        start: str | None = None,
        end: str | None = None,
    ) -> MarketDataResult:
        """Fetch OHLCV data for a given ticker.

        Args:
            ticker: Asset symbol (e.g., 'AAPL', 'BTC/USDT').
            period: Lookback period (yfinance format). Ignored if start/end provided.
            interval: Bar interval (e.g., '1d', '1h').
            start: Start date string (YYYY-MM-DD). Optional.
            end: End date string (YYYY-MM-DD). Optional.

        Returns:
            MarketDataResult with standardized OHLCV DataFrame.

        Raises:
            TickerNotFoundError: If the ticker returns no data.
            ExternalAPIError: If the data source API fails.
        """
        asset_type = detect_asset_type(ticker)

        if asset_type == AssetType.STOCK:
            return await self._fetch_yfinance(ticker, period, interval, start, end)
        else:
            return await self._fetch_crypto(ticker, interval, start, end)

    async def _fetch_yfinance(
        self,
        ticker: str,
        period: str,
        interval: str,
        start: str | None,
        end: str | None,
    ) -> MarketDataResult:
        """Fetch stock data from Yahoo Finance."""
        logger.info("Fetching stock data for %s (period=%s, interval=%s)", ticker, period, interval)

        actual_ticker = ticker
        try:
            # Run yfinance in a thread since it's synchronous
            loop = asyncio.get_event_loop()
            yf_ticker = yf.Ticker(ticker)

            if start and end:
                df = await loop.run_in_executor(
                    None,
                    lambda: yf_ticker.history(start=start, end=end, interval=interval),
                )
            else:
                df = await loop.run_in_executor(
                    None,
                    lambda: yf_ticker.history(period=period, interval=interval),
                )

            # If empty and no exchange suffix, try Indian exchange suffixes (.NS for NSE, .BO for BSE)
            if df.empty and "." not in ticker and "/" not in ticker:
                for suffix in [".NS", ".BO"]:
                    cand_sym = f"{ticker}{suffix}"
                    cand_yf = yf.Ticker(cand_sym)
                    if start and end:
                        cand_df = await loop.run_in_executor(
                            None,
                            lambda: cand_yf.history(start=start, end=end, interval=interval),
                        )
                    else:
                        cand_df = await loop.run_in_executor(
                            None,
                            lambda: cand_yf.history(period=period, interval=interval),
                        )
                    if not cand_df.empty:
                        df = cand_df
                        actual_ticker = cand_sym
                        yf_ticker = cand_yf
                        logger.info("Auto-resolved ticker %s to %s", ticker, cand_sym)
                        break
        except Exception as exc:
            raise ExternalAPIError("yfinance", str(exc)) from exc

        if df.empty:
            raise TickerNotFoundError(ticker)

        # Standardize column names to lowercase
        df = _standardize_ohlcv(df)

        logger.info(
            "Fetched %d bars for %s (%s to %s).",
            len(df), actual_ticker, df.index.min(), df.index.max(),
        )

        currency = "USD"
        try:
            currency = getattr(yf_ticker.fast_info, "currency", "USD") or "USD"
        except Exception:
            if actual_ticker.endswith(".NS") or actual_ticker.endswith(".BO"):
                currency = "INR"

        return MarketDataResult(
            ticker=actual_ticker.upper(),
            asset_type=AssetType.STOCK,
            df=df,
            currency=currency,
            exchange="Yahoo Finance",
        )

    async def _fetch_crypto(
        self,
        ticker: str,
        interval: str,
        start: str | None,
        end: str | None,
    ) -> MarketDataResult:
        """Fetch crypto data via CCXT (Binance by default)."""
        logger.info("Fetching crypto data for %s (interval=%s)", ticker, interval)

        try:
            import ccxt
        except ImportError:
            raise ExternalAPIError(
                "CCXT",
                "ccxt package not installed. Install with: pip install ccxt",
            )

        # Normalize ticker format for CCXT (e.g., BTCUSDT -> BTC/USDT)
        symbol = _normalize_crypto_symbol(ticker)
        timeframe = _interval_to_ccxt_timeframe(interval)

        try:
            exchange = ccxt.binance({"enableRateLimit": True})
            loop = asyncio.get_event_loop()

            since = None
            if start:
                since = int(
                    datetime.strptime(start, "%Y-%m-%d")
                    .replace(tzinfo=timezone.utc)
                    .timestamp()
                    * 1000
                )

            ohlcv = await loop.run_in_executor(
                None,
                lambda: exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000),
            )
        except Exception as exc:
            raise ExternalAPIError("CCXT", str(exc)) from exc

        if not ohlcv:
            raise TickerNotFoundError(ticker)

        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.set_index("timestamp")

        # Filter by end date if provided
        if end:
            end_dt = pd.Timestamp(end, tz="UTC")
            df = df[df.index <= end_dt]

        logger.info("Fetched %d bars for %s.", len(df), symbol)

        return MarketDataResult(
            ticker=symbol,
            asset_type=AssetType.CRYPTO,
            df=df,
            currency="USDT" if "USDT" in symbol else "USD",
            exchange="Binance",
        )


# ── Helpers ──────────────────────────────────────────────────


def _standardize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize OHLCV DataFrame column names to lowercase."""
    col_map = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
        "Adj Close": "adj_close",
    }
    df = df.rename(columns=col_map)

    # Keep only OHLCV columns
    keep = [c for c in ["open", "high", "low", "close", "volume", "adj_close"] if c in df.columns]
    df = df[keep]

    # Ensure timezone-aware index
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")

    return df


def _normalize_crypto_symbol(ticker: str) -> str:
    """Normalize crypto ticker to CCXT format (BASE/QUOTE)."""
    ticker = ticker.upper().strip()
    if "/" in ticker:
        return ticker

    # Try known quote currencies
    for quote in ["USDT", "USDC", "BUSD", "USD", "BTC", "ETH", "BNB"]:
        if ticker.endswith(quote) and len(ticker) > len(quote):
            base = ticker[: -len(quote)]
            return f"{base}/{quote}"

    # Default to /USDT
    return f"{ticker}/USDT"


def _interval_to_ccxt_timeframe(interval: str) -> str:
    """Map yfinance-style interval to CCXT timeframe."""
    mapping = {
        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
        "1h": "1h", "60m": "1h", "90m": "1h",
        "1d": "1d", "5d": "1w", "1wk": "1w",
        "1mo": "1M", "3mo": "1M",
    }
    return mapping.get(interval, "1d")
