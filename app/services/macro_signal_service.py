"""
Macro regime enrichment backed by FRED/ALFRED.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

import aiohttp

from app.core.config import settings
from app.services.runtime_cache import TTLCache


class MacroSignalService:
    """Fetch and summarize macro regime features from FRED."""

    SERIES = {
        "FEDFUNDS": "Effective Federal Funds Rate",
        "DGS10": "10-Year Treasury Constant Maturity Rate",
        "T10Y2Y": "10-Year Treasury Minus 2-Year Treasury",
        "CPIAUCSL": "Consumer Price Index for All Urban Consumers",
        "UNRATE": "Civilian Unemployment Rate",
        "BAMLH0A0HYM2": "ICE BofA US High Yield Index Option-Adjusted Spread",
    }

    _cache = TTLCache()

    def __init__(self, session: Optional[aiohttp.ClientSession]) -> None:
        self.session = session

    async def get_macro_snapshot(self) -> Dict[str, Any]:
        """Fetch the configured macro series and summarize the regime."""
        if not settings.ENABLE_FRED_MACRO:
            return self._unavailable("FRED macro features disabled in settings.")

        cache_key = "macro-snapshot:v1"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        if not self.session:
            return self._unavailable("HTTP session not initialized for FRED.")
        if not settings.FRED_API_KEY:
            return self._unavailable("FRED_API_KEY not configured.")

        tasks = [self._fetch_latest(series_id, label) for series_id, label in self.SERIES.items()]
        items = await asyncio.gather(*tasks)
        series = {item["seriesId"]: item for item in items if item}
        if not series:
            return self._unavailable("No FRED observations were returned.")

        score, summary, drivers = self._summarize(series)
        payload = {
            "available": True,
            "sourceId": "fred-alfred",
            "asOf": datetime.utcnow().isoformat(),
            "score": round(score, 4),
            "summary": summary,
            "drivers": drivers,
            "series": series,
        }
        return self._cache.set(cache_key, payload, settings.FRED_CACHE_TTL_SECONDS)

    async def _fetch_latest(self, series_id: str, label: str) -> Optional[Dict[str, Any]]:
        params = {
            "series_id": series_id,
            "api_key": settings.FRED_API_KEY,
            "file_type": "json",
            "sort_order": "desc",
            "limit": "3",
        }
        url = "https://api.stlouisfed.org/fred/series/observations"

        try:
            async with self.session.get(url, params=params, timeout=20) as response:
                if response.status != 200:
                    return None
                payload = await response.json()
        except Exception:
            return None

        for observation in payload.get("observations") or []:
            raw_value = observation.get("value")
            if raw_value in {None, "."}:
                continue
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            return {
                "seriesId": series_id,
                "label": label,
                "date": observation.get("date"),
                "value": value,
            }
        return None

    def _summarize(self, series: Dict[str, Dict[str, Any]]) -> tuple[float, str, list[str]]:
        drivers = []
        score = 0.0

        fed_funds = self._value(series, "FEDFUNDS")
        if fed_funds is not None:
            if fed_funds >= 4.5:
                score -= 0.2
                drivers.append("Policy rates remain restrictive.")
            elif fed_funds <= 2.5:
                score += 0.08
                drivers.append("Policy rates are comparatively supportive.")

        curve = self._value(series, "T10Y2Y")
        if curve is not None:
            if curve < 0:
                score -= 0.22
                drivers.append("Yield curve remains inverted.")
            elif curve > 1.0:
                score += 0.08
                drivers.append("Yield curve is positively sloped.")

        inflation = self._value(series, "CPIAUCSL")
        if inflation is not None:
            drivers.append("Inflation level tracked via CPI.")

        unemployment = self._value(series, "UNRATE")
        if unemployment is not None:
            if unemployment <= 4.5:
                score += 0.08
                drivers.append("Labor market remains relatively firm.")
            elif unemployment >= 5.5:
                score -= 0.12
                drivers.append("Unemployment is elevated.")

        credit_spread = self._value(series, "BAMLH0A0HYM2")
        if credit_spread is not None:
            if credit_spread >= 4.5:
                score -= 0.18
                drivers.append("High-yield credit spreads are wide.")
            elif credit_spread <= 3.2:
                score += 0.08
                drivers.append("Credit spreads remain contained.")

        treasury_10y = self._value(series, "DGS10")
        if treasury_10y is not None and treasury_10y >= 4.5:
            score -= 0.08
            drivers.append("Long-end yields remain elevated.")

        score = max(-1.0, min(1.0, score))
        if score >= 0.18:
            summary = "Macro backdrop is mildly supportive for risk assets."
        elif score <= -0.18:
            summary = "Macro backdrop is cautious with tightening or spread pressure."
        else:
            summary = "Macro backdrop is mixed and not strongly directional."

        return score, summary, drivers

    @staticmethod
    def _value(series: Dict[str, Dict[str, Any]], series_id: str) -> Optional[float]:
        item = series.get(series_id)
        if not item:
            return None
        return item.get("value")

    @staticmethod
    def _unavailable(reason: str) -> Dict[str, Any]:
        return {
            "available": False,
            "sourceId": "fred-alfred",
            "score": 0.0,
            "summary": "Macro regime context unavailable.",
            "drivers": [],
            "series": {},
            "reason": reason,
        }
