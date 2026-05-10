"""
Tests for daily prediction snapshot reporting.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.services.daily_prediction_report import DailyPredictionReportService
from app.services.data_fetcher import StockHistoricalData, StockQuote


class FakeFetcher:
    """Deterministic price history for next-day evaluation tests."""

    def __init__(self, as_of: datetime):
        self.as_of = as_of

    async def get_stock_quote(self, symbol: str):
        prices = {
            "NVDA": Decimal("100.00"),
            "NOW": Decimal("200.00"),
            "SPY": Decimal("500.00"),
        }
        price = prices.get(symbol)
        if price is None:
            return None
        return StockQuote(
            symbol=symbol,
            price=price,
            change=Decimal("0"),
            change_percent=Decimal("0"),
            volume=1_000_000,
            timestamp=self.as_of,
        )

    async def get_historical_data(self, symbol: str, days: int = 10):
        baseline = self.as_of.replace(hour=0, minute=0, second=0, microsecond=0)
        day_two = baseline + timedelta(days=1)
        prices = {
            "NVDA": [Decimal("100.00"), Decimal("103.00")],
            "NOW": [Decimal("200.00"), Decimal("204.00")],
            "SPY": [Decimal("500.00"), Decimal("501.00")],
        }
        symbol_prices = prices.get(symbol)
        if symbol_prices is None:
            return []

        return [
            StockHistoricalData(
                symbol=symbol,
                date=baseline + timedelta(days=index),
                open_price=price,
                high=price,
                low=price,
                close=price,
                volume=1_000_000,
                adjusted_close=price,
            )
            for index, price in enumerate(symbol_prices)
        ]


@pytest.mark.asyncio
async def test_daily_prediction_report_tracks_outcomes_and_evidence(
    monkeypatch
):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    monkeypatch.setattr(
        "app.services.daily_prediction_report.AsyncSessionLocal",
        session_factory,
    )

    as_of = datetime(2026, 5, 8, 14, 30)
    service = DailyPredictionReportService(FakeFetcher(as_of))
    created = await service.record_predictions(
        as_of,
        [
            {
                "symbol": "NVDA",
                "companyName": "NVIDIA Corporation",
                "direction": "up",
                "topic": "AI and Datacenter Buildout",
                "catalyst": "AI server demand remains elevated",
                "score": 88.0,
                "confidence": 0.78,
                "currentPrice": 100.0,
                "reasoning": ["Strong AI demand", "Positive research alignment"],
                "metrics": {"research21dProbability": 0.82},
                "sourceIds": ["yahoo-finance-yfinance", "sec-edgar"],
                "supportingEvidence": [
                    {
                        "title": "AI datacenter demand drives GPU inference growth",
                        "source": "Yahoo Finance",
                        "sourceId": "yahoo-finance-yfinance",
                        "url": "https://example.com/nvda-ai",
                    }
                ],
                "localModelAnalysis": {
                    "provider": "ollama",
                    "model": "qwen3:4b",
                    "verdict": "supports",
                    "thesisSummary": "The supplied evidence supports continued AI demand.",
                },
            },
            {
                "symbol": "NOW",
                "companyName": "ServiceNow, Inc.",
                "direction": "down",
                "topic": "Rates, Inflation, and Fed Policy",
                "catalyst": "Higher-rate pressure on premium software multiples",
                "score": 63.0,
                "confidence": 0.61,
                "currentPrice": 200.0,
                "reasoning": ["Macro headwind", "Rich multiple risk"],
                "metrics": {"research21dProbability": 0.35},
                "sourceIds": ["fred-alfred"],
                "supportingEvidence": [
                    {
                        "title": "Inflation concern pushes yields higher",
                        "source": "FRED",
                        "sourceId": "fred-alfred",
                        "url": "https://example.com/rates",
                    }
                ],
            },
        ],
    )

    assert created == 2

    evaluation_time = as_of + timedelta(days=2)
    evaluated = await service.evaluate_due_predictions(evaluation_time)
    assert evaluated["evaluated"] == 2

    report = await service.report(days=30, as_of=evaluation_time)

    assert report["overall"]["evaluatedPredictions"] == 2
    assert report["overall"]["accuracyPct"] == 50.0
    assert report["overall"]["systemRating"] == "C"
    assert report["overall"]["averageBenchmarkReturnPct"] == 0.2
    assert report["reportDate"] == evaluation_time.date().isoformat()
    assert "action" in report["exportColumns"]
    assert report["recentEvaluations"]
    assert report["recentEvaluations"][0]["supportingEvidence"]
    assert report["recentEvaluations"][0]["supportingEvidence"][0]["url"].startswith(
        "https://example.com/"
    )
    analyzed = next(
        item for item in report["recentEvaluations"] if item["symbol"] == "NVDA"
    )
    assert analyzed["localModelAnalysis"]["verdict"] == "supports"
    assert any("evidence links" in line.lower() for line in report["narrative"])

    await engine.dispose()
