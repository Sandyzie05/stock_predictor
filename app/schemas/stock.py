"""
Stock-related Pydantic schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class StockBase(BaseModel):
    """Base stock schema."""

    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    name: str = Field(..., min_length=1, max_length=200, description="Company name")
    sector: Optional[str] = Field(None, max_length=100, description="Company sector")
    industry: Optional[str] = Field(
        None, max_length=100, description="Company industry"
    )
    market_cap: Optional[Decimal] = Field(
        None, ge=0, description="Market capitalization"
    )
    description: Optional[str] = Field(None, description="Company description")
    is_sp500: bool = Field(default=False, description="Is S&P 500 constituent")


class StockCreate(StockBase):
    """Schema for creating a stock."""


class StockUpdate(BaseModel):
    """Schema for updating a stock."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    sector: Optional[str] = Field(None, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    market_cap: Optional[Decimal] = Field(None, ge=0)
    description: Optional[str] = None
    is_sp500: Optional[bool] = None
    is_active: Optional[bool] = None


class StockResponse(StockBase):
    """Schema for stock response."""

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StockPriceBase(BaseModel):
    """Base stock price schema."""

    date: datetime = Field(..., description="Price date")
    open_price: Decimal = Field(..., gt=0, description="Opening price")
    high: Decimal = Field(..., gt=0, description="High price")
    low: Decimal = Field(..., gt=0, description="Low price")
    close: Decimal = Field(..., gt=0, description="Closing price")
    volume: int = Field(..., ge=0, description="Trading volume")
    adjusted_close: Optional[Decimal] = Field(
        None, gt=0, description="Adjusted closing price"
    )


class StockPriceResponse(StockPriceBase):
    """Schema for stock price response."""

    id: int
    stock_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class FundamentalBase(BaseModel):
    """Base fundamental data schema."""

    date: datetime = Field(..., description="Report date")
    pe_ratio: Optional[Decimal] = Field(None, description="Price-to-earnings ratio")
    pb_ratio: Optional[Decimal] = Field(None, description="Price-to-book ratio")
    roe: Optional[Decimal] = Field(None, description="Return on equity")
    debt_to_equity: Optional[Decimal] = Field(
        None, ge=0, description="Debt-to-equity ratio"
    )
    revenue: Optional[Decimal] = Field(None, description="Total revenue")
    net_income: Optional[Decimal] = Field(None, description="Net income")
    eps: Optional[Decimal] = Field(None, description="Earnings per share")
    dividend_yield: Optional[Decimal] = Field(
        None, ge=0, le=1, description="Dividend yield"
    )


class FundamentalResponse(FundamentalBase):
    """Schema for fundamental data response."""

    id: int
    stock_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TechnicalIndicatorBase(BaseModel):
    """Base technical indicator schema."""

    date: datetime = Field(..., description="Calculation date")
    sma_20: Optional[Decimal] = Field(None, description="20-day simple moving average")
    sma_50: Optional[Decimal] = Field(None, description="50-day simple moving average")
    sma_200: Optional[Decimal] = Field(
        None, description="200-day simple moving average"
    )
    ema_12: Optional[Decimal] = Field(
        None, description="12-day exponential moving average"
    )
    ema_26: Optional[Decimal] = Field(
        None, description="26-day exponential moving average"
    )
    rsi: Optional[Decimal] = Field(
        None, ge=0, le=100, description="Relative strength index"
    )
    macd: Optional[Decimal] = Field(None, description="MACD line")
    macd_signal: Optional[Decimal] = Field(None, description="MACD signal line")
    bollinger_upper: Optional[Decimal] = Field(None, description="Bollinger upper band")
    bollinger_lower: Optional[Decimal] = Field(None, description="Bollinger lower band")
    atr: Optional[Decimal] = Field(None, ge=0, description="Average true range")


class TechnicalIndicatorResponse(TechnicalIndicatorBase):
    """Schema for technical indicator response."""

    id: int
    stock_id: int
    created_at: datetime

    class Config:
        from_attributes = True
