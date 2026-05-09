"""
Pytest configuration and shared fixtures.
"""

import asyncio
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base, get_db
from app.main import app
from app.models.news import NewsSentiment
from app.models.prediction import Prediction, RecommendationType
from app.models.stock import Fundamental, Stock, StockPrice, TechnicalIndicator

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


class TestSettings(Settings):
    """Test-specific settings."""

    DEBUG: bool = True
    ENVIRONMENT: str = "testing"
    DATABASE_URL: str = TEST_DATABASE_URL
    REDIS_URL: str = "redis://localhost:6379/1"  # Test Redis DB
    SECRET_KEY: str = "test-secret-key"
    POLYGON_API_KEY: str = "test-polygon-key"
    ALPHA_VANTAGE_API_KEY: str = "test-alpha-key"
    NEWS_API_KEY: str = "test-news-key"

    model_config = {"env_file": None}


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@pytest.fixture
def override_get_db(db_session: AsyncSession):
    """Override get_db dependency for testing."""

    async def _override_get_db():
        yield db_session

    return _override_get_db


@pytest.fixture
def test_settings() -> TestSettings:
    """Get test settings."""
    return TestSettings()


@pytest.fixture
def client(override_get_db) -> Generator[TestClient, None, None]:
    """Create test client with dependency overrides."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# Test data fixtures
@pytest.fixture
def sample_stock_data():
    """Sample stock data for testing."""
    return {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "market_cap": Decimal("2500000000000"),
        "description": "Apple Inc. designs and manufactures consumer electronics.",
        "is_sp500": True,
    }


@pytest.fixture
async def sample_stock(db_session: AsyncSession, sample_stock_data) -> Stock:
    """Create sample stock in database."""
    stock = Stock(**sample_stock_data)
    db_session.add(stock)
    await db_session.commit()
    await db_session.refresh(stock)
    return stock


@pytest.fixture
def sample_price_data():
    """Sample stock price data."""
    return {
        "date": datetime.utcnow(),
        "open_price": Decimal("150.00"),
        "high": Decimal("155.00"),
        "low": Decimal("148.00"),
        "close": Decimal("152.50"),
        "volume": 1000000,
        "adjusted_close": Decimal("152.50"),
    }


@pytest.fixture
async def sample_stock_price(
    db_session: AsyncSession, sample_stock: Stock, sample_price_data
) -> StockPrice:
    """Create sample stock price in database."""
    price_data = sample_price_data.copy()
    price_data["stock_id"] = sample_stock.id
    price = StockPrice(**price_data)
    db_session.add(price)
    await db_session.commit()
    await db_session.refresh(price)
    return price


@pytest.fixture
def sample_fundamental_data():
    """Sample fundamental data."""
    return {
        "date": datetime.utcnow(),
        "pe_ratio": Decimal("25.5"),
        "pb_ratio": Decimal("4.2"),
        "roe": Decimal("0.25"),
        "debt_to_equity": Decimal("1.5"),
        "revenue": Decimal("365000000000"),
        "net_income": Decimal("94000000000"),
        "eps": Decimal("5.89"),
        "dividend_yield": Decimal("0.005"),
    }


@pytest.fixture
async def sample_fundamental(
    db_session: AsyncSession, sample_stock: Stock, sample_fundamental_data
) -> Fundamental:
    """Create sample fundamental data in database."""
    fundamental_data = sample_fundamental_data.copy()
    fundamental_data["stock_id"] = sample_stock.id
    fundamental = Fundamental(**fundamental_data)
    db_session.add(fundamental)
    await db_session.commit()
    await db_session.refresh(fundamental)
    return fundamental


@pytest.fixture
def sample_prediction_data():
    """Sample prediction data."""
    return {
        "model_version": "v1.0.0",
        "prediction_date": datetime.utcnow(),
        "target_date": datetime.utcnow() + timedelta(days=30),
        "predicted_price": Decimal("160.00"),
        "confidence_score": Decimal("0.85"),
        "recommendation": RecommendationType.BUY,
        "reasoning": "Strong fundamentals and positive technical indicators.",
    }


@pytest.fixture
async def sample_prediction(
    db_session: AsyncSession, sample_stock: Stock, sample_prediction_data
) -> Prediction:
    """Create sample prediction in database."""
    prediction_data = sample_prediction_data.copy()
    prediction_data["stock_id"] = sample_stock.id
    prediction = Prediction(**prediction_data)
    db_session.add(prediction)
    await db_session.commit()
    await db_session.refresh(prediction)
    return prediction


@pytest.fixture
def sample_news_data():
    """Sample news sentiment data."""
    return {
        "date": datetime.utcnow(),
        "headline": "Apple Reports Strong Quarterly Results",
        "summary": "Apple exceeded analyst expectations with strong iPhone sales.",
        "sentiment_score": Decimal("0.8"),
        "sentiment_label": "positive",
        "source": "Reuters",
        "url": "https://example.com/news/apple-results",
        "author": "John Doe",
        "relevance_score": Decimal("0.9"),
    }


@pytest.fixture
async def sample_news_sentiment(
    db_session: AsyncSession, sample_stock: Stock, sample_news_data
) -> NewsSentiment:
    """Create sample news sentiment in database."""
    news_data = sample_news_data.copy()
    news_data["stock_id"] = sample_stock.id
    news = NewsSentiment(**news_data)
    db_session.add(news)
    await db_session.commit()
    await db_session.refresh(news)
    return news


# Mock data helpers
class MockPolygonResponse:
    """Mock response from Polygon API."""

    def __init__(self, data: dict, status_code: int = 200):
        self.data = data
        self.status_code = status_code

    def json(self):
        return self.data


class MockYFinanceStock:
    """Mock yfinance Stock object."""

    def __init__(self, symbol: str, info: dict, history_data: dict):
        self.symbol = symbol
        self.info = info
        self.history_data = history_data

    @property
    def info(self):
        return self._info

    @info.setter
    def info(self, value):
        self._info = value

    def history(self, period="1y", interval="1d"):
        """Mock history method."""
        import pandas as pd

        return pd.DataFrame(self.history_data)


@pytest.fixture
def mock_polygon_response():
    """Create mock Polygon API response."""

    def _create_response(data: dict, status_code: int = 200):
        return MockPolygonResponse(data, status_code)

    return _create_response


@pytest.fixture
def mock_yfinance_stock():
    """Create mock yfinance stock object."""

    def _create_stock(symbol: str, info: dict, history_data: dict):
        return MockYFinanceStock(symbol, info, history_data)

    return _create_stock


# Cleanup fixture
@pytest.fixture(autouse=True)
async def cleanup_database(db_session: AsyncSession):
    """Clean up database after each test."""
    yield
    # Clean up is handled by session rollback in db_session fixture
