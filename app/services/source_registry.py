"""
Registry of public data sources and their caveats.
"""

from typing import Dict, Iterable, List, Optional

from app.services.research_models import DataSourceProfile


class SourceRegistry:
    """Central source metadata used by ingestion and prediction services."""

    def __init__(self) -> None:
        self._sources: Dict[str, DataSourceProfile] = {
            "yahoo-finance-yfinance": DataSourceProfile(
                source_id="yahoo-finance-yfinance",
                name="Yahoo Finance via yfinance",
                categories=["market_data", "quotes", "corporate_actions"],
                access="no_key_unofficial",
                best_for="Broad personal research bootstrap for daily prices, dividends, splits, and quote metadata.",
                caveats="Unofficial/personal-use data source; do not treat as sole production dependency.",
                priority=10,
            ),
            "stooq": DataSourceProfile(
                source_id="stooq",
                name="Stooq",
                categories=["market_data", "indices"],
                access="no_key",
                best_for="No-key daily OHLCV backup for equities and indices.",
                caveats="Ticker naming differs by market and corporate-action adjustment must be verified.",
                priority=20,
            ),
            "sec-edgar": DataSourceProfile(
                source_id="sec-edgar",
                name="SEC EDGAR APIs",
                categories=["filings", "fundamentals", "events"],
                access="no_key",
                best_for="Official US company filings, submissions, XBRL facts, and 8-K event history.",
                caveats="US public companies only; XBRL facts require point-in-time normalization.",
                priority=5,
            ),
            "fred-alfred": DataSourceProfile(
                source_id="fred-alfred",
                name="FRED/ALFRED",
                categories=["macro", "rates", "economic_data"],
                access="free_key",
                best_for="Historical macro series, rates, inflation, employment, and revised/vintage data.",
                caveats="Use vintages for backtests to avoid revised-data leakage.",
                priority=30,
            ),
            "gdelt": DataSourceProfile(
                source_id="gdelt",
                name="GDELT",
                categories=["news", "events", "geopolitics"],
                access="no_key",
                best_for="Global news/event monitoring and entity/theme detection.",
                caveats="Entity extraction is noisy; dedupe and source-quality scoring are required.",
                priority=25,
            ),
            "guardian-open-platform": DataSourceProfile(
                source_id="guardian-open-platform",
                name="The Guardian Open Platform",
                categories=["news", "world_context"],
                access="free_key",
                best_for="Long archive of general world news and macro/geopolitical context.",
                caveats="Not finance-specific; commercial usage requires appropriate terms.",
                priority=45,
            ),
            "alpha-vantage": DataSourceProfile(
                source_id="alpha-vantage",
                name="Alpha Vantage",
                categories=["market_data", "technical_indicators", "news"],
                access="free_key",
                best_for="Narrow tests for daily time series, technical indicators, macro, and news sentiment.",
                caveats="Free request volume is very constrained; broad backfills need another source.",
                priority=40,
            ),
            "financial-modeling-prep": DataSourceProfile(
                source_id="financial-modeling-prep",
                name="Financial Modeling Prep",
                categories=["market_data", "fundamentals", "news"],
                access="free_key_paid_optional",
                best_for="Company profiles, statements, ratios, and starter EOD datasets.",
                caveats="Free tier is constrained; redistribution and larger history require paid terms.",
                priority=35,
            ),
            "twelve-data": DataSourceProfile(
                source_id="twelve-data",
                name="Twelve Data",
                categories=["market_data", "technical_indicators", "forex", "crypto"],
                access="free_key_paid_optional",
                best_for="Quotes, time series, technical indicators, and reference data across assets.",
                caveats="Free plan has credit, usage, and market coverage limits.",
                priority=50,
            ),
            "tiingo": DataSourceProfile(
                source_id="tiingo",
                name="Tiingo",
                categories=["market_data", "news"],
                access="free_key_paid_optional",
                best_for="Cleaner end-of-day stock price workflows with account token.",
                caveats="Internal-use and redistribution terms must be respected.",
                priority=32,
            ),
            "finnhub": DataSourceProfile(
                source_id="finnhub",
                name="Finnhub",
                categories=["market_data", "fundamentals", "news", "alternative_data"],
                access="free_key_paid_optional",
                best_for="Retail-friendly prototype API for quotes, candles, fundamentals, and company news.",
                caveats="Endpoint entitlements and rate limits must be verified before production use.",
                priority=55,
            ),
            "marketstack": DataSourceProfile(
                source_id="marketstack",
                name="Marketstack",
                categories=["market_data", "reference_data"],
                access="free_key_paid_optional",
                best_for="Tiny EOD demos and exchange/ticker reference experiments.",
                caveats="Free plan is too small for meaningful multi-year backtesting.",
                priority=90,
            ),
        }

    def list_sources(self) -> List[DataSourceProfile]:
        return sorted(self._sources.values(), key=lambda item: item.priority)

    def get(self, source_id: str) -> Optional[DataSourceProfile]:
        return self._sources.get(source_id)

    def by_category(self, category: str) -> List[DataSourceProfile]:
        return [
            source
            for source in self.list_sources()
            if category in source.categories
        ]

    def provenance_for(self, source_ids: Iterable[str]) -> List[dict]:
        provenance = []
        for source_id in source_ids:
            source = self.get(source_id)
            if source:
                provenance.append(source.to_api())
        return provenance
