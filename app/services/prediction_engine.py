"""
ML-based prediction engine service for stock market forecasting.
"""

import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from app.services.data_fetcher import StockHistoricalData
from app.services.real_data_fetcher import RealDataFetcherService
from app.services.stock_analyzer import (
    StockAnalyzerService,
    TechnicalIndicators,
    StockAnalysis,
)


class PredictionType(Enum):
    """Types of predictions supported."""
    
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class PredictionHorizon(Enum):
    """Time horizons for predictions."""
    
    SHORT_TERM = "1_week"  # 1 week
    MEDIUM_TERM = "1_month"  # 1 month
    LONG_TERM = "3_months"  # 3 months


@dataclass
class PredictionFeatures:
    """Features used for ML predictions."""
    
    symbol: str
    timestamp: datetime
    # Price features
    current_price: Decimal
    price_change_1d: Optional[Decimal] = None
    price_change_7d: Optional[Decimal] = None
    price_change_30d: Optional[Decimal] = None
    # Technical indicators
    rsi: Optional[Decimal] = None
    macd: Optional[Decimal] = None
    macd_signal: Optional[Decimal] = None
    sma_20: Optional[Decimal] = None
    sma_50: Optional[Decimal] = None
    ema_12: Optional[Decimal] = None
    ema_26: Optional[Decimal] = None
    bollinger_upper: Optional[Decimal] = None
    bollinger_lower: Optional[Decimal] = None
    # Volume features
    volume_ratio: Optional[Decimal] = None
    volume_trend: Optional[str] = None
    # Volatility features
    atr: Optional[Decimal] = None
    volatility: Optional[Decimal] = None


@dataclass
class PredictionSignal:
    """ML prediction signal with confidence and reasoning."""
    
    symbol: str
    prediction: PredictionType
    horizon: PredictionHorizon
    confidence: Decimal  # 0.0 to 1.0
    target_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    reasoning: List[str] = None
    risk_score: Optional[Decimal] = None  # 0.0 to 1.0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.reasoning is None:
            self.reasoning = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class ModelPrediction:
    """Complete prediction result with multiple horizons."""
    
    symbol: str
    short_term: PredictionSignal
    medium_term: PredictionSignal
    long_term: PredictionSignal
    overall_sentiment: PredictionType
    model_version: str
    features_used: PredictionFeatures
    prediction_date: datetime = None
    
    def __post_init__(self):
        if self.prediction_date is None:
            self.prediction_date = datetime.utcnow()


