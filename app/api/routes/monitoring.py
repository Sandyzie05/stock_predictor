"""
Monitoring and system health API routes.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends

from app.services.monitoring import MonitoringService


router = APIRouter(prefix="/monitoring", tags=["monitoring"])


async def get_monitoring_service():
    """Dependency to get MonitoringService."""
    async with MonitoringService() as service:
        yield service


@router.get("/health", response_model=Dict[str, Any])
async def system_health_check(
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Get comprehensive system health status."""
    try:
        health_checks = await monitoring.run_health_checks()

        checks_by_name = {check.service_name: check for check in health_checks}
        subsystems = {
            "api": checks_by_name.get(
                "APIService",
                {"status": "unhealthy", "details": {"reason": "Missing API health check."}},
            ),
            "data": checks_by_name.get(
                "RealDataFetcherService",
                {"status": "unhealthy", "details": {"reason": "Missing data health check."}},
            ),
            "ml": checks_by_name.get(
                "ResearchPredictionService",
                {"status": "unhealthy", "details": {"reason": "Missing ML health check."}},
            ),
            "observability": checks_by_name.get(
                "ObservabilityTelemetry",
                {"status": "unhealthy", "details": {"reason": "Missing observability health check."}},
            ),
        }

        critical_statuses = [
            subsystem.status if hasattr(subsystem, "status") else subsystem["status"]
            for key, subsystem in subsystems.items()
            if key in {"api", "data", "ml"}
        ]
        overall_status = "healthy"
        if any(status == "unhealthy" for status in critical_statuses):
            overall_status = "unhealthy"
        elif any(status == "degraded" for status in critical_statuses):
            overall_status = "degraded"

        return {
            "overall_status": overall_status,
            "timestamp": health_checks[0].timestamp.isoformat() if health_checks else None,
            "subsystems": {
                key: {
                    "status": subsystem.status if hasattr(subsystem, "status") else subsystem["status"],
                    "details": subsystem.details if hasattr(subsystem, "details") else subsystem.get("details", {}),
                    "error": subsystem.error_message if hasattr(subsystem, "error_message") else subsystem.get("error"),
                    "response_time_ms": float(subsystem.response_time_ms)
                    if hasattr(subsystem, "response_time_ms") and subsystem.response_time_ms
                    else None,
                }
                for key, subsystem in subsystems.items()
            },
            "services": [
                {
                    "name": check.service_name,
                    "status": check.status,
                    "response_time_ms": float(check.response_time_ms) if check.response_time_ms else None,
                    "error": check.error_message,
                    "details": check.details,
                }
                for check in health_checks
            ]
        }
    except Exception as e:
        return {
            "overall_status": "unhealthy",
            "error": str(e),
            "services": []
        }


@router.get("/metrics", response_model=Dict[str, Any])
async def get_system_metrics(
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Get system performance metrics summary."""
    try:
        return monitoring.get_metrics_summary()
    except Exception as e:
        return {"error": str(e)}


@router.get("/predictions/accuracy", response_model=Dict[str, Any])
async def get_prediction_accuracy(
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Get prediction accuracy metrics."""
    try:
        return await monitoring.validate_predictions()
    except Exception as e:
        return {"error": str(e)}
