"""
Tests for data fetcher service.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientSession

from app.services.data_fetcher import (CompanyInfo, DataFetcherService,
                                       NewsArticle, StockHistoricalData,
                                       StockQuote)


class TestDataFetcherService:
    """Test DataFetcherService."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        async with DataFetcherService() as service:
            assert service.session is not None
            assert isinstance(service.session, ClientSession)

        # Session should be closed after context exit
        assert service.session.closed

    @pytest.mark.asyncio
    async def test_service_requires_context_manager(self):
        """Test that service requires async context manager."""
        service = DataFetcherService()

        with pytest.raises(RuntimeError, match="must be used as async context manager"):
            # This should fail because session is None
            await service.get_stock_quote("AAPL")

    @pytest.mark.asyncio
    async def test_get_stock_quote_polygon_success(self):
        """Test successful stock quote from Polygon.io."""
        mock_response_data = {
            "status": "OK",
            "results": [
                {
                    "c": 150.25,  # close
                    "o": 148.50,  # open
                    "v": 1000000,  # volume
                    "t": int(datetime.now().timestamp() * 1000),  # timestamp
                }
            ],
        }

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_get.return_value.__aenter__.return_value = mock_response

            async with DataFetcherService() as service:
                service.polygon_api_key = "test-key"
                quote = await service.get_stock_quote("AAPL")

                assert quote is not None
                assert isinstance(quote, StockQuote)
                assert quote.symbol == "AAPL"
                assert quote.price == Decimal("150.25")
                assert quote.change == Decimal("1.75")  # 150.25 - 148.50
                assert quote.volume == 1000000

    @pytest.mark.asyncio
    async def test_get_stock_quote_polygon_failure_fallback(self):
        """Test fallback to Yahoo when Polygon fails."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            # Simulate Polygon failure
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_get.return_value.__aenter__.return_value = mock_response

            async with DataFetcherService() as service:
                service.polygon_api_key = "test-key"
                quote = await service.get_stock_quote("AAPL")

                # Should return None since Yahoo fallback is not implemented
                assert quote is None

    @pytest.mark.asyncio
    async def test_get_historical_data_polygon_success(self):
        """Test successful historical data from Polygon.io."""
        mock_response_data = {
            "status": "OK",
            "results": [
                {
                    "t": int((datetime.now() - timedelta(days=1)).timestamp() * 1000),
                    "o": 148.50,
                    "h": 152.00,
                    "l": 147.00,
                    "c": 150.25,
                    "v": 1000000,
                },
                {
                    "t": int(datetime.now().timestamp() * 1000),
                    "o": 150.25,
                    "h": 153.00,
                    "l": 149.00,
                    "c": 151.50,
                    "v": 1200000,
                },
            ],
        }

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_get.return_value.__aenter__.return_value = mock_response

            async with DataFetcherService() as service:
                service.polygon_api_key = "test-key"
                data = await service.get_historical_data("AAPL", days=30)

                assert len(data) == 2
                assert all(isinstance(item, StockHistoricalData) for item in data)
                assert data[0].symbol == "AAPL"
                assert data[0].open_price == Decimal("148.50")
                assert data[0].close == Decimal("150.25")
                assert data[1].high == Decimal("153.00")

    @pytest.mark.asyncio
    async def test_get_company_info_polygon_success(self):
        """Test successful company info from Polygon.io."""
        mock_response_data = {
            "status": "OK",
            "results": {
                "name": "Apple Inc.",
                "sic_description": "Technology",
                "industry_sector": "Consumer Electronics",
                "market_cap": 2500000000000,
                "description": "Apple Inc. designs and manufactures consumer electronics.",
                "homepage_url": "https://www.apple.com",
            },
        }

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_get.return_value.__aenter__.return_value = mock_response

            async with DataFetcherService() as service:
                service.polygon_api_key = "test-key"
                info = await service.get_company_info("AAPL")

                assert info is not None
                assert isinstance(info, CompanyInfo)
                assert info.symbol == "AAPL"
                assert info.name == "Apple Inc."
                assert info.sector == "Technology"
                assert info.industry == "Consumer Electronics"
                assert info.market_cap == Decimal("2500000000000")
                assert info.website == "https://www.apple.com"

    @pytest.mark.asyncio
    async def test_get_news_polygon_success(self):
        """Test successful news from Polygon.io."""
        mock_response_data = {
            "status": "OK",
            "results": [
                {
                    "title": "Apple Reports Strong Q4 Earnings",
                    "description": "Apple exceeded analyst expectations...",
                    "publisher": {"name": "Reuters"},
                    "article_url": "https://example.com/news/1",
                    "author": "John Doe",
                    "published_utc": "2023-01-15T10:30:00Z",
                    "tickers": ["AAPL"],
                }
            ],
        }

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_get.return_value.__aenter__.return_value = mock_response

            async with DataFetcherService() as service:
                service.polygon_api_key = "test-key"
                service.news_api_key = None  # Disable NewsAPI for this test
                articles = await service.get_news(symbols=["AAPL"], limit=10)

                assert len(articles) == 1
                assert isinstance(articles[0], NewsArticle)
                assert articles[0].headline == "Apple Reports Strong Q4 Earnings"
                assert articles[0].source == "Reuters"
                assert articles[0].symbols == ["AAPL"]

    @pytest.mark.asyncio
    async def test_get_news_newsapi_success(self):
        """Test successful news from NewsAPI."""
        mock_response_data = {
            "status": "ok",
            "articles": [
                {
                    "title": "Stock Market Update",
                    "description": "Market sees gains...",
                    "source": {"name": "Bloomberg"},
                    "url": "https://example.com/news/2",
                    "author": "Jane Smith",
                    "publishedAt": "2023-01-15T15:45:00Z",
                    "content": "Full article content...",
                }
            ],
        }

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_response_data)
            mock_get.return_value.__aenter__.return_value = mock_response

            async with DataFetcherService() as service:
                service.polygon_api_key = None  # Disable Polygon for this test
                service.news_api_key = "test-key"
                articles = await service.get_news(limit=10)

                assert len(articles) == 1
                assert articles[0].headline == "Stock Market Update"
                assert articles[0].source == "Bloomberg"
                assert articles[0].content == "Full article content..."

    @pytest.mark.asyncio
    async def test_no_api_keys_returns_empty_results(self):
        """Test behavior when no API keys are provided."""
        async with DataFetcherService() as service:
            # No API keys set
            service.polygon_api_key = None
            service.alpha_vantage_api_key = None
            service.news_api_key = None

            quote = await service.get_stock_quote("AAPL")
            assert quote is None

            historical = await service.get_historical_data("AAPL")
            assert historical == []

            info = await service.get_company_info("AAPL")
            assert info is None

            news = await service.get_news()
            assert news == []

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test proper error handling for API failures."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            # Simulate network error
            mock_get.side_effect = Exception("Network error")

            async with DataFetcherService() as service:
                service.polygon_api_key = "test-key"

                # Should not raise exception, should return None/empty
                quote = await service.get_stock_quote("AAPL")
                assert quote is None

                historical = await service.get_historical_data("AAPL")
                assert historical == []

                info = await service.get_company_info("AAPL")
                assert info is None


class TestDataClasses:
    """Test data classes."""

    def test_stock_quote_creation(self):
        """Test StockQuote data class."""
        quote = StockQuote(
            symbol="AAPL",
            price=Decimal("150.25"),
            change=Decimal("1.75"),
            change_percent=Decimal("1.18"),
            volume=1000000,
            timestamp=datetime.now(),
        )

        assert quote.symbol == "AAPL"
        assert quote.price == Decimal("150.25")
        assert quote.volume == 1000000

    def test_historical_data_creation(self):
        """Test StockHistoricalData data class."""
        data = StockHistoricalData(
            symbol="AAPL",
            date=datetime.now(),
            open_price=Decimal("148.50"),
            high=Decimal("152.00"),
            low=Decimal("147.00"),
            close=Decimal("150.25"),
            volume=1000000,
            adjusted_close=Decimal("150.25"),
        )

        assert data.symbol == "AAPL"
        assert data.open_price == Decimal("148.50")
        assert data.volume == 1000000

    def test_company_info_creation(self):
        """Test CompanyInfo data class."""
        info = CompanyInfo(
            symbol="AAPL",
            name="Apple Inc.",
            sector="Technology",
            industry="Consumer Electronics",
            market_cap=Decimal("2500000000000"),
            description="Apple Inc. designs consumer electronics.",
            website="https://www.apple.com",
        )

        assert info.symbol == "AAPL"
        assert info.name == "Apple Inc."
        assert info.market_cap == Decimal("2500000000000")

    def test_news_article_creation(self):
        """Test NewsArticle data class."""
        article = NewsArticle(
            headline="Apple Reports Earnings",
            summary="Strong quarter for Apple...",
            content="Full article content...",
            source="Reuters",
            url="https://example.com/news",
            author="John Doe",
            published_at=datetime.now(),
            symbols=["AAPL"],
        )

        assert article.headline == "Apple Reports Earnings"
        assert article.source == "Reuters"
        assert article.symbols == ["AAPL"]
