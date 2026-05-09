"""
Domain models for source-aware stock research predictions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class DataSourceProfile:
    """Metadata about a market, news, filing, or macro data source."""

    source_id: str
    name: str
    categories: List[str]
    access: str
    best_for: str
    caveats: str
    priority: int

    def to_api(self, source_type: str = "registry") -> dict:
        return {
            "sourceId": self.source_id,
            "name": self.name,
            "categories": self.categories,
            "access": self.access,
            "bestFor": self.best_for,
            "caveats": self.caveats,
            "priority": self.priority,
            "sourceType": source_type,
        }


@dataclass(frozen=True)
class EvidenceCard:
    """A source-backed fact, headline, filing note, or curated theme fact."""

    title: str
    summary: str
    source: str
    source_id: str
    source_type: str
    published_at: Optional[datetime] = None
    url: Optional[str] = None
    symbols: List[str] = field(default_factory=list)
    themes: List[str] = field(default_factory=list)
    sentiment: str = "neutral"
    confidence: float = 0.5

    def to_api(self) -> dict:
        return {
            "title": self.title,
            "summary": self.summary,
            "source": self.source,
            "sourceId": self.source_id,
            "sourceType": self.source_type,
            "publishedAt": self.published_at.isoformat()
            if self.published_at
            else None,
            "url": self.url,
            "symbols": self.symbols,
            "themes": self.themes,
            "sentiment": self.sentiment,
            "confidence": round(self.confidence, 4),
        }


@dataclass(frozen=True)
class MarketEvent:
    """Typed event extracted from an evidence card."""

    event_type: str
    direction: str
    magnitude: float
    symbols: List[str]
    themes: List[str]
    evidence: EvidenceCard

    def to_api(self) -> dict:
        return {
            "eventType": self.event_type,
            "direction": self.direction,
            "magnitude": round(self.magnitude, 4),
            "symbols": self.symbols,
            "themes": self.themes,
            "title": self.evidence.title,
            "sourceId": self.evidence.source_id,
        }


@dataclass(frozen=True)
class ThemeExposure:
    """Ticker-level exposure to a named investment theme."""

    theme_slug: str
    symbol: str
    company_name: str
    layer: str
    score: float
    drivers: List[str]
    bottlenecks: List[str]

    def to_api(self) -> dict:
        return {
            "themeSlug": self.theme_slug,
            "symbol": self.symbol,
            "companyName": self.company_name,
            "layer": self.layer,
            "score": round(self.score, 4),
            "drivers": self.drivers,
            "bottlenecks": self.bottlenecks,
        }


@dataclass(frozen=True)
class HorizonPrediction:
    """Research prediction for one forward horizon."""

    horizon: str
    recommendation: str
    probability_outperform: float
    expected_excess_return: float
    downside_risk: float
    confidence: float
    reasoning: List[str]

    def to_api(self) -> dict:
        return {
            "horizon": self.horizon,
            "recommendation": self.recommendation,
            "probabilityOutperform": round(self.probability_outperform, 4),
            "expectedExcessReturn": round(self.expected_excess_return, 4),
            "downsideRisk": round(self.downside_risk, 4),
            "confidence": round(self.confidence, 4),
            "reasoning": self.reasoning,
        }


@dataclass(frozen=True)
class ResearchPrediction:
    """Full source-aware research prediction response."""

    symbol: str
    company_name: str
    as_of: datetime
    model_version: str
    data_quality: dict
    source_provenance: List[dict]
    theme_exposures: List[ThemeExposure]
    events: List[MarketEvent]
    horizons: List[HorizonPrediction]
    risk_factors: List[str]
    evidence: List[EvidenceCard]
    coverage: dict
    degraded_reasons: List[str]
    signal_breakdown: dict
    disclaimer: str

    def to_api(self) -> dict:
        return {
            "symbol": self.symbol,
            "companyName": self.company_name,
            "asOf": self.as_of.isoformat(),
            "modelVersion": self.model_version,
            "dataQuality": self.data_quality,
            "sourceProvenance": self.source_provenance,
            "themeExposures": [item.to_api() for item in self.theme_exposures],
            "events": [item.to_api() for item in self.events],
            "horizons": [item.to_api() for item in self.horizons],
            "riskFactors": self.risk_factors,
            "evidence": [item.to_api() for item in self.evidence],
            "coverage": self.coverage,
            "degradedReasons": self.degraded_reasons,
            "signalBreakdown": self.signal_breakdown,
            "disclaimer": self.disclaimer,
        }
