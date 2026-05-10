"""
Market intelligence routes for open news, event linkage, and evaluation.
"""

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.services.market_intelligence import MarketIntelligenceService
from app.services.daily_prediction_report import DailyPredictionReportService


router = APIRouter(prefix="/market", tags=["market-intelligence"])


async def get_market_intelligence_service():
    async with MarketIntelligenceService() as service:
        yield service


async def get_daily_prediction_report_service():
    async with MarketIntelligenceService() as service:
        if not service.daily_report_service:
            raise RuntimeError("Daily report service unavailable")
        yield service.daily_report_service


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


@router.get("/predictions/daily-report", response_model=dict)
async def get_daily_prediction_report(
    days: int = Query(default=30, ge=7, le=365),
    service: MarketIntelligenceService = Depends(get_market_intelligence_service),
):
    """Get a daily prediction report with evidence links and next-day outcomes."""
    try:
        return await service.daily_prediction_report(days=days)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/predictions/daily-report.csv", response_class=PlainTextResponse)
async def export_daily_prediction_report_csv(
    days: int = Query(default=30, ge=7, le=365),
    report_service: DailyPredictionReportService = Depends(
        get_daily_prediction_report_service
    ),
):
    """Export daily prediction report rows as CSV for Excel or external analysis."""
    try:
        rows = await report_service.export_rows(days=days)
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=report_service.export_columns(),
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(report_service.export_row_to_flat_dict(row))
        return output.getvalue()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
