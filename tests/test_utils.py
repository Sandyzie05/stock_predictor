"""
Test utilities and helpers.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict

import pytest

from app.models.prediction import RecommendationType
from app.models.stock import Stock


def create_test_stock_data(symbol: str = "TEST") -> Dict[str, Any]:
    """Create test stock data."""
    return {
        "symbol": symbol,
        "name": f"{symbol} Test Company",
        "sector": "Technology",
        "industry": "Software",
        "market_cap": Decimal("1000000000"),
        "description": f"Test company for {symbol}",
        "is_sp500": False,
    }


def create_test_price_data(base_price: Decimal = Decimal("100.00")) -> Dict[str, Any]:
    """Create test price data."""
    return {
        "date": datetime.utcnow(),
        "open_price": base_price,
        "high": base_price * Decimal("1.05"),
        "low": base_price * Decimal("0.95"),
        "close": base_price * Decimal("1.02"),
        "volume": 1000000,
        "adjusted_close": base_price * Decimal("1.02"),
    }


def create_test_fundamental_data() -> Dict[str, Any]:
    """Create test fundamental data."""
    return {
        "date": datetime.utcnow(),
        "pe_ratio": Decimal("20.5"),
        "pb_ratio": Decimal("3.2"),
        "roe": Decimal("0.15"),
        "debt_to_equity": Decimal("0.8"),
        "revenue": Decimal("100000000000"),
        "net_income": Decimal("20000000000"),
        "eps": Decimal("4.50"),
        "dividend_yield": Decimal("0.025"),
    }


def create_test_prediction_data(
    recommendation: RecommendationType = RecommendationType.BUY,
) -> Dict[str, Any]:
    """Create test prediction data."""
    return {
        "model_version": "test-v1.0.0",
        "prediction_date": datetime.utcnow(),
        "target_date": datetime.utcnow() + timedelta(days=30),
        "predicted_price": Decimal("110.00"),
        "confidence_score": Decimal("0.85"),
        "recommendation": recommendation,
        "reasoning": "Test prediction reasoning",
    }


def create_test_news_data(
    sentiment_label: str = "positive", sentiment_score: Decimal = Decimal("0.7")
) -> Dict[str, Any]:
    """Create test news sentiment data."""
    return {
        "date": datetime.utcnow(),
        "headline": "Test News Headline",
        "summary": "Test news summary",
        "content": "Full test news content",
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label,
        "source": "Test News Source",
        "url": "https://example.com/news/test",
        "author": "Test Author",
        "relevance_score": Decimal("0.9"),
    }


class MockPolygonClient:
    """Mock Polygon API client for testing."""

    def __init__(self, responses: Dict[str, Any] = None):
        self.responses = responses or {}

    def get_stock_data(self, symbol: str):
        """Mock get stock data."""
        return self.responses.get(f"stock_{symbol}", {})

    def get_price_data(self, symbol: str, date_from: str, date_to: str):
        """Mock get price data."""
        return self.responses.get(f"prices_{symbol}", [])


class MockYFinanceData:
    """Mock Yahoo Finance data for testing."""

    def __init__(self, symbol: str, data: Dict[str, Any] = None):
        self.symbol = symbol
        self.data = data or {}

    @property
    def info(self):
        """Mock info property."""
        return self.data.get("info", {})

    def history(self, period="1y", interval="1d"):
        """Mock history method."""
        import pandas as pd

        history_data = self.data.get("history", {})
        return pd.DataFrame(history_data)


def assert_decimal_equal(actual: Decimal, expected: Decimal, places: int = 2):
    """Assert two decimals are equal within specified decimal places."""
    assert abs(actual - expected) < Decimal(
        f"1e-{places}"
    ), f"Expected {expected}, got {actual} (diff: {abs(actual - expected)})"


def assert_datetime_close(
    actual: datetime, expected: datetime, tolerance_seconds: int = 5
):
    """Assert two datetimes are close within tolerance."""
    diff = abs((actual - expected).total_seconds())
    assert (
        diff <= tolerance_seconds
    ), f"Datetime difference {diff}s exceeds tolerance {tolerance_seconds}s"


@pytest.fixture
def mock_polygon_client():
    """Fixture for mock Polygon client."""

    def _create_client(responses: Dict[str, Any] = None):
        return MockPolygonClient(responses)

    return _create_client


@pytest.fixture
def mock_yfinance_data():
    """Fixture for mock Yahoo Finance data."""

    def _create_data(symbol: str, data: Dict[str, Any] = None):
        return MockYFinanceData(symbol, data)

    return _create_data
