"""
Unit tests for monitoring service subsystem health.
"""

import pytest

from app.services.monitoring import MonitoringService


class MissingDataFetcher:
    async def get_stock_quote(self, symbol: str):
        return None

    async def get_historical_data(self, symbol: str, days: int = 30):
        return []

    async def get_company_info(self, symbol: str):
        return None


class FailingResearchService:
    async def predict(self, symbol: str):
        raise RuntimeError("prediction failed")


class FakePrediction:
    def to_api(self):
        return {
            "coverage": {
                "status": "partial",
                "nonDemoSignalCount": 1,
                "activeSignalFamilies": ["trend"],
            },
            "dataQuality": {"status": "mixed"},
            "degradedReasons": ["Fewer than two non-demo signal families are available."],
        }


class PartialResearchService:
    async def predict(self, symbol: str):
        return FakePrediction()


@pytest.mark.asyncio
async def test_observability_health_is_idle_on_fresh_boot():
    service = MonitoringService()
    check = await service._check_observability_health()
    assert check.status == "idle"
    assert check.details["recentMetricsCount"] == 0


@pytest.mark.asyncio
async def test_data_health_is_unhealthy_when_all_core_market_components_are_missing():
    service = MonitoringService()
    service.data_fetcher = MissingDataFetcher()

    check = await service._check_data_fetcher_health()
    assert check.status == "unhealthy"
    assert check.details["availableComponents"] == {
        "quote": False,
        "historical": False,
        "companyInfo": False,
    }


@pytest.mark.asyncio
async def test_research_health_is_unhealthy_on_prediction_failure():
    service = MonitoringService()
    service.research_service = FailingResearchService()

    check = await service._check_research_prediction_health()
    assert check.status == "unhealthy"
    assert "prediction failed" in check.error_message


@pytest.mark.asyncio
async def test_research_health_is_degraded_when_signal_coverage_is_partial():
    service = MonitoringService()
    service.research_service = PartialResearchService()

    check = await service._check_research_prediction_health()
    assert check.status == "degraded"
    assert check.details["nonDemoSignalCount"] == 1
