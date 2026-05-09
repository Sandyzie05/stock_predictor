"""
Convert evidence cards into typed market events.
"""

from typing import Iterable, List

from app.services.research_models import EvidenceCard, MarketEvent


class EventExtractionService:
    """Heuristic event extraction foundation for future news/filing adapters."""

    keyword_rules = [
        (
            "ai_demand",
            "demand_up",
            0.82,
            ["ai", "gpu", "inference", "agent", "datacenter", "data center", "hbm"],
        ),
        (
            "capex",
            "demand_up",
            0.72,
            ["capex", "capital expenditure", "infrastructure spending", "capacity expansion"],
        ),
        (
            "earnings",
            "margin_up",
            0.66,
            ["earnings", "revenue", "beat", "guidance", "margin"],
        ),
        (
            "supply_chain",
            "risk_up",
            0.68,
            ["shortage", "supply", "lead time", "packaging", "foundry"],
        ),
        (
            "regulation",
            "risk_up",
            0.7,
            ["export control", "tariff", "sanction", "regulation", "antitrust"],
        ),
        (
            "macro",
            "risk_up",
            0.58,
            ["fed", "inflation", "rates", "yield", "recession", "cpi"],
        ),
        (
            "product",
            "demand_up",
            0.56,
            ["launch", "partnership", "platform", "service", "product"],
        ),
    ]

    def extract(self, evidence_cards: Iterable[EvidenceCard]) -> List[MarketEvent]:
        events = []
        for evidence in evidence_cards:
            text = f"{evidence.title} {evidence.summary}".lower()
            event_type, direction, magnitude = self._classify(text, evidence)
            events.append(
                MarketEvent(
                    event_type=event_type,
                    direction=direction,
                    magnitude=magnitude,
                    symbols=evidence.symbols,
                    themes=evidence.themes,
                    evidence=evidence,
                )
            )
        return events

    def _classify(self, text: str, evidence: EvidenceCard) -> tuple[str, str, float]:
        for event_type, direction, magnitude, keywords in self.keyword_rules:
            if any(keyword in text for keyword in keywords):
                return event_type, self._adjust_direction(direction, evidence), magnitude
        return "risk" if evidence.sentiment == "negative" else "general", (
            "risk_up" if evidence.sentiment == "negative" else "neutral"
        ), 0.45

    def _adjust_direction(self, direction: str, evidence: EvidenceCard) -> str:
        if evidence.sentiment == "negative" and direction.endswith("_up"):
            if direction in {"demand_up", "margin_up"}:
                return direction.replace("_up", "_down")
        return direction
