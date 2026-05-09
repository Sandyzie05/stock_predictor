"""
Tests for recommendation engine service.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.services.recommendation_engine import (
    RecommendationEngineService,
    RecommendationType,
    RiskLevel,
    InvestmentRecommendation,
    PortfolioRecommendation,
    StockScreeningCriteria,
)
from app.services.data_fetcher import StockQuote, CompanyInfo
from app.services.stock_analyzer import (
    TechnicalIndicators,
    StockAnalysis,
)
from app.services.prediction_engine import (
    ModelPrediction,
    PredictionSignal,
    PredictionType,
    PredictionHorizon,
    PredictionFeatures,
)


class TestRecommendationEngineService:
    """Test RecommendationEngineService."""
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        async with RecommendationEngineService() as service:
            assert service.data_fetcher is not None
            assert service.stock_analyzer is not None
            assert service.prediction_engine is not None
            
    @pytest.mark.asyncio
    async def test_service_requires_context_manager(self):
        """Test that service requires async context manager."""
        service = RecommendationEngineService()
        
        with pytest.raises(RuntimeError, match="must be used as async context manager"):
            await service.generate_recommendation("AAPL")
            
    @pytest.mark.asyncio
    async def test_generate_recommendation_success(self):
        """Test successful recommendation generation."""
        with patch('app.services.recommendation_engine.RealDataFetcherService') as mock_fetcher_cls, \
             patch('app.services.recommendation_engine.StockAnalyzerService') as mock_analyzer_cls, \
             patch('app.services.recommendation_engine.PredictionEngineService') as mock_predictor_cls:
            
            service = RecommendationEngineService()
            
            # Mock services
            mock_fetcher = AsyncMock()
            mock_analyzer = AsyncMock()
            mock_predictor = AsyncMock()
            
            mock_fetcher_cls.return_value = mock_fetcher
            mock_analyzer_cls.return_value = mock_analyzer
            mock_predictor_cls.return_value = mock_predictor
            
            # Set up context manager mocks
            mock_fetcher.__aenter__.return_value = mock_fetcher
            mock_fetcher.__aexit__.return_value = None
            mock_analyzer.__aenter__.return_value = mock_analyzer
            mock_analyzer.__aexit__.return_value = None
            mock_predictor.__aenter__.return_value = mock_predictor
            mock_predictor.__aexit__.return_value = None
            
            # Mock data
            mock_quote = StockQuote(
                symbol="AAPL",
                price=Decimal("150.0"),
                change=Decimal("2.0"),
                change_percent=Decimal("1.3"),
                volume=2000000,
                timestamp=datetime.now(),
            )
            
            mock_company = CompanyInfo(
                symbol="AAPL",
                name="Apple Inc.",
                sector="Technology",
                market_cap=Decimal("2500000000000"),  # $2.5T
            )
            
            mock_technical = TechnicalIndicators(
                symbol="AAPL",
                date=datetime.now(),
                rsi=Decimal("45.0"),
                macd=Decimal("2.5"),
                macd_signal=Decimal("2.0"),
                sma_20=Decimal("148.0"),
                sma_50=Decimal("145.0"),
                sma_200=Decimal("140.0"),
            )
            
            mock_analysis = StockAnalysis(
                symbol="AAPL",
                analysis_date=datetime.now(),
                technical_indicators=mock_technical,
                volatility=Decimal("25.0"),
            )
            
            # Mock prediction signals
            short_signal = PredictionSignal(
                symbol="AAPL",
                prediction=PredictionType.BUY,
                horizon=PredictionHorizon.SHORT_TERM,
                confidence=Decimal("0.8"),
                target_price=Decimal("155.0"),
                stop_loss=Decimal("142.0"),
            )
            
            medium_signal = PredictionSignal(
                symbol="AAPL",
                prediction=PredictionType.BUY,
                horizon=PredictionHorizon.MEDIUM_TERM,
                confidence=Decimal("0.75"),
                target_price=Decimal("160.0"),
                stop_loss=Decimal("142.0"),
            )
            
            long_signal = PredictionSignal(
                symbol="AAPL",
                prediction=PredictionType.BUY,
                horizon=PredictionHorizon.LONG_TERM,
                confidence=Decimal("0.7"),
                target_price=Decimal("170.0"),
                stop_loss=Decimal("142.0"),
            )
            
            mock_prediction = ModelPrediction(
                symbol="AAPL",
                short_term=short_signal,
                medium_term=medium_signal,
                long_term=long_signal,
                overall_sentiment=PredictionType.BUY,
                model_version="v1.0.0",
                features_used=PredictionFeatures(
                    symbol="AAPL",
                    timestamp=datetime.now(),
                    current_price=Decimal("150.0"),
                ),
            )
            
            # Set up mock returns
            mock_fetcher.get_stock_quote.return_value = mock_quote
            mock_fetcher.get_company_info.return_value = mock_company
            mock_analyzer.analyze_stock.return_value = mock_analysis
            mock_predictor.predict_stock.return_value = mock_prediction
            
            # Set service dependencies
            service.data_fetcher = mock_fetcher
            service.stock_analyzer = mock_analyzer
            service.prediction_engine = mock_predictor
            
            # Test recommendation generation
            result = await service.generate_recommendation("AAPL")
            
            # Assertions
            assert result is not None
            assert isinstance(result, InvestmentRecommendation)
            assert result.symbol == "AAPL"
            assert result.company_name == "Apple Inc."
            assert result.recommendation in [
                RecommendationType.STRONG_BUY,
                RecommendationType.BUY,
                RecommendationType.HOLD,
                RecommendationType.SELL,
                RecommendationType.STRONG_SELL,
            ]
            assert 0 <= result.confidence <= 1
            assert result.target_price == Decimal("160.0")
            assert result.current_price == Decimal("150.0")
            assert len(result.reasoning) > 0
            assert result.fundamental_score is not None
            assert result.technical_score is not None
            assert result.sentiment_score is not None
            assert result.overall_score is not None
            
    @pytest.mark.asyncio
    async def test_generate_recommendation_insufficient_data(self):
        """Test recommendation with insufficient data."""
        with patch('app.services.recommendation_engine.RealDataFetcherService') as mock_fetcher_cls, \
             patch('app.services.recommendation_engine.StockAnalyzerService') as mock_analyzer_cls, \
             patch('app.services.recommendation_engine.PredictionEngineService') as mock_predictor_cls:
            
            service = RecommendationEngineService()
            
            # Mock services
            mock_fetcher = AsyncMock()
            mock_analyzer = AsyncMock()
            mock_predictor = AsyncMock()
            
            mock_fetcher_cls.return_value = mock_fetcher
            mock_analyzer_cls.return_value = mock_analyzer
            mock_predictor_cls.return_value = mock_predictor
            
            # Set up context manager mocks
            mock_fetcher.__aenter__.return_value = mock_fetcher
            mock_fetcher.__aexit__.return_value = None
            mock_analyzer.__aenter__.return_value = mock_analyzer
            mock_analyzer.__aexit__.return_value = None
            mock_predictor.__aenter__.return_value = mock_predictor
            mock_predictor.__aexit__.return_value = None
            
            # Return None for insufficient data
            mock_fetcher.get_stock_quote.return_value = None
            mock_fetcher.get_company_info.return_value = None
            mock_analyzer.analyze_stock.return_value = None
            mock_predictor.predict_stock.return_value = None
            
            # Set service dependencies
            service.data_fetcher = mock_fetcher
            service.stock_analyzer = mock_analyzer
            service.prediction_engine = mock_predictor
            
            # Test recommendation generation
            result = await service.generate_recommendation("INVALID")
            
            # Should return None for insufficient data
            assert result is None
            
    def test_calculate_fundamental_score(self):
        """Test fundamental score calculation."""
        service = RecommendationEngineService()
        
        # High-quality company
        company_info = CompanyInfo(
            symbol="AAPL",
            name="Apple Inc.",
            sector="Technology",
            market_cap=Decimal("2500000000000"),  # $2.5T
        )
        
        quote = StockQuote(
            symbol="AAPL",
            price=Decimal("150.0"),
            change=Decimal("1.0"),
            change_percent=Decimal("0.67"),  # Low volatility
            volume=2000000,  # High volume
            timestamp=datetime.now(),
        )
        
        # Test with async method
        async def test_async():
            return await service._calculate_fundamental_score(company_info, quote)
            
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            score = loop.run_until_complete(test_async())
        finally:
            loop.close()
        
        # Should be high score for large cap, high volume, low volatility
        assert score > 70
        assert isinstance(score, Decimal)
        
    def test_calculate_technical_score(self):
        """Test technical score calculation."""
        service = RecommendationEngineService()
        
        # Strong technical indicators
        technical = TechnicalIndicators(
            symbol="AAPL",
            date=datetime.now(),
            rsi=Decimal("45.0"),  # Healthy RSI
            macd=Decimal("2.5"),
            macd_signal=Decimal("2.0"),  # MACD > signal (bullish)
            sma_20=Decimal("150.0"),
            sma_50=Decimal("148.0"),
            sma_200=Decimal("145.0"),  # Uptrend
        )
        
        analysis = StockAnalysis(
            symbol="AAPL",
            analysis_date=datetime.now(),
            technical_indicators=technical,
            volatility=Decimal("15.0"),  # Low volatility
        )
        
        score = service._calculate_technical_score(analysis)
        
        # Should be high score for good technical indicators
        assert score > 60
        assert isinstance(score, Decimal)
        
    def test_calculate_sentiment_score(self):
        """Test sentiment score calculation."""
        service = RecommendationEngineService()
        
        # Bullish prediction
        short_signal = PredictionSignal(
            symbol="AAPL",
            prediction=PredictionType.BUY,
            horizon=PredictionHorizon.SHORT_TERM,
            confidence=Decimal("0.8"),
        )
        
        medium_signal = PredictionSignal(
            symbol="AAPL",
            prediction=PredictionType.BUY,
            horizon=PredictionHorizon.MEDIUM_TERM,
            confidence=Decimal("0.75"),
        )
        
        long_signal = PredictionSignal(
            symbol="AAPL",
            prediction=PredictionType.BUY,
            horizon=PredictionHorizon.LONG_TERM,
            confidence=Decimal("0.7"),
        )
        
        prediction = ModelPrediction(
            symbol="AAPL",
            short_term=short_signal,
            medium_term=medium_signal,
            long_term=long_signal,
            overall_sentiment=PredictionType.BUY,
            model_version="v1.0.0",
            features_used=PredictionFeatures(
                symbol="AAPL",
                timestamp=datetime.now(),
                current_price=Decimal("150.0"),
            ),
        )
        
        score = service._calculate_sentiment_score(prediction)
        
        # Should be high score for bullish predictions
        assert score > 65  # Adjusted for more realistic weighted calculation
        assert isinstance(score, Decimal)
        
    def test_generate_recommendation_type_strong_buy(self):
        """Test strong buy recommendation generation."""
        service = RecommendationEngineService()
        
        # High scores and bullish prediction
        fundamental_score = Decimal("90")
        technical_score = Decimal("85")
        sentiment_score = Decimal("88")
        
        prediction = ModelPrediction(
            symbol="AAPL",
            short_term=PredictionSignal(
                symbol="AAPL",
                prediction=PredictionType.BUY,
                horizon=PredictionHorizon.SHORT_TERM,
                confidence=Decimal("0.9"),
            ),
            medium_term=PredictionSignal(
                symbol="AAPL",
                prediction=PredictionType.BUY,
                horizon=PredictionHorizon.MEDIUM_TERM,
                confidence=Decimal("0.85"),
            ),
            long_term=PredictionSignal(
                symbol="AAPL",
                prediction=PredictionType.BUY,
                horizon=PredictionHorizon.LONG_TERM,
                confidence=Decimal("0.8"),
            ),
            overall_sentiment=PredictionType.BUY,
            model_version="v1.0.0",
            features_used=PredictionFeatures(
                symbol="AAPL",
                timestamp=datetime.now(),
                current_price=Decimal("150.0"),
            ),
        )
        
        recommendation = service._generate_recommendation_type(
            fundamental_score, technical_score, sentiment_score, prediction
        )
        
        assert recommendation == RecommendationType.STRONG_BUY
        
    def test_assess_risk_level(self):
        """Test risk level assessment."""
        service = RecommendationEngineService()
        
        # Low volatility analysis
        technical = TechnicalIndicators(
            symbol="AAPL",
            date=datetime.now(),
            rsi=Decimal("45.0"),
        )
        
        analysis = StockAnalysis(
            symbol="AAPL",
            analysis_date=datetime.now(),
            technical_indicators=technical,
            volatility=Decimal("10.0"),  # Low volatility
        )
        
        # High confidence prediction
        prediction = ModelPrediction(
            symbol="AAPL",
            short_term=PredictionSignal(
                symbol="AAPL",
                prediction=PredictionType.BUY,
                horizon=PredictionHorizon.SHORT_TERM,
                confidence=Decimal("0.9"),
            ),
            medium_term=PredictionSignal(
                symbol="AAPL",
                prediction=PredictionType.BUY,
                horizon=PredictionHorizon.MEDIUM_TERM,
                confidence=Decimal("0.85"),
            ),
            long_term=PredictionSignal(
                symbol="AAPL",
                prediction=PredictionType.BUY,
                horizon=PredictionHorizon.LONG_TERM,
                confidence=Decimal("0.8"),
            ),
            overall_sentiment=PredictionType.BUY,
            model_version="v1.0.0",
            features_used=PredictionFeatures(
                symbol="AAPL",
                timestamp=datetime.now(),
                current_price=Decimal("150.0"),
            ),
        )
        
        risk_level = service._assess_risk_level(analysis, prediction)
        
        # Should be low risk for low volatility and high confidence
        assert risk_level in [RiskLevel.LOW, RiskLevel.MODERATE]
        
    @pytest.mark.asyncio
    async def test_generate_portfolio_recommendations(self):
        """Test portfolio recommendation generation."""
        with patch('app.services.recommendation_engine.RealDataFetcherService') as mock_fetcher_cls, \
             patch('app.services.recommendation_engine.StockAnalyzerService') as mock_analyzer_cls, \
             patch('app.services.recommendation_engine.PredictionEngineService') as mock_predictor_cls:
            
            service = RecommendationEngineService()
            
            # Mock services
            mock_fetcher = AsyncMock()
            mock_analyzer = AsyncMock()
            mock_predictor = AsyncMock()
            
            mock_fetcher_cls.return_value = mock_fetcher
            mock_analyzer_cls.return_value = mock_analyzer
            mock_predictor_cls.return_value = mock_predictor
            
            # Set up context manager mocks
            mock_fetcher.__aenter__.return_value = mock_fetcher
            mock_fetcher.__aexit__.return_value = None
            mock_analyzer.__aenter__.return_value = mock_analyzer
            mock_analyzer.__aexit__.return_value = None
            mock_predictor.__aenter__.return_value = mock_predictor
            mock_predictor.__aexit__.return_value = None
            
            # Set service dependencies
            service.data_fetcher = mock_fetcher
            service.stock_analyzer = mock_analyzer
            service.prediction_engine = mock_predictor
            
            # Mock _get_sector method
            async def mock_get_sector(symbol):
                return "Technology"
            service._get_sector = mock_get_sector
            
            # Mock generate_recommendation to return valid recommendations
            async def mock_generate_recommendation(symbol):
                return InvestmentRecommendation(
                    symbol=symbol,
                    company_name=f"{symbol} Corp",
                    recommendation=RecommendationType.BUY,
                    confidence=Decimal("0.8"),
                    risk_level=RiskLevel.MODERATE,
                    fundamental_score=Decimal("75"),
                    technical_score=Decimal("70"),
                    sentiment_score=Decimal("80"),
                    overall_score=Decimal("75"),
                    current_price=Decimal("100.0"),
                    reasoning=["Strong fundamentals", "Good technical signals"],
                )
            
            service.generate_recommendation = mock_generate_recommendation
            
            # Test with multiple symbols
            symbols = ["AAPL", "GOOGL", "MSFT"]
            criteria = StockScreeningCriteria(min_confidence=Decimal("0.7"))
            
            result = await service.generate_portfolio_recommendations(symbols, criteria)
            
            # Assertions
            assert result is not None
            assert isinstance(result, PortfolioRecommendation)
            assert len(result.recommendations) == 3
            assert result.total_positions == 3
            assert result.portfolio_score > 0
            assert result.diversification_score > 0
            assert len(result.reasoning) > 0
            assert isinstance(result.risk_level, RiskLevel)

    def test_sentiment_score_stays_near_neutral_for_low_confidence_buy(self):
        """Low-confidence bullish signals should not collapse sentiment toward zero."""
        service = RecommendationEngineService()
        weak_buy = PredictionSignal(
            symbol="AAPL",
            prediction=PredictionType.BUY,
            horizon=PredictionHorizon.SHORT_TERM,
            confidence=Decimal("0.1"),
        )
        model_prediction = ModelPrediction(
            symbol="AAPL",
            short_term=weak_buy,
            medium_term=weak_buy,
            long_term=weak_buy,
            overall_sentiment=PredictionType.BUY,
            model_version="test",
            features_used=PredictionFeatures(
                symbol="AAPL",
                timestamp=datetime.now(),
                current_price=Decimal("100"),
            ),
        )

        sentiment_score = service._calculate_sentiment_score(model_prediction)

        assert sentiment_score > Decimal("50")
        assert sentiment_score < Decimal("60")


class TestDataClasses:
    """Test recommendation data classes."""
    
    def test_investment_recommendation_creation(self):
        """Test InvestmentRecommendation data class creation."""
        recommendation = InvestmentRecommendation(
            symbol="AAPL",
            company_name="Apple Inc.",
            recommendation=RecommendationType.BUY,
            confidence=Decimal("0.8"),
            target_price=Decimal("160.0"),
            risk_level=RiskLevel.MODERATE,
            reasoning=["Strong fundamentals", "Bullish technical signals"],
        )
        
        assert recommendation.symbol == "AAPL"
        assert recommendation.company_name == "Apple Inc."
        assert recommendation.recommendation == RecommendationType.BUY
        assert recommendation.confidence == Decimal("0.8")
        assert recommendation.target_price == Decimal("160.0")
        assert recommendation.risk_level == RiskLevel.MODERATE
        assert len(recommendation.reasoning) == 2
        assert isinstance(recommendation.created_at, datetime)
        
    def test_portfolio_recommendation_creation(self):
        """Test PortfolioRecommendation data class creation."""
        individual_rec = InvestmentRecommendation(
            symbol="AAPL",
            company_name="Apple Inc.",
            recommendation=RecommendationType.BUY,
            confidence=Decimal("0.8"),
        )
        
        portfolio = PortfolioRecommendation(
            recommendations=[individual_rec],
            portfolio_score=Decimal("75.0"),
            risk_level=RiskLevel.MODERATE,
            diversification_score=Decimal("60.0"),
            total_positions=1,
            sectors_covered=["Technology"],
            reasoning=["Well-balanced portfolio with good risk profile"],
        )
        
        assert len(portfolio.recommendations) == 1
        assert portfolio.portfolio_score == Decimal("75.0")
        assert portfolio.risk_level == RiskLevel.MODERATE
        assert portfolio.diversification_score == Decimal("60.0")
        assert portfolio.total_positions == 1
        assert "Technology" in portfolio.sectors_covered
        assert len(portfolio.reasoning) == 1
        assert isinstance(portfolio.created_at, datetime)
        
    def test_stock_screening_criteria_creation(self):
        """Test StockScreeningCriteria data class creation."""
        criteria = StockScreeningCriteria(
            min_market_cap=Decimal("1000000000"),
            max_risk_level=RiskLevel.MODERATE,
            min_confidence=Decimal("0.7"),
            max_positions=15,
        )
        
        assert criteria.min_market_cap == Decimal("1000000000")
        assert criteria.max_risk_level == RiskLevel.MODERATE
        assert criteria.min_confidence == Decimal("0.7")
        assert criteria.max_positions == 15
