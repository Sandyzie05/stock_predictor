"""
Monitoring and validation service for tracking prediction accuracy and system performance.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.prediction_engine import PredictionType
from app.services.real_data_fetcher import RealDataFetcherService
from app.services.research_prediction import ResearchPredictionService


class MetricType(Enum):
    """Types of metrics to track."""

    PREDICTION_ACCURACY = "prediction_accuracy"
    API_RESPONSE_TIME = "api_response_time"
    DATA_FRESHNESS = "data_freshness"
    SERVICE_AVAILABILITY = "service_availability"
    PREDICTION_CONFIDENCE = "prediction_confidence"


@dataclass
class PredictionAccuracyMetric:
    """Tracks prediction accuracy over time."""

    symbol: str
    prediction_date: datetime
    prediction_type: PredictionType
    prediction_confidence: Decimal
    target_price: Optional[Decimal]
    actual_price: Optional[Decimal] = None
    accuracy_date: Optional[datetime] = None
    accuracy_score: Optional[Decimal] = None
    is_correct: Optional[bool] = None
    horizon_days: int = 7


@dataclass
class SystemMetric:
    """General system performance metric."""

    metric_type: MetricType
    value: Decimal
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheck:
    """System health check result."""

    service_name: str
    status: str  # "healthy", "degraded", "unhealthy", "idle"
    response_time_ms: Optional[Decimal] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)


class MonitoringService:
    """Service for monitoring system performance and prediction accuracy."""

    def __init__(self):
        self.data_fetcher: Optional[RealDataFetcherService] = None
        self.research_service: Optional[ResearchPredictionService] = None

        self.prediction_metrics: List[PredictionAccuracyMetric] = []
        self.system_metrics: List[SystemMetric] = []
        self.health_checks: List[HealthCheck] = []

    async def __aenter__(self):
        self.data_fetcher = RealDataFetcherService()
        self.research_service = ResearchPredictionService()

        await self.data_fetcher.__aenter__()
        await self.research_service.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.research_service:
            await self.research_service.__aexit__(exc_type, exc_val, exc_tb)
        if self.data_fetcher:
            await self.data_fetcher.__aexit__(exc_type, exc_val, exc_tb)

    async def track_prediction(
        self,
        symbol: str,
        prediction_type: PredictionType,
        confidence: Decimal,
        target_price: Optional[Decimal] = None,
        horizon_days: int = 7,
    ) -> None:
        """Track a new prediction for later accuracy validation."""
        if not self.data_fetcher:
            raise RuntimeError("Service must be used as async context manager")

        metric = PredictionAccuracyMetric(
            symbol=symbol,
            prediction_date=datetime.now(),
            prediction_type=prediction_type,
            prediction_confidence=confidence,
            target_price=target_price,
            horizon_days=horizon_days,
        )

        self.prediction_metrics.append(metric)

    async def validate_predictions(self) -> Dict[str, Any]:
        """Validate past predictions against actual market data."""
        if not self.data_fetcher:
            raise RuntimeError("Service must be used as async context manager")

        validation_results = {
            "total_predictions": len(self.prediction_metrics),
            "validated_predictions": 0,
            "correct_predictions": 0,
            "accuracy_rate": 0.0,
            "by_symbol": {},
            "by_confidence_range": {},
        }

        current_time = datetime.now()
        for metric in self.prediction_metrics:
            if (current_time - metric.prediction_date).days < metric.horizon_days:
                continue
            if metric.is_correct is not None:
                continue

            try:
                quote = await self.data_fetcher.get_stock_quote(metric.symbol)
                if not quote:
                    continue

                metric.actual_price = quote.price
                metric.accuracy_date = current_time

                if metric.prediction_type == PredictionType.BUY:
                    if metric.target_price:
                        metric.is_correct = quote.price >= metric.target_price
                        metric.accuracy_score = min(
                            Decimal("100"),
                            (quote.price / metric.target_price) * Decimal("100"),
                        )
                    else:
                        metric.is_correct = True
                        metric.accuracy_score = Decimal("80")
                elif metric.prediction_type == PredictionType.SELL:
                    if metric.target_price:
                        metric.is_correct = quote.price <= metric.target_price
                        metric.accuracy_score = min(
                            Decimal("100"),
                            (metric.target_price / quote.price) * Decimal("100"),
                        )
                    else:
                        metric.is_correct = True
                        metric.accuracy_score = Decimal("80")
                else:
                    metric.is_correct = True
                    metric.accuracy_score = Decimal("70")

                validation_results["validated_predictions"] += 1
                if metric.is_correct:
                    validation_results["correct_predictions"] += 1
            except Exception:
                continue

        if validation_results["validated_predictions"] > 0:
            validation_results["accuracy_rate"] = (
                validation_results["correct_predictions"]
                / validation_results["validated_predictions"]
            )
        return validation_results

    async def run_health_checks(self) -> List[HealthCheck]:
        """Run comprehensive health checks on all services."""
        health_results = [
            await self._check_api_health(),
            await self._check_data_fetcher_health(),
            await self._check_research_prediction_health(),
            await self._check_observability_health(),
        ]
        self.health_checks.extend(health_results)
        return health_results

    async def _check_api_health(self) -> HealthCheck:
        """API layer is healthy if the route is executing and dependencies initialized."""
        details = {
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "docsEnabled": bool(settings.DEBUG),
            "dependenciesInitialized": bool(self.data_fetcher and self.research_service),
        }
        status = "healthy" if details["dependenciesInitialized"] else "degraded"
        return HealthCheck(service_name="APIService", status=status, details=details)

    async def _check_data_fetcher_health(self) -> HealthCheck:
        """Check live market data service health."""
        start_time = datetime.now()
        try:
            if not self.data_fetcher:
                return HealthCheck(
                    service_name="RealDataFetcherService",
                    status="unhealthy",
                    error_message="Service not initialized",
                )

            quote = await self.data_fetcher.get_stock_quote("AAPL")
            historical = await self.data_fetcher.get_historical_data("AAPL", 30)
            company = await self.data_fetcher.get_company_info("AAPL")

            response_time = (datetime.now() - start_time).total_seconds() * 1000
            available_components = {
                "quote": quote is not None,
                "historical": bool(historical),
                "companyInfo": company is not None,
            }
            score = sum(int(value) for value in available_components.values())
            status = "healthy" if score == 3 else "degraded" if score >= 1 else "unhealthy"

            return HealthCheck(
                service_name="RealDataFetcherService",
                status=status,
                response_time_ms=Decimal(str(response_time)),
                details={
                    "test_symbol": "AAPL",
                    "availableComponents": available_components,
                    "quoteSourceReady": quote is not None,
                    "historyPoints": len(historical),
                },
                error_message=None if status != "unhealthy" else "No market data returned.",
            )
        except Exception as exc:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return HealthCheck(
                service_name="RealDataFetcherService",
                status="unhealthy",
                response_time_ms=Decimal(str(response_time)),
                error_message=str(exc),
            )

    async def _check_research_prediction_health(self) -> HealthCheck:
        """Check research prediction health and signal coverage."""
        start_time = datetime.now()
        try:
            if not self.research_service:
                return HealthCheck(
                    service_name="ResearchPredictionService",
                    status="unhealthy",
                    error_message="Service not initialized",
                )

            prediction = await self.research_service.predict("AAPL")
            payload = prediction.to_api()
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            non_demo_signal_count = payload["coverage"]["nonDemoSignalCount"]
            if non_demo_signal_count >= 2:
                status = "healthy"
            elif non_demo_signal_count == 1:
                status = "degraded"
            else:
                status = "unhealthy"

            return HealthCheck(
                service_name="ResearchPredictionService",
                status=status,
                response_time_ms=Decimal(str(response_time)),
                details={
                    "test_symbol": "AAPL",
                    "coverageStatus": payload["coverage"]["status"],
                    "nonDemoSignalCount": non_demo_signal_count,
                    "activeSignalFamilies": payload["coverage"]["activeSignalFamilies"],
                    "dataQualityStatus": payload["dataQuality"]["status"],
                    "degradedReasons": payload["degradedReasons"],
                },
                error_message=None if status != "unhealthy" else "No non-demo signal families available.",
            )
        except Exception as exc:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return HealthCheck(
                service_name="ResearchPredictionService",
                status="unhealthy",
                response_time_ms=Decimal(str(response_time)),
                error_message=str(exc),
            )

    async def _check_observability_health(self) -> HealthCheck:
        """Check internal telemetry health without punishing a fresh dev boot."""
        try:
            recent_metrics = [
                metric
                for metric in self.system_metrics
                if (datetime.now() - metric.timestamp).seconds < 3600
            ]
            recent_predictions = [
                metric
                for metric in self.prediction_metrics
                if (datetime.now() - metric.prediction_date).days < 7
            ]
            details = {
                "recentMetricsCount": len(recent_metrics),
                "recentPredictionsCount": len(recent_predictions),
                "totalMetrics": len(self.system_metrics),
                "totalPredictions": len(self.prediction_metrics),
                "environment": settings.ENVIRONMENT,
            }
            status = "healthy" if (recent_metrics or recent_predictions) else "idle"
            return HealthCheck(
                service_name="ObservabilityTelemetry",
                status=status,
                details=details,
            )
        except Exception as exc:
            return HealthCheck(
                service_name="ObservabilityTelemetry",
                status="unhealthy",
                error_message=str(exc),
            )

    def record_metric(
        self,
        metric_type: MetricType,
        value: Decimal,
        unit: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a system performance metric."""
        metric = SystemMetric(
            metric_type=metric_type,
            value=value,
            unit=unit,
            context=context or {},
        )
        self.system_metrics.append(metric)

        cutoff_time = datetime.now() - timedelta(hours=24)
        self.system_metrics = [
            metric for metric in self.system_metrics if metric.timestamp > cutoff_time
        ]

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        recent_time = datetime.now() - timedelta(hours=1)
        recent_metrics = [
            metric for metric in self.system_metrics if metric.timestamp > recent_time
        ]
        recent_predictions = [
            metric
            for metric in self.prediction_metrics
            if metric.prediction_date > recent_time
        ]
        validated_predictions = [
            metric for metric in self.prediction_metrics if metric.is_correct is not None
        ]
        correct_predictions = [
            metric for metric in validated_predictions if metric.is_correct
        ]

        return {
            "monitoring_summary": {
                "total_metrics": len(self.system_metrics),
                "recent_metrics": len(recent_metrics),
                "total_predictions": len(self.prediction_metrics),
                "recent_predictions": len(recent_predictions),
                "validated_predictions": len(validated_predictions),
                "prediction_accuracy": (
                    len(correct_predictions) / len(validated_predictions)
                    if validated_predictions
                    else 0.0
                ),
            },
            "service_health": "monitoring_active",
            "last_health_check": self.health_checks[-1].timestamp.isoformat()
            if self.health_checks
            else None,
        }
