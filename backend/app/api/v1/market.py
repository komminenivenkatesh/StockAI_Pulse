"""Market data API endpoints.

Provides:
  - GET /data/{ticker}          — fetch OHLCV data with optional indicators
  - GET /indicators/{ticker}    — fetch technical indicators only
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

import httpx
import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Path, Query

from app.core.market.data_fetcher import MarketDataFetcher
from app.core.market.indicators import add_all_indicators
from app.models.market import (
    IndicatorsPayload,
    IndicatorsResponse,
    IndicatorValues,
    MarketDataPayload,
    MarketDataResponse,
    MarketSummary,
    OHLCVBar,
    ResponseMeta,
    SearchItem,
    SearchResponse,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _safe_float(val: object) -> float | None:
    """Safely convert a value to float, returning None for NaN/None."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    try:
        result = float(val)
        return None if np.isnan(result) else round(result, 6)
    except (ValueError, TypeError):
        return None


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Search ticker symbols and company names",
)
async def search_market(
    q: Annotated[str, Query(min_length=1, max_length=50, description="Search query (e.g. indian, tata, apple)")],
    limit: Annotated[int, Query(ge=1, le=20, description="Max results to return")] = 8,
) -> SearchResponse:
    """Search stock, ETF, and crypto tickers using Yahoo Finance search."""
    clean_query = q.strip()
    if not clean_query:
        return SearchResponse(data=[])

    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={clean_query}&quotesCount={limit * 2}&newsCount=0"
    headers = {"User-Agent": "Mozilla/5.0"}
    results: list[SearchItem] = []

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                data = r.json()
                quotes = data.get("quotes", [])
                for item in quotes:
                    sym = item.get("symbol")
                    if not sym or "=" in sym or "^" in sym:
                        continue
                    name = item.get("shortname") or item.get("longname") or item.get("name") or sym
                    raw_exch = item.get("exchange", "")
                    exch = "OTHER"
                    if raw_exch in ["NSI", "NSE"]:
                        exch = "NSE"
                    elif raw_exch in ["BOM", "BSE"]:
                        exch = "BSE"
                    elif raw_exch in ["NMS", "NGM", "NCM", "NAS"]:
                        exch = "NASDAQ"
                    elif raw_exch in ["NYQ", "NYSE"]:
                        exch = "NYSE"
                    elif raw_exch in ["CCC", "CCXT"]:
                        exch = "CRYPTO"
                    else:
                        exch = raw_exch

                    quote_type = item.get("quoteType", "EQUITY")
                    if quote_type == "EQUITY":
                        type_str = "Stock"
                    elif quote_type == "CRYPTOCURRENCY":
                        type_str = "Crypto"
                    elif quote_type == "ETF":
                        type_str = "ETF"
                    else:
                        type_str = "Asset"

                    results.append(
                        SearchItem(
                            symbol=sym,
                            name=name,
                            exchange=exch,
                            type=type_str,
                        )
                    )
                    if len(results) >= limit:
                        break
    except Exception as e:
        logger.warning("Search query '%s' failed: %s", clean_query, e)

    return SearchResponse(data=results)


