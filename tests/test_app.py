"""
Tests for main application.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestMainApp:
    """Test main application endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Stock Predictor API"
        assert data["version"] == "1.0.0"

    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_docs_endpoint_in_debug(self, client):
        """Test docs endpoint availability (should be available in test mode)."""
        response = client.get("/docs")

        # In test mode with DEBUG=True, docs should be available
        assert response.status_code == 200

    def test_api_v1_prefix(self, client):
        """Test that API endpoints use v1 prefix."""
        # This will fail until we implement actual API endpoints
        # but tests the routing structure
        response = client.get("/api/v1/nonexistent")

        # Should get 404 (not found) rather than 500 (server error)
        # This confirms the routing is working
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_lifespan_startup(self):
        """Test application lifespan startup."""
        # Test that the app can start without errors
        # The lifespan function should create tables
        test_client = TestClient(app)

        # Just creating the test client should trigger startup
        response = test_client.get("/health")
        assert response.status_code == 200

        test_client.close()


class TestCORSMiddleware:
    """Test CORS middleware configuration."""

    def test_cors_headers_in_debug(self, client):
        """Test CORS headers in debug mode."""
        response = client.options("/", headers={"Origin": "http://localhost:3000"})

        # Should allow CORS in debug mode
        assert response.status_code == 200

    def test_preflight_request(self, client):
        """Test CORS preflight request."""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        }

        response = client.options("/", headers=headers)

        # Should handle preflight request
        assert response.status_code == 200


class TestTrustedHostMiddleware:
    """Test trusted host middleware."""

    def test_trusted_host_allows_request(self, client):
        """Test that requests are allowed in test mode."""
        # In debug mode, all hosts should be allowed
        response = client.get("/", headers={"Host": "testserver"})

        assert response.status_code == 200

    def test_custom_host_header(self, client):
        """Test custom host header."""
        response = client.get("/", headers={"Host": "custom-host.com"})

        # Should be allowed in debug mode
        assert response.status_code == 200


class TestApplicationConfiguration:
    """Test application configuration."""

    def test_app_title(self):
        """Test application title."""
        assert app.title == "Stock Predictor API"

    def test_app_description(self):
        """Test application description."""
        assert (
            app.description == "A comprehensive stock prediction and analysis service"
        )

    def test_app_version(self):
        """Test application version."""
        assert app.version == "1.0.0"

    def test_openapi_url_in_debug(self):
        """Test OpenAPI URL in debug mode."""
        # In debug mode, OpenAPI should be available
        assert app.openapi_url == "/openapi.json"
