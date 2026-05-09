"""
Topic-driven market intelligence built from open news and live market data.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.core.config import settings
from app.services.event_extractor import EventExtractionService
from app.services.prediction_tracker import PredictionTrackerService
from app.services.real_data_fetcher import RealDataFetcherService
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

    async def __aenter__(self):
        self.data_fetcher = RealDataFetcherService()
        self.research_service = ResearchPredictionService()
        await self.data_fetcher.__aenter__()
        await self.research_service.__aenter__()
        self.tracker = PredictionTrackerService(self.data_fetcher)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.research_service:
            await self.research_service.__aexit__(exc_type, exc_val, exc_tb)
        if self.data_fetcher:
            await self.data_fetcher.__aexit__(exc_type, exc_val, exc_tb)

    async def build_today_report(self, limit: int = 5) -> Dict[str, Any]:
        """Return a report of the most important current event-linked stock ideas."""
        if not self.data_fetcher or not self.research_service or not self.tracker:
            raise RuntimeError("MarketIntelligenceService must be used as async context manager")

        cache_key = f"today-report:{limit}"
        cached = self._report_cache.get(cache_key)
        if cached is not None:
            return cached

        as_of = datetime.utcnow()
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

        await self.tracker.evaluate_due_predictions(as_of)
        await self.tracker.record_market_ideas(as_of, [*bullish, *bearish], horizon_days=5)
        scoreboard = await self.tracker.scoreboard(days=90)

        report = {
            "asOf": as_of.isoformat(),
            "majorStories": stories[: min(10, len(stories))],
            "topBullish": bullish,
            "topBearish": bearish,
            "scoreboard": scoreboard,
            "sources": self.source_registry.provenance_for(
                ["yahoo-finance-yfinance", "alpha-vantage", "sec-edgar", "fred-alfred"]
            ),
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
                "asOf": datetime.utcnow().isoformat(),
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
        stock_links: List[Tuple[str, str, float]] = []

        if related_tickers:
            for symbol in related_tickers:
                stock_links.append((symbol, "Mentioned directly in current news", 0.9))

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
            stock_links.append((symbol, f"Potential beneficiary of {topic.label.lower()}", 0.72))
        for symbol in bearish:
            stock_links.append((symbol, f"Potentially pressured by {topic.label.lower()}", 0.62))

        if any(keyword in text for keyword in ["ai", "inference", "datacenter", "data center", "gpu"]):
            for exposure in self.theme_model.get_theme_map()["exposures"]:
                if exposure["score"] >= 0.78:
                    stock_links.append(
                        (
                            exposure["symbol"],
                            "High-conviction AI infrastructure exposure",
                            float(exposure["score"]),
                        )
                    )

        deduped: Dict[str, Dict[str, Any]] = {}
        for symbol, reason, score in stock_links:
            previous = deduped.get(symbol)
            if previous and previous["score"] >= score:
                continue
            deduped[symbol] = {
                "symbol": symbol,
                "reason": reason,
                "score": round(score, 4),
            }

        return sorted(deduped.values(), key=lambda item: item["score"], reverse=True)

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
                    },
                    "sourceIds": sorted(
                        {entry["sourceId"] for entry in contributions if entry.get("sourceId")}
                    ),
                }
            )

        return ideas[:limit]

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
