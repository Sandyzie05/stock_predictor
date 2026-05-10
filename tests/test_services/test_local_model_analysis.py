"""
Tests for the OpenAI-compatible local model analysis client.
"""

import pytest

from app.core.config import settings
from app.services.local_model_analysis import LocalModelAnalysisService


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    def raise_for_status(self):
        return None

    async def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload

    def post(self, url, json):
        return FakeResponse(self.payload)


@pytest.mark.asyncio
async def test_local_model_analysis_parses_openai_compatible_response(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LOCAL_LLM", True)
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "openai-compatible")
    monkeypatch.setattr(settings, "LOCAL_LLM_BASE_URL", "http://macmini2.local:11434/v1")
    monkeypatch.setattr(settings, "LOCAL_LLM_MODEL", "qwen3:4b")

    service = LocalModelAnalysisService()
    service.session = FakeSession(
        {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"thesisSummary":"Evidence supports the bullish thesis.",'
                            '"verdict":"supports","keySupport":["Demand signal"],'
                            '"keyRisks":["Valuation"],"confidenceAdjustment":"increase",'
                            '"watchNextSession":["Datacenter capex headlines"]}'
                        )
                    }
                }
            ]
        }
    )

    result = await service.analyze_prediction(
        {
            "symbol": "NVDA",
            "companyName": "NVIDIA Corporation",
            "direction": "up",
            "supportingEvidence": [
                {
                    "title": "AI demand remains strong",
                    "source": "Yahoo Finance",
                    "url": "https://example.com/story",
                }
            ],
        }
    )

    assert result["provider"] == "openai-compatible"
    assert result["model"] == "qwen3:4b"
    assert result["verdict"] == "supports"
    assert result["confidenceAdjustment"] == "increase"


@pytest.mark.asyncio
async def test_local_model_analysis_parses_ollama_native_response(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_LOCAL_LLM", True)
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "LOCAL_LLM_BASE_URL", "http://macmini2.local:11434/v1")
    monkeypatch.setattr(settings, "LOCAL_LLM_MODEL", "qwen3:4b")

    service = LocalModelAnalysisService()
    service.session = FakeSession(
        {
            "message": {
                "content": (
                    '{"thesisSummary":"Evidence supports the bullish thesis.",'
                    '"verdict":"supports","keySupport":["Demand signal"],'
                    '"keyRisks":["Valuation"],"confidenceAdjustment":"increase",'
                    '"watchNextSession":["Datacenter capex headlines"]}'
                )
            }
        }
    )

    result = await service.analyze_prediction({"symbol": "NVDA"})

    assert result["provider"] == "ollama"
    assert result["verdict"] == "supports"
