"""
Simple in-memory TTL cache for lightweight local service reuse.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple


class TTLCache:
    """Very small process-local TTL cache."""

    def __init__(self) -> None:
        self._items: Dict[str, Tuple[datetime, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        item = self._items.get(key)
        if not item:
            return None

        expires_at, value = item
        if expires_at <= datetime.utcnow():
            self._items.pop(key, None)
            return None

        return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> Any:
        self._items[key] = (
            datetime.utcnow() + timedelta(seconds=max(ttl_seconds, 1)),
            value,
        )
        return value

    def clear(self) -> None:
        self._items.clear()
