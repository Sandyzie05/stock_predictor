"""
API tests for research prediction and theme routes.
"""

from fastapi.testclient import TestClient

from app.api.routes.stocks import get_research_prediction_service
from app.main import app


class FakePrediction:
    def to_api(self):
        return {
            "symbol": "NVDA",
            "companyName": "NVIDIA Corporation",
            "asOf": "2026-05-07T00:00:00",
            "modelVersion": "research-v0.2.0",
            "dataQuality": {"status": "mixed", "notes": []},
            "sourceProvenance": [{"sourceId": "test", "name": "Test"}],
            "themeExposures": [{"themeSlug": "ai-infrastructure", "score": 1.0}],
            "events": [{"eventType": "ai_demand", "direction": "demand_up"}],
            "horizons": [
                {"horizon": "5d", "recommendation": "buy"},
                {"horizon": "21d", "recommendation": "buy"},
                {"horizon": "63d", "recommendation": "buy"},
            ],
            "riskFactors": ["valuation compression risk"],
            "evidence": [{"title": "AI infrastructure exposure"}],
            "coverage": {
                "status": "complete",
                "activeSignalFamilies": ["trend", "theme", "news"],
                "nonDemoSignalCount": 3,
            },
            "degradedReasons": [],
            "signalBreakdown": {
                "trend": {"available": True, "score": 0.5},
                "theme": {"available": True, "score": 1.0},
                "news": {"available": True, "score": 0.3},
                "macro": {"available": False, "score": 0.0},
                "filings": {"available": False, "score": 0.0},
                "volatility": {"available": True, "score": 0.2},
            },
            "disclaimer": "Research signal only; not financial advice.",
        }


class FakeResearchService:
    async def predict(self, symbol: str):
        return FakePrediction()


async def override_research_service():
    yield FakeResearchService()


def test_research_prediction_endpoint():
    app.dependency_overrides[get_research_prediction_service] = override_research_service
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/stocks/NVDA/research-prediction")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "NVDA"
    assert len(data["horizons"]) == 3
    assert data["evidence"]
    assert data["coverage"]["nonDemoSignalCount"] == 3
    assert "signalBreakdown" in data
    assert "not financial advice" in data["disclaimer"].lower()


def test_ai_infrastructure_theme_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/v1/themes/ai-infrastructure")

    assert response.status_code == 200
    data = response.json()
    layers = {layer["layer"] for layer in data["layers"]}
    assert data["themeSlug"] == "ai-infrastructure"
    assert "gpu-accelerator" in layers
    assert "datacenter-power-cooling" in layers
    assert data["exposures"]
    assert any(item["symbol"] == "NVDA" for item in data["exposures"])
    assert data["bottlenecks"]
    assert data["risks"]