@router.get(
    "/data/{ticker:path}",
    response_model=MarketDataResponse,
    summary="Fetch OHLCV market data",
)
async def get_market_data(
    ticker: Annotated[str, Path(min_length=1, max_length=20, description="Ticker symbol")],
    period: Annotated[str, Query(description="Lookback period (e.g., 1y, 6mo, 3mo)")] = "1y",
    interval: Annotated[str, Query(description="Bar interval (e.g., 1d, 1h)")] = "1d",
    include_indicators: Annotated[bool, Query(description="Include technical indicators")] = False,
    start: Annotated[str | None, Query(description="Start date (YYYY-MM-DD)")] = None,
    end: Annotated[str | None, Query(description="End date (YYYY-MM-DD)")] = None,
) -> MarketDataResponse:
    """Fetch OHLCV data for a ticker with optional technical indicators."""
    fetcher = MarketDataFetcher()
    result = await fetcher.fetch(ticker, period=period, interval=interval, start=start, end=end)

    df = result.df

    # Build OHLCV bars
    ohlcv_bars = [
        OHLCVBar(
            timestamp=idx.to_pydatetime(),
            open=round(float(row["open"]), 6),
            high=round(float(row["high"]), 6),
            low=round(float(row["low"]), 6),
            close=round(float(row["close"]), 6),
            volume=float(row.get("volume", 0)),
        )
        for idx, row in df.iterrows()
    ]

    # Compute summary
    latest_close = float(df["close"].iloc[-1])
    prev_close = float(df["close"].iloc[-2]) if len(df) > 1 else latest_close
    change_pct = round(((latest_close - prev_close) / prev_close) * 100, 4)

    summary = MarketSummary(
        current_price=round(latest_close, 6),
        change_pct=change_pct,
        high_52w=_safe_float(df["high"].tail(252).max()) if len(df) >= 252 else _safe_float(df["high"].max()),
        low_52w=_safe_float(df["low"].tail(252).min()) if len(df) >= 252 else _safe_float(df["low"].min()),
        avg_volume=_safe_float(df["volume"].mean()) if "volume" in df.columns else None,
        volatility_20d=_safe_float(df["close"].pct_change().tail(20).std() * (252 ** 0.5)),
    )

    # Optional indicators
    indicator_list = None
    if include_indicators:
        ind_df = add_all_indicators(df)
        indicator_list = _df_to_indicator_values(ind_df)

    return MarketDataResponse(
        status="ok",
        data=MarketDataPayload(
            ticker=result.ticker,
            summary=summary,
            ohlcv=ohlcv_bars,
            indicators=indicator_list,
        ),
        meta=ResponseMeta(
            timestamp=datetime.now(tz=timezone.utc),
            ticker=result.ticker,
            asset_type=result.asset_type.value,
            exchange=result.exchange,
            currency=result.currency,
            bars=len(df),
            period=period,
            interval=interval,
        ),
    )


@router.get(
    "/indicators/{ticker:path}",
    response_model=IndicatorsResponse,
    summary="Fetch technical indicators",
)
async def get_indicators(
    ticker: Annotated[str, Path(min_length=1, max_length=20, description="Ticker symbol")],
    period: Annotated[str, Query(description="Lookback period")] = "1y",
    interval: Annotated[str, Query(description="Bar interval")] = "1d",
) -> IndicatorsResponse:
    """Fetch technical indicators for a ticker."""
    fetcher = MarketDataFetcher()
    result = await fetcher.fetch(ticker, period=period, interval=interval)

    ind_df = add_all_indicators(result.df)
    indicator_list = _df_to_indicator_values(ind_df)

    return IndicatorsResponse(
        status="ok",
        data=IndicatorsPayload(
            ticker=result.ticker,
            indicators=indicator_list,
        ),
        meta=ResponseMeta(
            timestamp=datetime.now(tz=timezone.utc),
            ticker=result.ticker,
            asset_type=result.asset_type.value,
            exchange=result.exchange,
            currency=result.currency,
            bars=len(result.df),
            period=period,
            interval=interval,
        ),
    )


def _df_to_indicator_values(df: pd.DataFrame) -> list[IndicatorValues]:
    """Convert an indicators DataFrame to a list of IndicatorValues."""
    indicators: list[IndicatorValues] = []
    for idx, row in df.iterrows():
        indicators.append(
            IndicatorValues(
                timestamp=idx.to_pydatetime(),
                rsi=_safe_float(row.get("rsi")),
                macd=_safe_float(row.get("macd")),
                macd_signal=_safe_float(row.get("macd_signal")),
                macd_histogram=_safe_float(row.get("macd_histogram")),
                sma_20=_safe_float(row.get("sma_20")),
                sma_50=_safe_float(row.get("sma_50")),
                sma_200=_safe_float(row.get("sma_200")),
                ema_12=_safe_float(row.get("ema_12")),
                ema_26=_safe_float(row.get("ema_26")),
                bb_upper=_safe_float(row.get("bb_upper")),
                bb_middle=_safe_float(row.get("bb_middle")),
                bb_lower=_safe_float(row.get("bb_lower")),
                atr=_safe_float(row.get("atr")),
                stoch_k=_safe_float(row.get("stoch_k")),
                stoch_d=_safe_float(row.get("stoch_d")),
            )
        )
    return indicators
