"""
Data fetcher service for external APIs.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import aiohttp

from app.core.config import settings


@dataclass
class StockQuote:
    """Stock quote data."""

    symbol: str
    price: Decimal
    change: Decimal
    change_percent: Decimal
    volume: int
    timestamp: datetime


@dataclass
class StockHistoricalData:
    """Historical stock data."""

    symbol: str
    date: datetime
    open_price: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    adjusted_close: Optional[Decimal] = None


@dataclass
class CompanyInfo:
    """Company information."""

    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[Decimal] = None
    description: Optional[str] = None
    website: Optional[str] = None
    pe_ratio: Optional[Decimal] = None
    forward_pe: Optional[Decimal] = None
    price_to_book: Optional[Decimal] = None
    price_to_sales: Optional[Decimal] = None
    dividend_yield: Optional[Decimal] = None
    beta: Optional[Decimal] = None


@dataclass(init=False)
class NewsArticle:
    """News article data with legacy title/description aliases.

    Older demo services in this project constructed news with
    ``title``/``description``/``sentiment`` while the canonical data fetcher
    used ``headline``/``summary``. This initializer keeps both shapes working
    while normalizing the internal fields.
    """

    headline: str
    summary: Optional[str]
    content: Optional[str]
    source: str
    url: Optional[str]
    author: Optional[str]
    published_at: datetime
    symbols: List[str]
    sentiment_label: str
    sentiment_score: Decimal
    source_id: str
    source_type: str
    relevance_score: Optional[Decimal]

    def __init__(
        self,
        headline: Optional[str] = None,
        summary: Optional[str] = None,
        content: Optional[str] = None,
        source: str = "unknown",
        url: Optional[str] = None,
        author: Optional[str] = None,
        published_at: Optional[datetime] = None,
        symbols: Optional[List[str]] = None,
        sentiment_label: Optional[str] = None,
        sentiment_score: Optional[Decimal] = None,
        source_id: Optional[str] = None,
        source_type: str = "live",
        relevance_score: Optional[Decimal] = None,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        sentiment: Optional[str] = None,
    ) -> None:
        self.headline = headline or title or ""
        self.summary = summary if summary is not None else description
        self.content = content
        self.source = source
        self.url = url
        self.author = author
        self.published_at = published_at or datetime.utcnow()
        self.symbols = symbols or []
        self.sentiment_label = (sentiment_label or sentiment or "neutral").lower()
        self.sentiment_score = sentiment_score or self._score_for_label(
            self.sentiment_label
        )
        self.source_id = source_id or "unknown-news-source"
        self.source_type = source_type
        self.relevance_score = relevance_score

    @staticmethod
    def _score_for_label(label: str) -> Decimal:
        if label == "positive":
            return Decimal("0.4")
        if label == "negative":
            return Decimal("-0.4")
        return Decimal("0.0")

    @property
    def title(self) -> str:
        """Backward-compatible title alias."""
        return self.headline

    @property
    def description(self) -> Optional[str]:
        """Backward-compatible description alias."""
        return self.summary

    @property
    def sentiment(self) -> str:
        """Backward-compatible sentiment alias."""
        return self.sentiment_label


class DataFetcherService:
    """Service for fetching data from external APIs."""

    def __init__(self):
        self.polygon_api_key = settings.POLYGON_API_KEY
        self.alpha_vantage_api_key = settings.ALPHA_VANTAGE_API_KEY
        self.news_api_key = settings.NEWS_API_KEY
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def get_stock_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get current stock quote."""
        if not self.session:
            raise RuntimeError(
                "DataFetcherService must be used as async context manager"
            )

        # Try Polygon.io first, then fallback to Yahoo Finance
        quote = await self._get_polygon_quote(symbol)
        if not quote:
            quote = await self._get_yahoo_quote(symbol)

        return quote

    async def get_historical_data(
        self, symbol: str, days: int = 365, interval: str = "1d"
    ) -> List[StockHistoricalData]:
        """Get historical stock data."""
        if not self.session:
            raise RuntimeError(
                "DataFetcherService must be used as async context manager"
            )

        # Try Polygon.io first, then fallback to Yahoo Finance
        data = await self._get_polygon_historical(symbol, days, interval)
        if not data:
            data = await self._get_yahoo_historical(symbol, days, interval)

        return data or []

    async def get_company_info(self, symbol: str) -> Optional[CompanyInfo]:
        """Get company information."""
        if not self.session:
            raise RuntimeError(
                "DataFetcherService must be used as async context manager"
            )

        # Try Polygon.io first, then fallback to Yahoo Finance
        info = await self._get_polygon_company_info(symbol)
        if not info:
            info = await self._get_yahoo_company_info(symbol)

        return info

    async def get_news(
        self, symbols: Optional[List[str]] = None, limit: int = 50
    ) -> List[NewsArticle]:
        """Get financial news."""
        if not self.session:
            raise RuntimeError(
                "DataFetcherService must be used as async context manager"
            )

        # Try multiple news sources
        articles = []

        # Polygon.io news
        polygon_articles = await self._get_polygon_news(symbols, limit // 2)
        articles.extend(polygon_articles)

        # NewsAPI
        newsapi_articles = await self._get_newsapi_articles(symbols, limit // 2)
        articles.extend(newsapi_articles)

        return articles[:limit]

    # Polygon.io API methods
    async def _get_polygon_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get quote from Polygon.io."""
        if not self.polygon_api_key:
            return None

        try:
            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
            params = {"apikey": self.polygon_api_key}

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                if data.get("status") != "OK" or not data.get("results"):
                    return None

                result = data["results"][0]
                return StockQuote(
                    symbol=symbol.upper(),
                    price=Decimal(str(result["c"])),
                    change=Decimal(str(result["c"] - result["o"])),
                    change_percent=Decimal(
                        str(((result["c"] - result["o"]) / result["o"]) * 100)
                    ),
                    volume=int(result["v"]),
                    timestamp=datetime.fromtimestamp(result["t"] / 1000),
                )
        except Exception as e:
            print(f"Error fetching Polygon quote for {symbol}: {e}")
            return None

    async def _get_polygon_historical(
        self, symbol: str, days: int, interval: str
    ) -> Optional[List[StockHistoricalData]]:
        """Get historical data from Polygon.io."""
        if not self.polygon_api_key:
            return None

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
            params = {"apikey": self.polygon_api_key}

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                if data.get("status") != "OK" or not data.get("results"):
                    return None

                historical_data = []
                for result in data["results"]:
                    historical_data.append(
                        StockHistoricalData(
                            symbol=symbol.upper(),
                            date=datetime.fromtimestamp(result["t"] / 1000),
                            open_price=Decimal(str(result["o"])),
                            high=Decimal(str(result["h"])),
                            low=Decimal(str(result["l"])),
                            close=Decimal(str(result["c"])),
                            volume=int(result["v"]),
                            adjusted_close=Decimal(
                                str(result["c"])
                            ),  # Polygon returns adjusted
                        )
                    )

                return historical_data
        except Exception as e:
            print(f"Error fetching Polygon historical data for {symbol}: {e}")
            return None

    async def _get_polygon_company_info(self, symbol: str) -> Optional[CompanyInfo]:
        """Get company info from Polygon.io."""
        if not self.polygon_api_key:
            return None

        try:
            url = f"https://api.polygon.io/v3/reference/tickers/{symbol}"
            params = {"apikey": self.polygon_api_key}

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                if data.get("status") != "OK" or not data.get("results"):
                    return None

                result = data["results"]
                return CompanyInfo(
                    symbol=symbol.upper(),
                    name=result.get("name", ""),
                    sector=result.get("sic_description"),
                    industry=result.get("industry_sector"),
                    market_cap=(
                        Decimal(str(result["market_cap"]))
                        if result.get("market_cap")
                        else None
                    ),
                    description=result.get("description"),
                    website=result.get("homepage_url"),
                )
        except Exception as e:
            print(f"Error fetching Polygon company info for {symbol}: {e}")
            return None

    async def _get_polygon_news(
        self, symbols: Optional[List[str]], limit: int
    ) -> List[NewsArticle]:
        """Get news from Polygon.io."""
        if not self.polygon_api_key:
            return []

        try:
            url = "https://api.polygon.io/v2/reference/news"
            params = {"apikey": self.polygon_api_key, "limit": limit}

            if symbols:
                params["ticker"] = ",".join(symbols)

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return []

                data = await response.json()
                if data.get("status") != "OK" or not data.get("results"):
                    return []

                articles = []
                for result in data["results"]:
                    articles.append(
                        NewsArticle(
                            headline=result.get("title", ""),
                            summary=result.get("description"),
                            content=None,  # Polygon doesn't provide full content
                            source=result.get("publisher", {}).get("name", "Polygon"),
                            url=result.get("article_url"),
                            author=result.get("author"),
                            published_at=datetime.fromisoformat(
                                result["published_utc"].replace("Z", "+00:00")
                            ),
                            symbols=result.get("tickers", []),
                        )
                    )

                return articles
        except Exception as e:
            print(f"Error fetching Polygon news: {e}")
            return []

    # Yahoo Finance fallback methods
    async def _get_yahoo_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get quote from Yahoo Finance (fallback)."""
        try:
            # This would use yfinance library or Yahoo Finance API
            # For now, return None as fallback
            return None
        except Exception as e:
            print(f"Error fetching Yahoo quote for {symbol}: {e}")
            return None

    async def _get_yahoo_historical(
        self, symbol: str, days: int, interval: str
    ) -> Optional[List[StockHistoricalData]]:
        """Get historical data from Yahoo Finance (fallback)."""
        try:
            # This would use yfinance library
            # For now, return None as fallback
            return None
        except Exception as e:
            print(f"Error fetching Yahoo historical data for {symbol}: {e}")
            return None

    async def _get_yahoo_company_info(self, symbol: str) -> Optional[CompanyInfo]:
        """Get company info from Yahoo Finance (fallback)."""
        try:
            # This would use yfinance library
            # For now, return None as fallback
            return None
        except Exception as e:
            print(f"Error fetching Yahoo company info for {symbol}: {e}")
            return None

    # NewsAPI methods
    async def _get_newsapi_articles(
        self, symbols: Optional[List[str]], limit: int
    ) -> List[NewsArticle]:
        """Get news from NewsAPI."""
        if not self.news_api_key:
            return []

        try:
            url = "https://newsapi.org/v2/everything"
            query = "stock market finance"
            if symbols:
                query += " " + " OR ".join(symbols)

            params = {
                "apiKey": self.news_api_key,
                "q": query,
                "sortBy": "publishedAt",
                "language": "en",
                "pageSize": limit,
            }

            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return []

                data = await response.json()
                if data.get("status") != "ok" or not data.get("articles"):
                    return []

                articles = []
                for article in data["articles"]:
                    # Try to determine relevant symbols from content
                    relevant_symbols = []
                    if symbols:
                        content_lower = (
                            article.get("title", "")
                            + " "
                            + article.get("description", "")
                        ).lower()
                        relevant_symbols = [
                            s for s in symbols if s.lower() in content_lower
                        ]

                    articles.append(
                        NewsArticle(
                            headline=article.get("title", ""),
                            summary=article.get("description"),
                            content=article.get("content"),
                            source=article.get("source", {}).get("name", "NewsAPI"),
                            url=article.get("url"),
                            author=article.get("author"),
                            published_at=datetime.fromisoformat(
                                article["publishedAt"].replace("Z", "+00:00")
                            ),
                            symbols=relevant_symbols,
                        )
                    )

                return articles
        except Exception as e:
            print(f"Error fetching NewsAPI articles: {e}")
            return []
