"""
Tests for stock models.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.stock import Fundamental, Stock, StockPrice, TechnicalIndicator


class TestStock:
    """Test Stock model."""

    @pytest.mark.asyncio
    async def test_create_stock(self, db_session, sample_stock_data):
        """Test creating a stock."""
        stock = Stock(**sample_stock_data)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        assert stock.id is not None
        assert stock.symbol == "AAPL"
        assert stock.name == "Apple Inc."
        assert stock.sector == "Technology"
        assert stock.industry == "Consumer Electronics"
        assert stock.market_cap == Decimal("2500000000000")
        assert stock.is_sp500 is True
        assert stock.is_active is True
        assert isinstance(stock.created_at, datetime)
        assert isinstance(stock.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_stock_symbol_unique(self, db_session, sample_stock_data):
        """Test that stock symbols must be unique."""
        # Create first stock
        stock1 = Stock(**sample_stock_data)
        db_session.add(stock1)
        await db_session.commit()

        # Try to create second stock with same symbol
        stock2 = Stock(**sample_stock_data)
        stock2.name = "Different Name"
        db_session.add(stock2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_stock_minimal_creation(self, db_session):
        """Test creating stock with minimal required fields."""
        stock = Stock(symbol="MSFT", name="Microsoft Corporation")
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        assert stock.symbol == "MSFT"
        assert stock.name == "Microsoft Corporation"
        assert stock.sector is None
        assert stock.industry is None
        assert stock.market_cap is None
        assert stock.description is None
        assert stock.is_sp500 is False
        assert stock.is_active is True

    @pytest.mark.asyncio
    async def test_stock_relationships(self, sample_stock):
        """Test stock model relationships."""
        assert hasattr(sample_stock, "prices")
        assert hasattr(sample_stock, "fundamentals")
        assert hasattr(sample_stock, "technical_indicators")
        assert hasattr(sample_stock, "predictions")
        assert hasattr(sample_stock, "news_sentiment")


class TestStockPrice:
    """Test StockPrice model."""

    @pytest.mark.asyncio
    async def test_create_stock_price(
        self, db_session, sample_stock, sample_price_data
    ):
        """Test creating a stock price."""
        price_data = sample_price_data.copy()
        price_data["stock_id"] = sample_stock.id

        price = StockPrice(**price_data)
        db_session.add(price)
        await db_session.commit()
        await db_session.refresh(price)

        assert price.id is not None
        assert price.stock_id == sample_stock.id
        assert price.open_price == Decimal("150.00")
        assert price.high == Decimal("155.00")
        assert price.low == Decimal("148.00")
        assert price.close == Decimal("152.50")
        assert price.volume == 1000000
        assert price.adjusted_close == Decimal("152.50")
        assert isinstance(price.date, datetime)
        assert isinstance(price.created_at, datetime)

    @pytest.mark.asyncio
    async def test_stock_price_without_adjusted_close(self, db_session, sample_stock):
        """Test creating stock price without adjusted close."""
        price = StockPrice(
            stock_id=sample_stock.id,
            date=datetime.utcnow(),
            open_price=Decimal("100.00"),
            high=Decimal("105.00"),
            low=Decimal("99.00"),
            close=Decimal("102.00"),
            volume=500000,
        )
        db_session.add(price)
        await db_session.commit()
        await db_session.refresh(price)

        assert price.adjusted_close is None
        assert price.close == Decimal("102.00")

    @pytest.mark.asyncio
    async def test_stock_price_relationship(self, sample_stock_price, sample_stock):
        """Test stock price relationship with stock."""
        assert sample_stock_price.stock_id == sample_stock.id
        # Note: In actual implementation, you'd load the relationship
        # assert sample_stock_price.stock.symbol == sample_stock.symbol


class TestFundamental:
    """Test Fundamental model."""

    @pytest.mark.asyncio
    async def test_create_fundamental(
        self, db_session, sample_stock, sample_fundamental_data
    ):
        """Test creating fundamental data."""
        fundamental_data = sample_fundamental_data.copy()
        fundamental_data["stock_id"] = sample_stock.id

        fundamental = Fundamental(**fundamental_data)
        db_session.add(fundamental)
        await db_session.commit()
        await db_session.refresh(fundamental)

        assert fundamental.id is not None
        assert fundamental.stock_id == sample_stock.id
        assert fundamental.pe_ratio == Decimal("25.5")
        assert fundamental.pb_ratio == Decimal("4.2")
        assert fundamental.roe == Decimal("0.25")
        assert fundamental.debt_to_equity == Decimal("1.5")
        assert fundamental.revenue == Decimal("365000000000")
        assert fundamental.net_income == Decimal("94000000000")
        assert fundamental.eps == Decimal("5.89")
        assert fundamental.dividend_yield == Decimal("0.005")

    @pytest.mark.asyncio
    async def test_fundamental_minimal_creation(self, db_session, sample_stock):
        """Test creating fundamental with minimal data."""
        fundamental = Fundamental(stock_id=sample_stock.id, date=datetime.utcnow())
        db_session.add(fundamental)
        await db_session.commit()
        await db_session.refresh(fundamental)

        assert fundamental.stock_id == sample_stock.id
        assert fundamental.pe_ratio is None
        assert fundamental.pb_ratio is None
        assert fundamental.revenue is None

    @pytest.mark.asyncio
    async def test_fundamental_multiple_periods(self, db_session, sample_stock):
        """Test multiple fundamental data periods for same stock."""
        dates = [
            datetime.utcnow() - timedelta(days=90),
            datetime.utcnow() - timedelta(days=180),
            datetime.utcnow() - timedelta(days=270),
        ]

        for i, date in enumerate(dates):
            fundamental = Fundamental(
                stock_id=sample_stock.id,
                date=date,
                pe_ratio=Decimal(f"{20 + i}.5"),
                revenue=Decimal(f"{300000000000 + i * 10000000000}"),
            )
            db_session.add(fundamental)

        await db_session.commit()

        # Query to verify all were created
        result = await db_session.execute(
            select(Fundamental).where(Fundamental.stock_id == sample_stock.id)
        )
        fundamentals = result.scalars().all()

        assert len(fundamentals) == 3


class TestTechnicalIndicator:
    """Test TechnicalIndicator model."""

    @pytest.mark.asyncio
    async def test_create_technical_indicator(self, db_session, sample_stock):
        """Test creating technical indicators."""
        indicator = TechnicalIndicator(
            stock_id=sample_stock.id,
            date=datetime.utcnow(),
            sma_20=Decimal("150.00"),
            sma_50=Decimal("145.00"),
            sma_200=Decimal("140.00"),
            ema_12=Decimal("152.00"),
            ema_26=Decimal("148.00"),
            rsi=Decimal("65.5"),
            macd=Decimal("2.5"),
            macd_signal=Decimal("2.2"),
            bollinger_upper=Decimal("160.00"),
            bollinger_lower=Decimal("140.00"),
            atr=Decimal("3.25"),
        )
        db_session.add(indicator)
        await db_session.commit()
        await db_session.refresh(indicator)

        assert indicator.id is not None
        assert indicator.stock_id == sample_stock.id
        assert indicator.sma_20 == Decimal("150.00")
        assert indicator.rsi == Decimal("65.5")
        assert indicator.atr == Decimal("3.25")

    @pytest.mark.asyncio
    async def test_technical_indicator_partial_data(self, db_session, sample_stock):
        """Test creating technical indicators with partial data."""
        indicator = TechnicalIndicator(
            stock_id=sample_stock.id,
            date=datetime.utcnow(),
            sma_20=Decimal("150.00"),
            rsi=Decimal("70.0"),
            # Other indicators are None
        )
        db_session.add(indicator)
        await db_session.commit()
        await db_session.refresh(indicator)

        assert indicator.sma_20 == Decimal("150.00")
        assert indicator.rsi == Decimal("70.0")
        assert indicator.sma_50 is None
        assert indicator.macd is None
        assert indicator.bollinger_upper is None

    @pytest.mark.asyncio
    async def test_technical_indicator_time_series(self, db_session, sample_stock):
        """Test creating time series of technical indicators."""
        dates = [datetime.utcnow() - timedelta(days=i) for i in range(5)]

        for i, date in enumerate(dates):
            indicator = TechnicalIndicator(
                stock_id=sample_stock.id,
                date=date,
                sma_20=Decimal(f"{150 + i}.00"),
                rsi=Decimal(f"{60 + i}.0"),
            )
            db_session.add(indicator)

        await db_session.commit()

        # Query to verify all were created
        result = await db_session.execute(
            select(TechnicalIndicator)
            .where(TechnicalIndicator.stock_id == sample_stock.id)
            .order_by(TechnicalIndicator.date.desc())
        )
        indicators = result.scalars().all()

        assert len(indicators) == 5
        # Most recent should be first (highest SMA value)
        assert indicators[0].sma_20 == Decimal("150.00")
        assert indicators[-1].sma_20 == Decimal("154.00")
