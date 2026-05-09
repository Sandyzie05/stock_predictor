"""
Evidence-backed research prediction service.
"""

import asyncio
from datetime import datetime
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional

from app.services.event_extractor import EventExtractionService
from app.services.filing_signal_service import FilingSignalService
from app.services.macro_signal_service import MacroSignalService
from app.services.real_data_fetcher import RealDataFetcherService
from app.services.research_models import (
    EvidenceCard,
    HorizonPrediction,
    ResearchPrediction,
    ThemeExposure,
)
from app.services.source_registry import SourceRegistry
from app.services.theme_models import AIInfrastructureThemeModel


class ResearchPredictionService:
    """Generate source-aware research predictions for a stock symbol."""

    model_version = "research-v0.2.0"
    disclaimer = (
        "Research signal only; not financial advice. Predictions are probabilistic "
        "and can be wrong, especially when source coverage is degraded."
    )

    def __init__(self) -> None:
        self.data_fetcher: Optional[RealDataFetcherService] = None
        self.macro_service: Optional[MacroSignalService] = None
        self.filing_service: Optional[FilingSignalService] = None
        self.source_registry = SourceRegistry()
        self.theme_model = AIInfrastructureThemeModel()
        self.event_extractor = EventExtractionService()

    async def __aenter__(self):
        self.data_fetcher = RealDataFetcherService()
        await self.data_fetcher.__aenter__()
        self.macro_service = MacroSignalService(self.data_fetcher.session)
        self.filing_service = FilingSignalService(self.data_fetcher.session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.data_fetcher:
            await self.data_fetcher.__aexit__(exc_type, exc_val, exc_tb)

    async def predict(self, symbol: str) -> ResearchPrediction:
        if not self.data_fetcher:
            raise RuntimeError(
                "ResearchPredictionService must be used as async context manager"
            )

        symbol = symbol.upper()
        quote, company, historical, news, macro_snapshot, filing_snapshot = await asyncio.gather(
            self.data_fetcher.get_stock_quote(symbol),
            self.data_fetcher.get_company_info(symbol),
            self.data_fetcher.get_historical_data(symbol, 180),
            self.data_fetcher.get_news(symbol, 5),
            self._get_macro_snapshot(),
            self._get_filing_snapshot(symbol),
        )

        theme_exposures = self.theme_model.get_exposures(symbol)
        trend_score, volatility_score, history_notes = self._market_features(historical)
        evidence = self._build_evidence(
            symbol=symbol,
            theme_exposures=theme_exposures,
            news_articles=news,
            macro_snapshot=macro_snapshot,
            filing_snapshot=filing_snapshot,
        )
        directional_evidence = [card for card in evidence if card.source_type != "demo"]
        events = self.event_extractor.extract(directional_evidence)

        signal_breakdown = self._signal_breakdown(
            historical=historical,
            trend_score=trend_score,
            volatility_score=volatility_score,
            theme_exposures=theme_exposures,
            evidence=evidence,
            macro_snapshot=macro_snapshot,
            filing_snapshot=filing_snapshot,
        )
        coverage = self._coverage(signal_breakdown, evidence)
        degraded_reasons = self._degraded_reasons(
            quote=quote,
            historical=historical,
            signal_breakdown=signal_breakdown,
            coverage=coverage,
            macro_snapshot=macro_snapshot,
            filing_snapshot=filing_snapshot,
        )
        data_quality = self._data_quality(
            quote=quote,
            historical=historical,
            evidence=evidence,
            coverage=coverage,
            macro_snapshot=macro_snapshot,
            filing_snapshot=filing_snapshot,
            notes=history_notes,
        )
        horizons = self._build_horizons(
            trend_score=trend_score,
            volatility_score=volatility_score,
            signal_breakdown=signal_breakdown,
            coverage=coverage,
            event_count=len(events),
        )
        risk_factors = self._risk_factors(
            volatility_score=volatility_score,
            theme_exposures=theme_exposures,
            data_quality=data_quality,
            macro_snapshot=macro_snapshot,
            filing_snapshot=filing_snapshot,
        )

        return ResearchPrediction(
            symbol=symbol,
            company_name=company.name if company else f"{symbol} Corporation",
            as_of=datetime.utcnow(),
            model_version=self.model_version,
            data_quality=data_quality,
            source_provenance=self._source_provenance(
                evidence=evidence,
                quote_available=quote is not None,
                historical_available=bool(historical),
                macro_snapshot=macro_snapshot,
                filing_snapshot=filing_snapshot,
            ),
            theme_exposures=theme_exposures,
            events=events,
            horizons=horizons,
            risk_factors=risk_factors,
            evidence=evidence,
            coverage=coverage,
            degraded_reasons=degraded_reasons,
            signal_breakdown=signal_breakdown,
            disclaimer=self.disclaimer,
        )

    async def _get_macro_snapshot(self) -> Dict[str, Any]:
        if not self.macro_service:
            return {"available": False, "score": 0.0, "summary": "Macro service unavailable."}
        return await self.macro_service.get_macro_snapshot()

    async def _get_filing_snapshot(self, symbol: str) -> Dict[str, Any]:
        if not self.filing_service:
            return {
                "available": False,
                "score": 0.0,
                "symbol": symbol,
                "reason": "Filing service unavailable.",
            }
        return await self.filing_service.get_filing_snapshot(symbol)

    def _build_evidence(
        self,
        symbol: str,
        theme_exposures: List[ThemeExposure],
        news_articles: List,
        macro_snapshot: Dict[str, Any],
        filing_snapshot: Dict[str, Any],
    ) -> List[EvidenceCard]:
        evidence: List[EvidenceCard] = [
            self.theme_model.evidence_for(exposure) for exposure in theme_exposures
        ]

        if macro_snapshot.get("available"):
            evidence.append(
                EvidenceCard(
                    title="Macro regime context from FRED",
                    summary=macro_snapshot.get("summary")
                    or "Macro regime context is available.",
                    source="FRED",
                    source_id="fred-alfred",
                    source_type="official",
                    symbols=[symbol],
                    sentiment=self._sentiment_for_score(macro_snapshot.get("score", 0.0)),
                    confidence=0.72,
                )
            )

        if filing_snapshot.get("available"):
            latest_periodic = filing_snapshot.get("recentPeriodic")
            filing_notes = []
            if latest_periodic:
                filing_notes.append(
                    f"Latest periodic filing {latest_periodic['form']} was filed {latest_periodic['filingDate']}."
                )
            revenue_growth = filing_snapshot.get("ttmRevenueGrowth")
            if revenue_growth is not None:
                filing_notes.append(f"TTM revenue growth: {revenue_growth:.1f}%.")
            eps_growth = filing_snapshot.get("ttmDilutedEpsGrowth")
            if eps_growth is not None:
                filing_notes.append(f"TTM diluted EPS growth: {eps_growth:.1f}%.")
            if filing_notes:
                evidence.append(
                    EvidenceCard(
                        title="SEC filing context",
                        summary=" ".join(filing_notes),
                        source="SEC EDGAR",
                        source_id="sec-edgar",
                        source_type="official",
                        symbols=[symbol],
                        sentiment=firing_sentiment
                        if (firing_sentiment := filing_snapshot.get("sentiment"))
                        else "neutral",
                        confidence=0.84,
                    )
                )

        for article in news_articles[:5]:
            source_type = getattr(article, "source_type", "live")
            source_id = getattr(article, "source_id", "unknown-news-source")
            relevance_score = getattr(article, "relevance_score", None)
            confidence = self._article_confidence(article, source_type, relevance_score)
            evidence.append(
                EvidenceCard(
                    title=article.headline,
                    summary=article.summary or "No summary provided.",
                    source=article.source,
                    source_id=source_id,
                    source_type=source_type,
                    published_at=article.published_at,
                    url=article.url,
                    symbols=[symbol],
                    themes=[self.theme_model.theme_slug] if theme_exposures else [],
                    sentiment=article.sentiment_label,
                    confidence=confidence,
                )
            )

        if not evidence:
            evidence.append(
                EvidenceCard(
                    title="Limited research context available",
                    summary=(
                        "No AI infrastructure theme exposure or recent evidence was "
                        "available in the local source set."
                    ),
                    source="research-platform",
                    source_id="derived-limited-context",
                    source_type="derived",
                    symbols=[symbol],
                    sentiment="neutral",
                    confidence=0.3,
                )
            )

        return evidence

    def _market_features(self, historical) -> tuple[float, float, List[str]]:
        if not historical or len(historical) < 5:
            return 0.0, 0.5, ["Insufficient historical data; market features are neutral."]

        closes = [float(item.adjusted_close or item.close) for item in historical if item.close]
        if len(closes) < 5:
            return 0.0, 0.5, ["Historical data had too few valid close prices."]

        start_price = closes[0]
        end_price = closes[-1]
        raw_return = (end_price - start_price) / start_price if start_price else 0.0
        trend_score = self._clamp(raw_return * 3.0, -1.0, 1.0)

        returns = [
            (closes[index] - closes[index - 1]) / closes[index - 1]
            for index in range(1, len(closes))
            if closes[index - 1]
        ]
        daily_volatility = pstdev(returns) if len(returns) > 1 else 0.03
        volatility_score = self._clamp(daily_volatility * 16.0, 0.05, 1.0)
        return trend_score, volatility_score, []

    def _build_horizons(
        self,
        trend_score: float,
        volatility_score: float,
        signal_breakdown: Dict[str, Dict[str, Any]],
        coverage: Dict[str, Any],
        event_count: int,
    ) -> List[HorizonPrediction]:
        theme_score = signal_breakdown["theme"]["score"]
        news_score = signal_breakdown["news"]["score"]
        macro_score = signal_breakdown["macro"]["score"]
        filings_score = signal_breakdown["filings"]["score"]
        evidence_strength = self._clamp(
            coverage["nonDemoEvidenceCount"] / 8.0, 0.0, 1.0
        )

        horizons = []
        for horizon, multiplier, theme_weight in [
            ("5d", 0.75, 0.7),
            ("21d", 1.25, 1.0),
            ("63d", 1.85, 1.25),
        ]:
            signal = (
                0.5
                + (0.12 * trend_score)
                + (0.08 * news_score)
                + (0.15 * theme_score * theme_weight)
                + (0.06 * macro_score)
                + (0.06 * filings_score)
                + (0.03 * min(event_count, 5))
                - (0.09 * volatility_score)
            )
            probability = self._clamp(signal, 0.08, 0.92)
            confidence = self._clamp(
                0.3
                + (0.16 * evidence_strength)
                + (0.1 * theme_score)
                + (0.08 if abs(trend_score) > 0.05 else 0.0)
                + (0.04 * max(macro_score, 0.0))
                + (0.04 * max(filings_score, 0.0))
                - (0.08 * volatility_score),
                0.15,
                0.9,
            )

            if coverage["nonDemoSignalCount"] < 2:
                probability = self._clamp(probability, 0.42, 0.58)
                confidence = min(confidence, 0.45)

            if coverage["nonDemoSignalCount"] == 0:
                probability = 0.5
                confidence = min(confidence, 0.35)

            recommendation = self._recommendation(probability)
            if coverage["nonDemoSignalCount"] == 0:
                recommendation = "hold"

            expected_excess_return = (probability - 0.5) * 10.0 * multiplier
            downside_risk = self._clamp(
                0.28
                + (0.42 * volatility_score)
                - (0.08 * theme_score)
                - (0.03 * news_score)
                - (0.02 * filings_score),
                0.05,
                0.9,
            )

            horizons.append(
                HorizonPrediction(
                    horizon=horizon,
                    recommendation=recommendation,
                    probability_outperform=probability,
                    expected_excess_return=expected_excess_return,
                    downside_risk=downside_risk,
                    confidence=confidence,
                    reasoning=self._reasoning(
                        trend_score=trend_score,
                        signal_breakdown=signal_breakdown,
                        volatility_score=volatility_score,
                        coverage=coverage,
                    ),
                )
            )
        return horizons

    def _sentiment_score(self, evidence: List[EvidenceCard]) -> float:
        scores = []
        for card in evidence:
            if card.source_type == "demo":
                continue
            if card.sentiment == "positive":
                scores.append(1.0 * card.confidence)
            elif card.sentiment == "negative":
                scores.append(-1.0 * card.confidence)
            else:
                scores.append(0.0)
        return self._clamp(mean(scores) if scores else 0.0, -1.0, 1.0)

    def _recommendation(self, probability: float) -> str:
        if probability >= 0.72:
            return "strong_buy"
        if probability >= 0.57:
            return "buy"
        if probability <= 0.28:
            return "strong_sell"
        if probability <= 0.43:
            return "sell"
        return "hold"

    def _reasoning(
        self,
        trend_score: float,
        signal_breakdown: Dict[str, Dict[str, Any]],
        volatility_score: float,
        coverage: Dict[str, Any],
    ) -> List[str]:
        reasons = []
        if signal_breakdown["theme"]["score"] >= 0.6:
            reasons.append("Positive AI infrastructure theme exposure")
        if signal_breakdown["news"]["score"] > 0.1:
            reasons.append("Live or official news sentiment is net positive")
        elif signal_breakdown["news"]["score"] < -0.1:
            reasons.append("Live or official news sentiment is net negative")
        if signal_breakdown["macro"]["available"]:
            reasons.append(signal_breakdown["macro"]["summary"])
        if signal_breakdown["filings"]["available"]:
            reasons.append(signal_breakdown["filings"]["summary"])
        if trend_score > 0.08:
            reasons.append("Recent price trend is positive")
        elif trend_score < -0.08:
            reasons.append("Recent price trend is negative")
        if volatility_score > 0.65:
            reasons.append("Elevated volatility reduces confidence")
        if coverage["nonDemoSignalCount"] < 2:
            reasons.append("Signal coverage is still partial, so recommendations stay conservative")
        if not reasons:
            reasons.append("Signals are mixed or limited; keep recommendation conservative")
        return reasons[:5]

    def _signal_breakdown(
        self,
        historical,
        trend_score: float,
        volatility_score: float,
        theme_exposures: List[ThemeExposure],
        evidence: List[EvidenceCard],
        macro_snapshot: Dict[str, Any],
        filing_snapshot: Dict[str, Any],
    ) -> Dict[str, Dict[str, Any]]:
        theme_score = mean([item.score for item in theme_exposures]) if theme_exposures else 0.0
        news_cards = [
            card
            for card in evidence
            if card.source_id
            not in {"curated-ai-infrastructure-theme", "fred-alfred", "sec-edgar"}
        ]
        live_news_cards = [card for card in news_cards if card.source_type != "demo"]
        demo_news_cards = [card for card in news_cards if card.source_type == "demo"]
        news_score = self._sentiment_score(live_news_cards)

        filings_summary = "SEC filing context unavailable."
        if filing_snapshot.get("available"):
            latest_periodic = filing_snapshot.get("recentPeriodic")
            filings_summary = (
                f"Latest periodic filing {latest_periodic['form']} was filed "
                f"{latest_periodic['filingDate']}."
                if latest_periodic
                else "SEC filings available but no recent periodic filing was summarized."
            )
        elif filing_snapshot.get("reason"):
            filings_summary = filing_snapshot["reason"]

        news_summary = "No live news evidence available."
        if live_news_cards:
            news_summary = f"{len(live_news_cards)} live or official news items scored."
        elif demo_news_cards:
            news_summary = "Only demo news is available; it is excluded from directional scoring."

        return {
            "trend": {
                "available": bool(historical and len(historical) >= 5),
                "score": round(trend_score, 4),
                "summary": "Price trend derived from recent adjusted closes."
                if historical
                else "Historical market data unavailable.",
            },
            "theme": {
                "available": bool(theme_exposures),
                "score": round(theme_score, 4),
                "summary": f"{len(theme_exposures)} AI theme exposures mapped."
                if theme_exposures
                else "No curated AI infrastructure exposure mapped for this ticker.",
            },
            "news": {
                "available": bool(live_news_cards),
                "score": round(news_score, 4),
                "summary": news_summary,
            },
            "macro": {
                "available": bool(macro_snapshot.get("available")),
                "score": round(float(macro_snapshot.get("score", 0.0)), 4),
                "summary": macro_snapshot.get("summary")
                or macro_snapshot.get("reason")
                or "Macro regime context unavailable.",
            },
            "filings": {
                "available": bool(filing_snapshot.get("available")),
                "score": round(float(filing_snapshot.get("score", 0.0)), 4),
                "summary": filings_summary,
            },
            "volatility": {
                "available": bool(historical and len(historical) >= 5),
                "score": round(volatility_score, 4),
                "summary": "Volatility estimated from daily returns."
                if historical
                else "Volatility neutral because historical data is unavailable.",
            },
        }

    def _coverage(
        self, signal_breakdown: Dict[str, Dict[str, Any]], evidence: List[EvidenceCard]
    ) -> Dict[str, Any]:
        counted_families = ["trend", "theme", "news", "macro", "filings"]
        active_families = [
            family for family in counted_families if signal_breakdown[family]["available"]
        ]
        non_demo_evidence_count = sum(1 for card in evidence if card.source_type != "demo")
        demo_evidence_count = sum(1 for card in evidence if card.source_type == "demo")
        status = "complete"
        if len(active_families) < 2:
            status = "partial" if active_families else "limited"

        return {
            "status": status,
            "signalFamiliesConsidered": counted_families,
            "activeSignalFamilies": active_families,
            "nonDemoSignalCount": len(active_families),
            "evidenceCount": len(evidence),
            "nonDemoEvidenceCount": non_demo_evidence_count,
            "demoEvidenceCount": demo_evidence_count,
        }

    def _degraded_reasons(
        self,
        quote,
        historical,
        signal_breakdown: Dict[str, Dict[str, Any]],
        coverage: Dict[str, Any],
        macro_snapshot: Dict[str, Any],
        filing_snapshot: Dict[str, Any],
    ) -> List[str]:
        reasons = []
        if quote is None:
            reasons.append("Live quote unavailable.")
        if not historical:
            reasons.append("Historical market data unavailable.")
        if coverage["nonDemoSignalCount"] < 2:
            reasons.append(
                "Fewer than two non-demo signal families are available, so ML confidence is capped."
            )
        if (
            not signal_breakdown["news"]["available"]
            and coverage["demoEvidenceCount"] > 0
        ):
            reasons.append("Only demo news is available; it does not contribute to directional scoring.")
        if not macro_snapshot.get("available") and macro_snapshot.get("reason"):
            reasons.append(macro_snapshot["reason"])
        if not filing_snapshot.get("available") and filing_snapshot.get("reason"):
            reasons.append(filing_snapshot["reason"])
        return reasons

    def _data_quality(
        self,
        quote,
        historical,
        evidence: List[EvidenceCard],
        coverage: Dict[str, Any],
        macro_snapshot: Dict[str, Any],
        filing_snapshot: Dict[str, Any],
        notes: List[str],
    ) -> Dict[str, Any]:
        live_components = int(quote is not None) + int(bool(historical))
        if any(card.source_type == "live" for card in evidence):
            live_components += 1
        if macro_snapshot.get("available"):
            live_components += 1
        if filing_snapshot.get("available"):
            live_components += 1

        if live_components >= 4 and coverage["nonDemoSignalCount"] >= 2:
            status = "live"
        elif live_components >= 2:
            status = "mixed"
        else:
            status = "degraded"

        quality_notes = list(notes)
        if quote is None:
            quality_notes.append("Live quote unavailable.")
        if not historical:
            quality_notes.append("Historical market data unavailable.")
        if coverage["demoEvidenceCount"] > 0:
            quality_notes.append("Demo news is present for explanation only and is excluded from directional scoring.")
        if not macro_snapshot.get("available") and macro_snapshot.get("reason"):
            quality_notes.append(macro_snapshot["reason"])
        if not filing_snapshot.get("available") and filing_snapshot.get("reason"):
            quality_notes.append(filing_snapshot["reason"])
        return {
            "status": status,
            "notes": quality_notes,
            "liveComponents": live_components,
            "demoEvidenceCount": coverage["demoEvidenceCount"],
        }

    def _source_provenance(
        self,
        evidence: List[EvidenceCard],
        quote_available: bool,
        historical_available: bool,
        macro_snapshot: Dict[str, Any],
        filing_snapshot: Dict[str, Any],
    ) -> List[dict]:
        source_ids = {card.source_id for card in evidence}
        if quote_available or historical_available:
            source_ids.add("yahoo-finance-yfinance")
        if macro_snapshot.get("available"):
            source_ids.add("fred-alfred")
        if filing_snapshot.get("available"):
            source_ids.add("sec-edgar")

        provenance = self.source_registry.provenance_for(source_ids)
        if any(card.source_id == "curated-ai-infrastructure-theme" for card in evidence):
            provenance.append(
                {
                    "sourceId": "curated-ai-infrastructure-theme",
                    "name": "Curated AI infrastructure theme model",
                    "sourceType": "curated",
                    "caveats": "Human-curated MVP mapping; later versions should derive exposure from filings, news, and supply-chain data.",
                }
            )
        if any(card.source_id == "demo-news-generator" for card in evidence):
            provenance.append(
                {
                    "sourceId": "demo-news-generator",
                    "name": "Local demo news generator",
                    "sourceType": "demo",
                    "caveats": "Synthetic placeholder news used until a real news adapter is configured.",
                }
            )
        return provenance

    def _risk_factors(
        self,
        volatility_score: float,
        theme_exposures: List[ThemeExposure],
        data_quality: dict,
        macro_snapshot: Dict[str, Any],
        filing_snapshot: Dict[str, Any],
    ) -> List[str]:
        risks = []
        for exposure in theme_exposures:
            risks.extend(exposure.bottlenecks[:2])
        if theme_exposures:
            risks.extend(["AI capex digestion risk", "valuation compression risk"])
        if macro_snapshot.get("available") and macro_snapshot.get("score", 0.0) < 0:
            risks.append("macro regime remains somewhat restrictive")
        if filing_snapshot.get("available"):
            latest_filing = filing_snapshot.get("latestFiling")
            if latest_filing and latest_filing.get("daysAgo", 0) > 180:
                risks.append("latest SEC filing is stale")
        if volatility_score > 0.6:
            risks.append("elevated realized volatility")
        if data_quality["status"] != "live":
            risks.append("degraded or mixed source coverage")

        deduped = []
        for risk in risks:
            if risk not in deduped:
                deduped.append(risk)
        return deduped or ["limited evidence coverage"]

    @staticmethod
    def _article_confidence(article, source_type: str, relevance_score: Optional[Any]) -> float:
        if source_type == "demo":
            return 0.22

        base_confidence = 0.58 if source_type == "live" else 0.7
        if getattr(article, "sentiment_label", "neutral") != "neutral":
            base_confidence += 0.07
        if relevance_score is not None:
            try:
                base_confidence += min(float(relevance_score), 1.0) * 0.1
            except (TypeError, ValueError):
                pass
        return max(0.3, min(base_confidence, 0.9))

    @staticmethod
    def _sentiment_for_score(score: float) -> str:
        if score >= 0.12:
            return "positive"
        if score <= -0.12:
            return "negative"
        return "neutral"

    @staticmethod
    def _clamp(value: float, lower: float, upper: float) -> float:
        return max(lower, min(upper, value))
