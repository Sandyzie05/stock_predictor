"""
API tests for monitoring health subsystems.
"""

from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.routes.monitoring import get_monitoring_service
from app.main import app
from app.services.monitoring import HealthCheck


class FakeMonitoringService:
    async def run_health_checks(self):
        return [
            HealthCheck(
                service_name="APIService",
                status="healthy",
                response_time_ms=Decimal("10.0"),
                details={"dependenciesInitialized": True},
            ),
            HealthCheck(
                service_name="RealDataFetcherService",
                status="healthy",
                response_time_ms=Decimal("45.0"),
                details={"availableComponents": {"quote": True, "historical": True, "companyInfo": True}},
            ),
            HealthCheck(
                service_name="ResearchPredictionService",
                status="healthy",
                response_time_ms=Decimal("90.0"),
                details={"nonDemoSignalCount": 3, "activeSignalFamilies": ["trend", "theme", "news"]},
            ),
            HealthCheck(
                service_name="ObservabilityTelemetry",
                status="idle",
                details={"recentMetricsCount": 0, "recentPredictionsCount": 0},
            ),
        ]


async def override_monitoring_service():
    yield FakeMonitoringService()


def test_monitoring_health_exposes_subsystems_without_penalizing_idle_telemetry():
    app.dependency_overrides[get_monitoring_service] = override_monitoring_service
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/monitoring/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["overall_status"] == "healthy"
    assert data["subsystems"]["api"]["status"] == "healthy"
    assert data["subsystems"]["data"]["status"] == "healthy"
    assert data["subsystems"]["ml"]["status"] == "healthy"
    assert data["subsystems"]["observability"]["status"] == "idle"
