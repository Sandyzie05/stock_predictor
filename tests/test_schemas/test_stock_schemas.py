"""
Tests for stock schemas.
"""

from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.stock import (FundamentalBase, FundamentalResponse, StockBase,
                               StockCreate, StockPriceBase, StockPriceResponse,
                               StockResponse, StockUpdate,
                               TechnicalIndicatorBase,
                               TechnicalIndicatorResponse)


class TestStockBase:
    """Test StockBase schema."""

    def test_valid_stock_base(self):
        """Test valid stock base creation."""
        stock_data = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "market_cap": Decimal("2500000000000"),
            "description": "Apple Inc. designs and manufactures consumer electronics.",
            "is_sp500": True,
        }

        stock = StockBase(**stock_data)

        assert stock.symbol == "AAPL"
        assert stock.name == "Apple Inc."
        assert stock.sector == "Technology"
        assert stock.industry == "Consumer Electronics"
        assert stock.market_cap == Decimal("2500000000000")
        assert stock.is_sp500 is True

    def test_stock_base_minimal(self):
        """Test stock base with minimal required fields."""
        stock = StockBase(symbol="MSFT", name="Microsoft Corporation")

        assert stock.symbol == "MSFT"
        assert stock.name == "Microsoft Corporation"
        assert stock.sector is None
        assert stock.industry is None
        assert stock.market_cap is None
        assert stock.is_sp500 is False

    def test_symbol_validation(self):
        """Test symbol field validation."""
        # Empty symbol should fail
        with pytest.raises(ValidationError):
            StockBase(symbol="", name="Test Company")

        # Too long symbol should fail
        with pytest.raises(ValidationError):
            StockBase(symbol="VERYLONGSYMBOL", name="Test Company")

        # Valid short symbol
        stock = StockBase(symbol="A", name="Test Company")
        assert stock.symbol == "A"

    def test_name_validation(self):
        """Test name field validation."""
        # Empty name should fail
        with pytest.raises(ValidationError):
            StockBase(symbol="TEST", name="")

        # Valid name
        stock = StockBase(symbol="TEST", name="T")
        assert stock.name == "T"

    def test_negative_market_cap_validation(self):
        """Test market cap cannot be negative."""
        with pytest.raises(ValidationError):
            StockBase(
                symbol="TEST", name="Test Company", market_cap=Decimal("-1000000")
            )


class TestStockCreate:
    """Test StockCreate schema."""

    def test_stock_create_inheritance(self):
        """Test that StockCreate inherits from StockBase."""
        stock_data = {
            "symbol": "GOOGL",
            "name": "Alphabet Inc.",
            "sector": "Technology",
        }

        stock = StockCreate(**stock_data)
        assert isinstance(stock, StockBase)
        assert stock.symbol == "GOOGL"


class TestStockUpdate:
    """Test StockUpdate schema."""

    def test_stock_update_partial(self):
        """Test partial update with only some fields."""
        update = StockUpdate(name="Updated Company Name", sector="Updated Sector")

        assert update.name == "Updated Company Name"
        assert update.sector == "Updated Sector"
        assert update.industry is None
        assert update.market_cap is None

    def test_stock_update_all_none(self):
        """Test update with all None values."""
        update = StockUpdate()

        assert update.name is None
        assert update.sector is None
        assert update.industry is None
        assert update.is_active is None

    def test_stock_update_validation(self):
        """Test update validation."""
        # Empty name should fail
        with pytest.raises(ValidationError):
            StockUpdate(name="")

        # Negative market cap should fail
        with pytest.raises(ValidationError):
            StockUpdate(market_cap=Decimal("-100"))


class TestStockResponse:
    """Test StockResponse schema."""

    def test_stock_response_from_model(self, sample_stock):
        """Test creating response from database model."""
        response = StockResponse.from_orm(sample_stock)

        assert response.id == sample_stock.id
        assert response.symbol == sample_stock.symbol
        assert response.name == sample_stock.name
        assert response.is_active == sample_stock.is_active
        assert isinstance(response.created_at, datetime)
        assert isinstance(response.updated_at, datetime)