class PredictionEngineService:
    """ML-based prediction engine for stock market forecasting."""
    
    def __init__(self):
        self.data_fetcher: Optional[RealDataFetcherService] = None
        self.stock_analyzer: Optional[StockAnalyzerService] = None
        self.model_version = "v1.0.0_rule_based"  # Start with rule-based
        
    async def __aenter__(self):
        """Initialize service dependencies."""
        self.data_fetcher = RealDataFetcherService()
        self.stock_analyzer = StockAnalyzerService()
        
        await self.data_fetcher.__aenter__()
        await self.stock_analyzer.__aenter__()
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup service dependencies."""
        if self.stock_analyzer:
            await self.stock_analyzer.__aexit__(exc_type, exc_val, exc_tb)
        if self.data_fetcher:
            await self.data_fetcher.__aexit__(exc_type, exc_val, exc_tb)
            
    async def predict_stock(
        self, symbol: str, days_history: int = 30
    ) -> Optional[ModelPrediction]:
        """Generate comprehensive prediction for a stock."""
        if not self.data_fetcher or not self.stock_analyzer:
            raise RuntimeError("Service must be used as async context manager")
            
        try:
            # Get analysis data
            analysis = await self.stock_analyzer.analyze_stock(
                symbol, days_history
            )
            if not analysis:
                print(f"No analysis data available for {symbol}")
                return None
                
            # Extract features
            features = await self._extract_features(symbol, analysis)
            if not features:
                print(f"Could not extract features for {symbol}")
                return None
                
            # Generate predictions for different horizons
            short_term = await self._predict_horizon(
                features, PredictionHorizon.SHORT_TERM
            )
            medium_term = await self._predict_horizon(
                features, PredictionHorizon.MEDIUM_TERM
            )
            long_term = await self._predict_horizon(
                features, PredictionHorizon.LONG_TERM
            )
            
            # Determine overall sentiment
            overall = self._determine_overall_sentiment([
                short_term, medium_term, long_term
            ])
            
            return ModelPrediction(
                symbol=symbol,
                short_term=short_term,
                medium_term=medium_term,
                long_term=long_term,
                overall_sentiment=overall,
                model_version=self.model_version,
                features_used=features,
            )
            
        except Exception as e:
            print(f"Error predicting {symbol}: {e}")
            return None
            
    async def _extract_features(
        self, symbol: str, analysis: StockAnalysis
    ) -> Optional[PredictionFeatures]:
        """Extract features from stock analysis for ML model."""
        try:
            # Get current quote for price data
            quote = await self.data_fetcher.get_stock_quote(symbol)
            if not quote:
                return None
                
            # Get historical data for price changes
            historical = await self.data_fetcher.get_historical_data(symbol, 30)
            if not historical or len(historical) < 2:
                price_changes = (None, None, None)
            else:
                price_changes = self._calculate_price_changes(historical)
                
            # Extract technical indicators
            tech = analysis.technical_indicators
            volume_analysis = analysis.volume_analysis or {}
            
            return PredictionFeatures(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                current_price=quote.price,
                price_change_1d=price_changes[0],
                price_change_7d=price_changes[1],
                price_change_30d=price_changes[2],
                rsi=tech.rsi if tech else None,
                macd=tech.macd if tech else None,
                macd_signal=tech.macd_signal if tech else None,
                sma_20=tech.sma_20 if tech else None,
                sma_50=tech.sma_50 if tech else None,
                ema_12=tech.ema_12 if tech else None,
                ema_26=tech.ema_26 if tech else None,
                bollinger_upper=tech.bollinger_upper if tech else None,
                bollinger_lower=tech.bollinger_lower if tech else None,
                volume_ratio=volume_analysis.get("volume_ratio"),
                volume_trend=volume_analysis.get("trend"),
                atr=tech.atr if tech else None,
                volatility=analysis.volatility,
            )
            
        except Exception as e:
            print(f"Error extracting features for {symbol}: {e}")
            return None
            
    def _calculate_price_changes(
        self, historical: List[StockHistoricalData]
    ) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        """Calculate price changes over different periods."""
        if len(historical) < 2:
            return (None, None, None)
            
        current_price = historical[-1].close
        
        # 1-day change
        change_1d = None
        if len(historical) >= 2:
            prev_price = historical[-2].close
            change_1d = (current_price - prev_price) / prev_price * 100
            
        # 7-day change
        change_7d = None
        if len(historical) >= 8:
            week_ago_price = historical[-8].close
            change_7d = (current_price - week_ago_price) / week_ago_price * 100
            
        # 30-day change
        change_30d = None
        if len(historical) >= 30:
            month_ago_price = historical[0].close
            change_30d = (current_price - month_ago_price) / month_ago_price * 100
            
        return (change_1d, change_7d, change_30d)
        
    async def _predict_horizon(
        self, features: PredictionFeatures, horizon: PredictionHorizon
    ) -> PredictionSignal:
        """Generate prediction for specific time horizon using rule-based model."""
        # Rule-based prediction logic (to be replaced with ML models)
        
        reasoning = []
        score_components = []
        
        # RSI-based signals
        if features.rsi is not None:
            if features.rsi < 30:
                score_components.append(0.8)  # Oversold = bullish
                reasoning.append("RSI indicates oversold conditions")
            elif features.rsi > 70:
                score_components.append(-0.8)  # Overbought = bearish
                reasoning.append("RSI indicates overbought conditions")
            else:
                score_components.append(0.0)
                
        # MACD signals
        if features.macd is not None and features.macd_signal is not None:
            macd_diff = features.macd - features.macd_signal
            if macd_diff > 0:
                score_components.append(0.6)  # MACD above signal = bullish
                reasoning.append("MACD above signal line")
            else:
                score_components.append(-0.6)  # MACD below signal = bearish
                reasoning.append("MACD below signal line")
                
        # Moving average signals
        if (features.sma_20 is not None and features.sma_50 is not None 
            and features.current_price is not None):
            
            if features.current_price > features.sma_20 > features.sma_50:
                score_components.append(0.7)  # Price > SMA20 > SMA50 = bullish
                reasoning.append("Price above short-term moving averages")
            elif features.current_price < features.sma_20 < features.sma_50:
                score_components.append(-0.7)  # Price < SMA20 < SMA50 = bearish
                reasoning.append("Price below short-term moving averages")
                
        # Volume confirmation
        if features.volume_trend == "increasing":
            score_components.append(0.3)
            reasoning.append("Increasing volume trend")
        elif features.volume_trend == "decreasing":
            score_components.append(-0.2)
            reasoning.append("Decreasing volume trend")
            
        # Calculate overall score
        if not score_components:
            # No indicators available
            prediction = PredictionType.HOLD
            confidence = Decimal("0.1")
            reasoning.append("Insufficient technical indicators")
        else:
            avg_score = sum(score_components) / len(score_components)
            
            # Determine prediction based on score
            if avg_score > 0.3:
                prediction = PredictionType.BUY
                confidence = min(Decimal(str(abs(avg_score))), Decimal("0.95"))
            elif avg_score < -0.3:
                prediction = PredictionType.SELL
                confidence = min(Decimal(str(abs(avg_score))), Decimal("0.95"))
            else:
                prediction = PredictionType.HOLD
                confidence = Decimal("0.5")
                reasoning.append("Mixed signals suggest holding")
                
        # Calculate target price and stop loss
        target_price = None
        stop_loss = None
        
        if features.current_price and prediction != PredictionType.HOLD:
            if prediction == PredictionType.BUY:
                # Target 5-15% upside based on horizon
                multiplier = {
                    PredictionHorizon.SHORT_TERM: 1.05,
                    PredictionHorizon.MEDIUM_TERM: 1.10,
                    PredictionHorizon.LONG_TERM: 1.15,
                }[horizon]
                target_price = features.current_price * Decimal(str(multiplier))
                stop_loss = features.current_price * Decimal("0.95")  # 5% stop loss
                
            else:  # SELL
                # Target 5-15% downside based on horizon
                multiplier = {
                    PredictionHorizon.SHORT_TERM: 0.95,
                    PredictionHorizon.MEDIUM_TERM: 0.90,
                    PredictionHorizon.LONG_TERM: 0.85,
                }[horizon]
                target_price = features.current_price * Decimal(str(multiplier))
                stop_loss = features.current_price * Decimal("1.05")  # 5% stop loss
                
        # Risk score based on volatility
        risk_score = None
        if features.volatility:
            # Higher volatility = higher risk
            risk_score = min(features.volatility / 50, Decimal("1.0"))
            
        return PredictionSignal(
            symbol=features.symbol,
            prediction=prediction,
            horizon=horizon,
            confidence=confidence,
            target_price=target_price,
            stop_loss=stop_loss,
            reasoning=reasoning,
            risk_score=risk_score,
        )
        
    def _determine_overall_sentiment(
        self, predictions: List[PredictionSignal]
    ) -> PredictionType:
        """Determine overall sentiment from multiple horizon predictions."""
        
        # Weight predictions by confidence
        weighted_scores = []
        
        for pred in predictions:
            if pred.prediction == PredictionType.BUY:
                score = float(pred.confidence)
            elif pred.prediction == PredictionType.SELL:
                score = -float(pred.confidence)
            else:  # HOLD
                score = 0
                
            weighted_scores.append(score)
            
        # Calculate weighted average
        if not weighted_scores:
            return PredictionType.HOLD
            
        avg_score = sum(weighted_scores) / len(weighted_scores)
        
        if avg_score > 0.2:
            return PredictionType.BUY
        elif avg_score < -0.2:
            return PredictionType.SELL
        else:
            return PredictionType.HOLD
