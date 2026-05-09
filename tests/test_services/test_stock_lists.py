"""
Tests for stock list generation service.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.services.stock_lists import (
    StockListGeneratorService,
    StockListType,
    StockListItem,
    StockList,
)
from app.services.data_fetcher import StockQuote, CompanyInfo, StockHistoricalData
from app.services.recommendation_engine import (
    InvestmentRecommendation,
    RecommendationType,
    RiskLevel,
)


class TestStockListGeneratorService:
    """Test StockListGeneratorService."""
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        async with StockListGeneratorService() as service:
            assert service.data_fetcher is not None
            assert service.stock_analyzer is not None
            assert service.prediction_engine is not None
            assert service.recommendation_engine is not None
            
    @pytest.mark.asyncio
    async def test_service_requires_context_manager(self):
        """Test that service requires async context manager."""
        service = StockListGeneratorService()
        
        with pytest.raises(RuntimeError, match="must be used as async context manager"):
            await service.generate_stock_list(StockListType.ALL_TIME_HIGH)
            
    @pytest.mark.asyncio
    async def test_generate_undervalued_list(self):
        """Test undervalued stock list generation."""
        with patch('app.services.stock_lists.DataFetcherService') as mock_fetcher_cls, \
             patch('app.services.stock_lists.StockAnalyzerService') as mock_analyzer_cls, \
             patch('app.services.stock_lists.PredictionEngineService') as mock_predictor_cls, \
             patch('app.services.stock_lists.RecommendationEngineService') as mock_recommender_cls:
            
            service = StockListGeneratorService()
            
            # Mock services
            mock_fetcher = AsyncMock()
            mock_analyzer = AsyncMock()
            mock_predictor = AsyncMock()
            mock_recommender = AsyncMock()
            
            mock_fetcher_cls.return_value = mock_fetcher
            mock_analyzer_cls.return_value = mock_analyzer
            mock_predictor_cls.return_value = mock_predictor
            mock_recommender_cls.return_value = mock_recommender
            
            # Set up context manager mocks
            mock_fetcher.__aenter__.return_value = mock_fetcher
            mock_fetcher.__aexit__.return_value = None
            mock_analyzer.__aenter__.return_value = mock_analyzer
            mock_analyzer.__aexit__.return_value = None
            mock_predictor.__aenter__.return_value = mock_predictor
            mock_predictor.__aexit__.return_value = None
            mock_recommender.__aenter__.return_value = mock_recommender
            mock_recommender.__aexit__.return_value = None
            
            # Set service dependencies
            service.data_fetcher = mock_fetcher
            service.stock_analyzer = mock_analyzer
            service.prediction_engine = mock_predictor
            service.recommendation_engine = mock_recommender
            
            # Mock undervalued recommendation
            mock_recommendation = InvestmentRecommendation(
                symbol="AAPL",
                company_name="Apple Inc.",
                recommendation=RecommendationType.BUY,
                confidence=Decimal("0.8"),
                fundamental_score=Decimal("75"),  # Strong fundamentals
                technical_score=Decimal("55"),   # Not overbought
                sentiment_score=Decimal("70"),
                overall_score=Decimal("67"),
                current_price=Decimal("150.0"),
                target_price=Decimal("170.0"),
                risk_level=RiskLevel.MODERATE,
                reasoning=["Strong financials", "Good growth prospects"],
            )
            
            # Mock recommendation engine to return undervalued stock
            async def mock_generate_recommendation(symbol):
                if symbol == "AAPL":
                    return mock_recommendation
                return None
                
            mock_recommender.generate_recommendation = mock_generate_recommendation
            
            # Test undervalued list generation
            result = await service.generate_stock_list(
                StockListType.UNDERVALUED, 
                max_items=5,
                symbols=["AAPL", "GOOGL"]
            )
            
            # Assertions
            assert result is not None
            assert isinstance(result, StockList)
            assert result.list_type == StockListType.UNDERVALUED
            assert result.title == "Top Undervalued Stocks"
            assert len(result.items) == 1  # Only AAPL should qualify
            assert result.items[0].symbol == "AAPL"
            assert result.items[0].rank == 1
            assert result.items[0].recommendation == RecommendationType.BUY
            assert len(result.items[0].reasoning) > 0
            assert "Strong fundamentals" in str(result.items[0].reasoning)
            
    @pytest.mark.asyncio
    async def test_generate_overvalued_list(self):
        """Test overvalued stock list generation."""
        with patch('app.services.stock_lists.DataFetcherService') as mock_fetcher_cls, \
             patch('app.services.stock_lists.StockAnalyzerService') as mock_analyzer_cls, \
             patch('app.services.stock_lists.PredictionEngineService') as mock_predictor_cls, \
             patch('app.services.stock_lists.RecommendationEngineService') as mock_recommender_cls:
            
            service = StockListGeneratorService()
            
            # Mock services
            mock_fetcher = AsyncMock()
            mock_analyzer = AsyncMock()
            mock_predictor = AsyncMock()
            mock_recommender = AsyncMock()
            
            mock_fetcher_cls.return_value = mock_fetcher
            mock_analyzer_cls.return_value = mock_analyzer
            mock_predictor_cls.return_value = mock_predictor
            mock_recommender_cls.return_value = mock_recommender
            
            # Set up context manager mocks
            mock_fetcher.__aenter__.return_value = mock_fetcher
            mock_fetcher.__aexit__.return_value = None
            mock_analyzer.__aenter__.return_value = mock_analyzer
            mock_analyzer.__aexit__.return_value = None
            mock_predictor.__aenter__.return_value = mock_predictor
            mock_predictor.__aexit__.return_value = None
            mock_recommender.__aenter__.return_value = mock_recommender
            mock_recommender.__aexit__.return_value = None
            
            # Set service dependencies
            service.data_fetcher = mock_fetcher
            service.stock_analyzer = mock_analyzer
            service.prediction_engine = mock_predictor
            service.recommendation_engine = mock_recommender
            
            # Mock overvalued recommendation
            mock_recommendation = InvestmentRecommendation(
                symbol="TSLA",
                company_name="Tesla Inc.",
                recommendation=RecommendationType.SELL,
                confidence=Decimal("0.7"),
                fundamental_score=Decimal("45"),  # Weak fundamentals
                technical_score=Decimal("80"),   # Overbought
                sentiment_score=Decimal("30"),
                overall_score=Decimal("52"),
                current_price=Decimal("250.0"),
                target_price=Decimal("200.0"),
                risk_level=RiskLevel.HIGH,
                reasoning=["Overvalued metrics", "Weak fundamentals"],
            )
            
            # Mock recommendation engine to return overvalued stock
            async def mock_generate_recommendation(symbol):
                if symbol == "TSLA":
                    return mock_recommendation
                return None
                
            mock_recommender.generate_recommendation = mock_generate_recommendation
            
            # Test overvalued list generation
            result = await service.generate_stock_list(
                StockListType.OVERVALUED,
                max_items=5,
                symbols=["TSLA", "NVDA"]
            )
            
            # Assertions
            assert result is not None
            assert isinstance(result, StockList)
            assert result.list_type == StockListType.OVERVALUED
            assert result.title == "Top Overvalued Stocks"
            assert len(result.items) == 1  # Only TSLA should qualify
            assert result.items[0].symbol == "TSLA"
            assert result.items[0].rank == 1
            assert result.items[0].recommendation == RecommendationType.SELL
            assert len(result.items[0].reasoning) > 0
            
    @pytest.mark.asyncio
    async def test_generate_ath_list(self):
        """Test all-time high list generation."""
        with patch('app.services.stock_lists.DataFetcherService') as mock_fetcher_cls, \
             patch('app.services.stock_lists.StockAnalyzerService') as mock_analyzer_cls, \
             patch('app.services.stock_lists.PredictionEngineService') as mock_predictor_cls, \
             patch('app.services.stock_lists.RecommendationEngineService') as mock_recommender_cls:
            
            service = StockListGeneratorService()
            
            # Mock services
            mock_fetcher = AsyncMock()
            mock_analyzer = AsyncMock()
            mock_predictor = AsyncMock()
            mock_recommender = AsyncMock()
            
            mock_fetcher_cls.return_value = mock_fetcher
            mock_analyzer_cls.return_value = mock_analyzer
            mock_predictor_cls.return_value = mock_predictor
            mock_recommender_cls.return_value = mock_recommender
            
            # Set up context manager mocks
            mock_fetcher.__aenter__.return_value = mock_fetcher
            mock_fetcher.__aexit__.return_value = None
            mock_analyzer.__aenter__.return_value = mock_analyzer
            mock_analyzer.__aexit__.return_value = None
            mock_predictor.__aenter__.return_value = mock_predictor
            mock_predictor.__aexit__.return_value = None
            mock_recommender.__aenter__.return_value = mock_recommender
            mock_recommender.__aexit__.return_value = None
            
            # Set service dependencies
            service.data_fetcher = mock_fetcher
            service.stock_analyzer = mock_analyzer
            service.prediction_engine = mock_predictor
            service.recommendation_engine = mock_recommender
            
            # Mock current quote (near ATH)
            mock_quote = StockQuote(
                symbol="AAPL",
                price=Decimal("180.0"),  # Current price
                change=Decimal("2.0"),
                change_percent=Decimal("1.1"),
                volume=50000000,
                timestamp=datetime.now(),
            )
            
            mock_company = CompanyInfo(
                symbol="AAPL",
                name="Apple Inc.",
                market_cap=Decimal("2800000000000"),
            )
            
            # Mock historical data showing ATH at $185
            mock_historical = [
                StockHistoricalData(
                    symbol="AAPL",
                    date=datetime.now() - timedelta(days=30),
                    open_price=Decimal("170.0"),
                    high=Decimal("185.0"),  # All-time high
                    low=Decimal("165.0"),
                    close=Decimal("175.0"),
                    volume=40000000,
                ),
                StockHistoricalData(
                    symbol="AAPL",
                    date=datetime.now() - timedelta(days=1),
                    open_price=Decimal("178.0"),
                    high=Decimal("182.0"),
                    low=Decimal("176.0"),
                    close=Decimal("180.0"),
                    volume=45000000,
                ),
            ]
            
            # Set up mock returns
            mock_fetcher.get_stock_quote.return_value = mock_quote
            mock_fetcher.get_company_info.return_value = mock_company
            mock_fetcher.get_historical_data.return_value = mock_historical
            
            # Test ATH list generation
            result = await service.generate_stock_list(
                StockListType.ALL_TIME_HIGH,
                max_items=5,
                symbols=["AAPL"]
            )
            
            # Assertions
            assert result is not None
            assert isinstance(result, StockList)
            assert result.list_type == StockListType.ALL_TIME_HIGH
            assert result.title == "Stocks at All-Time Highs"
            assert len(result.items) == 1  # AAPL should qualify (within 5% of ATH)
            assert result.items[0].symbol == "AAPL"
            assert result.items[0].rank == 1
            assert result.items[0].distance_from_ath is not None
            assert result.items[0].distance_from_ath < 5  # Within 5% of ATH
            assert result.items[0].ath_date is not None
            assert len(result.items[0].reasoning) > 0
            
    @pytest.mark.asyncio
    async def test_generate_sp500_list(self):
        """Test S&P 500 list generation."""
        with patch('app.services.stock_lists.DataFetcherService') as mock_fetcher_cls, \
             patch('app.services.stock_lists.StockAnalyzerService') as mock_analyzer_cls, \
             patch('app.services.stock_lists.PredictionEngineService') as mock_predictor_cls, \
             patch('app.services.stock_lists.RecommendationEngineService') as mock_recommender_cls:
            
            service = StockListGeneratorService()
            
            # Mock services  
            mock_fetcher = AsyncMock()
            mock_analyzer = AsyncMock()
            mock_predictor = AsyncMock()
            mock_recommender = AsyncMock()
            
            mock_fetcher_cls.return_value = mock_fetcher
            mock_analyzer_cls.return_value = mock_analyzer
            mock_predictor_cls.return_value = mock_predictor
            mock_recommender_cls.return_value = mock_recommender
            
            # Set up context manager mocks
            mock_fetcher.__aenter__.return_value = mock_fetcher
            mock_fetcher.__aexit__.return_value = None
            mock_analyzer.__aenter__.return_value = mock_analyzer
            mock_analyzer.__aexit__.return_value = None
            mock_predictor.__aenter__.return_value = mock_predictor
            mock_predictor.__aexit__.return_value = None
            mock_recommender.__aenter__.return_value = mock_recommender
            mock_recommender.__aexit__.return_value = None
            
            # Set service dependencies
            service.data_fetcher = mock_fetcher
            service.stock_analyzer = mock_analyzer
            service.prediction_engine = mock_predictor
            service.recommendation_engine = mock_recommender
            
            # Mock S&P 500 stock data
            async def mock_get_quote(symbol):
                return StockQuote(
                    symbol=symbol,
                    price=Decimal("100.0"),
                    change=Decimal("1.0"),
                    change_percent=Decimal("1.0"),
                    volume=1000000,
                    timestamp=datetime.now(),
                )
                
            async def mock_get_company_info(symbol):
                return CompanyInfo(
                    symbol=symbol,
                    name=f"{symbol} Corp",
                    market_cap=Decimal("100000000000"),  # $100B
                )
                
            async def mock_generate_recommendation(symbol):
                return InvestmentRecommendation(
                    symbol=symbol,
                    company_name=f"{symbol} Corp",
                    recommendation=RecommendationType.HOLD,
                    confidence=Decimal("0.6"),
                    risk_level=RiskLevel.MODERATE,
                )
            
            mock_fetcher.get_stock_quote = mock_get_quote
            mock_fetcher.get_company_info = mock_get_company_info
            mock_recommender.generate_recommendation = mock_generate_recommendation
            
            # Test S&P 500 list generation
            result = await service.generate_stock_list(
                StockListType.SP500_ALL,
                max_items=5
            )
            
            # Assertions
            assert result is not None
            assert isinstance(result, StockList)
            assert result.list_type == StockListType.SP500_ALL
            assert result.title == "S&P 500 Companies"
            assert len(result.items) == 5  # Should get 5 items
            assert all(item.symbol in service.SP500_SYMBOLS for item in result.items)
            assert all(item.rank > 0 for item in result.items)
            assert all("S&P 500 constituent" in str(item.reasoning) for item in result.items)


class TestStockListDataClasses:
    """Test stock list data classes."""
    
    def test_stock_list_item_creation(self):
        """Test StockListItem data class creation."""
        item = StockListItem(
            symbol="AAPL",
            company_name="Apple Inc.",
            current_price=Decimal("150.0"),
            list_type=StockListType.ALL_TIME_HIGH,
            rank=1,
            score=Decimal("95.0"),
            reasoning=["Near all-time high", "Strong performance"],
            change_percent=Decimal("1.5"),
            volume=50000000,
            recommendation=RecommendationType.BUY,
        )
        
        assert item.symbol == "AAPL"
        assert item.company_name == "Apple Inc."
        assert item.current_price == Decimal("150.0")
        assert item.list_type == StockListType.ALL_TIME_HIGH
        assert item.rank == 1
        assert item.score == Decimal("95.0")
        assert len(item.reasoning) == 2
        assert item.change_percent == Decimal("1.5")
        assert item.volume == 50000000
        assert item.recommendation == RecommendationType.BUY
        assert isinstance(item.created_at, datetime)
        
    def test_stock_list_creation(self):
        """Test StockList data class creation."""
        item = StockListItem(
            symbol="AAPL",
            company_name="Apple Inc.",
            current_price=Decimal("150.0"),
            list_type=StockListType.UNDERVALUED,
            rank=1,
            score=Decimal("85.0"),
        )
        
        stock_list = StockList(
            list_type=StockListType.UNDERVALUED,
            title="Top Undervalued Stocks",
            description="Stocks with strong fundamentals trading below fair value",
            items=[item],
            total_items=1,
            generation_criteria={"min_fundamental_score": 65},
        )
        
        assert stock_list.list_type == StockListType.UNDERVALUED
        assert stock_list.title == "Top Undervalued Stocks"
        assert len(stock_list.items) == 1
        assert stock_list.total_items == 1
        assert stock_list.generation_criteria["min_fundamental_score"] == 65
        assert isinstance(stock_list.last_updated, datetime)
        
    def test_stock_list_type_enum(self):
        """Test StockListType enum values."""
        assert StockListType.ALL_TIME_HIGH.value == "all_time_high"
        assert StockListType.ALL_TIME_LOW.value == "all_time_low"
        assert StockListType.SP500_ALL.value == "sp500_all"
        assert StockListType.SP500_ATH.value == "sp500_ath"
        assert StockListType.SP500_ATL.value == "sp500_atl"
        assert StockListType.UNDERVALUED.value == "undervalued"
        assert StockListType.OVERVALUED.value == "overvalued"
        assert StockListType.STRONG_BUY.value == "strong_buy"
        assert StockListType.STRONG_SELL.value == "strong_sell"
