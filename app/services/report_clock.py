"""
Helpers for consistent report timing across the daily recommendation flow.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings


def report_timezone() -> ZoneInfo:
    """Return the configured timezone for daily report boundaries."""
    return ZoneInfo(settings.REPORT_TIMEZONE)


def report_now() -> datetime:
    """Return the current wall-clock time in the configured report timezone."""
    return datetime.now(report_timezone()).replace(tzinfo=None)


def report_day(value: datetime) -> datetime:
    """Normalize a datetime to the local report-day boundary."""
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def next_reset(value: datetime) -> datetime:
    """Return the next local midnight for report resets."""
    return report_day(value) + timedelta(days=1)
