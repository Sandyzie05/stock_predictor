"""
Tests for the source-aware research platform services.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.services.data_fetcher import NewsArticle, StockHistoricalData, StockQuote
from app.services.event_extractor import EventExtractionService
from app.services.research_models import EvidenceCard
from app.services.research_prediction import ResearchPredictionService
from app.services.source_registry import SourceRegistry
from app.services.theme_models import AIInfrastructureThemeModel


class FakeResearchFetcher:
    """Deterministic fetcher for research prediction tests."""

    async def get_stock_quote(self, symbol: str):
        return StockQuote(
            symbol=symbol,
            price=Decimal("120.00"),
            change=Decimal("1.50"),
            change_percent=Decimal("1.25"),
            volume=2_000_000,
            timestamp=datetime.utcnow(),
        )

    async def get_company_info(self, symbol: str):
        class Company:
            name = "NVIDIA Corporation"

        return Company()

    async def get_historical_data(self, symbol: str, days: int = 180):
        start = datetime.utcnow() - timedelta(days=30)
        return [
            StockHistoricalData(
                symbol=symbol,
                date=start + timedelta(days=index),
                open_price=Decimal(str(100 + index)),
                high=Decimal(str(101 + index)),
                low=Decimal(str(99 + index)),
                close=Decimal(str(100 + index)),
                volume=1_000_000 + (index * 1_000),
                adjusted_close=Decimal(str(100 + index)),
            )
            for index in range(30)
        ]

    async def get_news(self, symbol: str, limit: int = 5):
        return [
            NewsArticle(
                headline="AI datacenter demand drives GPU inference growth",
                summary="Hyperscaler infrastructure demand remains strong.",
                source="Demo",
                source_id="yahoo-finance-yfinance",
                source_type="live",
                url="https://example.com/ai-demand",
                published_at=datetime.utcnow(),
                symbols=[symbol],
                sentiment_label="positive",
            )
        ]


class DemoOnlyResearchFetcher:
    """Fetcher that only returns demo-style evidence."""

    async def get_stock_quote(self, symbol: str):
        return None

    async def get_company_info(self, symbol: str):
        return None

    async def get_historical_data(self, symbol: str, days: int = 180):
        return []

    async def get_news(self, symbol: str, limit: int = 5):
        return [
            NewsArticle(
                headline=f"{symbol} placeholder market update",
                summary="Synthetic headline used for explanation only.",
                source="Demo Feed",
                source_id="demo-news-generator",
                source_type="demo",
                published_at=datetime.utcnow(),
                symbols=[symbol],
                sentiment_label="positive",
            )
        ]


def test_source_registry_contains_core_sources():
    registry = SourceRegistry()
    source_ids = {source.source_id for source in registry.list_sources()}

    assert "yahoo-finance-yfinance" in source_ids
    assert "sec-edgar" in source_ids
    assert "gdelt" in source_ids
    assert "fred-alfred" in source_ids


def test_ai_infrastructure_theme_contains_required_layers():
    theme = AIInfrastructureThemeModel()
    theme_map = theme.get_theme_map()
    layers = {layer["layer"] for layer in theme_map["layers"]}

    assert "gpu-accelerator" in layers
    assert "foundry-manufacturing" in layers
    assert "datacenter-power-cooling" in layers
    assert "agentic-inference-software" in layers

    nvda = theme.get_exposures("NVDA")
    assert nvda
    assert nvda[0].score >= 0.9


def test_event_extractor_classifies_ai_demand():
    extractor = EventExtractionService()
    evidence = EvidenceCard(
        title="AI inference datacenter demand accelerates",
        summary="GPU and HBM demand remain elevated.",
        source="curated",
        source_id="test",
        source_type="curated",
        symbols=["NVDA"],
        themes=["ai-infrastructure"],
        sentiment="positive",
        confidence=0.8,
    )

    events = extractor.extract([evidence])

    assert len(events) == 1
    assert events[0].event_type == "ai_demand"
    assert events[0].direction == "demand_up"
    assert events[0].magnitude > 0.7


@pytest.mark.asyncio
async def test_research_prediction_includes_evidence_horizons_and_provenance():
    service = ResearchPredictionService()
    service.data_fetcher = FakeResearchFetcher()

    prediction = await service.predict("NVDA")
    payload = prediction.to_api()

    assert payload["symbol"] == "NVDA"
    assert payload["modelVersion"] == "research-v0.2.0"
    assert len(payload["horizons"]) == 3
    assert {item["horizon"] for item in payload["horizons"]} == {"5d", "21d", "63d"}
    assert payload["evidence"]
    assert payload["sourceProvenance"]
    assert payload["themeExposures"]
    assert payload["coverage"]["nonDemoSignalCount"] >= 2
    assert set(payload["signalBreakdown"].keys()) == {
        "trend",
        "theme",
        "news",
        "macro",
        "filings",
        "volatility",
    }
    assert "not financial advice" in payload["disclaimer"].lower()


@pytest.mark.asyncio
async def test_research_prediction_caps_demo_only_evidence_to_hold():
    service = ResearchPredictionService()
    service.data_fetcher = DemoOnlyResearchFetcher()

    prediction = await service.predict("ZZZZ")
    payload = prediction.to_api()

    assert payload["coverage"]["nonDemoSignalCount"] == 0
    assert any("demo news" in reason.lower() for reason in payload["degradedReasons"])
    assert all(item["recommendation"] == "hold" for item in payload["horizons"])
    assert all(item["confidence"] <= 0.35 for item in payload["horizons"])
