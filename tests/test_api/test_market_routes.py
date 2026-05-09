"""
API tests for market intelligence routes.
"""

from fastapi.testclient import TestClient

from app.api.routes.market import get_market_intelligence_service
from app.main import app


class FakeMarketIntelligenceService:
    async def build_today_report(self, limit: int = 5):
        return {
            "asOf": "2026-05-08T00:00:00",
            "majorStories": [{"title": "AI datacenter spending rises", "linkedStocks": [{"symbol": "NVDA"}]}],
            "topBullish": [{"symbol": "NVDA", "direction": "up", "score": 88.0}],
            "topBearish": [{"symbol": "NOW", "direction": "down", "score": 66.0}],
            "scoreboard": {"totalIdeas": 6, "pendingIdeas": 6, "recentIdeas": []},
            "sources": [{"sourceId": "yahoo-finance-yfinance"}],
            "disclaimer": "Research support only.",
        }

    async def search_news(self, query: str, limit: int = 10):
        return {
            "query": query,
            "count": 1,
            "results": [{"title": "Semiconductor export control story", "linkedStocks": [{"symbol": "NVDA"}]}],
        }

    async def scoreboard(self, days: int = 90):
        return {"totalIdeas": 4, "pendingIdeas": 2, "recentIdeas": []}


async def override_market_service():
    yield FakeMarketIntelligenceService()


def test_market_intelligence_today_endpoint():
    app.dependency_overrides[get_market_intelligence_service] = override_market_service
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/market/intelligence/today?limit=3")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["topBullish"][0]["symbol"] == "NVDA"
    assert payload["majorStories"]


def test_market_news_search_endpoint():
    app.dependency_overrides[get_market_intelligence_service] = override_market_service
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/market/news/search?query=semiconductors")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "semiconductors"
    assert payload["results"][0]["linkedStocks"][0]["symbol"] == "NVDA"


def test_market_prediction_scoreboard_endpoint():
    app.dependency_overrides[get_market_intelligence_service] = override_market_service
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/market/predictions/scoreboard?days=30")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["totalIdeas"] == 4