class TestStockPriceBase:
    """Test StockPriceBase schema."""

    def test_valid_stock_price(self):
        """Test valid stock price creation."""
        price_data = {
            "date": datetime.utcnow(),
            "open_price": Decimal("150.00"),
            "high": Decimal("155.00"),
            "low": Decimal("148.00"),
            "close": Decimal("152.50"),
            "volume": 1000000,
            "adjusted_close": Decimal("152.50"),
        }

        price = StockPriceBase(**price_data)

        assert price.open_price == Decimal("150.00")
        assert price.high == Decimal("155.00")
        assert price.low == Decimal("148.00")
        assert price.close == Decimal("152.50")
        assert price.volume == 1000000

    def test_price_validation(self):
        """Test price field validation."""
        base_data = {
            "date": datetime.utcnow(),
            "high": Decimal("155.00"),
            "low": Decimal("148.00"),
            "close": Decimal("152.50"),
            "volume": 1000000,
        }

        # Zero or negative prices should fail
        with pytest.raises(ValidationError):
            StockPriceBase(**{**base_data, "open_price": Decimal("0")})

        with pytest.raises(ValidationError):
            StockPriceBase(**{**base_data, "open_price": Decimal("-10")})

    def test_volume_validation(self):
        """Test volume validation."""
        base_data = {
            "date": datetime.utcnow(),
            "open_price": Decimal("150.00"),
            "high": Decimal("155.00"),
            "low": Decimal("148.00"),
            "close": Decimal("152.50"),
        }

        # Negative volume should fail
        with pytest.raises(ValidationError):
            StockPriceBase(**{**base_data, "volume": -1})

        # Zero volume should pass
        price = StockPriceBase(**{**base_data, "volume": 0})
        assert price.volume == 0


class TestFundamentalBase:
    """Test FundamentalBase schema."""

    def test_valid_fundamental(self):
        """Test valid fundamental data creation."""
        fundamental_data = {
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

        fundamental = FundamentalBase(**fundamental_data)

        assert fundamental.pe_ratio == Decimal("25.5")
        assert fundamental.revenue == Decimal("365000000000")
        assert fundamental.dividend_yield == Decimal("0.005")

    def test_fundamental_minimal(self):
        """Test fundamental with minimal data."""
        fundamental = FundamentalBase(date=datetime.utcnow())

        assert fundamental.pe_ratio is None
        assert fundamental.revenue is None
        assert isinstance(fundamental.date, datetime)

    def test_debt_to_equity_validation(self):
        """Test debt-to-equity ratio validation."""
        # Negative debt-to-equity should fail
        with pytest.raises(ValidationError):
            FundamentalBase(date=datetime.utcnow(), debt_to_equity=Decimal("-1.0"))

    def test_dividend_yield_validation(self):
        """Test dividend yield validation."""
        # Dividend yield above 100% should fail
        with pytest.raises(ValidationError):
            FundamentalBase(date=datetime.utcnow(), dividend_yield=Decimal("1.5"))

        # Negative dividend yield should fail
        with pytest.raises(ValidationError):
            FundamentalBase(date=datetime.utcnow(), dividend_yield=Decimal("-0.1"))


class TestTechnicalIndicatorBase:
    """Test TechnicalIndicatorBase schema."""

    def test_valid_technical_indicator(self):
        """Test valid technical indicator creation."""
        indicator_data = {
            "date": datetime.utcnow(),
            "sma_20": Decimal("150.00"),
            "sma_50": Decimal("145.00"),
            "rsi": Decimal("65.5"),
            "macd": Decimal("2.5"),
            "atr": Decimal("3.25"),
        }

        indicator = TechnicalIndicatorBase(**indicator_data)

        assert indicator.sma_20 == Decimal("150.00")
        assert indicator.rsi == Decimal("65.5")
        assert indicator.atr == Decimal("3.25")

    def test_rsi_validation(self):
        """Test RSI validation (0-100 range)."""
        base_data = {"date": datetime.utcnow()}

        # RSI above 100 should fail
        with pytest.raises(ValidationError):
            TechnicalIndicatorBase(**{**base_data, "rsi": Decimal("101")})

        # Negative RSI should fail
        with pytest.raises(ValidationError):
            TechnicalIndicatorBase(**{**base_data, "rsi": Decimal("-1")})

        # Valid RSI values
        for rsi_value in [Decimal("0"), Decimal("50"), Decimal("100")]:
            indicator = TechnicalIndicatorBase(**{**base_data, "rsi": rsi_value})
            assert indicator.rsi == rsi_value

    def test_atr_validation(self):
        """Test ATR validation (must be non-negative)."""
        base_data = {"date": datetime.utcnow()}

        # Negative ATR should fail
        with pytest.raises(ValidationError):
            TechnicalIndicatorBase(**{**base_data, "atr": Decimal("-1")})

        # Zero and positive ATR should pass
        indicator = TechnicalIndicatorBase(**{**base_data, "atr": Decimal("0")})
        assert indicator.atr == Decimal("0")
