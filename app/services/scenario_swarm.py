"""
Small local-agent scenario swarm for stock ideas.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from app.core.config import settings
from app.services.local_model_analysis import LocalModelAnalysisService


@dataclass(frozen=True)
class ScenarioAgentProfile:
    name: str
    system_prompt: str


class ScenarioSwarmService:
    """Run a handful of role-based local-agent reviews, then aggregate deterministically."""

    prompt_version = "scenario-swarm-v1"

    AGENTS: List[ScenarioAgentProfile] = [
        ScenarioAgentProfile(
            name="macro",
            system_prompt=(
                "You are the Macro Agent for a stock research tool. Use only the supplied facts. "
                "Evaluate whether current macro, rates, inflation, spending, policy, or broad market "
                "conditions support or weaken the proposed direction."
            ),
        ),
        ScenarioAgentProfile(
            name="sector",
            system_prompt=(
                "You are the Sector Agent for a stock research tool. Use only the supplied facts. "
                "Evaluate whether sector demand, competitive position, and theme fit support or weaken "
                "the proposed direction."
            ),
        ),
        ScenarioAgentProfile(
            name="supply-chain",
            system_prompt=(
                "You are the Supply Chain Agent for a stock research tool. Use only the supplied facts. "
                "Evaluate supplier, datacenter, distribution, capex, and operational dependencies that "
                "could support or weaken the proposed direction."
            ),
        ),
        ScenarioAgentProfile(
            name="risk",
            system_prompt=(
                "You are the Risk Agent for a stock research tool. Use only the supplied facts. "
                "Look for fragility, valuation pressure, contradictory evidence, and near-term downside "
                "risk that could invalidate the proposed direction."
            ),
        ),
        ScenarioAgentProfile(
            name="valuation",
            system_prompt=(
                "You are the Valuation Agent for a stock research tool. Use only the supplied facts. "
                "Evaluate whether the available valuation and score context leaves room for the proposed move."
            ),
        ),
        ScenarioAgentProfile(
            name="crowd-reaction",
            system_prompt=(
                "You are the Crowd Reaction Agent for a stock research tool. Use only the supplied facts. "
                "Evaluate whether the current headlines are likely to reinforce or fade in the next session."
            ),
        ),
    ]

    OPINION_SCHEMA = {
        "type": "object",
        "properties": {
            "stance": {
                "type": "string",
                "enum": ["supports", "mixed", "contradicts"],
            },
            "confidence": {"type": "number"},
            "keyReason": {"type": "string"},
            "whatChangesMyView": {"type": "string"},
            "nextSessionRisk": {"type": "string"},
        },
        "required": [
            "stance",
            "confidence",
            "keyReason",
            "whatChangesMyView",
            "nextSessionRisk",
        ],
    }

    STANCE_WEIGHT = {
        "supports": 1.0,
        "mixed": 0.0,
        "contradicts": -1.0,
    }

    def __init__(self, local_model_service: LocalModelAnalysisService) -> None:
        self.local_model_service = local_model_service

    def enabled(self) -> bool:
        return bool(
            settings.ENABLE_SCENARIO_SWARM
            and self.local_model_service
            and self.local_model_service.enabled()
        )

    async def analyze_idea(self, idea: Dict[str, Any]) -> Dict[str, Any]:
        """Ask a few specialized local agents to evaluate the same facts packet."""
        if not self.enabled():
            raise RuntimeError("Scenario swarm is not enabled.")

        packet = self._build_packet(idea)
        opinions: List[Dict[str, Any]] = []
        agent_count = min(
            max(settings.SCENARIO_SWARM_AGENT_COUNT, 1),
            len(self.AGENTS),
        )

        for profile in self.AGENTS[:agent_count]:
            parsed = await self.local_model_service.request_structured_json(
                system_prompt=profile.system_prompt,
                user_prompt=self._build_prompt(packet, profile.name),
                schema=self.OPINION_SCHEMA,
                prompt_version=f"{self.prompt_version}:{profile.name}",
                max_tokens=180,
                temperature=0.0,
            )
            opinions.append(
                {
                    "agentName": profile.name,
                    "stance": parsed.get("stance") or "mixed",
                    "confidence": self._clamp_score(parsed.get("confidence"), 0.55),
                    "keyReason": parsed.get("keyReason") or "No rationale provided.",
                    "whatChangesMyView": parsed.get("whatChangesMyView")
                    or "A materially different fact pattern.",
                    "nextSessionRisk": parsed.get("nextSessionRisk")
                    or "Watch for follow-through in the next session.",
                }
            )

        return self._aggregate(packet, opinions)

    def _build_packet(self, idea: Dict[str, Any]) -> Dict[str, Any]:
        evidence = []
        for item in (idea.get("supportingEvidence") or [])[:5]:
            evidence.append(
                {
                    "title": item.get("title"),
                    "summary": item.get("summary"),
                    "source": item.get("source"),
                    "publishedAt": item.get("publishedAt"),
                    "url": item.get("url"),
                    "confidence": item.get("confidence"),
                }
            )

        metrics = idea.get("metrics") or {}
        return {
            "symbol": idea.get("symbol"),
            "companyName": idea.get("companyName"),
            "direction": idea.get("direction"),
            "action": idea.get("action"),
            "topic": idea.get("topic"),
            "catalyst": idea.get("catalyst"),
            "score": idea.get("score"),
            "confidence": idea.get("confidence"),
            "buyScore": idea.get("buyScore"),
            "reasoning": (idea.get("reasoning") or [])[:4],
            "metrics": {
                "research21dProbability": metrics.get("research21dProbability"),
                "research21dConfidence": metrics.get("research21dConfidence"),
                "marketCapBillions": metrics.get("marketCapBillions"),
                "peRatio": metrics.get("peRatio"),
                "forwardPe": metrics.get("forwardPe"),
                "priceToBook": metrics.get("priceToBook"),
                "dayChangePct": metrics.get("dayChangePct"),
                "nonDemoEvidenceCount": metrics.get("nonDemoEvidenceCount"),
                "signalFamilies": metrics.get("signalFamilies"),
            },
            "supportingEvidence": evidence,
        }

    def _build_prompt(self, packet: Dict[str, Any], agent_name: str) -> str:
        return (
            "Review this stock idea using only the supplied packet.\n"
            "Do not add outside facts.\n"
            "Return concise JSON that matches the schema.\n"
            f"AGENT:{agent_name}\n"
            f"IDEA_PACKET:{json.dumps(packet, ensure_ascii=True)}"
        )

    def _aggregate(
        self,
        packet: Dict[str, Any],
        opinions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        total_confidence = sum(float(opinion["confidence"]) for opinion in opinions) or 1.0
        weighted_support = sum(
            self.STANCE_WEIGHT.get(str(opinion["stance"]), 0.0) * float(opinion["confidence"])
            for opinion in opinions
        )
        support_score = (weighted_support + total_confidence) / (2 * total_confidence)

        stance_weights = {
            stance: sum(
                float(opinion["confidence"])
                for opinion in opinions
                if opinion["stance"] == stance
            )
            for stance in self.STANCE_WEIGHT.keys()
        }
        majority_weight = max(stance_weights.values()) if stance_weights else 0.0
        disagreement_score = 1.0 - (majority_weight / total_confidence)
        fragility_score = min(
            1.0,
            sum(
                float(opinion["confidence"])
                * (
                    0.85
                    if opinion["stance"] == "contradicts"
                    else 0.55
                    if opinion["stance"] == "mixed"
                    else 0.18
                )
                for opinion in opinions
            )
            / total_confidence,
        )

        scenario_verdict = "mixed"
        if support_score >= 0.67 and disagreement_score <= 0.42:
            scenario_verdict = "supports"
        elif support_score <= 0.4 or (
            support_score < 0.5 and disagreement_score >= 0.45
        ):
            scenario_verdict = "contradicts"

        watch_next_session = self._dedupe_preserve_order(
            opinion["nextSessionRisk"] for opinion in opinions if opinion.get("nextSessionRisk")
        )[:4]
        summary = self._build_summary(
            packet.get("symbol") or "This idea",
            scenario_verdict,
            support_score,
            disagreement_score,
            fragility_score,
            opinions,
        )

        return {
            "provider": self.local_model_service.provider,
            "model": self.local_model_service.model,
            "promptVersion": self.prompt_version,
            "generatedAt": datetime.utcnow().isoformat(),
            "agentCount": len(opinions),
            "scenarioVerdict": scenario_verdict,
            "supportScore": round(support_score, 4),
            "disagreementScore": round(disagreement_score, 4),
            "fragilityScore": round(fragility_score, 4),
            "summary": summary,
            "watchNextSession": watch_next_session,
            "agents": opinions,
        }

    @staticmethod
    def _build_summary(
        symbol: str,
        scenario_verdict: str,
        support_score: float,
        disagreement_score: float,
        fragility_score: float,
        opinions: List[Dict[str, Any]],
    ) -> str:
        strongest = max(opinions, key=lambda item: float(item["confidence"]), default=None)
        if strongest is None:
            return f"{symbol} has no scenario review yet."
        verdict_text = {
            "supports": "supports the call",
            "mixed": "is split on the call",
            "contradicts": "leans against the call",
        }[scenario_verdict]
        return (
            f"Scenario swarm {verdict_text} for {symbol}: support {support_score:.2f}, "
            f"disagreement {disagreement_score:.2f}, fragility {fragility_score:.2f}. "
            f"Strongest view came from {strongest['agentName']}: {strongest['keyReason']}"
        )

    @staticmethod
    def _clamp_score(value: Any, default: float) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return default
        return max(0.0, min(score, 1.0))

    @staticmethod
    def _dedupe_preserve_order(items) -> List[str]:
        seen = set()
        ordered: List[str] = []
        for item in items:
            normalized = str(item).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            ordered.append(normalized)
        return ordered
