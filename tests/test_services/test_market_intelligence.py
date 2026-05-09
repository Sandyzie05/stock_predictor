"""
Tests for topic-driven market intelligence.
"""

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.data_fetcher import CompanyInfo, StockQuote
from app.services.market_intelligence import MarketIntelligenceService


class FakeFetcher:
    async def get_stock_quote(self, symbol: str):
        return StockQuote(
            symbol=symbol,
            price=Decimal("100.0"),
            change=Decimal("1.5"),
            change_percent=Decimal("1.5"),
            volume=1000000,
            timestamp=datetime.utcnow(),
        )

    async def get_company_info(self, symbol: str):
        pe_ratio = {"NVDA": Decimal("34.0"), "VRT": Decimal("28.0"), "JPM": Decimal("13.0")}.get(symbol, Decimal("22.0"))
        price_to_book = {"NVDA": Decimal("16.0"), "VRT": Decimal("12.0"), "JPM": Decimal("1.8")}.get(symbol, Decimal("4.0"))
        return CompanyInfo(
            symbol=symbol,
            name=f"{symbol} Inc.",
            sector="Technology",
            market_cap=Decimal("500000000000"),
            pe_ratio=pe_ratio,
            price_to_book=price_to_book,
        )


class FakeResearchService:
    async def predict(self, symbol: str):
        if symbol in {"NVDA", "VRT"}:
            horizon = SimpleNamespace(
                horizon="21d",
                recommendation="strong_buy",
                probability_outperform=0.82,
                confidence=0.64,
            )
        else:
            horizon = SimpleNamespace(
                horizon="21d",
                recommendation="sell",
                probability_outperform=0.32,
                confidence=0.58,
            )
        return SimpleNamespace(
            horizons=[horizon],
            coverage={"activeSignalFamilies": ["trend", "theme", "news"]},
        )


class FakeTracker:
    async def evaluate_due_predictions(self, as_of):
        return {"evaluated": 0}

    async def record_market_ideas(self, as_of, ideas, horizon_days=5):
        return len(list(ideas))

    async def scoreboard(self, days=90):
        return {"totalIdeas": 4, "pendingIdeas": 4, "recentIdeas": []}


@pytest.mark.asyncio
async def test_build_today_report_links_news_to_stocks():
    service = MarketIntelligenceService()
    service.data_fetcher = FakeFetcher()
    service.research_service = FakeResearchService()
    service.tracker = FakeTracker()

    async def fake_search(query: str, limit: int):
        if "artificial intelligence" in query:
            return [
                {
                    "title": "AI datacenter expansion drives fresh server demand",
                    "publisher": "Yahoo Finance",
                    "link": "https://example.com/ai",
                    "providerPublishTime": int(datetime.utcnow().timestamp()),
                    "relatedTickers": ["NVDA", "VRT"],
                }
            ]
        if "federal reserve inflation" in query:
            return [
                {
                    "title": "Hotter inflation raises concern over higher rates",
                    "publisher": "Yahoo Finance",
                    "link": "https://example.com/fed",
                    "providerPublishTime": int(datetime.utcnow().timestamp()),
                    "relatedTickers": ["JPM"],
                }
            ]
        return []

    service._run_yfinance_search = fake_search  # type: ignore[method-assign]

    report = await service.build_today_report(limit=2)

    assert report["topBullish"]
    assert report["topBearish"]
    assert report["majorStories"]
    assert any(idea["symbol"] == "NVDA" for idea in report["topBullish"])
    assert any(story["linkedStocks"] for story in report["majorStories"])
    assert report["scoreboard"]["totalIdeas"] == 4
