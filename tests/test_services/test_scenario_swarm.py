"""
Tests for the local scenario swarm aggregation.
"""

import pytest

from app.core.config import settings
from app.services.local_model_analysis import LocalModelAnalysisService
from app.services.scenario_swarm import ScenarioSwarmService


class StubLocalModelService(LocalModelAnalysisService):
    def __init__(self):
        super().__init__()
        self.provider = "ollama"
        self.model = "qwen3:4b"

    def enabled(self) -> bool:
        return True

    async def request_structured_json(self, **kwargs):
        prompt = kwargs.get("user_prompt") or ""
        agent_name = prompt.split("AGENT:", 1)[1].splitlines()[0].strip()
        if agent_name == "risk":
            return {
                "stance": "mixed",
                "confidence": 0.66,
                "keyReason": "Near-term volatility is still elevated.",
                "whatChangesMyView": "Cleaner confirmation from the next session.",
                "nextSessionRisk": "Watch for momentum fading after the open.",
            }
        return {
            "stance": "supports",
            "confidence": 0.74,
            "keyReason": f"{agent_name} agrees with the available facts.",
            "whatChangesMyView": "A materially weaker data packet.",
            "nextSessionRisk": f"Watch {agent_name} follow-through.",
        }


@pytest.mark.asyncio
async def test_scenario_swarm_returns_deterministic_summary(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_SCENARIO_SWARM", True)
    monkeypatch.setattr(settings, "SCENARIO_SWARM_AGENT_COUNT", 4)

    service = ScenarioSwarmService(StubLocalModelService())
    result = await service.analyze_idea(
        {
            "symbol": "NVDA",
            "companyName": "NVIDIA Corporation",
            "direction": "up",
            "topic": "AI and Datacenter Buildout",
            "catalyst": "Datacenter demand remains elevated",
            "score": 88.0,
            "confidence": 0.81,
            "buyScore": 0.76,
            "reasoning": ["AI demand remains strong"],
            "metrics": {
                "research21dProbability": 0.82,
                "research21dConfidence": 0.64,
                "peRatio": 34.0,
                "nonDemoEvidenceCount": 3,
            },
            "supportingEvidence": [
                {
                    "title": "AI demand story",
                    "summary": "GPU demand remains elevated.",
                    "source": "Yahoo Finance",
                    "url": "https://example.com/nvda-ai",
                    "confidence": 0.8,
                }
            ],
        }
    )

    assert result["scenarioVerdict"] in {"supports", "mixed"}
    assert result["agentCount"] == 4
    assert len(result["agents"]) == 4
    assert result["supportScore"] >= 0.5
    assert "Scenario swarm" in result["summary"]
