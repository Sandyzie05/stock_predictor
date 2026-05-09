"""
SEC EDGAR filing enrichment for research predictions.
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from app.core.config import settings
from app.services.runtime_cache import TTLCache


class FilingSignalService:
    """Fetch company filing activity and simple fundamentals from SEC EDGAR."""

    REVENUE_CONCEPTS = [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "Revenues",
    ]
    EPS_DILUTED_CONCEPTS = ["EarningsPerShareDiluted"]

    _cache = TTLCache()
    _rate_lock = asyncio.Lock()
    _last_request_at = 0.0

    def __init__(self, session: Optional[aiohttp.ClientSession]) -> None:
        self.session = session

    async def get_filing_snapshot(self, symbol: str) -> Dict[str, Any]:
        """Return SEC filing context for a symbol when configured."""
        symbol = symbol.upper()
        if not settings.ENABLE_SEC_EDGAR:
            return self._unavailable(symbol, "SEC EDGAR integration disabled in settings.")
        if not self.session:
            return self._unavailable(symbol, "HTTP session not initialized for SEC.")
        if not settings.SEC_USER_AGENT:
            return self._unavailable(symbol, "SEC_USER_AGENT not configured.")

        cache_key = f"sec-snapshot:{symbol}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        cik = await self._lookup_cik(symbol)
        if not cik:
            return self._unavailable(symbol, f"No SEC CIK mapping found for {symbol}.")

        submissions = await self._fetch_json(
            f"https://data.sec.gov/submissions/CIK{cik}.json"
        )
        if not submissions:
            return self._unavailable(symbol, f"SEC submissions unavailable for {symbol}.")

        company_facts = await self._fetch_json(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        )
        payload = self._build_snapshot(symbol, cik, submissions, company_facts or {})
        return self._cache.set(cache_key, payload, settings.SEC_CACHE_TTL_SECONDS)

    async def _lookup_cik(self, symbol: str) -> Optional[str]:
        cache_key = "sec-company-tickers"
        mapping = self._cache.get(cache_key)
        if mapping is None:
            mapping = await self._fetch_json("https://www.sec.gov/files/company_tickers.json")
            if mapping:
                self._cache.set(cache_key, mapping, 86400)
        if not mapping:
            return None

        for item in mapping.values():
            if str(item.get("ticker", "")).upper() == symbol:
                try:
                    return f"{int(item['cik_str']):010d}"
                except (TypeError, ValueError, KeyError):
                    return None
        return None

    async def _fetch_json(self, url: str) -> Optional[Dict[str, Any]]:
        await self._throttle()
        headers = {
            "User-Agent": settings.SEC_USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json, text/plain, */*",
        }

        try:
            async with self.session.get(url, headers=headers, timeout=20) as response:
                if response.status != 200:
                    return None
                return await response.json()
        except Exception:
            return None

    async def _throttle(self) -> None:
        minimum_interval = 1 / max(settings.SEC_MAX_REQUESTS_PER_SECOND, 1)
        async with self._rate_lock:
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < minimum_interval:
                await asyncio.sleep(minimum_interval - elapsed)
            self._last_request_at = time.monotonic()

    def _build_snapshot(
        self, symbol: str, cik: str, submissions: Dict[str, Any], company_facts: Dict[str, Any]
    ) -> Dict[str, Any]:
        filings = self._recent_filings(submissions)
        latest_filing = filings[0] if filings else None
        latest_8k = next((item for item in filings if item["form"] == "8-K"), None)
        latest_periodic = next(
            (item for item in filings if item["form"] in {"10-Q", "10-K"}),
            None,
        )
        ttm_revenue_growth = self._ttm_growth(company_facts, self.REVENUE_CONCEPTS)
        ttm_eps_growth = self._ttm_growth(company_facts, self.EPS_DILUTED_CONCEPTS)

        score = 0.0
        if latest_periodic and latest_periodic["daysAgo"] <= 120:
            score += 0.08
        if latest_filing and latest_filing["daysAgo"] > 180:
            score -= 0.08
        if ttm_revenue_growth is not None:
            score += max(-0.2, min(0.2, ttm_revenue_growth / 100))
        if ttm_eps_growth is not None:
            score += max(-0.25, min(0.25, ttm_eps_growth / 100))

        score = max(-1.0, min(1.0, score))
        if score >= 0.12:
            sentiment = "positive"
        elif score <= -0.12:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return {
            "available": True,
            "sourceId": "sec-edgar",
            "symbol": symbol,
            "cik": cik,
            "score": round(score, 4),
            "sentiment": sentiment,
            "latestFiling": latest_filing,
            "recent8K": latest_8k,
            "recentPeriodic": latest_periodic,
            "ttmRevenueGrowth": round(ttm_revenue_growth, 4)
            if ttm_revenue_growth is not None
            else None,
            "ttmDilutedEpsGrowth": round(ttm_eps_growth, 4)
            if ttm_eps_growth is not None
            else None,
        }

    def _recent_filings(self, submissions: Dict[str, Any]) -> List[Dict[str, Any]]:
        recent = (((submissions.get("filings") or {}).get("recent")) or {})
        forms = recent.get("form") or []
        filing_dates = recent.get("filingDate") or []
        accession_numbers = recent.get("accessionNumber") or []

        filings: List[Dict[str, Any]] = []
        for form, filing_date, accession in zip(forms, filing_dates, accession_numbers):
            parsed = self._parse_date(filing_date)
            if not parsed:
                continue
            filings.append(
                {
                    "form": form,
                    "filingDate": filing_date,
                    "daysAgo": max((datetime.utcnow().date() - parsed.date()).days, 0),
                    "accessionNumber": accession,
                }
            )
        filings.sort(key=lambda item: item["filingDate"], reverse=True)
        return filings

    def _ttm_growth(self, company_facts: Dict[str, Any], concepts: List[str]) -> Optional[float]:
        quarterly_values = self._quarterly_values(company_facts, concepts)
        if len(quarterly_values) < 8:
            return None

        latest_ttm = sum(item["val"] for item in quarterly_values[-4:])
        prior_ttm = sum(item["val"] for item in quarterly_values[-8:-4])
        if prior_ttm == 0:
            return None

        return ((latest_ttm - prior_ttm) / abs(prior_ttm)) * 100

    def _quarterly_values(
        self, company_facts: Dict[str, Any], concepts: List[str]
    ) -> List[Dict[str, Any]]:
        facts = ((company_facts.get("facts") or {}).get("us-gaap")) or {}
        values_by_end: Dict[str, Dict[str, Any]] = {}

        for concept in concepts:
            concept_data = facts.get(concept) or {}
            units = concept_data.get("units") or {}
            for entries in units.values():
                for entry in entries or []:
                    form = entry.get("form")
                    if form not in {"10-Q", "10-Q/A"}:
                        continue
                    end = entry.get("end")
                    filed = entry.get("filed") or ""
                    val = entry.get("val")
                    if end is None or val is None:
                        continue
                    current = values_by_end.get(end)
                    if current is None or filed > current.get("filed", ""):
                        try:
                            numeric_value = float(val)
                        except (TypeError, ValueError):
                            continue
                        values_by_end[end] = {
                            "end": end,
                            "filed": filed,
                            "val": numeric_value,
                        }

        return sorted(values_by_end.values(), key=lambda item: item["end"])

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _unavailable(symbol: str, reason: str) -> Dict[str, Any]:
        return {
            "available": False,
            "sourceId": "sec-edgar",
            "symbol": symbol,
            "score": 0.0,
            "sentiment": "neutral",
            "latestFiling": None,
            "recent8K": None,
            "recentPeriodic": None,
            "ttmRevenueGrowth": None,
            "ttmDilutedEpsGrowth": None,
            "reason": reason,
        }
