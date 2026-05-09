"""
Stock-related API routes.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from app.services import (
    DataFetcherService,
    StockAnalyzerService, 
    PredictionEngineService,
    RecommendationEngineService,
    StockListGeneratorService,
)
from app.services.real_data_fetcher import RealDataFetcherService
from app.services.research_prediction import ResearchPredictionService
from app.services.stock_lists import StockListType
# Response models will be defined as dict for now
# from app.schemas.stock import StockResponse, StockPriceResponse
# from app.schemas.prediction import PredictionResponse
# from app.schemas.lists import StockListResponse  # Not needed


router = APIRouter(prefix="/stocks", tags=["stocks"])


async def get_data_fetcher():
    """Dependency to get RealDataFetcherService for production data."""
    async with RealDataFetcherService() as service:
        yield service


async def get_stock_analyzer():
    """Dependency to get StockAnalyzerService."""
    async with StockAnalyzerService() as service:
        yield service


async def get_prediction_engine():
    """Dependency to get PredictionEngineService."""
    async with PredictionEngineService() as service:
        yield service


async def get_recommendation_engine():
    """Dependency to get RecommendationEngineService."""
    async with RecommendationEngineService() as service:
        yield service


async def get_stock_list_generator():
    """Dependency to get StockListGeneratorService."""
    async with StockListGeneratorService() as service:
        yield service


async def get_research_prediction_service():
    """Dependency to get source-aware research prediction service."""
    async with ResearchPredictionService() as service:
        yield service


@router.get("/{symbol}/quote", response_model=dict)
async def get_stock_quote(
    symbol: str,
    data_fetcher: RealDataFetcherService = Depends(get_data_fetcher)
):
    """Get current stock quote."""
    try:
        quote = await data_fetcher.get_stock_quote(symbol.upper())
        if not quote:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
        
        return {
            "symbol": quote.symbol,
            "price": float(quote.price),
            "change": float(quote.change),
            "change_percent": float(quote.change_percent),
            "volume": quote.volume,
            "timestamp": quote.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/company", response_model=dict)
async def get_company_info(
    symbol: str,
    data_fetcher: RealDataFetcherService = Depends(get_data_fetcher)
):
    """Get company information."""
    try:
        company = await data_fetcher.get_company_info(symbol.upper())
        if not company:
            raise HTTPException(status_code=404, detail=f"Company info for {symbol} not found")
        
        return {
            "symbol": company.symbol,
            "name": company.name,
            "sector": company.sector,
            "market_cap": float(company.market_cap) if company.market_cap else None,
            "description": company.description,
            "website": company.website,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/analysis", response_model=dict)
async def get_stock_analysis(
    symbol: str,
    stock_analyzer: StockAnalyzerService = Depends(get_stock_analyzer)
):
    """Get comprehensive stock analysis."""
    try:
        analysis = await stock_analyzer.analyze_stock(symbol.upper())
        if not analysis:
            raise HTTPException(status_code=404, detail=f"Analysis for {symbol} not available")
        
        result = {
            "symbol": analysis.symbol,
            "analysis_date": analysis.analysis_date.isoformat(),
            "volatility": float(analysis.volatility) if analysis.volatility else None,
            "trend": analysis.trend_analysis,
            "support_resistance": analysis.support_resistance,
            "volume_analysis": analysis.volume_analysis,
        }
        
        if analysis.technical_indicators:
            tech = analysis.technical_indicators
            result["technical_indicators"] = {
                "rsi": float(tech.rsi) if tech.rsi else None,
                "macd": float(tech.macd) if tech.macd else None,
                "macd_signal": float(tech.macd_signal) if tech.macd_signal else None,
                "sma_20": float(tech.sma_20) if tech.sma_20 else None,
                "sma_50": float(tech.sma_50) if tech.sma_50 else None,
                "sma_200": float(tech.sma_200) if tech.sma_200 else None,
                "ema_12": float(tech.ema_12) if tech.ema_12 else None,
                "ema_26": float(tech.ema_26) if tech.ema_26 else None,
                "bollinger_upper": float(tech.bollinger_upper) if tech.bollinger_upper else None,
                "bollinger_lower": float(tech.bollinger_lower) if tech.bollinger_lower else None,
                "atr": float(tech.atr) if tech.atr else None,
            }
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/prediction", response_model=dict)
async def get_stock_prediction(
    symbol: str,
    prediction_engine: PredictionEngineService = Depends(get_prediction_engine)
):
    """Get ML-based stock prediction."""
    try:
        prediction = await prediction_engine.predict_stock(symbol.upper())
        if not prediction:
            raise HTTPException(status_code=404, detail=f"Prediction for {symbol} not available")
        
        return {
            "symbol": prediction.symbol,
            "overall_sentiment": prediction.overall_sentiment.value,
            "model_version": prediction.model_version,
            "short_term": {
                "prediction": prediction.short_term.prediction.value,
                "confidence": float(prediction.short_term.confidence),
                "target_price": float(prediction.short_term.target_price) if prediction.short_term.target_price else None,
                "stop_loss": float(prediction.short_term.stop_loss) if prediction.short_term.stop_loss else None,
                "horizon": prediction.short_term.horizon.value,
            },
            "medium_term": {
                "prediction": prediction.medium_term.prediction.value,
                "confidence": float(prediction.medium_term.confidence),
                "target_price": float(prediction.medium_term.target_price) if prediction.medium_term.target_price else None,
                "stop_loss": float(prediction.medium_term.stop_loss) if prediction.medium_term.stop_loss else None,
                "horizon": prediction.medium_term.horizon.value,
            },
            "long_term": {
                "prediction": prediction.long_term.prediction.value,
                "confidence": float(prediction.long_term.confidence),
                "target_price": float(prediction.long_term.target_price) if prediction.long_term.target_price else None,
                "stop_loss": float(prediction.long_term.stop_loss) if prediction.long_term.stop_loss else None,
                "horizon": prediction.long_term.horizon.value,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/research-prediction", response_model=dict)
async def get_stock_research_prediction(
    symbol: str,
    research_service: ResearchPredictionService = Depends(
        get_research_prediction_service
    ),
):
    """Get evidence-backed, source-aware stock research prediction."""
    try:
        prediction = await research_service.predict(symbol.upper())
        return prediction.to_api()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/recommendation", response_model=dict)
async def get_stock_recommendation(
    symbol: str,
    recommendation_engine: RecommendationEngineService = Depends(get_recommendation_engine)
):
    """Get investment recommendation for a stock."""
    try:
        recommendation = await recommendation_engine.generate_recommendation(symbol.upper())
        if not recommendation:
            raise HTTPException(status_code=404, detail=f"Recommendation for {symbol} not available")
        
        return {
            "symbol": recommendation.symbol,
            "company_name": recommendation.company_name,
            "recommendation": recommendation.recommendation.value,
            "confidence": float(recommendation.confidence),
            "risk_level": recommendation.risk_level.value,
            "target_price": float(recommendation.target_price) if recommendation.target_price else None,
            "stop_loss": float(recommendation.stop_loss) if recommendation.stop_loss else None,
            "current_price": float(recommendation.current_price) if recommendation.current_price else None,
            "potential_return": float(recommendation.potential_return) if recommendation.potential_return else None,
            "fundamental_score": float(recommendation.fundamental_score) if recommendation.fundamental_score else None,
            "technical_score": float(recommendation.technical_score) if recommendation.technical_score else None,
            "sentiment_score": float(recommendation.sentiment_score) if recommendation.sentiment_score else None,
            "overall_score": float(recommendation.overall_score) if recommendation.overall_score else None,
            "reasoning": recommendation.reasoning,
            "created_at": recommendation.created_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/historical", response_model=List[dict])
async def get_historical_data(
    symbol: str,
    days: int = Query(default=30, ge=1, le=365, description="Number of days of historical data"),
    data_fetcher: RealDataFetcherService = Depends(get_data_fetcher)
):
    """Get historical stock data."""
    try:
        historical = await data_fetcher.get_historical_data(symbol.upper(), days)
        if not historical:
            raise HTTPException(status_code=404, detail=f"Historical data for {symbol} not available")
        
        return [
            {
                "date": data.date.isoformat(),
                "open": float(data.open_price),
                "high": float(data.high),
                "low": float(data.low),
                "close": float(data.close),
                "volume": data.volume,
                "adjusted_close": float(data.adjusted_close) if data.adjusted_close else None,
            }
            for data in historical
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{symbol}/news", response_model=List[dict])
async def get_stock_news(
    symbol: str,
    limit: int = Query(default=10, ge=1, le=50, description="Number of news articles"),
    data_fetcher: RealDataFetcherService = Depends(get_data_fetcher)
):
    """Get recent news for a stock."""
    try:
        news = await data_fetcher.get_news(symbol.upper(), limit)
        if not news:
            return []
        
        return [
            {
                "title": article.title,
                "description": article.description,
                "url": article.url,
                "published_at": article.published_at.isoformat() if article.published_at else None,
                "source": article.source,
                "sentiment": article.sentiment,
            }
            for article in news
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
