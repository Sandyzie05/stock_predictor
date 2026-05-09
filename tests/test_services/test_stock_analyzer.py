"""
Tests for stock analyzer service.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

from app.services.data_fetcher import (CompanyInfo, StockHistoricalData,
                                       StockQuote)
from app.services.stock_analyzer import (FundamentalMetrics, StockAnalysis,
                                         StockAnalyzerService,
                                         TechnicalIndicators)


class TestStockAnalyzerService:
    """Test StockAnalyzerService."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        async with StockAnalyzerService() as service:
            assert service.data_fetcher is not None

        # Data fetcher should be closed after context exit
        assert service.data_fetcher.session.closed

    @pytest.mark.asyncio
    async def test_service_requires_context_manager(self):
        """Test that service requires async context manager."""
        service = StockAnalyzerService()

        with pytest.raises(RuntimeError, match="must be used as async context manager"):
            await service.analyze_stock("AAPL")

    @pytest.mark.asyncio
    async def test_analyze_stock_success(self):
        """Test successful stock analysis."""
        # Mock data
        historical_data = self._create_mock_historical_data("AAPL", 30)
        mock_quote = StockQuote(
            symbol="AAPL",
            price=Decimal("150.00"),
            change=Decimal("2.50"),
            change_percent=Decimal("1.69"),
            volume=1000000,
            timestamp=datetime.utcnow(),
        )
        mock_company = CompanyInfo(
            symbol="AAPL",
            name="Apple Inc.",
            sector="Technology",
            market_cap=Decimal("2500000000000"),
        )

        with patch(
            "app.services.data_fetcher.DataFetcherService"
        ) as mock_fetcher_class:
            mock_fetcher = AsyncMock()
            mock_fetcher.get_historical_data.return_value = historical_data
            mock_fetcher.get_stock_quote.return_value = mock_quote
            mock_fetcher.get_company_info.return_value = mock_company
            mock_fetcher_class.return_value = mock_fetcher

            async with StockAnalyzerService() as service:
                analysis = await service.analyze_stock("AAPL")

                assert analysis is not None
                assert isinstance(analysis, StockAnalysis)
                assert analysis.symbol == "AAPL"
                assert analysis.current_price == Decimal("150.00")
                assert analysis.technical_indicators is not None
                assert analysis.fundamental_metrics is not None

    @pytest.mark.asyncio
    async def test_analyze_stock_no_data(self):
        """Test analysis when no historical data is available."""
        with patch(
            "app.services.data_fetcher.DataFetcherService"
        ) as mock_fetcher_class:
            mock_fetcher = AsyncMock()
            mock_fetcher.get_historical_data.return_value = None
            mock_fetcher.get_stock_quote.return_value = None
            mock_fetcher.get_company_info.return_value = None
            mock_fetcher_class.return_value = mock_fetcher

            async with StockAnalyzerService() as service:
                analysis = await service.analyze_stock("INVALID")

                assert analysis is None

    @pytest.mark.asyncio
    async def test_technical_analysis_only(self):
        """Test analysis with only technical indicators."""
        historical_data = self._create_mock_historical_data("AAPL", 50)
        mock_quote = StockQuote(
            symbol="AAPL",
            price=Decimal("150.00"),
            change=Decimal("2.50"),
            change_percent=Decimal("1.69"),
            volume=1000000,
            timestamp=datetime.utcnow(),
        )

        with patch(
            "app.services.data_fetcher.DataFetcherService"
        ) as mock_fetcher_class:
            mock_fetcher = AsyncMock()
            mock_fetcher.get_historical_data.return_value = historical_data
            mock_fetcher.get_stock_quote.return_value = mock_quote
            mock_fetcher.get_company_info.return_value = None
            mock_fetcher_class.return_value = mock_fetcher

            async with StockAnalyzerService() as service:
                analysis = await service.analyze_stock(
                    "AAPL", include_technical=True, include_fundamental=False
                )

                assert analysis is not None
                assert analysis.technical_indicators is not None
                assert analysis.fundamental_metrics is None

    @pytest.mark.asyncio
    async def test_get_technical_signals_success(self):
        """Test technical signals generation."""
        historical_data = self._create_mock_historical_data("AAPL", 100)
        mock_quote = StockQuote(
            symbol="AAPL",
            price=Decimal("150.00"),
            change=Decimal("2.50"),
            change_percent=Decimal("1.69"),
            volume=1000000,
            timestamp=datetime.utcnow(),
        )

        with patch(
            "app.services.data_fetcher.DataFetcherService"
        ) as mock_fetcher_class:
            mock_fetcher = AsyncMock()
            mock_fetcher.get_historical_data.return_value = historical_data
            mock_fetcher.get_stock_quote.return_value = mock_quote
            mock_fetcher.get_company_info.return_value = None
            mock_fetcher_class.return_value = mock_fetcher

            async with StockAnalyzerService() as service:
                signals = await service.get_technical_signals("AAPL")

                assert signals is not None
                assert isinstance(signals, dict)
                # Should have various signal types
                assert any(
                    key in signals
                    for key in ["rsi", "macd", "moving_averages", "bollinger"]
                )

    def test_calculate_ema(self):
        """Test EMA calculation."""
        service = StockAnalyzerService()
        prices = np.array([10, 11, 12, 13, 14, 15])

        ema = service._calculate_ema(prices, 3)

        # EMA should be between min and max prices
        assert 10 <= ema <= 15
        # Should be weighted toward recent prices
        assert ema > np.mean(prices)

    def test_calculate_rsi(self):
        """Test RSI calculation."""
        service = StockAnalyzerService()

        # Create prices with clear up/down pattern
        prices = np.array(
            [100, 102, 104, 103, 105, 107, 106, 108, 110, 109, 111, 113, 112, 114, 116]
        )

        rsi = service._calculate_rsi(prices, 14)

        # RSI should be between 0 and 100
        assert 0 <= rsi <= 100
        # With mostly upward movement, RSI should be > 50
        assert rsi > 50

    def test_calculate_atr(self):
        """Test ATR calculation."""
        service = StockAnalyzerService()

        highs = np.array([105, 107, 106, 108, 110])
        lows = np.array([95, 97, 96, 98, 100])
        closes = np.array([100, 102, 101, 103, 105])

        atr = service._calculate_atr(highs, lows, closes, 4)

        # ATR should be positive
        assert atr > 0
        # Should be reasonable given the price range
        assert 5 <= atr <= 15

    def test_analyze_trend_bullish(self):
        """Test trend analysis - bullish case."""
        service = StockAnalyzerService()

        # Create upward trending data
        data = []
        base_price = 100
        for i in range(25):
            price = base_price + i * 0.5  # Gradual increase
            data.append(
                StockHistoricalData(
                    symbol="TEST",
                    date=datetime.utcnow() - timedelta(days=25 - i),
                    open_price=Decimal(str(price - 0.1)),
                    high=Decimal(str(price + 0.2)),
                    low=Decimal(str(price - 0.3)),
                    close=Decimal(str(price)),
                    volume=1000000,
                )
            )

        trend = service._analyze_trend(data)
        assert trend == "bullish"

    def test_analyze_trend_bearish(self):
        """Test trend analysis - bearish case."""
        service = StockAnalyzerService()

        # Create downward trending data
        data = []
        base_price = 120
        for i in range(25):
            price = base_price - i * 0.5  # Gradual decrease
            data.append(
                StockHistoricalData(
                    symbol="TEST",
                    date=datetime.utcnow() - timedelta(days=25 - i),
                    open_price=Decimal(str(price - 0.1)),
                    high=Decimal(str(price + 0.2)),
                    low=Decimal(str(price - 0.3)),
                    close=Decimal(str(price)),
                    volume=1000000,
                )
            )

        trend = service._analyze_trend(data)
        assert trend == "bearish"

    def test_find_support_resistance(self):
        """Test support and resistance calculation."""
        service = StockAnalyzerService()

        data = []
        prices = [
            100,
            105,
            98,
            110,
            95,
            115,
            92,
            108,
            90,
            112,
        ]  # Clear high/low pattern
        for i, price in enumerate(prices):
            data.append(
                StockHistoricalData(
                    symbol="TEST",
                    date=datetime.utcnow() - timedelta(days=len(prices) - i),
                    open_price=Decimal(str(price - 1)),
                    high=Decimal(str(price + 2)),
                    low=Decimal(str(price - 3)),
                    close=Decimal(str(price)),
                    volume=1000000,
                )
            )

        levels = service._find_support_resistance(data)

        assert "support" in levels
        assert "resistance" in levels
        assert "current_range" in levels
        assert levels["resistance"] > levels["support"]

    def test_calculate_volatility(self):
        """Test volatility calculation."""
        service = StockAnalyzerService()

        # Create data with varying volatility
        data = []
        prices = [100, 102, 99, 103, 97, 105, 95, 107, 93, 110]
        for i, price in enumerate(prices):
            data.append(
                StockHistoricalData(
                    symbol="TEST",
                    date=datetime.utcnow() - timedelta(days=len(prices) - i),
                    open_price=Decimal(str(price)),
                    high=Decimal(str(price + 1)),
                    low=Decimal(str(price - 1)),
                    close=Decimal(str(price)),
                    volume=1000000,
                )
            )

        volatility = service._calculate_volatility(data)

        assert volatility > 0
        assert isinstance(volatility, Decimal)

    def test_analyze_volume(self):
        """Test volume analysis."""
        service = StockAnalyzerService()

        data = []
        volumes = [1000000] * 19 + [2000000]  # High recent volume
        for i, volume in enumerate(volumes):
            data.append(
                StockHistoricalData(
                    symbol="TEST",
                    date=datetime.utcnow() - timedelta(days=len(volumes) - i),
                    open_price=Decimal("100"),
                    high=Decimal("101"),
                    low=Decimal("99"),
                    close=Decimal("100"),
                    volume=volume,
                )
            )

        volume_analysis = service._analyze_volume(data)

        assert "average_volume" in volume_analysis
        assert "recent_volume" in volume_analysis
        assert "volume_ratio" in volume_analysis
        assert "volume_trend" in volume_analysis
        assert volume_analysis["volume_trend"] == "increasing"

    def _create_mock_historical_data(
        self, symbol: str, days: int
    ) -> List[StockHistoricalData]:
        """Create mock historical data for testing."""
        data = []
        base_price = 100.0

        for i in range(days):
            # Add some randomness but keep it realistic
            price_change = (i * 0.1) + np.random.normal(
                0, 1
            )  # Slight upward trend with noise
            price = base_price + price_change

            data.append(
                StockHistoricalData(
                    symbol=symbol,
                    date=datetime.utcnow() - timedelta(days=days - i),
                    open_price=Decimal(str(round(price - 0.5, 2))),
                    high=Decimal(str(round(price + 1.0, 2))),
                    low=Decimal(str(round(price - 1.5, 2))),
                    close=Decimal(str(round(price, 2))),
                    volume=int(np.random.normal(1000000, 200000)),
                    adjusted_close=Decimal(str(round(price, 2))),
                )
            )

        return data


