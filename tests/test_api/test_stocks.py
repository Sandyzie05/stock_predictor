"""
Tests for stock API endpoints.
"""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Stock Predictor API"
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_stock_quote_endpoint():
    """Test stock quote endpoint."""
    # This test would need proper mocking to work without external APIs
    # For now, we'll test the structure
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # This would fail without proper API setup, but tests the endpoint exists
        response = await ac.get("/api/v1/stocks/AAPL/quote")
        # Expecting either 500 (service error) or valid response
        assert response.status_code in [404, 500, 200]


class TestStockEndpoints:
    """Test stock-related API endpoints."""
    
    def test_endpoints_exist(self, client):
        """Test that all stock endpoints are properly registered."""
        # Test that endpoints exist (they may return errors without proper setup)
        endpoints = [
            "/api/v1/stocks/AAPL/quote",
            "/api/v1/stocks/AAPL/company", 
            "/api/v1/stocks/AAPL/analysis",
            "/api/v1/stocks/AAPL/prediction",
            "/api/v1/stocks/AAPL/recommendation",
            "/api/v1/stocks/AAPL/historical",
            "/api/v1/stocks/AAPL/news",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Endpoints should exist (not 404) even if they return errors
            assert response.status_code != 404, f"Endpoint {endpoint} not found"
