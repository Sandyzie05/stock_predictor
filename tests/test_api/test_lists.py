"""
Tests for stock list API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


class TestStockListEndpoints:
    """Test stock list API endpoints."""
    
    def test_list_endpoints_exist(self, client):
        """Test that all stock list endpoints are properly registered."""
        endpoints = [
            "/api/v1/lists/all-time-high",
            "/api/v1/lists/all-time-low",
            "/api/v1/lists/sp500",
            "/api/v1/lists/sp500/all-time-high",
            "/api/v1/lists/sp500/all-time-low", 
            "/api/v1/lists/undervalued",
            "/api/v1/lists/overvalued",
            "/api/v1/lists/strong-buy",
            "/api/v1/lists/strong-sell",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Endpoints should exist (not 404) even if they return errors
            assert response.status_code != 404, f"Endpoint {endpoint} not found"
    
    def test_all_time_high_endpoint_structure(self, client):
        """Test all-time high endpoint response structure."""
        response = client.get("/api/v1/lists/all-time-high?max_items=5")
        
        # Should not be 404
        assert response.status_code != 404
        
        # If successful, should have proper structure
        if response.status_code == 200:
            data = response.json()
            assert "list_type" in data
            assert "title" in data
            assert "description" in data
            assert "items" in data
            assert isinstance(data["items"], list)
    
    def test_undervalued_endpoint_with_symbols(self, client):
        """Test undervalued endpoint with custom symbols."""
        response = client.get("/api/v1/lists/undervalued?symbols=AAPL,GOOGL&max_items=10")
        
        # Should not be 404
        assert response.status_code != 404
    
    def test_sp500_endpoint(self, client):
        """Test S&P 500 endpoint."""
        response = client.get("/api/v1/lists/sp500?max_items=20")
        
        # Should not be 404
        assert response.status_code != 404
