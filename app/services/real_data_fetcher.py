"""
Real data fetcher service for live and no-key-friendly market data.
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import aiohttp

from app.core.config import settings
from app.services.data_fetcher import (
    CompanyInfo,
    NewsArticle,
    StockHistoricalData,
    StockQuote,
)
from app.services.runtime_cache import TTLCache

try:
    import yfinance as yf
except ImportError:  # pragma: no cover - dependency is installed in runtime
    yf = None


class RealDataFetcherService:
    """Live market data service backed by yfinance with Alpha Vantage enrichment."""

    _quote_cache = TTLCache()
    _news_cache = TTLCache()
    _company_cache = TTLCache()

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.alpha_vantage_api_key = settings.ALPHA_VANTAGE_API_KEY

    async def __aenter__(self):
        """Initialize the service."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up the service."""
        if self.session:
            await self.session.close()

    async def get_stock_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get a live stock quote."""
        symbol = symbol.upper()
        cache_key = f"quote:{symbol}"
        cached = self._quote_cache.get(cache_key)
        if cached:
            return cached

        quote = await self._get_yfinance_quote(symbol)
        if quote:
            return self._quote_cache.set(
                cache_key, quote, settings.QUOTE_CACHE_TTL_SECONDS
            )

        quote = await self._get_alpha_vantage_quote(symbol)
        if quote:
            return self._quote_cache.set(
                cache_key, quote, settings.QUOTE_CACHE_TTL_SECONDS
            )

        quote = await self._get_yahoo_chart_quote(symbol)
        if quote:
            return self._quote_cache.set(
                cache_key, quote, settings.QUOTE_CACHE_TTL_SECONDS
            )
        return None

    async def get_company_info(self, symbol: str) -> Optional[CompanyInfo]:
        """Get company information with live and curated fallbacks."""
        symbol = symbol.upper()
        cache_key = f"company:{symbol}"
        cached = self._company_cache.get(cache_key)
        if cached:
            return cached

        company = await self._get_yfinance_company_info(symbol)
        if company:
            return self._company_cache.set(
                cache_key, company, settings.COMPANY_INFO_CACHE_TTL_SECONDS
            )

        company = await self._get_alpha_vantage_company_info(symbol)
        if company:
            return self._company_cache.set(
                cache_key, company, settings.COMPANY_INFO_CACHE_TTL_SECONDS
            )

        return self._company_cache.set(
            cache_key,
            self._static_company_info(symbol),
            settings.COMPANY_INFO_CACHE_TTL_SECONDS,
        )

    async def get_stock_historical_data(
        self, symbol: str, days: int = 30
    ) -> List[StockHistoricalData]:
        """Get historical stock data."""
        symbol = symbol.upper()

        historical = await self._get_yfinance_historical(symbol, days)
        if historical:
            return historical

        historical = await self._get_alpha_vantage_historical(symbol, days)
        if historical:
            return historical

        return []

    async def get_historical_data(
        self, symbol: str, days: int = 30
    ) -> List[StockHistoricalData]:
        """Compatibility alias used by existing routes and services."""
        return await self.get_stock_historical_data(symbol, days)

    async def get_financial_news(self, symbol: str, limit: int = 5) -> List[NewsArticle]:
        """Get ticker-specific financial news."""
        symbol = symbol.upper()
        cache_key = f"news:{symbol}:{limit}"
        cached = self._news_cache.get(cache_key)
        if cached is not None:
            return cached

        news = await self._get_yfinance_news(symbol, limit)
        if len(news) < limit:
            alpha_news = await self._get_alpha_vantage_news(symbol, limit)
            news = self._merge_news(news, alpha_news, limit)

        if news:
            return self._news_cache.set(
                cache_key, news[:limit], settings.NEWS_CACHE_TTL_SECONDS
            )

        return self._news_cache.set(
            cache_key,
            self._synthetic_news(symbol, limit),
            settings.NEWS_CACHE_TTL_SECONDS,
        )

    async def get_news(self, symbol: str, limit: int = 5) -> List[NewsArticle]:
        """Compatibility alias used by existing routes and services."""
        return await self.get_financial_news(symbol, limit)

    async def test_connection(self) -> Dict[str, Any]:
        """Test the current live data path."""
        quote = await self.get_stock_quote("AAPL")
        if quote and quote.price > 0:
            return {
                "status": "healthy",
                "message": "Live market data connection working",
                "test_quote": f"AAPL: ${quote.price}",
                "data_source": "yfinance/Yahoo Finance",
                "alpha_vantage_configured": bool(self.alpha_vantage_api_key),
            }

        return {
            "status": "degraded",
            "message": "Live market data unavailable; fallback sources did not return data.",
            "data_source": "yfinance/Yahoo Finance",
            "alpha_vantage_configured": bool(self.alpha_vantage_api_key),
        }

    async def _get_yfinance_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get a quote via yfinance."""
        if yf is None:
            return None

        def _load_quote() -> Optional[StockQuote]:
            ticker = yf.Ticker(self._yahoo_symbol(symbol))
            fast_info = self._safe_dict(getattr(ticker, "fast_info", None))

            price = self._as_float(
                fast_info.get("lastPrice") or fast_info.get("regularMarketPrice")
            )
            previous_close = self._as_float(fast_info.get("previousClose"))
            volume = self._as_int(
                fast_info.get("lastVolume") or fast_info.get("regularMarketVolume")
            )

            if price is None:
                history = ticker.history(period="5d", interval="1d", auto_adjust=False)
                if history is None or history.empty:
                    return None
                closes = history["Close"].dropna()
                if closes.empty:
                    return None
                price = float(closes.iloc[-1])
                previous_close = (
                    float(closes.iloc[-2]) if len(closes) > 1 else float(closes.iloc[-1])
                )
                if "Volume" in history.columns:
                    volume = self._as_int(history["Volume"].fillna(0).iloc[-1])

            if price is None:
                return None

            previous_close = previous_close if previous_close is not None else price
            change = price - previous_close
            change_percent = ((change / previous_close) * 100) if previous_close else 0.0

            return StockQuote(
                symbol=symbol,
                price=Decimal(str(round(price, 4))),
                change=Decimal(str(round(change, 4))),
                change_percent=Decimal(str(round(change_percent, 4))),
                volume=volume or 0,
                timestamp=datetime.now(),
            )

        try:
            return await asyncio.to_thread(_load_quote)
        except Exception as exc:
            print(f"yfinance quote error for {symbol}: {exc}")
            return None

    async def _get_yfinance_historical(
        self, symbol: str, days: int
    ) -> List[StockHistoricalData]:
        """Get daily historical data via yfinance."""
        if yf is None:
            return []

        calendar_days = max(days * 2, 30)

        def _load_history() -> List[StockHistoricalData]:
            ticker = yf.Ticker(self._yahoo_symbol(symbol))
            history = ticker.history(
                period=f"{calendar_days}d",
                interval="1d",
                auto_adjust=False,
                actions=False,
            )
            if history is None or history.empty:
                return []

            rows = history.tail(days)
            items: List[StockHistoricalData] = []
            for timestamp, row in rows.iterrows():
                close_value = self._as_float(row.get("Close"))
                if close_value is None:
                    continue

                items.append(
                    StockHistoricalData(
                        symbol=symbol,
                        date=self._normalize_timestamp(timestamp),
                        open_price=Decimal(str(self._as_float(row.get("Open")) or close_value)),
                        high=Decimal(str(self._as_float(row.get("High")) or close_value)),
                        low=Decimal(str(self._as_float(row.get("Low")) or close_value)),
                        close=Decimal(str(close_value)),
                        volume=self._as_int(row.get("Volume")) or 0,
                        adjusted_close=Decimal(
                            str(self._as_float(row.get("Adj Close")) or close_value)
                        ),
                    )
                )

            return items

        try:
            return await asyncio.to_thread(_load_history)
        except Exception as exc:
            print(f"yfinance historical error for {symbol}: {exc}")
            return []

    async def _get_yfinance_company_info(self, symbol: str) -> Optional[CompanyInfo]:
        """Get company metadata via yfinance."""
        if yf is None:
            return None

        def _load_company() -> Optional[CompanyInfo]:
            ticker = yf.Ticker(self._yahoo_symbol(symbol))
            info = self._safe_dict(getattr(ticker, "info", None))
            if not info:
                return None

            market_cap = info.get("marketCap")
            website = info.get("website")
            sector = info.get("sectorDisp") or info.get("sector")
            description = info.get("longBusinessSummary") or info.get("description")
            name = (
                info.get("longName")
                or info.get("shortName")
                or info.get("displayName")
                or f"{symbol} Corporation"
            )

            return CompanyInfo(
                symbol=symbol,
                name=name,
                sector=sector,
                industry=info.get("industryDisp") or info.get("industry"),
                market_cap=Decimal(str(market_cap)) if market_cap else None,
                description=description,
                website=website,
                pe_ratio=self._optional_decimal(info.get("trailingPE")),
                forward_pe=self._optional_decimal(info.get("forwardPE")),
                price_to_book=self._optional_decimal(info.get("priceToBook")),
                price_to_sales=self._optional_decimal(
                    info.get("priceToSalesTrailing12Months")
                ),
                dividend_yield=self._optional_decimal(
                    (self._as_float(info.get("dividendYield")) or 0.0) * 100
                )
                if info.get("dividendYield") is not None
                else None,
                beta=self._optional_decimal(info.get("beta")),
            )

        try:
            return await asyncio.to_thread(_load_company)
        except Exception as exc:
            print(f"yfinance company info error for {symbol}: {exc}")
            return None

    async def _get_yfinance_news(self, symbol: str, limit: int) -> List[NewsArticle]:
        """Get recent news items via yfinance when available."""
        if yf is None:
            return []

        def _load_news() -> List[NewsArticle]:
            ticker = yf.Ticker(self._yahoo_symbol(symbol))
            raw_items = getattr(ticker, "news", None) or []
            items: List[NewsArticle] = []

            for entry in raw_items[:limit]:
                content = self._safe_dict(entry.get("content"))
                title = (
                    content.get("title")
                    or entry.get("title")
                    or f"{symbol} market update"
                )
                summary = (
                    content.get("summary")
                    or entry.get("summary")
                    or f"Recent market developments for {symbol}."
                )
                url = content.get("canonicalUrl", {}).get("url") if isinstance(
                    content.get("canonicalUrl"), dict
                ) else entry.get("link")
                provider = (
                    content.get("provider", {}).get("displayName")
                    if isinstance(content.get("provider"), dict)
                    else None
                ) or entry.get("publisher") or "Yahoo Finance"
                publish_time = (
                    content.get("pubDate")
                    or entry.get("providerPublishTime")
                    or entry.get("pubDate")
                )

                items.append(
                    NewsArticle(
                        headline=title,
                        summary=summary,
                        source=provider,
                        source_id="yahoo-finance-yfinance",
                        source_type="live",
                        url=url,
                        published_at=self._parse_published_at(publish_time),
                        symbols=[symbol],
                        sentiment_label="neutral",
                        relevance_score=Decimal("0.45"),
                    )
                )

            return items

        try:
            return await asyncio.to_thread(_load_news)
        except Exception as exc:
            print(f"yfinance news error for {symbol}: {exc}")
            return []

    async def _get_alpha_vantage_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get quote data from Alpha Vantage."""
        if not self.alpha_vantage_api_key or not self.session:
            return None

        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.alpha_vantage_api_key,
            }

            async with self.session.get(url, params=params, timeout=15) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                quote_data = data.get("Global Quote") or {}
                price = self._as_float(quote_data.get("05. price"))
                if price is None:
                    return None

                change = self._as_float(quote_data.get("09. change")) or 0.0
                change_percent = self._parse_percent(
                    quote_data.get("10. change percent")
                )
                volume = self._as_int(quote_data.get("06. volume")) or 0

                return StockQuote(
                    symbol=symbol,
                    price=Decimal(str(price)),
                    change=Decimal(str(change)),
                    change_percent=Decimal(str(change_percent)),
                    volume=volume,
                    timestamp=datetime.now(),
                )
        except Exception as exc:
            print(f"Alpha Vantage quote error for {symbol}: {exc}")
            return None

    async def _get_alpha_vantage_historical(
        self, symbol: str, days: int
    ) -> List[StockHistoricalData]:
        """Get daily time series data from Alpha Vantage."""
        if not self.alpha_vantage_api_key or not self.session:
            return []

        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "TIME_SERIES_DAILY_ADJUSTED",
                "symbol": symbol,
                "outputsize": "compact" if days <= 100 else "full",
                "apikey": self.alpha_vantage_api_key,
            }

            async with self.session.get(url, params=params, timeout=20) as response:
                if response.status != 200:
                    return []

                data = await response.json()
                series = data.get("Time Series (Daily)") or {}
                items: List[StockHistoricalData] = []

                for day, row in sorted(series.items())[-days:]:
                    close_value = self._as_float(row.get("4. close"))
                    if close_value is None:
                        continue
                    items.append(
                        StockHistoricalData(
                            symbol=symbol,
                            date=datetime.strptime(day, "%Y-%m-%d"),
                            open_price=Decimal(str(self._as_float(row.get("1. open")) or close_value)),
                            high=Decimal(str(self._as_float(row.get("2. high")) or close_value)),
                            low=Decimal(str(self._as_float(row.get("3. low")) or close_value)),
                            close=Decimal(str(close_value)),
                            volume=self._as_int(row.get("6. volume")) or 0,
                            adjusted_close=Decimal(
                                str(self._as_float(row.get("5. adjusted close")) or close_value)
                            ),
                        )
                    )

                return items
        except Exception as exc:
            print(f"Alpha Vantage historical error for {symbol}: {exc}")
            return []

    async def _get_alpha_vantage_company_info(
        self, symbol: str
    ) -> Optional[CompanyInfo]:
        """Get company overview from Alpha Vantage."""
        if not self.alpha_vantage_api_key or not self.session:
            return None

        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "OVERVIEW",
                "symbol": symbol,
                "apikey": self.alpha_vantage_api_key,
            }

            async with self.session.get(url, params=params, timeout=15) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                if "Symbol" not in data:
                    return None

                market_cap = data.get("MarketCapitalization")
                return CompanyInfo(
                    symbol=symbol,
                    name=data.get("Name", f"{symbol} Corporation"),
                    sector=data.get("Sector"),
                    industry=data.get("Industry"),
                    market_cap=Decimal(str(market_cap)) if market_cap else None,
                    description=data.get("Description"),
                    website=data.get("OfficialSite"),
                    pe_ratio=self._optional_decimal(data.get("PERatio")),
                    forward_pe=self._optional_decimal(data.get("ForwardPE")),
                    price_to_book=self._optional_decimal(data.get("PriceToBookRatio")),
                    price_to_sales=self._optional_decimal(data.get("PriceToSalesRatioTTM")),
                    dividend_yield=self._optional_decimal(
                        (self._as_float(data.get("DividendYield")) or 0.0) * 100
                    )
                    if data.get("DividendYield") not in {None, "None", ""}
                    else None,
                    beta=self._optional_decimal(data.get("Beta")),
                )
        except Exception as exc:
            print(f"Alpha Vantage company info error for {symbol}: {exc}")
            return None

    async def _get_alpha_vantage_news(self, symbol: str, limit: int) -> List[NewsArticle]:
        """Get ticker news and sentiment from Alpha Vantage when configured."""
        if not self.alpha_vantage_api_key or not self.session:
            return []

        try:
            url = "https://www.alphavantage.co/query"
            params = {
                "function": "NEWS_SENTIMENT",
                "tickers": symbol,
                "limit": str(limit),
                "apikey": self.alpha_vantage_api_key,
            }

            async with self.session.get(url, params=params, timeout=20) as response:
                if response.status != 200:
                    return []

                data = await response.json()
                feed = data.get("feed") or []
                items: List[NewsArticle] = []

                for entry in feed[:limit]:
                    label = self._normalize_sentiment_label(
                        entry.get("overall_sentiment_label")
                    )
                    score = self._as_float(entry.get("overall_sentiment_score"))
                    items.append(
                        NewsArticle(
                            headline=entry.get("title") or f"{symbol} market update",
                            summary=entry.get("summary"),
                            source=entry.get("source") or "Alpha Vantage",
                            source_id="alpha-vantage",
                            source_type="live",
                            url=entry.get("url"),
                            author=", ".join(entry.get("authors") or []),
                            published_at=self._parse_published_at(
                                entry.get("time_published")
                            ),
                            symbols=[symbol],
                            sentiment_label=label,
                            sentiment_score=Decimal(str(score)) if score is not None else None,
                            relevance_score=Decimal("0.7"),
                        )
                    )

                return items
        except Exception as exc:
            print(f"Alpha Vantage news error for {symbol}: {exc}")
            return []

    async def _get_yahoo_chart_quote(self, symbol: str) -> Optional[StockQuote]:
        """Fallback quote lookup against the raw Yahoo chart endpoint."""
        if not self.session:
            return None

        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{self._yahoo_symbol(symbol)}"
            async with self.session.get(url, timeout=10) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                chart = data.get("chart") or {}
                result = (chart.get("result") or [None])[0]
                if not result:
                    return None

                meta = result.get("meta") or {}
                price = self._as_float(meta.get("regularMarketPrice"))
                previous_close = self._as_float(meta.get("previousClose"))
                volume = self._as_int(meta.get("regularMarketVolume")) or 0

                if price is None:
                    return None

                previous_close = previous_close if previous_close is not None else price
                change = price - previous_close
                change_percent = ((change / previous_close) * 100) if previous_close else 0.0

                return StockQuote(
                    symbol=symbol,
                    price=Decimal(str(price)),
                    change=Decimal(str(change)),
                    change_percent=Decimal(str(change_percent)),
                    volume=volume,
                    timestamp=datetime.now(),
                )
        except Exception as exc:
            print(f"Yahoo chart quote error for {symbol}: {exc}")
            return None

    def _static_company_info(self, symbol: str) -> CompanyInfo:
        """Curated fallback company records for common symbols."""
        company_data = {
            "AAPL": {
                "name": "Apple Inc.",
                "sector": "Technology",
                "market_cap": Decimal("3500000000000"),
                "description": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.",
                "website": "https://www.apple.com",
            },
            "GOOGL": {
                "name": "Alphabet Inc.",
                "sector": "Communication Services",
                "market_cap": Decimal("2100000000000"),
                "description": "Alphabet Inc. provides online advertising services and cloud computing solutions.",
                "website": "https://www.alphabet.com",
            },
            "MSFT": {
                "name": "Microsoft Corporation",
                "sector": "Technology",
                "market_cap": Decimal("3200000000000"),
                "description": "Microsoft Corporation develops, licenses, and supports software, services, devices, and solutions worldwide.",
                "website": "https://www.microsoft.com",
            },
            "TSLA": {
                "name": "Tesla, Inc.",
                "sector": "Consumer Cyclical",
                "market_cap": Decimal("900000000000"),
                "description": "Tesla, Inc. designs, develops, manufactures, leases, and sells electric vehicles.",
                "website": "https://www.tesla.com",
            },
            "AMZN": {
                "name": "Amazon.com, Inc.",
                "sector": "Consumer Cyclical",
                "market_cap": Decimal("1800000000000"),
                "description": "Amazon.com, Inc. engages in the retail sale of consumer products and subscriptions.",
                "website": "https://www.amazon.com",
            },
            "META": {
                "name": "Meta Platforms, Inc.",
                "sector": "Communication Services",
                "market_cap": Decimal("1300000000000"),
                "description": "Meta Platforms, Inc. develops products that enable people to connect and share.",
                "website": "https://www.meta.com",
            },
            "NVDA": {
                "name": "NVIDIA Corporation",
                "sector": "Technology",
                "market_cap": Decimal("2800000000000"),
                "description": "NVIDIA Corporation provides graphics, and compute and networking solutions.",
                "website": "https://www.nvidia.com",
            },
        }

        data = company_data.get(
            symbol,
            {
                "name": f"{symbol} Corporation",
                "sector": "Technology",
                "market_cap": Decimal("10000000000"),
                "description": f"{symbol} is a publicly traded company.",
                "website": f"https://www.{symbol.lower()}.com",
            },
        )
        return CompanyInfo(
            symbol=symbol,
            name=data["name"],
            sector=data["sector"],
            market_cap=data["market_cap"],
            description=data["description"],
            website=data["website"],
        )

    def _synthetic_news(self, symbol: str, limit: int) -> List[NewsArticle]:
        """Fallback demo news used only when live adapters are unavailable."""
        templates = [
            (
                f"{symbol} reports strong quarterly earnings",
                f"Latest financial results show positive growth for {symbol}",
                "Yahoo Finance",
                "positive",
            ),
            (
                f"Analysts update {symbol} price targets",
                f"Investment firms adjust recommendations for {symbol}",
                "MarketWatch",
                "neutral",
            ),
            (
                f"{symbol} announces strategic partnerships",
                f"Company expands market presence through new alliances",
                "Reuters",
                "positive",
            ),
        ]

        items: List[NewsArticle] = []
        for index, (title, summary, source, sentiment) in enumerate(templates[:limit]):
            items.append(
                NewsArticle(
                    title=title,
                    description=summary,
                    source=source,
                    source_id="demo-news-generator",
                    source_type="demo",
                    url=f"https://finance.yahoo.com/news/{symbol.lower()}-{index + 1}",
                    published_at=datetime.now() - timedelta(hours=(index + 1) * 6),
                    symbols=[symbol],
                    sentiment=sentiment,
                    relevance_score=Decimal("0.2"),
                )
            )
        return items

    @staticmethod
    def _merge_news(
        primary: List[NewsArticle], secondary: List[NewsArticle], limit: int
    ) -> List[NewsArticle]:
        merged: List[NewsArticle] = []
        seen = set()
        for article in [*(primary or []), *(secondary or [])]:
            identity = article.url or article.title
            if identity in seen:
                continue
            seen.add(identity)
            merged.append(article)
            if len(merged) >= limit:
                break
        return merged

    @staticmethod
    def _safe_dict(value: Any) -> Dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _as_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _as_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _optional_decimal(value: Any) -> Optional[Decimal]:
        if value is None:
            return None
        try:
            return Decimal(str(float(value)))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_percent(value: Any) -> float:
        if value is None:
            return 0.0
        try:
            return float(str(value).replace("%", ""))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _normalize_timestamp(value: Any) -> datetime:
        if hasattr(value, "to_pydatetime"):
            return value.to_pydatetime().replace(tzinfo=None)
        if isinstance(value, datetime):
            return value.replace(tzinfo=None)
        return datetime.now()

    @staticmethod
    def _normalize_sentiment_label(label: Any) -> str:
        normalized = str(label or "neutral").lower()
        if "bullish" in normalized or normalized == "positive":
            return "positive"
        if "bearish" in normalized or normalized == "negative":
            return "negative"
        return "neutral"

    @staticmethod
    def _yahoo_symbol(symbol: str) -> str:
        return symbol.replace(".", "-")

    @staticmethod
    def _parse_published_at(value: Any) -> datetime:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value)
        if isinstance(value, str):
            for fmt in ("%Y%m%dT%H%M%S", "%Y-%m-%dT%H:%M:%SZ"):
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(
                    tzinfo=None
                )
            except ValueError:
                return datetime.now()
        return datetime.now()
