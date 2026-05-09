"""
Recommendation engine service for generating investment recommendations.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from app.services.data_fetcher import CompanyInfo, StockQuote
from app.services.real_data_fetcher import RealDataFetcherService
from app.services.stock_analyzer import StockAnalyzerService, StockAnalysis
from app.services.prediction_engine import (
    PredictionEngineService,
    ModelPrediction,
    PredictionType,
    PredictionHorizon,
)


class RecommendationType(Enum):
    """Types of investment recommendations."""
    
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


class RiskLevel(Enum):
    """Investment risk levels."""
    
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class InvestmentRecommendation:
    """Complete investment recommendation with reasoning."""
    
    symbol: str
    company_name: str
    recommendation: RecommendationType
    confidence: Decimal  # 0.0 to 1.0
    target_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    time_horizon: str = "3_months"
    risk_level: RiskLevel = RiskLevel.MODERATE
    reasoning: List[str] = field(default_factory=list)
    fundamental_score: Optional[Decimal] = None
    technical_score: Optional[Decimal] = None
    sentiment_score: Optional[Decimal] = None
    overall_score: Optional[Decimal] = None
    current_price: Optional[Decimal] = None
    potential_return: Optional[Decimal] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PortfolioRecommendation:
    """Portfolio-level recommendation with diversification."""
    
    recommendations: List[InvestmentRecommendation]
    portfolio_score: Decimal
    risk_level: RiskLevel
    diversification_score: Decimal
    total_positions: int
    sectors_covered: List[str]
    reasoning: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class StockScreeningCriteria:
    """Criteria for stock screening and filtering."""
    
    min_market_cap: Optional[Decimal] = None
    max_market_cap: Optional[Decimal] = None
    min_volume: Optional[int] = None
    max_risk_level: RiskLevel = RiskLevel.HIGH
    sectors: Optional[List[str]] = None
    exclude_sectors: Optional[List[str]] = None
    min_confidence: Decimal = Decimal("0.6")
    max_positions: int = 20


class RecommendationEngineService:
    """Service for generating comprehensive investment recommendations."""
    
    def __init__(self):
        self.data_fetcher: Optional[RealDataFetcherService] = None
        self.stock_analyzer: Optional[StockAnalyzerService] = None
        self.prediction_engine: Optional[PredictionEngineService] = None
        
    async def __aenter__(self):
        """Initialize service dependencies."""
        self.data_fetcher = RealDataFetcherService()
        self.stock_analyzer = StockAnalyzerService()
        self.prediction_engine = PredictionEngineService()
        
        await self.data_fetcher.__aenter__()
        await self.stock_analyzer.__aenter__()
        await self.prediction_engine.__aenter__()
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup service dependencies."""
        if self.prediction_engine:
            await self.prediction_engine.__aexit__(exc_type, exc_val, exc_tb)
        if self.stock_analyzer:
            await self.stock_analyzer.__aexit__(exc_type, exc_val, exc_tb)
        if self.data_fetcher:
            await self.data_fetcher.__aexit__(exc_type, exc_val, exc_tb)
            
    async def generate_recommendation(
        self, symbol: str
    ) -> Optional[InvestmentRecommendation]:
        """Generate comprehensive investment recommendation for a stock."""
        if not all([self.data_fetcher, self.stock_analyzer, self.prediction_engine]):
            raise RuntimeError("Service must be used as async context manager")
            
        try:
            # Get all required data
            quote = await self.data_fetcher.get_stock_quote(symbol)
            company_info = await self.data_fetcher.get_company_info(symbol)
            analysis = await self.stock_analyzer.analyze_stock(symbol)
            prediction = await self.prediction_engine.predict_stock(symbol)
            
            if not all([quote, company_info, prediction]):
                print(f"Insufficient data for recommendation: {symbol}")
                return None
                
            # Calculate component scores
            fundamental_score = await self._calculate_fundamental_score(
                company_info, quote
            )
            technical_score = self._calculate_technical_score(analysis)
            sentiment_score = self._calculate_sentiment_score(prediction)
            
            # Generate overall recommendation
            recommendation = self._generate_recommendation_type(
                fundamental_score, technical_score, sentiment_score, prediction
            )
            
            # Calculate confidence and risk
            confidence = self._calculate_confidence(
                fundamental_score, technical_score, sentiment_score
            )
            risk_level = self._assess_risk_level(analysis, prediction)
            
            # Generate reasoning
            reasoning = self._generate_reasoning(
                fundamental_score, technical_score, sentiment_score,
                prediction, analysis
            )
            
            # Calculate potential return
            potential_return = None
            if prediction.short_term.target_price and quote.price:
                potential_return = (
                    (prediction.short_term.target_price - quote.price) / 
                    quote.price * 100
                )
            
            return InvestmentRecommendation(
                symbol=symbol,
                company_name=company_info.name,
                recommendation=recommendation,
                confidence=confidence,
                target_price=prediction.medium_term.target_price,
                stop_loss=prediction.medium_term.stop_loss,
                risk_level=risk_level,
                reasoning=reasoning,
                fundamental_score=fundamental_score,
                technical_score=technical_score,
                sentiment_score=sentiment_score,
                overall_score=(fundamental_score + technical_score + sentiment_score) / 3,
                current_price=quote.price,
                potential_return=potential_return,
            )
            
        except Exception as e:
            print(f"Error generating recommendation for {symbol}: {e}")
            return None
            
    async def generate_portfolio_recommendations(
        self, 
        symbols: List[str],
        criteria: Optional[StockScreeningCriteria] = None
    ) -> Optional[PortfolioRecommendation]:
        """Generate portfolio-level recommendations with diversification."""
        if not criteria:
            criteria = StockScreeningCriteria()
            
        try:
            # Generate individual recommendations
            recommendations = []
            for symbol in symbols:
                rec = await self.generate_recommendation(symbol)
                if rec and rec.confidence >= criteria.min_confidence:
                    recommendations.append(rec)
                    
            if not recommendations:
                print("No qualifying recommendations found")
                return None
                
            # Filter and rank recommendations
            filtered_recs = self._filter_recommendations(recommendations, criteria)
            ranked_recs = self._rank_recommendations(filtered_recs)
            
            # Select portfolio with diversification
            portfolio_recs = self._select_diversified_portfolio(
                ranked_recs, criteria
            )
            
            # Calculate portfolio metrics
            portfolio_score = self._calculate_portfolio_score(portfolio_recs)
            diversification_score = self._calculate_diversification_score(
                portfolio_recs
            )
            risk_level = self._assess_portfolio_risk(portfolio_recs)
            
            # Get sectors covered
            sectors = list(set([
                await self._get_sector(rec.symbol) 
                for rec in portfolio_recs
            ]))
            sectors = [s for s in sectors if s]  # Remove None values
            
            # Generate portfolio reasoning
            reasoning = self._generate_portfolio_reasoning(
                portfolio_recs, diversification_score, risk_level
            )
            
            return PortfolioRecommendation(
                recommendations=portfolio_recs,
                portfolio_score=portfolio_score,
                risk_level=risk_level,
                diversification_score=diversification_score,
                total_positions=len(portfolio_recs),
                sectors_covered=sectors,
                reasoning=reasoning,
            )
            
        except Exception as e:
            print(f"Error generating portfolio recommendations: {e}")
            return None
            
    async def _calculate_fundamental_score(
        self, company_info: CompanyInfo, quote: StockQuote
    ) -> Decimal:
        """Calculate fundamental analysis score (0-100)."""
        score_components = []
        
        # Market cap assessment (prefer mid to large cap)
        if company_info.market_cap:
            if company_info.market_cap > 10_000_000_000:  # > $10B
                score_components.append(85)
            elif company_info.market_cap > 2_000_000_000:  # > $2B
                score_components.append(75)
            elif company_info.market_cap > 300_000_000:  # > $300M
                score_components.append(60)
            else:
                score_components.append(40)
        else:
            score_components.append(50)  # Neutral if unknown
            
        # Volume assessment (liquidity indicator)
        if quote.volume > 1_000_000:  # High volume
            score_components.append(80)
        elif quote.volume > 100_000:  # Moderate volume
            score_components.append(60)
        else:
            score_components.append(30)  # Low volume
            
        # Price stability (prefer less volatile moves)
        if abs(float(quote.change_percent)) < 2:  # Low daily volatility
            score_components.append(70)
        elif abs(float(quote.change_percent)) < 5:  # Moderate volatility
            score_components.append(50)
        else:
            score_components.append(30)  # High volatility
            
        return Decimal(str(sum(score_components) / len(score_components)))
        
    def _calculate_technical_score(
        self, analysis: Optional[StockAnalysis]
    ) -> Decimal:
        """Calculate technical analysis score (0-100)."""
        if not analysis or not analysis.technical_indicators:
            return Decimal("50")  # Neutral score
            
        tech = analysis.technical_indicators
        score_components = []
        
        # RSI assessment
        if tech.rsi:
            if 30 <= tech.rsi <= 70:  # Healthy range
                score_components.append(80)
            elif tech.rsi < 30:  # Oversold (potential buying opportunity)
                score_components.append(75)
            elif tech.rsi > 70:  # Overbought (caution)
                score_components.append(40)
                
        # MACD assessment
        if tech.macd and tech.macd_signal:
            if tech.macd > tech.macd_signal:  # Bullish
                score_components.append(75)
            else:  # Bearish
                score_components.append(45)
                
        # Moving average assessment
        if all([tech.sma_20, tech.sma_50, analysis.technical_indicators.sma_200]):
            if tech.sma_20 > tech.sma_50 > tech.sma_200:  # Strong uptrend
                score_components.append(85)
            elif tech.sma_20 > tech.sma_50:  # Moderate uptrend
                score_components.append(70)
            elif tech.sma_20 < tech.sma_50 < tech.sma_200:  # Strong downtrend
                score_components.append(25)
            else:  # Mixed signals
                score_components.append(50)
                
        # Volatility assessment
        if analysis.volatility:
            if analysis.volatility < 20:  # Low volatility
                score_components.append(75)
            elif analysis.volatility < 40:  # Moderate volatility
                score_components.append(60)
            else:  # High volatility
                score_components.append(35)
                
        if not score_components:
            return Decimal("50")
            
        return Decimal(str(sum(score_components) / len(score_components)))
        
    def _calculate_sentiment_score(
        self, prediction: ModelPrediction
    ) -> Decimal:
        """Calculate sentiment score based on prediction (0-100)."""
        # Blend each horizon toward neutral when confidence is low instead of
        # collapsing the score toward zero. Low-confidence BUY/SELL signals
        # should behave like "slightly bullish/bearish", not "very negative".
        horizon_weights = [Decimal("0.2"), Decimal("0.5"), Decimal("0.3")]
        adjusted_scores = []

        for horizon_pred, weight in zip(
            [prediction.short_term, prediction.medium_term, prediction.long_term],
            horizon_weights,
        ):
            if horizon_pred.prediction == PredictionType.BUY:
                directional_score = Decimal("70") + (
                    horizon_pred.confidence * Decimal("25")
                )
            elif horizon_pred.prediction == PredictionType.SELL:
                directional_score = Decimal("30") - (
                    horizon_pred.confidence * Decimal("25")
                )
            else:
                directional_score = Decimal("50")

            adjusted_score = Decimal("50") + (
                horizon_pred.confidence * (directional_score - Decimal("50"))
            )
            adjusted_scores.append(adjusted_score * weight)

        weighted_score = sum(adjusted_scores)
        return Decimal(str(max(0, min(100, float(weighted_score)))))
        
    def _generate_recommendation_type(
        self,
        fundamental_score: Decimal,
        technical_score: Decimal,
        sentiment_score: Decimal,
        prediction: ModelPrediction,
    ) -> RecommendationType:
        """Generate overall recommendation type."""
        overall_score = (fundamental_score + technical_score + sentiment_score) / 3
        
        # Strong signals
        if overall_score >= 85 and prediction.overall_sentiment == PredictionType.BUY:
            return RecommendationType.STRONG_BUY
        elif overall_score <= 25 and prediction.overall_sentiment == PredictionType.SELL:
            return RecommendationType.STRONG_SELL
            
        # Regular signals based on prediction and score
        elif prediction.overall_sentiment == PredictionType.BUY and overall_score >= 65:
            return RecommendationType.BUY
        elif prediction.overall_sentiment == PredictionType.SELL and overall_score <= 40:
            return RecommendationType.SELL
        else:
            return RecommendationType.HOLD
            
    def _calculate_confidence(
        self,
        fundamental_score: Decimal,
        technical_score: Decimal,
        sentiment_score: Decimal,
    ) -> Decimal:
        """Calculate overall confidence score."""
        # Check score agreement (higher agreement = higher confidence)
        scores = [fundamental_score, technical_score, sentiment_score]
        score_range = max(scores) - min(scores)
        
        # Lower range = higher agreement = higher confidence
        agreement_factor = max(Decimal("0"), (Decimal("50") - score_range) / Decimal("50"))
        
        # Average score strength
        avg_score = sum(scores) / Decimal("3")
        strength_factor = abs(avg_score - Decimal("50")) / Decimal("50")  # Distance from neutral
        
        # Combine factors
        confidence = (agreement_factor * Decimal("0.6") + strength_factor * Decimal("0.4"))
        
        return Decimal(str(max(0.1, min(0.95, float(confidence)))))
        
    def _assess_risk_level(
        self, analysis: Optional[StockAnalysis], prediction: ModelPrediction
    ) -> RiskLevel:
        """Assess investment risk level."""
        risk_factors = []
        
        # Volatility-based risk
        if analysis and analysis.volatility:
            if analysis.volatility > 50:
                risk_factors.append(4)  # Very high
            elif analysis.volatility > 30:
                risk_factors.append(3)  # High
            elif analysis.volatility > 15:
                risk_factors.append(2)  # Moderate
            else:
                risk_factors.append(1)  # Low
        else:
            risk_factors.append(2)  # Default moderate
            
        # Prediction confidence risk (lower confidence = higher risk)
        avg_confidence = (
            prediction.short_term.confidence +
            prediction.medium_term.confidence +
            prediction.long_term.confidence
        ) / 3
        
        if avg_confidence < 0.4:
            risk_factors.append(4)
        elif avg_confidence < 0.6:
            risk_factors.append(3)
        elif avg_confidence < 0.8:
            risk_factors.append(2)
        else:
            risk_factors.append(1)
            
        avg_risk = sum(risk_factors) / len(risk_factors)
        
        if avg_risk >= 3.5:
            return RiskLevel.VERY_HIGH
        elif avg_risk >= 2.5:
            return RiskLevel.HIGH
        elif avg_risk >= 1.5:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW
            
    def _generate_reasoning(
        self,
        fundamental_score: Decimal,
        technical_score: Decimal,
        sentiment_score: Decimal,
        prediction: ModelPrediction,
        analysis: Optional[StockAnalysis],
    ) -> List[str]:
        """Generate human-readable reasoning for recommendation."""
        reasoning = []
        
        # Fundamental reasoning
        if fundamental_score >= 75:
            reasoning.append("Strong fundamental indicators with good market cap and liquidity")
        elif fundamental_score >= 60:
            reasoning.append("Moderate fundamental strength")
        else:
            reasoning.append("Weaker fundamental indicators suggest caution")
            
        # Technical reasoning
        if technical_score >= 75:
            reasoning.append("Technical indicators show strong positive momentum")
        elif technical_score >= 60:
            reasoning.append("Technical analysis shows mixed but generally positive signals")
        else:
            reasoning.append("Technical indicators suggest neutral to negative momentum")
            
        # Sentiment reasoning
        if sentiment_score >= 75:
            reasoning.append("ML prediction models show strong bullish sentiment across timeframes")
        elif sentiment_score >= 60:
            reasoning.append("Prediction models indicate moderate positive outlook")
        else:
            reasoning.append("Prediction models suggest bearish or neutral sentiment")
            
        # Add specific prediction insights
        if prediction.overall_sentiment == PredictionType.BUY:
            reasoning.append(f"Overall model consensus: BUY with {prediction.medium_term.confidence:.0%} confidence")
        elif prediction.overall_sentiment == PredictionType.SELL:
            reasoning.append(f"Overall model consensus: SELL with {prediction.medium_term.confidence:.0%} confidence")
        else:
            reasoning.append("Models suggest holding current position")
            
        return reasoning
        
    def _filter_recommendations(
        self, recommendations: List[InvestmentRecommendation], criteria: StockScreeningCriteria
    ) -> List[InvestmentRecommendation]:
        """Filter recommendations based on criteria."""
        filtered = []
        
        for rec in recommendations:
            # Skip if below minimum confidence
            if rec.confidence < criteria.min_confidence:
                continue
                
            # Skip if risk too high
            risk_levels = [RiskLevel.LOW, RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.VERY_HIGH]
            if risk_levels.index(rec.risk_level) > risk_levels.index(criteria.max_risk_level):
                continue
                
            filtered.append(rec)
            
        return filtered
        
    def _rank_recommendations(
        self, recommendations: List[InvestmentRecommendation]
    ) -> List[InvestmentRecommendation]:
        """Rank recommendations by overall attractiveness."""
        def score_recommendation(rec: InvestmentRecommendation) -> float:
            # Combine overall score and confidence
            base_score = float(rec.overall_score or 50)
            confidence_bonus = float(rec.confidence) * 20
            
            # Bonus for buy recommendations
            rec_bonus = {
                RecommendationType.STRONG_BUY: 20,
                RecommendationType.BUY: 10,
                RecommendationType.HOLD: 0,
                RecommendationType.SELL: -10,
                RecommendationType.STRONG_SELL: -20,
            }[rec.recommendation]
            
            return base_score + confidence_bonus + rec_bonus
            
        return sorted(recommendations, key=score_recommendation, reverse=True)
        
    def _select_diversified_portfolio(
        self, ranked_recs: List[InvestmentRecommendation], criteria: StockScreeningCriteria
    ) -> List[InvestmentRecommendation]:
        """Select diversified portfolio from ranked recommendations."""
        selected = []
        sectors_used = set()
        
        for rec in ranked_recs:
            if len(selected) >= criteria.max_positions:
                break
                
            # Simple diversification: try to avoid too many from same sector
            # (In real implementation, would get actual sector from company data)
            if len(selected) < 5 or len(sectors_used) < 3:
                selected.append(rec)
                # Simulate sector assignment
                sectors_used.add(f"sector_{len(sectors_used) % 5}")
                
        return selected
        
    def _calculate_portfolio_score(
        self, recommendations: List[InvestmentRecommendation]
    ) -> Decimal:
        """Calculate overall portfolio score."""
        if not recommendations:
            return Decimal("0")
            
        scores = [rec.overall_score or Decimal("50") for rec in recommendations]
        return sum(scores) / len(scores)
        
    def _calculate_diversification_score(
        self, recommendations: List[InvestmentRecommendation]
    ) -> Decimal:
        """Calculate portfolio diversification score."""
        if len(recommendations) <= 1:
            return Decimal("20")  # Low diversification
        elif len(recommendations) <= 5:
            return Decimal("60")  # Moderate diversification
        elif len(recommendations) <= 10:
            return Decimal("80")  # Good diversification
        else:
            return Decimal("90")  # Excellent diversification
            
    def _assess_portfolio_risk(
        self, recommendations: List[InvestmentRecommendation]
    ) -> RiskLevel:
        """Assess overall portfolio risk."""
        if not recommendations:
            return RiskLevel.MODERATE
            
        risk_values = {
            RiskLevel.LOW: 1,
            RiskLevel.MODERATE: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.VERY_HIGH: 4,
        }
        
        avg_risk = sum(risk_values[rec.risk_level] for rec in recommendations) / len(recommendations)
        
        if avg_risk >= 3.5:
            return RiskLevel.VERY_HIGH
        elif avg_risk >= 2.5:
            return RiskLevel.HIGH
        elif avg_risk >= 1.5:
            return RiskLevel.MODERATE
        else:
            return RiskLevel.LOW
            
    def _generate_portfolio_reasoning(
        self,
        recommendations: List[InvestmentRecommendation],
        diversification_score: Decimal,
        risk_level: RiskLevel,
    ) -> List[str]:
        """Generate portfolio-level reasoning."""
        reasoning = []
        
        buy_count = sum(1 for r in recommendations if r.recommendation in [
            RecommendationType.BUY, RecommendationType.STRONG_BUY
        ])
        
        reasoning.append(f"Portfolio contains {len(recommendations)} positions with {buy_count} buy recommendations")
        
        if diversification_score >= 80:
            reasoning.append("Excellent diversification across multiple positions")
        elif diversification_score >= 60:
            reasoning.append("Good diversification with moderate position spread")
        else:
            reasoning.append("Limited diversification - consider adding more positions")
            
        reasoning.append(f"Overall portfolio risk level: {risk_level.value}")
        
        return reasoning
        
    async def _get_sector(self, symbol: str) -> Optional[str]:
        """Get sector for a symbol (simplified implementation)."""
        try:
            company_info = await self.data_fetcher.get_company_info(symbol)
            return company_info.sector if company_info else None
        except Exception:
            return None