class TestDataClasses:
    """Test data classes."""

    def test_technical_indicators_creation(self):
        """Test TechnicalIndicators data class."""
        indicators = TechnicalIndicators(
            symbol="AAPL",
            date=datetime.utcnow(),
            sma_20=Decimal("150.00"),
            rsi=Decimal("65.5"),
            macd=Decimal("2.5"),
        )

        assert indicators.symbol == "AAPL"
        assert indicators.sma_20 == Decimal("150.00")
        assert indicators.rsi == Decimal("65.5")
        assert indicators.macd == Decimal("2.5")

    def test_fundamental_metrics_creation(self):
        """Test FundamentalMetrics data class."""
        metrics = FundamentalMetrics(
            symbol="AAPL",
            date=datetime.utcnow(),
            market_cap=Decimal("2500000000000"),
            pe_ratio=Decimal("25.5"),
            roe=Decimal("0.25"),
        )

        assert metrics.symbol == "AAPL"
        assert metrics.market_cap == Decimal("2500000000000")
        assert metrics.pe_ratio == Decimal("25.5")
        assert metrics.roe == Decimal("0.25")

    def test_stock_analysis_creation(self):
        """Test StockAnalysis data class."""
        analysis = StockAnalysis(
            symbol="AAPL",
            analysis_date=datetime.utcnow(),
            current_price=Decimal("150.00"),
            trend_analysis="bullish",
            volatility=Decimal("0.25"),
        )

        assert analysis.symbol == "AAPL"
        assert analysis.current_price == Decimal("150.00")
        assert analysis.trend_analysis == "bullish"
        assert analysis.volatility == Decimal("0.25")
