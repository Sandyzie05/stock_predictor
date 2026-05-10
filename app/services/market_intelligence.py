"""
Topic-driven market intelligence built from open news and live market data.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.core.config import settings
from app.services.daily_prediction_report import DailyPredictionReportService
from app.services.event_extractor import EventExtractionService
from app.services.local_model_analysis import LocalModelAnalysisService
from app.services.prediction_tracker import PredictionTrackerService
from app.services.real_data_fetcher import RealDataFetcherService
from app.services.report_clock import next_reset, report_day, report_now
from app.services.research_models import EvidenceCard
from app.services.research_prediction import ResearchPredictionService
from app.services.runtime_cache import TTLCache
from app.services.source_registry import SourceRegistry
from app.services.theme_models import AIInfrastructureThemeModel

try:
    import yfinance as yf
except ImportError:  # pragma: no cover - runtime dependency
    yf = None


@dataclass(frozen=True)
class TopicProfile:
    slug: str
    label: str
    query: str
    bullish_if_positive: List[str]
    bearish_if_positive: List[str]
    bullish_if_negative: List[str]
    bearish_if_negative: List[str]
    sectors: List[str]
    keywords: List[str]


class MarketIntelligenceService:
    """Aggregates open news, maps events to stocks, and tracks the results."""

    _report_cache = TTLCache()
    _search_cache = TTLCache()

    TOPIC_PROFILES: List[TopicProfile] = [
        TopicProfile(
            slug="ai-datacenter",
            label="AI and Datacenter Buildout",
            query="artificial intelligence datacenter",
            bullish_if_positive=["NVDA", "AVGO", "ANET", "VRT", "ETN", "MSFT", "AMZN", "NOW", "DDOG"],
            bearish_if_positive=[],
            bullish_if_negative=[],
            bearish_if_negative=["NVDA", "AVGO", "ANET", "VRT", "SMCI", "AMD"],
            sectors=["technology", "industrials", "utilities"],
            keywords=["ai", "datacenter", "gpu", "inference", "agent", "server"],
        ),
        TopicProfile(
            slug="chip-trade",
            label="Semiconductor Trade and Export Controls",
            query="semiconductor export controls",
            bullish_if_positive=["INTC", "GFS", "AMAT"],
            bearish_if_positive=["NVDA", "AMD", "TSM", "ASML", "AAPL"],
            bullish_if_negative=["NVDA", "AMD", "TSM", "ASML"],
            bearish_if_negative=["INTC", "GFS"],
            sectors=["technology", "industrials"],
            keywords=["semiconductor", "export", "tariff", "foundry", "smuggled", "chip"],
        ),
        TopicProfile(
            slug="rates-inflation",
            label="Rates, Inflation, and Fed Policy",
            query="federal reserve inflation",
            bullish_if_positive=["HD", "LOW", "DHI", "MA", "V", "PYPL", "AAPL", "AMZN"],
            bearish_if_positive=["JPM", "BAC", "BRK.B"],
            bullish_if_negative=["JPM", "BAC", "BRK.B", "XOM"],
            bearish_if_negative=["HD", "LOW", "DHI", "NOW", "PLTR", "AMZN"],
            sectors=["financials", "consumer", "housing", "technology"],
            keywords=["fed", "inflation", "rates", "mortgage", "yield", "cpi"],
        ),
        TopicProfile(
            slug="energy-supply",
            label="Oil, Shipping, and Global Supply",
            query="oil supply opec shipping disruption",
            bullish_if_positive=["XOM", "CVX", "SLB", "HAL"],
            bearish_if_positive=["DAL", "UAL", "FDX", "UPS", "AAL"],
            bullish_if_negative=["DAL", "UAL", "FDX", "UPS"],
            bearish_if_negative=["XOM", "CVX"],
            sectors=["energy", "transport", "industrials"],
            keywords=["oil", "opec", "shipping", "supply", "crude", "disruption"],
        ),
        TopicProfile(
            slug="cybersecurity",
            label="Cybersecurity and Platform Resilience",
            query="cybersecurity breach enterprise software",
            bullish_if_positive=["CRWD", "PANW", "ZS", "NET", "DDOG"],
            bearish_if_positive=[],
            bullish_if_negative=[],
            bearish_if_negative=["NOW", "CRM", "MSFT", "ORCL"],
            sectors=["technology"],
            keywords=["cybersecurity", "breach", "ransomware", "outage", "hack"],
        ),
        TopicProfile(
            slug="geopolitics-defense",
            label="Defense and Geopolitics",
            query="defense spending geopolitics",
            bullish_if_positive=["RTX", "LMT", "NOC", "GD"],
            bearish_if_positive=[],
            bullish_if_negative=[],
            bearish_if_negative=["DAL", "UAL", "BKNG"],
            sectors=["industrials", "travel"],
            keywords=["defense", "missile", "war", "conflict", "geopolitics"],
        ),
    ]

    def __init__(self):
        self.data_fetcher: Optional[RealDataFetcherService] = None
        self.research_service: Optional[ResearchPredictionService] = None
        self.theme_model = AIInfrastructureThemeModel()
        self.event_extractor = EventExtractionService()
        self.source_registry = SourceRegistry()
        self.tracker: Optional[PredictionTrackerService] = None
        self.daily_report_service: Optional[DailyPredictionReportService] = None
        self.local_model_service: Optional[LocalModelAnalysisService] = None

    async def __aenter__(self):
        self.data_fetcher = RealDataFetcherService()
        self.research_service = ResearchPredictionService()
        self.local_model_service = LocalModelAnalysisService()
        await self.data_fetcher.__aenter__()
        await self.research_service.__aenter__()
        if self.local_model_service.enabled():
            await self.local_model_service.__aenter__()
        self.tracker = PredictionTrackerService(self.data_fetcher)
        self.daily_report_service = DailyPredictionReportService(self.data_fetcher)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.local_model_service and self.local_model_service.enabled():
            await self.local_model_service.__aexit__(exc_type, exc_val, exc_tb)
        if self.research_service:
            await self.research_service.__aexit__(exc_type, exc_val, exc_tb)
        if self.data_fetcher:
            await self.data_fetcher.__aexit__(exc_type, exc_val, exc_tb)

    async def build_today_report(self, limit: int = 5) -> Dict[str, Any]:
        """Return a report of the most important current event-linked stock ideas."""
        if not self.data_fetcher or not self.research_service or not self.tracker:
            raise RuntimeError("MarketIntelligenceService must be used as async context manager")

        local_now = report_now()
        report_date = local_now.date().isoformat()
        cache_key = f"today-report:{report_date}:{limit}"
        cached = self._report_cache.get(cache_key)
        if cached is not None:
            return cached

        as_of = local_now
        topic_results = await asyncio.gather(
            *[self._search_topic_news(topic, limit=6) for topic in self.TOPIC_PROFILES]
        )
        stories = self._dedupe_stories(
            [story for bucket in topic_results for story in bucket]
        )
        stories.sort(key=lambda story: story["impactScore"], reverse=True)

        scorebook = {"up": defaultdict(list), "down": defaultdict(list)}
        for story in stories:
            self._accumulate_story_scores(story, scorebook)

        bullish_ranked = await self._rank_stock_ideas(
            scorebook["up"], direction="up", limit=max(limit * 2, 8)
        )
        bearish_ranked = await self._rank_stock_ideas(
            scorebook["down"], direction="down", limit=max(limit * 2, 8)
        )
        bullish, bearish = self._separate_conflicts(
            bullish_ranked, bearish_ranked, limit=limit
        )
        await self._attach_local_model_analysis([*bullish, *bearish])
        self._finalize_recommendations([*bullish, *bearish])

        await self.tracker.evaluate_due_predictions(as_of)
        await self.tracker.record_market_ideas(as_of, [*bullish, *bearish], horizon_days=5)
        if self.daily_report_service:
            await self.daily_report_service.record_predictions(
                as_of, [*bullish, *bearish], horizon_days=1
            )
        scoreboard = await self.tracker.scoreboard(days=90)

        report = {
            "asOf": as_of.isoformat(),
            "reportDate": report_date,
            "resetAt": next_reset(as_of).isoformat(),
            "majorStories": stories[: min(10, len(stories))],
            "topBullish": bullish,
            "topBearish": bearish,
            "scoreboard": scoreboard,
            "summary": self._daily_summary([*bullish, *bearish], scoreboard),
            "sources": self.source_registry.provenance_for(
                ["yahoo-finance-yfinance", "alpha-vantage", "sec-edgar", "fred-alfred"]
            ),
            "decisionMethod": {
                "mode": "deterministic-scoring-plus-structured-llm-review",
                "description": (
                    "Current-event stories and market data are scored first; the local model only evaluates "
                    "the prepared dataset and nudges the final buy/watch/avoid action."
                ),
            },
            "dataFreshness": {
                "reportTimezone": settings.REPORT_TIMEZONE,
                "cacheTtlSeconds": settings.MARKET_INTELLIGENCE_CACHE_TTL_SECONDS,
                "datasetPolicy": (
                    "Current-event stories are refreshed on demand and by the background refresher. "
                    "Daily recommendation snapshots reset at local midnight."
                ),
            },
            "disclaimer": (
                "This feed links current events to market-sensitive stocks using open data "
                "and heuristic scoring. It is for research support, not a promise of future performance."
            ),
        }
        return self._report_cache.set(
            cache_key, report, settings.MARKET_INTELLIGENCE_CACHE_TTL_SECONDS
        )

    async def search_news(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search open market news and link stories to relevant stocks."""
        cache_key = f"news-search:{query.lower()}:{limit}"
        cached = self._search_cache.get(cache_key)
        if cached is not None:
            return cached

        raw_items = await self._run_yfinance_search(query, limit)
        stories = [
            self._build_story_dict(
                item,
                topic=TopicProfile(
                    slug="custom-search",
                    label="Custom Search",
                    query=query,
                    bullish_if_positive=[],
                    bearish_if_positive=[],
                    bullish_if_negative=[],
                    bearish_if_negative=[],
                    sectors=[],
                    keywords=query.lower().split(),
                ),
            )
            for item in raw_items
        ]
        stories = self._dedupe_stories(stories)
        return self._search_cache.set(
            cache_key,
            {
                "query": query,
                "asOf": report_now().isoformat(),
                "results": stories[:limit],
                "count": len(stories[:limit]),
            },
            settings.NEWS_CACHE_TTL_SECONDS,
        )

    async def scoreboard(self, days: int = 90) -> Dict[str, Any]:
        if not self.tracker:
            raise RuntimeError("MarketIntelligenceService must be used as async context manager")
        await self.tracker.evaluate_due_predictions(datetime.utcnow())
        return await self.tracker.scoreboard(days)

    async def daily_prediction_report(self, days: int = 30) -> Dict[str, Any]:
        """Return a daily prediction quality report with evidence links."""
        if not self.daily_report_service:
            raise RuntimeError("MarketIntelligenceService must be used as async context manager")
        await self.build_today_report(limit=5)
        return await self.daily_report_service.report(days=days, as_of=datetime.utcnow())

    async def _search_topic_news(
        self, topic: TopicProfile, limit: int = 6
    ) -> List[Dict[str, Any]]:
        raw_items = await self._run_yfinance_search(topic.query, limit)
        return [self._build_story_dict(item, topic) for item in raw_items]

    async def _run_yfinance_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        if yf is None:
            return []

        def _search() -> List[Dict[str, Any]]:
            search = yf.Search(query, news_count=limit)
            return list(getattr(search, "news", None) or [])

        try:
            return await asyncio.to_thread(_search)
        except Exception as exc:
            print(f"yfinance search error for '{query}': {exc}")
            return []

    def _build_story_dict(self, item: Dict[str, Any], topic: TopicProfile) -> Dict[str, Any]:
        title = item.get("title") or topic.label
        related_tickers = [symbol.upper() for symbol in item.get("relatedTickers") or []]
        published_at = self._from_unix(item.get("providerPublishTime"))

        evidence = EvidenceCard(
            title=title,
            summary=f"{topic.label} headline linked to current market themes.",
            source=item.get("publisher") or "Yahoo Finance",
            source_id="yahoo-finance-yfinance",
            source_type="live",
            published_at=published_at,
            url=item.get("link"),
            symbols=related_tickers,
            themes=[topic.slug],
            sentiment=self._infer_sentiment(title),
            confidence=0.62,
        )
        event = self.event_extractor.extract([evidence])[0]
        sentiment = evidence.sentiment
        linked_stocks = self._linked_stocks_for_story(topic, title, related_tickers, sentiment)
        impact_score = self._story_impact_score(sentiment, related_tickers, published_at)

        return {
            "title": title,
            "source": evidence.source,
            "sourceId": evidence.source_id,
            "url": evidence.url,
            "publishedAt": published_at.isoformat(),
            "topic": topic.label,
            "topicSlug": topic.slug,
            "sentiment": sentiment,
            "eventType": event.event_type,
            "directionalBias": "up" if sentiment == "positive" else "down" if sentiment == "negative" else "mixed",
            "impactScore": round(impact_score, 4),
            "relatedTickers": related_tickers,
            "linkedStocks": linked_stocks[:8],
            "sectors": topic.sectors,
        }

    def _linked_stocks_for_story(
        self,
        topic: TopicProfile,
        title: str,
        related_tickers: List[str],
        sentiment: str,
    ) -> List[Dict[str, Any]]:
        text = title.lower()
        stock_links: List[Dict[str, Any]] = []

        if related_tickers:
            for symbol in related_tickers:
                stock_links.append(
                    {
                        "symbol": symbol,
                        "reason": self._direct_mention_reason(topic, symbol),
                        "score": 0.9,
                        "specificity": 1,
                    }
                )

        if sentiment == "positive":
            bullish = topic.bullish_if_positive
            bearish = topic.bearish_if_positive
        elif sentiment == "negative":
            bullish = topic.bullish_if_negative
            bearish = topic.bearish_if_negative
        else:
            bullish = topic.bullish_if_positive
            bearish = topic.bearish_if_negative

        for symbol in bullish:
            stock_links.append(
                {
                    "symbol": symbol,
                    "reason": self._topic_link_reason(topic, symbol, sentiment, "beneficiary"),
                    "score": 0.72,
                    "specificity": 2,
                }
            )
        for symbol in bearish:
            stock_links.append(
                {
                    "symbol": symbol,
                    "reason": self._topic_link_reason(topic, symbol, sentiment, "pressured"),
                    "score": 0.62,
                    "specificity": 2,
                }
            )

        if any(keyword in text for keyword in ["ai", "inference", "datacenter", "data center", "gpu"]):
            for exposure in self.theme_model.get_theme_map()["exposures"]:
                if exposure["score"] >= 0.78:
                    stock_links.append(
                        {
                            "symbol": exposure["symbol"],
                            "reason": self._theme_exposure_reason(exposure),
                            "score": float(exposure["score"]),
                            "specificity": 3,
                        }
                    )

        deduped: Dict[str, Dict[str, Any]] = {}
        for link in stock_links:
            symbol = link["symbol"]
            previous = deduped.get(symbol)
            if previous is None:
                deduped[symbol] = {
                    "symbol": symbol,
                    "score": round(float(link["score"]), 4),
                    "reasonFragments": [link["reason"]],
                    "topSpecificity": int(link["specificity"]),
                    "reason": link["reason"],
                }
                continue

            previous["score"] = round(max(float(previous["score"]), float(link["score"])), 4)
            if link["reason"] not in previous["reasonFragments"]:
                previous["reasonFragments"].append(link["reason"])
            previous["reasonFragments"] = sorted(
                previous["reasonFragments"],
                key=lambda fragment: (
                    -self._reason_specificity(previous["symbol"], fragment),
                    fragment,
                ),
            )
            previous["topSpecificity"] = max(previous["topSpecificity"], int(link["specificity"]))
            previous["reason"] = self._compose_link_reason(previous["reasonFragments"])

        return sorted(deduped.values(), key=lambda item: item["score"], reverse=True)

    def _direct_mention_reason(self, topic: TopicProfile, symbol: str) -> str:
        return f"{symbol} is explicitly mentioned in current {topic.label.lower()} coverage"

    def _topic_link_reason(
        self,
        topic: TopicProfile,
        symbol: str,
        sentiment: str,
        relation: str,
    ) -> str:
        exposure = self._top_theme_exposure(symbol)
        if relation == "beneficiary":
            base = f"{symbol} screens as a likely beneficiary of {topic.label.lower()}"
        else:
            base = f"{symbol} screens as more exposed if {topic.label.lower()} worsens"

        if exposure:
            layer = exposure.layer.replace("-", " ")
            driver = exposure.drivers[0] if exposure.drivers else None
            if driver:
                return f"{base} through its {layer} role and {driver.lower()} driver"
            return f"{base} through its {layer} role"

        if sentiment == "positive" and relation == "beneficiary":
            return base
        return base

    def _theme_exposure_reason(self, exposure: Dict[str, Any]) -> str:
        layer = str(exposure.get("layer") or "theme exposure").replace("-", " ")
        drivers = exposure.get("drivers") or []
        driver = str(drivers[0]).lower() if drivers else None
        symbol = exposure.get("symbol") or "This stock"
        if driver:
            return f"{symbol} has strong AI infrastructure exposure via {layer}, tied to {driver}"
        return f"{symbol} has strong AI infrastructure exposure via {layer}"

    def _top_theme_exposure(self, symbol: str):
        exposures = self.theme_model.get_exposures(symbol)
        if not exposures:
            return None
        return max(exposures, key=lambda item: item.score)

    @staticmethod
    def _compose_link_reason(reason_fragments: List[str]) -> str:
        if not reason_fragments:
            return "Linked to the current market story"
        if len(reason_fragments) == 1:
            return reason_fragments[0]
        return f"{reason_fragments[0]}; also {reason_fragments[1]}"

    def _reason_specificity(self, symbol: str, reason: str) -> int:
        if "strong ai infrastructure exposure" in reason.lower():
            return 3
        if symbol in reason and ("beneficiary" in reason.lower() or "exposed" in reason.lower()):
            return 2
        return 1

    def _accumulate_story_scores(
        self,
        story: Dict[str, Any],
        scorebook: Dict[str, Dict[str, List[Dict[str, Any]]]],
    ) -> None:
        direction = story["directionalBias"]
        for linked in story["linkedStocks"]:
            reason = {
                "topic": story["topic"],
                "catalyst": story["title"],
                "storyScore": story["impactScore"],
                "linkedReason": linked["reason"],
                "sourceId": story["sourceId"],
                "source": story["source"],
                "url": story["url"],
                "publishedAt": story["publishedAt"],
            }

            if direction == "up":
                scorebook["up"][linked["symbol"]].append(
                    {**reason, "score": linked["score"] * story["impactScore"]}
                )
            elif direction == "down":
                scorebook["down"][linked["symbol"]].append(
                    {**reason, "score": linked["score"] * story["impactScore"]}
                )
            else:
                # Mixed news should contribute to both sides lightly.
                diluted = linked["score"] * story["impactScore"] * 0.45
                scorebook["up"][linked["symbol"]].append({**reason, "score": diluted})
                scorebook["down"][linked["symbol"]].append({**reason, "score": diluted})

    async def _rank_stock_ideas(
        self,
        score_map: Dict[str, List[Dict[str, Any]]],
        direction: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        if not self.data_fetcher or not self.research_service:
            return []

        candidates = sorted(
            score_map.items(),
            key=lambda item: sum(entry["score"] for entry in item[1]),
            reverse=True,
        )[: max(limit * 2, 8)]

        ideas: List[Dict[str, Any]] = []
        for symbol, contributions in candidates:
            quote, company, research = await asyncio.gather(
                self.data_fetcher.get_stock_quote(symbol),
                self.data_fetcher.get_company_info(symbol),
                self.research_service.predict(symbol),
            )
            if not quote or not company:
                continue

            medium = next(
                (h for h in research.horizons if h.horizon == "21d"),
                research.horizons[0] if research and research.horizons else None,
            )
            if research and medium is not None:
                if direction == "up":
                    alignment = medium.probability_outperform
                    direction_matches = medium.recommendation in {"buy", "strong_buy"}
                else:
                    alignment = 1 - medium.probability_outperform
                    direction_matches = medium.recommendation in {"sell", "strong_sell"}
            else:
                alignment = 0.5
                direction_matches = False

            raw_score = sum(entry["score"] for entry in contributions)
            theme_bonus = max(
                [exposure.score for exposure in self.theme_model.get_exposures(symbol)] or [0.0]
            )
            evidence_count = len(contributions)
            valuation_bonus = self._valuation_bonus(company, direction)
            final_score = min(
                100.0,
                raw_score * 24
                + alignment * 30
                + theme_bonus * 12
                + valuation_bonus,
            )
            confidence = min(
                0.92,
                0.42
                + min(raw_score, 1.5) * 0.12
                + alignment * 0.18
                + (0.08 if direction_matches else 0.0),
            )
            catalysts = [entry["catalyst"] for entry in contributions[:3]]

            ideas.append(
                {
                    "symbol": symbol,
                    "companyName": company.name,
                    "direction": direction,
                    "topic": contributions[0]["topic"],
                    "catalyst": catalysts[0],
                    "score": round(final_score, 2),
                    "confidence": round(confidence, 4),
                    "currentPrice": float(quote.price),
                    "changePercent": float(quote.change_percent),
                    "reasoning": self._build_idea_reasoning(
                        company,
                        direction,
                        contributions,
                        medium,
                        theme_bonus,
                    ),
                    "modelVersion": getattr(research, "model_version", None),
                    "metrics": {
                        "marketCapBillions": round(float(company.market_cap or 0) / 1_000_000_000, 2)
                        if company.market_cap
                        else None,
                        "peRatio": float(company.pe_ratio) if company.pe_ratio is not None else None,
                        "forwardPe": float(company.forward_pe) if company.forward_pe is not None else None,
                        "priceToBook": float(company.price_to_book)
                        if company.price_to_book is not None
                        else None,
                        "dayChangePct": float(quote.change_percent),
                        "research21dProbability": round(medium.probability_outperform, 4)
                        if medium
                        else None,
                        "research21dConfidence": round(medium.confidence, 4)
                        if medium
                        else None,
                        "signalFamilies": research.coverage.get("activeSignalFamilies", [])
                        if research
                        else [],
                        "evidenceCount": evidence_count,
                        "nonDemoEvidenceCount": len(
                            [
                                card
                                for card in getattr(research, "evidence", []) or []
                                if getattr(card, "source_type", None) != "demo"
                                and (
                                    not getattr(card, "symbols", [])
                                    or symbol in (getattr(card, "symbols", []) or [])
                                )
                            ]
                        ),
                    },
                    "sourceIds": sorted(
                        {entry["sourceId"] for entry in contributions if entry.get("sourceId")}
                    ),
                    "coverage": getattr(research, "coverage", {}) if research else {},
                    "signalBreakdown": getattr(research, "signal_breakdown", {})
                    if research
                    else {},
                    "supportingEvidence": self._build_supporting_evidence(
                        symbol=symbol,
                        contributions=contributions,
                        research=research,
                    ),
                    "action": "watch" if direction == "up" else "avoid",
                    "dailyRating": "PENDING",
                    "buyScore": None,
                }
            )

        return ideas[:limit]

    async def _attach_local_model_analysis(self, ideas: List[Dict[str, Any]]) -> None:
        if (
            not self.local_model_service
            or not self.local_model_service.enabled()
            or not ideas
        ):
            return

        budget = max(0, settings.LOCAL_LLM_MAX_ANALYSES_PER_REPORT)
        if budget <= 0:
            return

        ranked = sorted(
            ideas,
            key=lambda item: float(item.get("score") or 0.0),
            reverse=True,
        )[:budget]

        for idea in ranked:
            try:
                idea["localModelAnalysis"] = await self.local_model_service.analyze_prediction(
                    idea
                )
            except Exception as exc:
                idea["localModelError"] = str(exc)

    def _finalize_recommendations(self, ideas: List[Dict[str, Any]]) -> None:
        for idea in ideas:
            metrics = idea.get("metrics") or {}
            model_analysis = idea.get("localModelAnalysis") or {}
            local_verdict = model_analysis.get("verdict")
            base_score = float(idea.get("score") or 0.0) / 100.0
            confidence = float(idea.get("confidence") or 0.0)
            research_prob = float(metrics.get("research21dProbability") or 0.5)
            evidence_strength = min(1.0, float(metrics.get("nonDemoEvidenceCount") or 0) / 4.0)

            llm_adjustment = 0.0
            if local_verdict == "supports":
                llm_adjustment = 0.08
            elif local_verdict == "mixed":
                llm_adjustment = -0.03
            elif local_verdict == "contradicts":
                llm_adjustment = -0.12

            if idea.get("direction") == "up":
                buy_score = (
                    0.38 * base_score
                    + 0.24 * confidence
                    + 0.18 * research_prob
                    + 0.12 * evidence_strength
                    + llm_adjustment
                )
            else:
                buy_score = (
                    0.18 * (1 - base_score)
                    + 0.18 * confidence
                    + 0.14 * (1 - research_prob)
                    + 0.10 * evidence_strength
                )

            buy_score = max(0.0, min(1.0, buy_score))
            action = "avoid"
            if idea.get("direction") == "up":
                if buy_score >= 0.72 and local_verdict != "contradicts":
                    action = "buy"
                elif buy_score >= 0.55:
                    action = "watch"
                else:
                    action = "avoid"

            rating = self._rating_for_action(action, buy_score, local_verdict)
            idea["buyScore"] = round(buy_score, 4)
            idea["action"] = action
            idea["dailyRating"] = rating
            metrics["buyScore"] = round(buy_score, 4)
            metrics["action"] = action
            metrics["dailyRating"] = rating
            idea["metrics"] = metrics

    @staticmethod
    def _rating_for_action(action: str, buy_score: float, local_verdict: Optional[str]) -> str:
        if action == "buy":
            if buy_score >= 0.85 and local_verdict == "supports":
                return "A"
            if buy_score >= 0.72:
                return "B"
            return "C"
        if action == "watch":
            return "C"
        if local_verdict == "contradicts":
            return "F"
        return "D"

    @staticmethod
    def _daily_summary(
        ideas: List[Dict[str, Any]], scoreboard: Dict[str, Any]
    ) -> Dict[str, Any]:
        buys = [idea for idea in ideas if idea.get("action") == "buy"]
        watches = [idea for idea in ideas if idea.get("action") == "watch"]
        avoids = [idea for idea in ideas if idea.get("action") == "avoid"]
        top_buy = max(buys, key=lambda item: item.get("buyScore") or 0.0, default=None)
        return {
            "buyCount": len(buys),
            "watchCount": len(watches),
            "avoidCount": len(avoids),
            "trackerAccuracyPct": scoreboard.get("accuracyPct"),
            "topBuySymbol": top_buy.get("symbol") if top_buy else None,
        }

    def _build_supporting_evidence(
        self,
        symbol: str,
        contributions: List[Dict[str, Any]],
        research,
    ) -> List[Dict[str, Any]]:
        evidence: List[Dict[str, Any]] = []
        seen = set()

        for entry in contributions:
            key = ("story", entry.get("catalyst"), entry.get("url"))
            if key in seen:
                continue
            seen.add(key)
            evidence.append(
                {
                    "title": entry.get("catalyst"),
                    "summary": entry.get("linkedReason"),
                    "source": entry.get("source"),
                    "sourceId": entry.get("sourceId"),
                    "sourceType": "live",
                    "publishedAt": entry.get("publishedAt"),
                    "url": entry.get("url"),
                    "confidence": round(min(max(entry.get("score", 0.0), 0.0), 1.0), 4),
                }
            )

        for card in getattr(research, "evidence", []) or []:
            if getattr(card, "source_type", None) == "demo":
                continue
            card_symbols = getattr(card, "symbols", []) or []
            if card_symbols and symbol not in card_symbols:
                continue
            key = (
                "research",
                getattr(card, "title", None),
                getattr(card, "url", None),
                getattr(card, "source_id", None),
            )
            if key in seen:
                continue
            seen.add(key)
            evidence.append(
                {
                    "title": getattr(card, "title", None),
                    "summary": getattr(card, "summary", None),
                    "source": getattr(card, "source", None),
                    "sourceId": getattr(card, "source_id", None),
                    "sourceType": getattr(card, "source_type", None),
                    "publishedAt": getattr(card, "published_at", None).isoformat()
                    if getattr(card, "published_at", None)
                    else None,
                    "url": getattr(card, "url", None),
                    "confidence": round(getattr(card, "confidence", 0.0), 4),
                }
            )

        evidence.sort(
            key=lambda item: (
                0 if item.get("url") else 1,
                -float(item.get("confidence") or 0.0),
            )
        )
        return evidence[:5]

    def _build_idea_reasoning(
        self,
        company,
        direction: str,
        contributions: List[Dict[str, Any]],
        medium_horizon,
        theme_bonus: float,
    ) -> List[str]:
        reasons = []
        for entry in contributions[:2]:
            reasons.append(f"{entry['topic']}: {entry['linkedReason']}")
        if medium_horizon:
            reasons.append(
                f"21-day research view: {medium_horizon.recommendation.replace('_', ' ')} "
                f"with {medium_horizon.confidence:.0%} confidence"
            )
        if company.pe_ratio is not None:
            reasons.append(f"Trailing P/E: {float(company.pe_ratio):.1f}")
        if theme_bonus >= 0.75:
            reasons.append("Strong AI infrastructure or digital platform exposure")
        if direction == "down" and company.price_to_book is not None:
            reasons.append(
                f"Rich price-to-book multiple ({float(company.price_to_book):.1f}) leaves less room for disappointment"
            )
        return reasons

    def _valuation_bonus(self, company, direction: str) -> float:
        pe = float(company.pe_ratio) if company.pe_ratio is not None else None
        pb = float(company.price_to_book) if company.price_to_book is not None else None
        if direction == "up":
            bonus = 0.0
            if pe is not None and pe < 25:
                bonus += 8.0
            if pb is not None and pb < 5:
                bonus += 6.0
            return bonus
        bonus = 0.0
        if pe is not None and pe > 35:
            bonus += 8.0
        if pb is not None and pb > 8:
            bonus += 6.0
        return bonus

    def _story_impact_score(
        self, sentiment: str, related_tickers: List[str], published_at: datetime
    ) -> float:
        age_hours = max((datetime.utcnow() - published_at).total_seconds() / 3600, 0.0)
        recency = 1.0 if age_hours <= 24 else 0.8 if age_hours <= 72 else 0.55
        sentiment_weight = 1.0 if sentiment != "neutral" else 0.7
        ticker_bonus = 1.0 + min(len(related_tickers), 4) * 0.08
        return recency * sentiment_weight * ticker_bonus

    def _dedupe_stories(self, stories: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped: Dict[str, Dict[str, Any]] = {}
        for story in stories:
            key = story.get("url") or story["title"]
            previous = deduped.get(key)
            if previous and previous["impactScore"] >= story["impactScore"]:
                continue
            deduped[key] = story
        return list(deduped.values())

    def _infer_sentiment(self, title: str) -> str:
        text = title.lower()
        positive_words = [
            "beat",
            "growth",
            "surge",
            "boom",
            "build",
            "partnership",
            "expansion",
            "approval",
            "funding",
            "cooling",
            "easing",
            "cut",
        ]
        negative_words = [
            "tariff",
            "sanction",
            "breach",
            "war",
            "shortage",
            "delay",
            "inflation",
            "hotter",
            "smuggled",
            "probe",
            "lawsuit",
            "outage",
            "recall",
        ]
        if any(word in text for word in positive_words):
            return "positive"
        if any(word in text for word in negative_words):
            return "negative"
        return "neutral"

    def _separate_conflicts(
        self,
        bullish_ranked: List[Dict[str, Any]],
        bearish_ranked: List[Dict[str, Any]],
        limit: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        bearish_by_symbol = {idea["symbol"]: idea for idea in bearish_ranked}
        bullish: List[Dict[str, Any]] = []
        bearish: List[Dict[str, Any]] = []

        for idea in bullish_ranked:
            opposing = bearish_by_symbol.get(idea["symbol"])
            if opposing and float(opposing["score"]) >= float(idea["score"]):
                continue
            bullish.append(idea)
            if len(bullish) >= limit:
                break

        bullish_symbols = {idea["symbol"] for idea in bullish}
        for idea in bearish_ranked:
            if idea["symbol"] in bullish_symbols:
                continue
            bearish.append(idea)
            if len(bearish) >= limit:
                break

        return bullish, bearish

    @staticmethod
    def _from_unix(value: Any) -> datetime:
        if value is None:
            return datetime.utcnow()
        try:
            return datetime.fromtimestamp(int(value))
        except Exception:
            return datetime.utcnow()
