"""Financial news fetching from NewsAPI and Alpha Vantage.

Provides async HTTP clients with retry logic and rate limiting.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Final

import httpx

from app.utils.errors import ExternalAPIError
from app.utils.logging import get_logger

if TYPE_CHECKING:
    from app.config import Settings

logger = get_logger(__name__)

# ── Constants ────────────────────────────────────────────────
NEWSAPI_BASE: Final[str] = "https://newsapi.org/v2/everything"
ALPHA_VANTAGE_BASE: Final[str] = "https://www.alphavantage.co/query"
DEFAULT_LOOKBACK_DAYS: Final[int] = 7
MAX_RETRIES: Final[int] = 3
BACKOFF_FACTOR: Final[float] = 1.5
REQUEST_TIMEOUT: Final[float] = 15.0

# Map base crypto symbols to human-readable names for better news search
CRYPTO_KEYWORDS: Final[dict[str, str]] = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
    "XRP": "Ripple",
    "ADA": "Cardano",
    "DOT": "Polkadot",
    "DOGE": "Dogecoin",
    "AVAX": "Avalanche",
    "MATIC": "Polygon",
    "LINK": "Chainlink",
    "LTC": "Litecoin",
    "UNI": "Uniswap",
    "SHIB": "Shiba Inu",
    "BNB": "Binance Coin",
    "ATOM": "Cosmos",
}


# ── Domain Reputation & Trust Tiering ───────────────────────────
TIER_1_DOMAINS: Final[tuple[str, ...]] = (
    "reuters", "bloomberg", "wsj", "wall street journal", "financial times", "ft.com",
    "livemint", "mint", "moneycontrol", "economic times", "economictimes",
    "business standard", "financial express", "cnbc", "cnbc-tv18", "ndtv profit",
    "forbes", "barrons", "bse", "nse", "sec.gov", "edgar", "regulatory"
)

TIER_2_DOMAINS: Final[tuple[str, ...]] = (
    "yahoo finance", "yahoo", "marketwatch", "benzinga", "investing.com",
    "the hindu", "times of india", "hindustan times", "ndtv", "india today",
    "zee business", "outlook", "seeking alpha", "ap news", "associated press",
    "google news", "tradingview"
)


def classify_source_tier(source: str, url: str = "") -> tuple[int, str, float]:
    """Classify a news source into domain trust tiers.

    Returns:
        (tier_number, tier_label, tier_weight)
        Tier 1: High Trust (1.0 weight) - Official disclosures, leading financial wires
        Tier 2: Secondary Media (0.65 weight) - Aggregators, mainstream news
        Tier 3: Unverified / High Risk (0.25 weight) - Blogs, forums, retail social feeds
    """
    text = f"{source} {url}".lower()
    for t1 in TIER_1_DOMAINS:
        if t1 in text:
            return 1, "Tier 1: High Trust", 1.0
    for t2 in TIER_2_DOMAINS:
        if t2 in text:
            return 2, "Tier 2: Secondary Media", 0.65
    return 3, "Tier 3: Unverified", 0.25


class NewsArticle:
    """Normalized news article container with domain reputation metadata."""

    __slots__ = (
        "title",
        "source",
        "published_at",
        "url",
        "description",
        "source_tier",
        "trust_label",
        "tier_weight",
    )

    def __init__(
        self,
        title: str,
        source: str,
        published_at: datetime,
        url: str = "",
        description: str = "",
    ) -> None:
        self.title = title
        self.source = source
        self.published_at = published_at
        self.url = url
        self.description = description
        tier, label, weight = classify_source_tier(source, url)
        self.source_tier = tier
        self.trust_label = label
        self.tier_weight = weight

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "source": self.source,
            "published_at": self.published_at.isoformat(),
            "url": self.url,
            "description": self.description,
            "source_tier": self.source_tier,
            "trust_label": self.trust_label,
            "tier_weight": self.tier_weight,
        }


class NewsFetcher:
    """Async news fetcher aggregating NewsAPI and Alpha Vantage results."""

    def __init__(self, settings: Settings) -> None:
        self._newsapi_key = settings.newsapi_key
        self._alpha_vantage_key = settings.alpha_vantage_key

    @staticmethod
    def _build_search_query(ticker: str) -> str:
        """Convert a ticker into an optimal news search query.

        For crypto pairs like 'ETH/USDT', search for 'Ethereum OR ETH crypto'.
        For exchange-suffixed tickers like 'RELIANCE.NS', search for 'RELIANCE'.
        For stock tickers like 'AAPL', return as-is.
        """
        base = ticker.split("/")[0].upper() if "/" in ticker else ticker.upper()
        if "." in base:
            base = base.split(".")[0]
        crypto_name = CRYPTO_KEYWORDS.get(base)
        if crypto_name:
            return f"{crypto_name} OR {base} crypto"
        return base

    def _has_valid_key(self, key: str | None) -> bool:
        if not key:
            return False
        k = key.strip().lower()
        return not (k.startswith("your_") or "here" in k or "placeholder" in k or "demo" in k)

    async def fetch(self, ticker: str, lookback_days: int = DEFAULT_LOOKBACK_DAYS) -> list[NewsArticle]:
        """Fetch news articles for a ticker from all configured sources.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL').
            lookback_days: Number of days to look back.

        Returns:
            Deduplicated and sorted (newest-first) list of NewsArticle.
        """
        tasks: list[asyncio.Task[list[NewsArticle]]] = []

        # Always include Google News RSS (real-time, zero keys needed, covers NSE/BSE/US/Crypto)
        tasks.append(
            asyncio.create_task(self._fetch_google_news(ticker, lookback_days))
        )

        # Include Yahoo Finance news
        tasks.append(
            asyncio.create_task(self._fetch_yfinance(ticker))
        )

        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            if self._has_valid_key(self._newsapi_key):
                tasks.append(
                    asyncio.create_task(self._fetch_newsapi(client, ticker, lookback_days))
                )
            if self._has_valid_key(self._alpha_vantage_key):
                tasks.append(
                    asyncio.create_task(self._fetch_alpha_vantage(client, ticker))
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)

        articles: list[NewsArticle] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("News fetch failed: %s", result)
            else:
                articles.extend(result)

        # Deduplicate by title, sort newest first
        seen: set[str] = set()
        unique: list[NewsArticle] = []
        for article in articles:
            key = article.title.strip().lower()
            if key not in seen:
                seen.add(key)
                unique.append(article)

        unique.sort(key=lambda a: a.published_at, reverse=True)
        logger.info("Fetched %d unique articles for %s.", len(unique), ticker)
        return unique

    # ── NewsAPI ─────────────────────────────────────────────

    async def _fetch_newsapi(
        self, client: httpx.AsyncClient, ticker: str, lookback_days: int
    ) -> list[NewsArticle]:
        """Fetch from NewsAPI with retry + exponential backoff."""
        from_date = (datetime.now(tz=timezone.utc) - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        query = self._build_search_query(ticker)
        params = {
            "q": query,
            "from": from_date,
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": 50,
            "apiKey": self._newsapi_key,
        }
        data = await self._request_with_retry(client, NEWSAPI_BASE, params, "NewsAPI")
        articles: list[NewsArticle] = []

        for item in data.get("articles", []):
            try:
                published = datetime.fromisoformat(
                    item["publishedAt"].replace("Z", "+00:00")
                )
                articles.append(
                    NewsArticle(
                        title=item.get("title", ""),
                        source=item.get("source", {}).get("name", "NewsAPI"),
                        published_at=published,
                        url=item.get("url", ""),
                        description=item.get("description", ""),
                    )
                )
            except (KeyError, ValueError) as exc:
                logger.debug("Skipping malformed NewsAPI article: %s", exc)

        return articles

    # ── Alpha Vantage ───────────────────────────────────────

    async def _fetch_alpha_vantage(
        self, client: httpx.AsyncClient, ticker: str
    ) -> list[NewsArticle]:
        """Fetch from Alpha Vantage News Sentiment endpoint."""
        # AV expects tickers like 'AAPL' or 'CRYPTO:BTC'
        base = ticker.split("/")[0].upper() if "/" in ticker else ticker.upper()
        av_ticker = f"CRYPTO:{base}" if base in CRYPTO_KEYWORDS else ticker
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": av_ticker,
            "limit": 50,
            "apikey": self._alpha_vantage_key,
        }
        data = await self._request_with_retry(client, ALPHA_VANTAGE_BASE, params, "AlphaVantage")
        articles: list[NewsArticle] = []

        for item in data.get("feed", []):
            try:
                # AV format: "20240115T143000"
                raw_time = item.get("time_published", "")
                published = datetime.strptime(raw_time, "%Y%m%dT%H%M%S").replace(
                    tzinfo=timezone.utc
                )
                articles.append(
                    NewsArticle(
                        title=item.get("title", ""),
                        source=item.get("source", "AlphaVantage"),
                        published_at=published,
                        url=item.get("url", ""),
                        description=item.get("summary", ""),
                    )
                )
            except (KeyError, ValueError) as exc:
                logger.debug("Skipping malformed AV article: %s", exc)

        return articles

    # ── Yahoo Finance ───────────────────────────────────────

    async def _fetch_yfinance(self, ticker: str) -> list[NewsArticle]:
        """Fetch live news from Yahoo Finance for any ticker without API keys."""
        def _get_news() -> list[NewsArticle]:
            import yfinance as yf
            # Format ticker for yfinance
            sym = ticker.replace("/", "-")
            yf_ticker = yf.Ticker(sym)
            raw_news = getattr(yf_ticker, "news", []) or []
            articles: list[NewsArticle] = []

            for item in raw_news:
                title = ""
                source = "Yahoo Finance"
                published_at = datetime.now(tz=timezone.utc)
                url = ""

                # Format in yfinance >= 0.2.40: item['content']
                if "content" in item and isinstance(item["content"], dict):
                    c = item["content"]
                    title = c.get("title", "")
                    provider = c.get("provider", {})
                    if isinstance(provider, dict) and "displayName" in provider:
                        source = provider["displayName"]
                    pub_str = c.get("pubDate")
                    if pub_str:
                        try:
                            published_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                        except Exception:
                            pass
                    click_through = c.get("clickThroughUrl", {})
                    if isinstance(click_through, dict):
                        url = click_through.get("url", "")
                elif "title" in item:
                    title = item.get("title", "")
                    source = item.get("publisher", "Yahoo Finance")
                    ts = item.get("providerPublishTime")
                    if ts:
                        try:
                            published_at = datetime.fromtimestamp(ts, tz=timezone.utc)
                        except Exception:
                            pass
                    url = item.get("link", "")

                if title:
                    articles.append(
                        NewsArticle(
                            title=title.strip(),
                            source=source or "Financial News",
                            published_at=published_at,
                            url=url,
                        )
                    )
            return articles

        try:
            return await asyncio.to_thread(_get_news)
        except Exception as exc:
            logger.warning("Yahoo Finance news fetch failed for %s: %s", ticker, exc)
            return []

    # ── Google News RSS ─────────────────────────────────────

    async def _fetch_google_news(self, ticker: str, lookback_days: int = 14) -> list[NewsArticle]:
        """Fetch live verified financial news from Google News RSS feed."""
        def _get_gnews() -> list[NewsArticle]:
            import urllib.request
            import urllib.parse
            import xml.etree.ElementTree as ET
            from email.utils import parsedate_to_datetime

            base = ticker.replace(".NS", "").replace(".BO", "").split("/")[0].upper()
            is_indian = ticker.endswith(".NS") or ticker.endswith(".BO") or base in [
                "IRFC", "RELIANCE", "TCS", "HDFCBANK", "INFY", "IREDA", "IOC", "SBIN", "TATAMOTORS"
            ]

            search_kw = f"{base} share price OR {base} stock"
            if is_indian:
                url = (
                    f"https://news.google.com/rss/search?q={urllib.parse.quote(search_kw)}"
                    f"+when:{max(7, lookback_days)}d&hl=en-IN&gl=IN&ceid=IN:en"
                )
            else:
                url = (
                    f"https://news.google.com/rss/search?q={urllib.parse.quote(search_kw)}"
                    f"+when:{max(7, lookback_days)}d&hl=en-US&gl=US&ceid=US:en"
                )

            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            articles: list[NewsArticle] = []

            try:
                with urllib.request.urlopen(req, timeout=12.0) as resp:
                    tree = ET.fromstring(resp.read())
                    for item in tree.findall(".//item")[:25]:
                        title = item.find("title").text if item.find("title") is not None else ""
                        source = item.find("source").text if item.find("source") is not None else "Financial Media"
                        link = item.find("link").text if item.find("link") is not None else ""
                        pub_str = item.find("pubDate").text if item.find("pubDate") is not None else ""

                        pub_dt = datetime.now(tz=timezone.utc)
                        if pub_str:
                            try:
                                pub_dt = parsedate_to_datetime(pub_str)
                            except Exception:
                                pass

                        # Clean trailing source name in Google News RSS title (e.g., "... - Livemint")
                        if " - " in title:
                            clean_title = title.rsplit(" - ", 1)[0].strip()
                        else:
                            clean_title = title.strip()

                        if clean_title:
                            articles.append(
                                NewsArticle(
                                    title=clean_title,
                                    source=source.strip(),
                                    published_at=pub_dt,
                                    url=link,
                                )
                            )
            except Exception as e:
                logger.warning("Google News RSS parsing error for %s: %s", ticker, e)

            return articles

        try:
            return await asyncio.to_thread(_get_gnews)
        except Exception as exc:
            logger.warning("Google News task failed for %s: %s", ticker, exc)
            return []

    # ── HTTP helper ─────────────────────────────────────────

    @staticmethod
    async def _request_with_retry(
        client: httpx.AsyncClient,
        url: str,
        params: dict[str, Any],
        service_name: str,
    ) -> dict[str, Any]:
        """Make an HTTP GET with exponential backoff retry."""
        last_exc: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()  # type: ignore[no-any-return]
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_exc = exc
                wait = BACKOFF_FACTOR ** attempt
                logger.warning(
                    "%s request failed (attempt %d/%d): %s — retrying in %.1fs",
                    service_name, attempt, MAX_RETRIES, exc, wait,
                )
                await asyncio.sleep(wait)

        raise ExternalAPIError(service_name, str(last_exc))
