"""
Stock list API routes.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query

from app.services import StockListGeneratorService
from app.services.stock_lists import StockListType


router = APIRouter(prefix="/lists", tags=["stock-lists"])


async def get_stock_list_generator():
    """Dependency to get StockListGeneratorService."""
    async with StockListGeneratorService() as service:
        yield service


@router.get("/all-time-high", response_model=dict)
async def get_all_time_high_stocks(
    max_items: int = Query(default=20, ge=1, le=100, description="Maximum number of stocks to return"),
    symbols: Optional[str] = Query(default=None, description="Comma-separated list of symbols to analyze"),
    stock_list_generator: StockListGeneratorService = Depends(get_stock_list_generator)
):
    """Get stocks at or near all-time highs."""
    try:
        symbol_list = symbols.split(",") if symbols else None
        if symbol_list:
            symbol_list = [s.strip().upper() for s in symbol_list]
            
        stock_list = await stock_list_generator.generate_stock_list(
            StockListType.ALL_TIME_HIGH, 
            max_items=max_items,
            symbols=symbol_list
        )
        
        if not stock_list:
            raise HTTPException(status_code=404, detail="Unable to generate all-time high list")
        
        return {
            "list_type": stock_list.list_type.value,
            "title": stock_list.title,
            "description": stock_list.description,
            "total_items": stock_list.total_items,
            "last_updated": stock_list.last_updated.isoformat(),
            "generation_criteria": stock_list.generation_criteria,
            "items": [
                {
                    "rank": item.rank,
                    "symbol": item.symbol,
                    "company_name": item.company_name,
                    "current_price": float(item.current_price),
                    "score": float(item.score),
                    "reasoning": item.reasoning,
                    "change_percent": float(item.change_percent) if item.change_percent else None,
                    "volume": item.volume,
                    "market_cap": float(item.market_cap) if item.market_cap else None,
                    "distance_from_ath": float(item.distance_from_ath) if item.distance_from_ath else None,
                    "ath_date": item.ath_date.isoformat() if item.ath_date else None,
                }
                for item in stock_list.items
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all-time-low", response_model=dict)
async def get_all_time_low_stocks(
    max_items: int = Query(default=20, ge=1, le=100),
    symbols: Optional[str] = Query(default=None, description="Comma-separated list of symbols"),
    stock_list_generator: StockListGeneratorService = Depends(get_stock_list_generator)
):
    """Get stocks at or near all-time lows."""
    try:
        symbol_list = symbols.split(",") if symbols else None
        if symbol_list:
            symbol_list = [s.strip().upper() for s in symbol_list]
            
        stock_list = await stock_list_generator.generate_stock_list(
            StockListType.ALL_TIME_LOW,
            max_items=max_items,
            symbols=symbol_list
        )
        
        if not stock_list:
            raise HTTPException(status_code=404, detail="Unable to generate all-time low list")
            
        return _format_stock_list_response(stock_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sp500", response_model=dict)
async def get_sp500_stocks(
    max_items: int = Query(default=50, ge=1, le=100),
    stock_list_generator: StockListGeneratorService = Depends(get_stock_list_generator)
):
    """Get S&P 500 companies overview."""
    try:
        stock_list = await stock_list_generator.generate_stock_list(
            StockListType.SP500_ALL,
            max_items=max_items
        )
        
        if not stock_list:
            raise HTTPException(status_code=404, detail="Unable to generate S&P 500 list")
            
        return _format_stock_list_response(stock_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sp500/all-time-high", response_model=dict)
async def get_sp500_ath_stocks(
    max_items: int = Query(default=20, ge=1, le=100),
    stock_list_generator: StockListGeneratorService = Depends(get_stock_list_generator)
):
    """Get S&P 500 stocks at all-time highs."""
    try:
        stock_list = await stock_list_generator.generate_stock_list(
            StockListType.SP500_ATH,
            max_items=max_items
        )
        
        if not stock_list:
            raise HTTPException(status_code=404, detail="Unable to generate S&P 500 ATH list")
            
        return _format_stock_list_response(stock_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sp500/all-time-low", response_model=dict)
async def get_sp500_atl_stocks(
    max_items: int = Query(default=20, ge=1, le=100),
    stock_list_generator: StockListGeneratorService = Depends(get_stock_list_generator)
):
    """Get S&P 500 stocks at all-time lows."""
    try:
        stock_list = await stock_list_generator.generate_stock_list(
            StockListType.SP500_ATL,
            max_items=max_items
        )
        
        if not stock_list:
            raise HTTPException(status_code=404, detail="Unable to generate S&P 500 ATL list")
            
        return _format_stock_list_response(stock_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/undervalued", response_model=dict)
async def get_undervalued_stocks(
    max_items: int = Query(default=20, ge=1, le=100),
    symbols: Optional[str] = Query(default=None, description="Comma-separated list of symbols"),
    stock_list_generator: StockListGeneratorService = Depends(get_stock_list_generator)
):
    """Get undervalued stocks with strong fundamentals."""
    try:
        symbol_list = symbols.split(",") if symbols else None
        if symbol_list:
            symbol_list = [s.strip().upper() for s in symbol_list]
            
        stock_list = await stock_list_generator.generate_stock_list(
            StockListType.UNDERVALUED,
            max_items=max_items,
            symbols=symbol_list
        )
        
        if not stock_list:
            raise HTTPException(status_code=404, detail="Unable to generate undervalued stocks list")
            
        return _format_stock_list_response(
            stock_list, include_scores=True, include_recommendations=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overvalued", response_model=dict)
async def get_overvalued_stocks(
    max_items: int = Query(default=20, ge=1, le=100),
    symbols: Optional[str] = Query(default=None, description="Comma-separated list of symbols"),
    stock_list_generator: StockListGeneratorService = Depends(get_stock_list_generator)
):
    """Get overvalued stocks with weak fundamentals."""
    try:
        symbol_list = symbols.split(",") if symbols else None
        if symbol_list:
            symbol_list = [s.strip().upper() for s in symbol_list]
            
        stock_list = await stock_list_generator.generate_stock_list(
            StockListType.OVERVALUED,
            max_items=max_items,
            symbols=symbol_list
        )
        
        if not stock_list:
            raise HTTPException(status_code=404, detail="Unable to generate overvalued stocks list")
            
        return _format_stock_list_response(
            stock_list, include_scores=True, include_recommendations=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strong-buy", response_model=dict)
async def get_strong_buy_stocks(
    max_items: int = Query(default=20, ge=1, le=100),
    symbols: Optional[str] = Query(default=None, description="Comma-separated list of symbols"),
    stock_list_generator: StockListGeneratorService = Depends(get_stock_list_generator)
):
    """Get stocks with strong buy recommendations."""
    try:
        symbol_list = symbols.split(",") if symbols else None
        if symbol_list:
            symbol_list = [s.strip().upper() for s in symbol_list]
            
        stock_list = await stock_list_generator.generate_stock_list(
            StockListType.STRONG_BUY,
            max_items=max_items,
            symbols=symbol_list
        )
        
        if not stock_list:
            raise HTTPException(status_code=404, detail="Unable to generate strong buy list")
            
        return _format_stock_list_response(stock_list, include_recommendations=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strong-sell", response_model=dict)
async def get_strong_sell_stocks(
    max_items: int = Query(default=20, ge=1, le=100),
    symbols: Optional[str] = Query(default=None, description="Comma-separated list of symbols"),
    stock_list_generator: StockListGeneratorService = Depends(get_stock_list_generator)
):
    """Get stocks with strong sell recommendations."""
    try:
        symbol_list = symbols.split(",") if symbols else None
        if symbol_list:
            symbol_list = [s.strip().upper() for s in symbol_list]
            
        stock_list = await stock_list_generator.generate_stock_list(
            StockListType.STRONG_SELL,
            max_items=max_items,
            symbols=symbol_list
        )
        
        if not stock_list:
            raise HTTPException(status_code=404, detail="Unable to generate strong sell list")
            
        return _format_stock_list_response(stock_list, include_recommendations=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _format_stock_list_response(stock_list, include_scores: bool = False, include_recommendations: bool = False) -> dict:
    """Format stock list for API response."""
    response = {
        "list_type": stock_list.list_type.value,
        "title": stock_list.title,
        "description": stock_list.description,
        "total_items": stock_list.total_items,
        "last_updated": stock_list.last_updated.isoformat(),
        "generation_criteria": stock_list.generation_criteria,
        "items": []
    }
    
    for item in stock_list.items:
        item_data = {
            "rank": item.rank,
            "symbol": item.symbol,
            "company_name": item.company_name,
            "current_price": float(item.current_price),
            "score": float(item.score),
            "reasoning": item.reasoning,
            "change_percent": float(item.change_percent) if item.change_percent else None,
            "volume": item.volume,
            "market_cap": float(item.market_cap) if item.market_cap else None,
        }
        
        # ATH/ATL specific fields
        if item.distance_from_ath is not None:
            item_data["distance_from_ath"] = float(item.distance_from_ath)
            item_data["ath_date"] = item.ath_date.isoformat() if item.ath_date else None
            
        if item.distance_from_atl is not None:
            item_data["distance_from_atl"] = float(item.distance_from_atl)
            item_data["atl_date"] = item.atl_date.isoformat() if item.atl_date else None
        
        # Include detailed scores for valuation lists
        if include_scores:
            item_data.update({
                "fundamental_score": float(item.fundamental_score) if item.fundamental_score else None,
                "technical_score": float(item.technical_score) if item.technical_score else None,
                "sentiment_score": float(item.sentiment_score) if item.sentiment_score else None,
            })
        
        # Include recommendation details
        if include_recommendations:
            item_data.update({
                "recommendation": item.recommendation.value if item.recommendation else None,
                "confidence": float(item.confidence) if item.confidence else None,
                "risk_level": item.risk_level.value if item.risk_level else None,
            })
        
        response["items"].append(item_data)
    
    return response
