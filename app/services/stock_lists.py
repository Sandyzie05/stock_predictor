"""
Stock list generation service for ATH, S&P500, undervalued, and overvalued stocks.
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from app.services.data_fetcher import CompanyInfo, StockQuote
from app.services.real_data_fetcher import RealDataFetcherService
from app.services.research_models import ResearchPrediction
from app.services.research_prediction import ResearchPredictionService
from app.services.stock_analyzer import StockAnalyzerService, StockAnalysis
from app.services.prediction_engine import PredictionEngineService, ModelPrediction, PredictionType
from app.services.recommendation_engine import (
    RecommendationEngineService, 
    InvestmentRecommendation,
    RecommendationType,
    RiskLevel,
)


class StockListType(Enum):
    """Types of stock lists supported."""
    
    ALL_TIME_HIGH = "all_time_high"
    ALL_TIME_LOW = "all_time_low"  
    SP500_ALL = "sp500_all"
    SP500_ATH = "sp500_ath"
    SP500_ATL = "sp500_atl"
    UNDERVALUED = "undervalued"
    OVERVALUED = "overvalued"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


@dataclass
class StockListItem:
    """Individual stock in a generated list."""
    
    symbol: str
    company_name: str
    current_price: Decimal
    list_type: StockListType
    rank: int
    score: Decimal  # Relevance score for this list
    reasoning: List[str] = field(default_factory=list)
    
    # Market data
    change_percent: Optional[Decimal] = None
    volume: Optional[int] = None
    market_cap: Optional[Decimal] = None
    
    # Analysis data
    recommendation: Optional[RecommendationType] = None
    confidence: Optional[Decimal] = None
    risk_level: Optional[RiskLevel] = None
    
    # ATH/ATL specific
    distance_from_ath: Optional[Decimal] = None  # % below ATH
    distance_from_atl: Optional[Decimal] = None  # % above ATL
    ath_date: Optional[datetime] = None
    atl_date: Optional[datetime] = None
    
    # Valuation specific  
    fundamental_score: Optional[Decimal] = None
    technical_score: Optional[Decimal] = None
    sentiment_score: Optional[Decimal] = None
    
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class StockList:
    """Complete stock list with metadata."""
    
    list_type: StockListType
    title: str
    description: str
    items: List[StockListItem]
    total_items: int
    generation_criteria: Dict[str, Any]
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class SymbolListSnapshot:
    """Pre-fetched data used to rank list candidates."""

    symbol: str
    quote: StockQuote
    company: CompanyInfo
    recommendation: Optional[InvestmentRecommendation] = None
    research: Optional[ResearchPrediction] = None
    historical: Optional[List[Any]] = None


class StockListGeneratorService:
    """Service for generating various stock lists."""
    
    # S&P 500 symbols (sample - in production would be loaded from data source)
    SP500_SYMBOLS = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B",
        "UNH", "JNJ", "JPM", "V", "PG", "XOM", "MA", "HD", "CVX", "ABBV",
        "LLY", "BAC", "COST", "KO", "AVGO", "PEP", "TMO", "MRK", "WMT",
        "ACN", "CSCO", "ABT", "DHR", "VZ", "TXN", "NEE", "DIS", "CRM",
        "AMD", "ADBE", "NFLX", "PM", "RTX", "NKE", "QCOM", "IBM", "WFC",
        "CMCSA", "HON", "UPS", "T", "MDT", "LOW", "BMY", "AMAT", "CAT",
        "SPGI", "GE", "SBUX", "INTC", "MMM", "AXP", "BA", "GILD", "NOW",
        "AMT", "PYPL", "ISRG", "SYK", "MO", "ZTS", "C", "PLD", "CB",
        "TJX", "ADI", "BLK", "DE", "CVS", "FIS", "SO", "MDLZ", "BKNG"
    ]

    SCREENING_UNIVERSE = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "AVGO", "AMD",
        "ANET", "VRT", "ETN", "PWR", "JPM", "BAC", "BRK.B", "XOM",
        "CVX", "RTX", "LMT", "LLY", "UNH", "HD", "LOW", "CAT",
        "DE", "CRM", "NOW", "DDOG", "PLTR", "ORCL",
    ]
    
    def __init__(self):
        self.data_fetcher: Optional[RealDataFetcherService] = None
        self.stock_analyzer: Optional[StockAnalyzerService] = None
        self.prediction_engine: Optional[PredictionEngineService] = None
        self.recommendation_engine: Optional[RecommendationEngineService] = None
        self.research_service: Optional[ResearchPredictionService] = None
        
    async def __aenter__(self):
        """Initialize service dependencies."""
        self.data_fetcher = RealDataFetcherService()
        self.stock_analyzer = StockAnalyzerService()
        self.prediction_engine = PredictionEngineService()
        self.recommendation_engine = RecommendationEngineService()
        self.research_service = ResearchPredictionService()
        
        await self.data_fetcher.__aenter__()
        await self.stock_analyzer.__aenter__()
        await self.prediction_engine.__aenter__()
        await self.recommendation_engine.__aenter__()
        await self.research_service.__aenter__()
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup service dependencies."""
        if self.research_service:
            await self.research_service.__aexit__(exc_type, exc_val, exc_tb)
        if self.recommendation_engine:
            await self.recommendation_engine.__aexit__(exc_type, exc_val, exc_tb)
        if self.prediction_engine:
            await self.prediction_engine.__aexit__(exc_type, exc_val, exc_tb)
        if self.stock_analyzer:
            await self.stock_analyzer.__aexit__(exc_type, exc_val, exc_tb)
        if self.data_fetcher:
            await self.data_fetcher.__aexit__(exc_type, exc_val, exc_tb)
            
    async def generate_stock_list(
        self, 
        list_type: StockListType,
        max_items: int = 20,
        symbols: Optional[List[str]] = None
    ) -> Optional[StockList]:
        """Generate specified type of stock list."""
        if not all([self.data_fetcher, self.stock_analyzer, 
                   self.prediction_engine, self.recommendation_engine, self.research_service]):
            raise RuntimeError("Service must be used as async context manager")
            
        try:
            if list_type == StockListType.ALL_TIME_HIGH:
                return await self._generate_ath_list(max_items, symbols)
            elif list_type == StockListType.ALL_TIME_LOW:
                return await self._generate_atl_list(max_items, symbols)
            elif list_type == StockListType.SP500_ALL:
                return await self._generate_sp500_list(max_items)
            elif list_type == StockListType.SP500_ATH:
                return await self._generate_sp500_ath_list(max_items)
            elif list_type == StockListType.SP500_ATL:
                return await self._generate_sp500_atl_list(max_items)
            elif list_type == StockListType.UNDERVALUED:
                return await self._generate_undervalued_list(max_items, symbols)
            elif list_type == StockListType.OVERVALUED:
                return await self._generate_overvalued_list(max_items, symbols)
            elif list_type == StockListType.STRONG_BUY:
                return await self._generate_strong_buy_list(max_items, symbols)
            elif list_type == StockListType.STRONG_SELL:
                return await self._generate_strong_sell_list(max_items, symbols)
            else:
                print(f"Unknown list type: {list_type}")
                return None
                
        except Exception as e:
            print(f"Error generating {list_type.value} list: {e}")
            return None
            
    async def _generate_ath_list(
        self, max_items: int, symbols: Optional[List[str]]
    ) -> Optional[StockList]:
        """Generate list of stocks at or near all-time highs."""
        if not symbols:
            symbols = self.SP500_SYMBOLS[:15]  # Keep the live-data path responsive
            
        items = []
        
        for symbol in symbols:
            try:
                quote = await self.data_fetcher.get_stock_quote(symbol)
                company_info = await self.data_fetcher.get_company_info(symbol)
                historical = await self.data_fetcher.get_historical_data(symbol, 252)  # 1 year
                
                if not all([quote, company_info, historical]):
                    continue
                    
                # Calculate ATH metrics
                ath_data = self._calculate_ath_metrics(quote, historical)
                if not ath_data:
                    continue
                    
                distance_from_ath, ath_date, ath_price = ath_data
                
                # Only include stocks within 5% of ATH
                if distance_from_ath > 5:
                    continue
                    
                # Generate reasoning
                reasoning = [
                    f"Trading {distance_from_ath:.1f}% below all-time high of ${ath_price:.2f}",
                    f"ATH reached on {ath_date.strftime('%Y-%m-%d')}",
                ]
                
                if distance_from_ath <= 1:
                    reasoning.append("At or very near all-time high levels")
                    score = Decimal("95")
                elif distance_from_ath <= 2:
                    reasoning.append("Within 2% of all-time high")
                    score = Decimal("85")
                else:
                    reasoning.append("Near all-time high levels")
                    score = Decimal("75")
                    
                item = StockListItem(
                    symbol=symbol,
                    company_name=company_info.name,
                    current_price=quote.price,
                    list_type=StockListType.ALL_TIME_HIGH,
                    rank=0,  # Will be set after sorting
                    score=score,
                    reasoning=reasoning,
                    change_percent=quote.change_percent,
                    volume=quote.volume,
                    market_cap=company_info.market_cap,
                    distance_from_ath=distance_from_ath,
                    ath_date=ath_date,
                )
                
                items.append(item)
                
            except Exception as e:
                print(f"Error processing {symbol} for ATH list: {e}")
                continue
                
        # Sort by distance from ATH (closer = higher rank)
        items.sort(key=lambda x: x.distance_from_ath or 100)
        
        # Assign ranks and limit items
        for i, item in enumerate(items[:max_items]):
            item.rank = i + 1
            
        return StockList(
            list_type=StockListType.ALL_TIME_HIGH,
            title="Stocks at All-Time Highs",
            description="Companies trading at or near their all-time high prices",
            items=items[:max_items],
            total_items=len(items[:max_items]),
            generation_criteria={
                "max_distance_from_ath": 5.0,
                "lookback_period_days": 252,
                "symbols_analyzed": len(symbols),
            }
        )
        
    async def _generate_undervalued_list(
        self, max_items: int, symbols: Optional[List[str]]
    ) -> Optional[StockList]:
        """Generate list of value-tilted opportunities with supportive signals."""
        items = await self._rank_valuation_candidates(
            list_type=StockListType.UNDERVALUED,
            symbols=symbols or self.SCREENING_UNIVERSE,
            max_items=max_items,
        )
        
        for i, item in enumerate(items[:max_items]):
            item.rank = i + 1
            
        return StockList(
            list_type=StockListType.UNDERVALUED,
            title="Top Undervalued Opportunities",
            description="Stocks with supportive research signals and more reasonable valuation metrics",
            items=items[:max_items],
            total_items=len(items[:max_items]),
            generation_criteria={
                "signals_used": ["research_prediction", "fundamental_score", "valuation_multiples"],
                "symbols_analyzed": len(symbols or self.SCREENING_UNIVERSE),
            }
        )
        
    async def _generate_overvalued_list(
        self, max_items: int, symbols: Optional[List[str]]
    ) -> Optional[StockList]:
        """Generate list of stretched names with weaker support."""
        items = await self._rank_valuation_candidates(
            list_type=StockListType.OVERVALUED,
            symbols=symbols or self.SCREENING_UNIVERSE,
            max_items=max_items,
        )
        
        for i, item in enumerate(items[:max_items]):
            item.rank = i + 1
            
        return StockList(
            list_type=StockListType.OVERVALUED,
            title="Top Overvalued Risk Names",
            description="Stocks where stretched valuation or weaker research support raises downside risk",
            items=items[:max_items],
            total_items=len(items[:max_items]),
            generation_criteria={
                "signals_used": ["research_prediction", "fundamental_score", "valuation_multiples"],
                "symbols_analyzed": len(symbols or self.SCREENING_UNIVERSE),
            }
        )
        
    async def _generate_sp500_list(self, max_items: int) -> Optional[StockList]:
        """Generate S&P 500 overview list."""
        items = []
        
        for symbol in self.SP500_SYMBOLS[:max_items]:
            try:
                quote = await self.data_fetcher.get_stock_quote(symbol)
                company_info = await self.data_fetcher.get_company_info(symbol)
                recommendation = await self.recommendation_engine.generate_recommendation(symbol)
                
                if not all([quote, company_info]):
                    continue
                    
                reasoning = [
                    f"S&P 500 constituent company",
                    f"Market cap: ${company_info.market_cap/1_000_000_000:.1f}B" if company_info.market_cap else "Large cap stock",
                    f"Daily change: {quote.change_percent:+.2f}%",
                ]
                
                if recommendation:
                    reasoning.append(f"Current recommendation: {recommendation.recommendation.value.upper()}")
                    
                # Score based on market cap and recommendation
                base_score = Decimal("50")
                if company_info.market_cap:
                    # Higher score for larger market cap
                    if company_info.market_cap > 500_000_000_000:  # >$500B
                        base_score += Decimal("30")
                    elif company_info.market_cap > 100_000_000_000:  # >$100B
                        base_score += Decimal("20")
                    elif company_info.market_cap > 50_000_000_000:  # >$50B
                        base_score += Decimal("10")
                        
                item = StockListItem(
                    symbol=symbol,
                    company_name=company_info.name,
                    current_price=quote.price,
                    list_type=StockListType.SP500_ALL,
                    rank=0,
                    score=base_score,
                    reasoning=reasoning,
                    change_percent=quote.change_percent,
                    volume=quote.volume,
                    market_cap=company_info.market_cap,
                    recommendation=recommendation.recommendation if recommendation else None,
                    confidence=recommendation.confidence if recommendation else None,
                    risk_level=recommendation.risk_level if recommendation else None,
                )
                
                items.append(item)
                
            except Exception as e:
                print(f"Error processing {symbol} for S&P 500 list: {e}")
                continue
                
        # Sort by market cap (larger first)
        items.sort(key=lambda x: x.market_cap or 0, reverse=True)
        
        # Assign ranks
        for i, item in enumerate(items):
            item.rank = i + 1
            
        return StockList(
            list_type=StockListType.SP500_ALL,
            title="S&P 500 Companies",
            description="Overview of S&P 500 constituent companies with current analysis",
            items=items,
            total_items=len(items),
            generation_criteria={
                "source": "S&P 500 Index",
                "sort_by": "market_cap",
                "symbols_analyzed": len(self.SP500_SYMBOLS[:max_items]),
            }
        )
        
    async def _generate_sp500_ath_list(self, max_items: int) -> Optional[StockList]:
        """Generate S&P 500 stocks at all-time highs."""
        ath_list = await self._generate_ath_list(max_items, self.SP500_SYMBOLS)
        if ath_list:
            ath_list.list_type = StockListType.SP500_ATH
            ath_list.title = "S&P 500 Stocks at All-Time Highs"
            ath_list.description = "S&P 500 companies trading at or near all-time high prices"
            for item in ath_list.items:
                item.list_type = StockListType.SP500_ATH
                item.reasoning.insert(0, "S&P 500 constituent company")
        return ath_list
        
    async def _generate_sp500_atl_list(self, max_items: int) -> Optional[StockList]:
        """Generate S&P 500 stocks at all-time lows."""
        atl_list = await self._generate_atl_list(max_items, self.SP500_SYMBOLS)
        if atl_list:
            atl_list.list_type = StockListType.SP500_ATL
            atl_list.title = "S&P 500 Stocks at All-Time Lows"
            atl_list.description = "S&P 500 companies trading at or near all-time low prices"
            for item in atl_list.items:
                item.list_type = StockListType.SP500_ATL
                item.reasoning.insert(0, "S&P 500 constituent company")
        return atl_list
        
    async def _generate_atl_list(
        self, max_items: int, symbols: Optional[List[str]]
    ) -> Optional[StockList]:
        """Generate list of stocks at or near all-time lows."""
        if not symbols:
            symbols = self.SP500_SYMBOLS[:15]
            
        items = []
        
        for symbol in symbols:
            try:
                quote = await self.data_fetcher.get_stock_quote(symbol)
                company_info = await self.data_fetcher.get_company_info(symbol)
                historical = await self.data_fetcher.get_historical_data(symbol, 252)
                
                if not all([quote, company_info, historical]):
                    continue
                    
                # Calculate ATL metrics
                atl_data = self._calculate_atl_metrics(quote, historical)
                if not atl_data:
                    continue
                    
                distance_from_atl, atl_date, atl_price = atl_data
                
                # Only include stocks within 5% of ATL
                if distance_from_atl > 5:
                    continue
                    
                reasoning = [
                    f"Trading {distance_from_atl:.1f}% above all-time low of ${atl_price:.2f}",
                    f"ATL reached on {atl_date.strftime('%Y-%m-%d')}",
                ]
                
                if distance_from_atl <= 1:
                    reasoning.append("At or very near all-time low levels")
                    score = Decimal("95")
                elif distance_from_atl <= 2:
                    reasoning.append("Within 2% of all-time low")
                    score = Decimal("85")
                else:
                    reasoning.append("Near all-time low levels")
                    score = Decimal("75")
                    
                item = StockListItem(
                    symbol=symbol,
                    company_name=company_info.name,
                    current_price=quote.price,
                    list_type=StockListType.ALL_TIME_LOW,
                    rank=0,
                    score=score,
                    reasoning=reasoning,
                    change_percent=quote.change_percent,
                    volume=quote.volume,
                    market_cap=company_info.market_cap,
                    distance_from_atl=distance_from_atl,
                    atl_date=atl_date,
                )
                
                items.append(item)
                
            except Exception as e:
                print(f"Error processing {symbol} for ATL list: {e}")
                continue
                
        # Sort by distance from ATL (closer = higher rank)
        items.sort(key=lambda x: x.distance_from_atl or 100)
        
        for i, item in enumerate(items[:max_items]):
            item.rank = i + 1
            
        return StockList(
            list_type=StockListType.ALL_TIME_LOW,
            title="Stocks at All-Time Lows",
            description="Companies trading at or near their all-time low prices",
            items=items[:max_items],
            total_items=len(items[:max_items]),
            generation_criteria={
                "max_distance_from_atl": 5.0,
                "lookback_period_days": 252,
                "symbols_analyzed": len(symbols),
            }
        )
        
    async def _generate_strong_buy_list(
        self, max_items: int, symbols: Optional[List[str]]
    ) -> Optional[StockList]:
        """Generate a best-of current bullish opportunities list."""
        items = await self._rank_directional_candidates(
            list_type=StockListType.STRONG_BUY,
            symbols=symbols or self.SCREENING_UNIVERSE,
            max_items=max_items,
        )
        
        for i, item in enumerate(items[:max_items]):
            item.rank = i + 1
            
        return StockList(
            list_type=StockListType.STRONG_BUY,
            title="Strong Buy Candidates",
            description="The most compelling current bullish setups across research, fundamentals, and live market context",
            items=items[:max_items],
            total_items=len(items[:max_items]),
            generation_criteria={
                "signals_used": ["research_prediction", "fundamental_score", "technical_score"],
                "symbols_analyzed": len(symbols or self.SCREENING_UNIVERSE),
            }
        )
        
    async def _generate_strong_sell_list(
        self, max_items: int, symbols: Optional[List[str]]
    ) -> Optional[StockList]:
        """Generate a best-of current bearish opportunities list."""
        items = await self._rank_directional_candidates(
            list_type=StockListType.STRONG_SELL,
            symbols=symbols or self.SCREENING_UNIVERSE,
            max_items=max_items,
        )
        
        for i, item in enumerate(items[:max_items]):
            item.rank = i + 1
            
        return StockList(
            list_type=StockListType.STRONG_SELL,
            title="Strong Sell Candidates", 
            description="The weakest current setups based on event-linked research, valuation stretch, and downside risk",
            items=items[:max_items],
            total_items=len(items[:max_items]),
            generation_criteria={
                "signals_used": ["research_prediction", "fundamental_score", "technical_score"],
                "symbols_analyzed": len(symbols or self.SCREENING_UNIVERSE),
            }
        )

    async def _rank_directional_candidates(
        self, list_type: StockListType, symbols: List[str], max_items: int
    ) -> List[StockListItem]:
        snapshots = await self._collect_snapshots(symbols, include_historical=False)
        items: List[StockListItem] = []

        for snapshot in snapshots:
            if not snapshot.research:
                continue

            short_horizon = next(
                (h for h in snapshot.research.horizons if h.horizon == "21d"),
                snapshot.research.horizons[0] if snapshot.research.horizons else None,
            )
            if not short_horizon:
                continue

            bullish = list_type == StockListType.STRONG_BUY
            alignment = (
                short_horizon.probability_outperform
                if bullish
                else 1 - short_horizon.probability_outperform
            )
            research_bonus = 18 if short_horizon.recommendation.startswith("strong_") else 10
            direction_bonus = (
                12
                if bullish
                and short_horizon.recommendation in {"buy", "strong_buy"}
                else 12
                if (not bullish)
                and short_horizon.recommendation in {"sell", "strong_sell"}
                else 0
            )
            fundamentals = float(snapshot.recommendation.fundamental_score or 50) if snapshot.recommendation else 50
            technicals = float(snapshot.recommendation.technical_score or 50) if snapshot.recommendation else 50
            score_value = min(
                100.0,
                alignment * 55
                + direction_bonus
                + research_bonus
                + (fundamentals * 0.12 if bullish else (100 - fundamentals) * 0.10)
                + (technicals * 0.08 if bullish else technicals * 0.12),
            )
            reasoning = [
                f"21-day research view: {short_horizon.recommendation.replace('_', ' ')}",
                f"Probability of outperform: {short_horizon.probability_outperform:.0%}",
                f"Research confidence: {short_horizon.confidence:.0%}",
            ]
            if snapshot.recommendation:
                reasoning.extend(snapshot.recommendation.reasoning[:2])

            items.append(
                StockListItem(
                    symbol=snapshot.symbol,
                    company_name=snapshot.company.name,
                    current_price=snapshot.quote.price,
                    list_type=list_type,
                    rank=0,
                    score=Decimal(str(round(score_value, 2))),
                    reasoning=reasoning,
                    change_percent=snapshot.quote.change_percent,
                    volume=snapshot.quote.volume,
                    market_cap=snapshot.company.market_cap,
                    recommendation=(
                        RecommendationType.STRONG_BUY
                        if bullish
                        else RecommendationType.STRONG_SELL
                    ),
                    confidence=Decimal(str(round(short_horizon.confidence, 4))),
                    risk_level=snapshot.recommendation.risk_level if snapshot.recommendation else None,
                    fundamental_score=snapshot.recommendation.fundamental_score if snapshot.recommendation else None,
                    technical_score=snapshot.recommendation.technical_score if snapshot.recommendation else None,
                    sentiment_score=snapshot.recommendation.sentiment_score if snapshot.recommendation else None,
                )
            )

        items.sort(key=lambda item: item.score, reverse=True)
        return items[:max_items]

    async def _rank_valuation_candidates(
        self, list_type: StockListType, symbols: List[str], max_items: int
    ) -> List[StockListItem]:
        snapshots = await self._collect_snapshots(symbols, include_historical=False)
        items: List[StockListItem] = []

        for snapshot in snapshots:
            recommendation = snapshot.recommendation
            research = snapshot.research
            if not recommendation or not research:
                continue

            medium = next(
                (h for h in research.horizons if h.horizon == "21d"),
                research.horizons[0] if research.horizons else None,
            )
            if not medium:
                continue

            pe = float(snapshot.company.pe_ratio) if snapshot.company.pe_ratio is not None else None
            pb = float(snapshot.company.price_to_book) if snapshot.company.price_to_book is not None else None
            is_undervalued = list_type == StockListType.UNDERVALUED
            valuation_score = self._valuation_component(pe, pb, is_undervalued)
            research_alignment = (
                medium.probability_outperform if is_undervalued else 1 - medium.probability_outperform
            )
            direction_bias = 10 if medium.recommendation in (
                {"buy", "strong_buy"} if is_undervalued else {"sell", "strong_sell"}
            ) else 0
            score_value = min(
                100.0,
                valuation_score * 0.55
                + research_alignment * 22
                + direction_bias
                + (
                    float(recommendation.fundamental_score or 50)
                    * (0.14 if is_undervalued else -0.05)
                )
                + (
                    float(recommendation.technical_score or 50)
                    * (-0.05 if is_undervalued else 0.10)
                )
                + (float(recommendation.confidence or 0.3) * 12),
            )
            score_value = max(0.0, score_value)

            valuation_text = []
            if pe is not None:
                valuation_text.append(f"Trailing P/E {pe:.1f}")
            if pb is not None:
                valuation_text.append(f"Price-to-book {pb:.1f}")
            if not valuation_text:
                valuation_text.append("Valuation multiples unavailable; ranking leans on research and fundamentals")

            reasoning = [
                valuation_text[0],
                f"21-day research view: {medium.recommendation.replace('_', ' ')}",
                f"Research confidence: {medium.confidence:.0%}",
            ]
            if recommendation.target_price and recommendation.current_price:
                move_pct = (
                    (recommendation.target_price - recommendation.current_price)
                    / recommendation.current_price
                    * 100
                )
                reasoning.append(
                    f"Target-price gap: {float(move_pct):+.1f}%"
                )

            items.append(
                StockListItem(
                    symbol=snapshot.symbol,
                    company_name=snapshot.company.name,
                    current_price=snapshot.quote.price,
                    list_type=list_type,
                    rank=0,
                    score=Decimal(str(round(score_value, 2))),
                    reasoning=reasoning,
                    change_percent=snapshot.quote.change_percent,
                    volume=snapshot.quote.volume,
                    market_cap=snapshot.company.market_cap,
                    recommendation=(
                        recommendation.recommendation
                        if recommendation and recommendation.recommendation != RecommendationType.HOLD
                        else RecommendationType.BUY
                        if is_undervalued
                        else RecommendationType.SELL
                    ),
                    confidence=recommendation.confidence or Decimal(str(round(medium.confidence, 4))),
                    risk_level=recommendation.risk_level,
                    fundamental_score=recommendation.fundamental_score,
                    technical_score=recommendation.technical_score,
                    sentiment_score=recommendation.sentiment_score,
                )
            )

        items.sort(key=lambda item: item.score, reverse=True)
        return items[:max_items]

    async def _collect_snapshots(
        self, symbols: List[str], include_historical: bool
    ) -> List[SymbolListSnapshot]:
        async def _load(symbol: str) -> Optional[SymbolListSnapshot]:
            try:
                quote, company, recommendation, research = await asyncio.gather(
                    self.data_fetcher.get_stock_quote(symbol),
                    self.data_fetcher.get_company_info(symbol),
                    self.recommendation_engine.generate_recommendation(symbol),
                    self.research_service.predict(symbol),
                )
                historical = (
                    await self.data_fetcher.get_historical_data(symbol, 252)
                    if include_historical
                    else None
                )
                if not quote or not company:
                    return None
                return SymbolListSnapshot(
                    symbol=symbol,
                    quote=quote,
                    company=company,
                    recommendation=recommendation,
                    research=research,
                    historical=historical,
                )
            except Exception as exc:
                print(f"Error collecting snapshot for {symbol}: {exc}")
                return None

        results = await asyncio.gather(*[_load(symbol) for symbol in symbols])
        return [snapshot for snapshot in results if snapshot is not None]

    def _valuation_component(
        self, pe_ratio: Optional[float], pb_ratio: Optional[float], undervalued: bool
    ) -> float:
        if pe_ratio is None and pb_ratio is None:
            return 42.0 if undervalued else 30.0

        score = 35.0
        if pe_ratio is not None:
            if undervalued:
                if pe_ratio < 18:
                    score += 22
                elif pe_ratio < 25:
                    score += 14
                elif pe_ratio > 40:
                    score -= 18
            else:
                if pe_ratio > 40:
                    score += 22
                elif pe_ratio > 30:
                    score += 14
                elif pe_ratio < 18:
                    score -= 12

        if pb_ratio is not None:
            if undervalued:
                if pb_ratio < 4:
                    score += 12
                elif pb_ratio > 10:
                    score -= 10
            else:
                if pb_ratio > 10:
                    score += 12
                elif pb_ratio < 3:
                    score -= 8
        return score
        
    def _calculate_ath_metrics(
        self, quote: StockQuote, historical: List[Any]
    ) -> Optional[Tuple[Decimal, datetime, Decimal]]:
        """Calculate all-time high metrics."""
        try:
            if not historical:
                return None
                
            # Find highest price in historical data
            max_price = Decimal("0")
            max_date = None
            
            for data_point in historical:
                # Handle different historical data formats
                if hasattr(data_point, 'high'):
                    price = data_point.high
                    date = data_point.date
                elif hasattr(data_point, 'high_price'):
                    price = data_point.high_price  
                    date = data_point.date
                else:
                    continue
                    
                if price > max_price:
                    max_price = price
                    max_date = date
                    
            if not max_price or not max_date:
                return None
                
            # Calculate distance from ATH
            distance_from_ath = ((max_price - quote.price) / max_price * 100)
            
            return (distance_from_ath, max_date, max_price)
            
        except Exception as e:
            print(f"Error calculating ATH metrics: {e}")
            return None
            
    def _calculate_atl_metrics(
        self, quote: StockQuote, historical: List[Any]
    ) -> Optional[Tuple[Decimal, datetime, Decimal]]:
        """Calculate all-time low metrics."""
        try:
            if not historical:
                return None
                
            # Find lowest price in historical data
            min_price = Decimal("999999")
            min_date = None
            
            for data_point in historical:
                # Handle different historical data formats
                if hasattr(data_point, 'low'):
                    price = data_point.low
                    date = data_point.date
                elif hasattr(data_point, 'low_price'):
                    price = data_point.low_price
                    date = data_point.date
                else:
                    continue
                    
                if price < min_price and price > 0:  # Exclude zero prices
                    min_price = price
                    min_date = date
                    
            if min_price == Decimal("999999") or not min_date:
                return None
                
            # Calculate distance from ATL
            distance_from_atl = ((quote.price - min_price) / min_price * 100)
            
            return (distance_from_atl, min_date, min_price)
            
        except Exception as e:
            print(f"Error calculating ATL metrics: {e}")
            return None
