"""
Tests for prediction engine service.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.services.prediction_engine import (
    PredictionEngineService,
    PredictionType,
    PredictionHorizon,
    PredictionFeatures,
    PredictionSignal,
    ModelPrediction,
)
from app.services.data_fetcher import StockQuote, StockHistoricalData
from app.services.stock_analyzer import (
    TechnicalIndicators,
    StockAnalysis,
)


class TestPredictionEngineService:
    """Test PredictionEngineService."""
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        async with PredictionEngineService() as service:
            assert service.data_fetcher is not None
            assert service.stock_analyzer is not None
        
    @pytest.mark.asyncio
    async def test_service_requires_context_manager(self):
        """Test that service requires async context manager."""
        service = PredictionEngineService()
        
        with pytest.raises(RuntimeError, match="must be used as async context manager"):
            await service.predict_stock("AAPL")
            
    @pytest.mark.asyncio
    async def test_predict_stock_success(self):
        """Test successful stock prediction."""
        with patch('app.services.prediction_engine.StockAnalyzerService') as mock_analyzer_cls, \
             patch('app.services.prediction_engine.DataFetcherService') as mock_fetcher_cls:
            
            # Create service instance
            service = PredictionEngineService()
            
            # Mock analyzer service
            mock_analyzer = AsyncMock()
            mock_analyzer_cls.return_value = mock_analyzer
            
            # Mock data fetcher service  
            mock_fetcher = AsyncMock()
            mock_fetcher_cls.return_value = mock_fetcher
            
            # Mock analysis result
            mock_technical = TechnicalIndicators(
                symbol="AAPL",
                date=datetime.utcnow(),
                rsi=Decimal("45.0"),
                macd=Decimal("2.5"),
                macd_signal=Decimal("2.0"),
                sma_20=Decimal("150.0"),
                sma_50=Decimal("148.0"),
                bollinger_upper=Decimal("155.0"),
                bollinger_lower=Decimal("145.0"),
                atr=Decimal("3.5"),
            )
            
            mock_analysis = StockAnalysis(
                symbol="AAPL",
                analysis_date=datetime.utcnow(),
                technical_indicators=mock_technical,
                volatility=Decimal("25.0"),
                volume_analysis={"volume_ratio": Decimal("1.2"), "trend": "increasing"},
            )
            
            mock_analyzer.analyze_stock.return_value = mock_analysis
            
            # Mock quote
            mock_quote = StockQuote(
                symbol="AAPL",
                price=Decimal("152.50"),
                change=Decimal("1.50"),
                change_percent=Decimal("1.0"),
                volume=1000000,
                timestamp=datetime.utcnow(),
            )
            mock_fetcher.get_stock_quote.return_value = mock_quote
            
            # Mock historical data
            mock_historical = [
                StockHistoricalData(
                    symbol="AAPL",
                    date=datetime.now() - timedelta(days=i),
                    open_price=Decimal("150.0"),
                    high=Decimal("155.0"),
                    low=Decimal("149.0"),
                    close=Decimal("151.0") + Decimal(str(i * 0.5)),
                    volume=1000000 + i * 10000,
                ) for i in range(30)
            ]
            mock_fetcher.get_historical_data.return_value = mock_historical
            
            # Set up context manager mocks
            mock_analyzer.__aenter__.return_value = mock_analyzer
            mock_analyzer.__aexit__.return_value = None
            mock_fetcher.__aenter__.return_value = mock_fetcher
            mock_fetcher.__aexit__.return_value = None
            
            # Set up service dependencies
            service.data_fetcher = mock_fetcher
            service.stock_analyzer = mock_analyzer
            
            # Test prediction
            result = await service.predict_stock("AAPL")
            
            # Assertions
            assert result is not None
            assert isinstance(result, ModelPrediction)
            assert result.symbol == "AAPL"
            assert result.short_term.prediction in [PredictionType.BUY, PredictionType.SELL, PredictionType.HOLD]
            assert result.medium_term.prediction in [PredictionType.BUY, PredictionType.SELL, PredictionType.HOLD]
            assert result.long_term.prediction in [PredictionType.BUY, PredictionType.SELL, PredictionType.HOLD]
            assert result.overall_sentiment in [PredictionType.BUY, PredictionType.SELL, PredictionType.HOLD]
            assert result.model_version == "v1.0.0_rule_based"
            
    @pytest.mark.asyncio
    async def test_predict_stock_no_analysis(self):
        """Test prediction when no analysis data available."""
        with patch('app.services.prediction_engine.StockAnalyzerService') as mock_analyzer_cls, \
             patch('app.services.prediction_engine.DataFetcherService') as mock_fetcher_cls:
            
            service = PredictionEngineService()
            
            # Mock analyzer service
            mock_analyzer = AsyncMock()
            mock_analyzer_cls.return_value = mock_analyzer
            mock_analyzer.analyze_stock.return_value = None
            
            # Mock data fetcher service
            mock_fetcher = AsyncMock()
            mock_fetcher_cls.return_value = mock_fetcher
            
            # Set up context manager mocks
            mock_analyzer.__aenter__.return_value = mock_analyzer
            mock_analyzer.__aexit__.return_value = None
            mock_fetcher.__aenter__.return_value = mock_fetcher
            mock_fetcher.__aexit__.return_value = None
            
            # Set up service dependencies
            service.stock_analyzer = mock_analyzer
            service.data_fetcher = mock_fetcher
            
            # Test prediction
            result = await service.predict_stock("INVALID")
            
            # Should return None when no analysis available
            assert result is None
            
    def test_calculate_price_changes(self):
        """Test price change calculation."""
        service = PredictionEngineService()
        
        # Create test historical data
        historical = [
            StockHistoricalData(
                symbol="AAPL",
                date=datetime.now() - timedelta(days=30-i),
                open_price=Decimal("100.0"),
                high=Decimal("105.0"),
                low=Decimal("95.0"),
                close=Decimal("100.0") + Decimal(str(i * 0.5)),
                volume=1000000,
            ) for i in range(30)
        ]
        
        changes = service._calculate_price_changes(historical)
        
        # Should return tuple of (1d, 7d, 30d) changes
        assert len(changes) == 3
        assert all(isinstance(change, (Decimal, type(None))) for change in changes)
        
        # With 30 days of data, all changes should be calculated
        assert changes[0] is not None  # 1-day change
        assert changes[1] is not None  # 7-day change
        assert changes[2] is not None  # 30-day change
        
    def test_calculate_price_changes_insufficient_data(self):
        """Test price change calculation with insufficient data."""
        service = PredictionEngineService()
        
        # Only 1 day of data
        historical = [
            StockHistoricalData(
                symbol="AAPL",
                date=datetime.now(),
                open_price=Decimal("100.0"),
                high=Decimal("105.0"),
                low=Decimal("95.0"),
                close=Decimal("102.0"),
                volume=1000000,
            )
        ]
        
        changes = service._calculate_price_changes(historical)
        
        # Should return all None with insufficient data
        assert changes == (None, None, None)
        
    def test_determine_overall_sentiment_bullish(self):
        """Test overall sentiment determination - bullish case."""
        service = PredictionEngineService()
        
        predictions = [
            PredictionSignal(
                symbol="AAPL",
                prediction=PredictionType.BUY,
                horizon=PredictionHorizon.SHORT_TERM,
                confidence=Decimal("0.8"),
            ),
            PredictionSignal(
                symbol="AAPL", 
                prediction=PredictionType.BUY,
                horizon=PredictionHorizon.MEDIUM_TERM,
                confidence=Decimal("0.7"),
            ),
            PredictionSignal(
                symbol="AAPL",
                prediction=PredictionType.HOLD,
                horizon=PredictionHorizon.LONG_TERM,
                confidence=Decimal("0.5"),
            ),
        ]
        
        overall = service._determine_overall_sentiment(predictions)
        assert overall == PredictionType.BUY
        
    def test_determine_overall_sentiment_bearish(self):
        """Test overall sentiment determination - bearish case."""
        service = PredictionEngineService()
        
        predictions = [
            PredictionSignal(
                symbol="AAPL",
                prediction=PredictionType.SELL,
                horizon=PredictionHorizon.SHORT_TERM,
                confidence=Decimal("0.9"),
            ),
            PredictionSignal(
                symbol="AAPL",
                prediction=PredictionType.SELL,
                horizon=PredictionHorizon.MEDIUM_TERM,
                confidence=Decimal("0.6"),
            ),
            PredictionSignal(
                symbol="AAPL",
                prediction=PredictionType.HOLD,
                horizon=PredictionHorizon.LONG_TERM,
                confidence=Decimal("0.3"),
            ),
        ]
        
        overall = service._determine_overall_sentiment(predictions)
        assert overall == PredictionType.SELL
        
    def test_determine_overall_sentiment_neutral(self):
        """Test overall sentiment determination - neutral case."""
        service = PredictionEngineService()
        
        predictions = [
            PredictionSignal(
                symbol="AAPL",
                prediction=PredictionType.BUY,
                horizon=PredictionHorizon.SHORT_TERM,
                confidence=Decimal("0.4"),
            ),
            PredictionSignal(
                symbol="AAPL",
                prediction=PredictionType.SELL,
                horizon=PredictionHorizon.MEDIUM_TERM,
                confidence=Decimal("0.3"),
            ),
            PredictionSignal(
                symbol="AAPL",
                prediction=PredictionType.HOLD,
                horizon=PredictionHorizon.LONG_TERM,
                confidence=Decimal("0.6"),
            ),
        ]
        
        overall = service._determine_overall_sentiment(predictions)
        assert overall == PredictionType.HOLD


class TestDataClasses:
    """Test prediction data classes."""
    
    def test_prediction_features_creation(self):
        """Test PredictionFeatures data class creation."""
        features = PredictionFeatures(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            current_price=Decimal("150.0"),
            rsi=Decimal("45.0"),
            macd=Decimal("2.5"),
        )
        
        assert features.symbol == "AAPL"
        assert isinstance(features.timestamp, datetime)
        assert features.current_price == Decimal("150.0")
        assert features.rsi == Decimal("45.0")
        assert features.macd == Decimal("2.5")
        
    def test_prediction_signal_creation(self):
        """Test PredictionSignal data class creation."""
        signal = PredictionSignal(
            symbol="AAPL",
            prediction=PredictionType.BUY,
            horizon=PredictionHorizon.SHORT_TERM,
            confidence=Decimal("0.8"),
            target_price=Decimal("160.0"),
            reasoning=["RSI oversold", "MACD bullish"],
        )
        
        assert signal.symbol == "AAPL"
        assert signal.prediction == PredictionType.BUY
        assert signal.horizon == PredictionHorizon.SHORT_TERM
        assert signal.confidence == Decimal("0.8")
        assert signal.target_price == Decimal("160.0")
        assert len(signal.reasoning) == 2
        assert isinstance(signal.created_at, datetime)
        
    def test_model_prediction_creation(self):
        """Test ModelPrediction data class creation."""
        short_signal = PredictionSignal(
            symbol="AAPL",
            prediction=PredictionType.BUY,
            horizon=PredictionHorizon.SHORT_TERM,
            confidence=Decimal("0.8"),
        )
        
        medium_signal = PredictionSignal(
            symbol="AAPL",
            prediction=PredictionType.HOLD,
            horizon=PredictionHorizon.MEDIUM_TERM,
            confidence=Decimal("0.5"),
        )
        
        long_signal = PredictionSignal(
            symbol="AAPL",
            prediction=PredictionType.BUY,
            horizon=PredictionHorizon.LONG_TERM,
            confidence=Decimal("0.7"),
        )
        
        features = PredictionFeatures(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            current_price=Decimal("150.0"),
        )
        
        prediction = ModelPrediction(
            symbol="AAPL",
            short_term=short_signal,
            medium_term=medium_signal,
            long_term=long_signal,
            overall_sentiment=PredictionType.BUY,
            model_version="v1.0.0",
            features_used=features,
        )
        
        assert prediction.symbol == "AAPL"
        assert prediction.short_term == short_signal
        assert prediction.medium_term == medium_signal
        assert prediction.long_term == long_signal
        assert prediction.overall_sentiment == PredictionType.BUY
        assert prediction.model_version == "v1.0.0"
        assert prediction.features_used == features
        assert isinstance(prediction.prediction_date, datetime)
