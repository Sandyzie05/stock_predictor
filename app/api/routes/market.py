"""
Market intelligence routes for open news, event linkage, and evaluation.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.services.market_intelligence import MarketIntelligenceService


router = APIRouter(prefix="/market", tags=["market-intelligence"])


async def get_market_intelligence_service():
    async with MarketIntelligenceService() as service:
        yield service


@router.get("/intelligence/today", response_model=dict)
async def get_today_market_intelligence(
    limit: int = Query(default=5, ge=1, le=10),
    service: MarketIntelligenceService = Depends(get_market_intelligence_service),
):
    """Get the most important current event-linked stock ideas."""
    try:
        return await service.build_today_report(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/news/search", response_model=dict)
async def search_market_news(
    query: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(default=10, ge=1, le=25),
    service: MarketIntelligenceService = Depends(get_market_intelligence_service),
):
    """Search financial and technology news and link the stories to stocks."""
    try:
        return await service.search_news(query=query, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/predictions/scoreboard", response_model=dict)
async def get_prediction_scoreboard(
    days: int = Query(default=90, ge=7, le=365),
    service: MarketIntelligenceService = Depends(get_market_intelligence_service),
):
    """Get event-linked idea evaluation accuracy and recent history."""
    try:
        return await service.scoreboard(days=days)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
