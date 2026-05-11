"""
API tests for market intelligence routes.
"""

from fastapi.testclient import TestClient

from app.api.routes.market import (get_daily_prediction_report_service,
                                   get_market_intelligence_service)
from app.main import app


class FakeMarketIntelligenceService:
    async def build_today_report(self, limit: int = 5):
        return {
            "asOf": "2026-05-08T00:00:00",
            "majorStories": [{"title": "AI datacenter spending rises", "linkedStocks": [{"symbol": "NVDA"}]}],
            "topBullish": [{"symbol": "NVDA", "direction": "up", "score": 88.0, "action": "buy", "dailyRating": "A"}],
            "topBearish": [{"symbol": "NOW", "direction": "down", "score": 66.0, "action": "avoid", "dailyRating": "D"}],
            "scoreboard": {"totalIdeas": 6, "pendingIdeas": 6, "recentIdeas": []},
            "summary": {"buyCount": 1, "watchCount": 0, "avoidCount": 1},
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

    async def daily_prediction_report(self, days: int = 30):
        return {
            "overall": {"accuracyPct": 60.0, "evaluatedPredictions": 5, "systemRating": "B"},
            "todayPredictions": [
                {
                    "symbol": "NVDA",
                    "action": "buy",
                    "dailyRating": "A",
                    "supportingEvidence": [
                        {"url": "https://example.com/nvda-ai", "title": "AI demand story"}
                    ],
                    "scenarioSwarm": {
                        "scenarioVerdict": "supports",
                        "supportScore": 0.74,
                        "agentCount": 4,
                    },
                }
            ],
            "recentEvaluations": [],
            "narrative": ["Recent evaluated calls are improving versus the prior window."],
            "exportColumns": ["report_date", "symbol", "action"],
        }


class FakeDailyPredictionReportService:
    async def export_rows(self, days: int = 30):
        return ["row"]

    def export_columns(self):
        return ["report_date", "symbol", "action", "scenario_verdict"]

    def export_row_to_flat_dict(self, row):
        return {
            "report_date": "2026-05-10",
            "symbol": "NVDA",
            "action": "buy",
            "scenario_verdict": "supports",
        }


async def override_market_service():
    yield FakeMarketIntelligenceService()


async def override_daily_report_service():
    yield FakeDailyPredictionReportService()


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


def test_market_daily_prediction_report_endpoint():
    app.dependency_overrides[get_market_intelligence_service] = override_market_service
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/market/predictions/daily-report?days=30")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["overall"]["accuracyPct"] == 60.0
    assert payload["todayPredictions"][0]["supportingEvidence"][0]["url"].startswith(
        "https://example.com/"
    )
    assert payload["todayPredictions"][0]["action"] == "buy"
    assert payload["todayPredictions"][0]["scenarioSwarm"]["scenarioVerdict"] == "supports"


def test_market_daily_prediction_report_csv_endpoint():
    app.dependency_overrides[get_daily_prediction_report_service] = override_daily_report_service
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/market/predictions/daily-report.csv?days=30")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "report_date,symbol,action,scenario_verdict" in response.text
    assert "2026-05-10,NVDA,buy,supports" in response.text
