"""
Stock-related database models.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Stock(Base):
    """Stock master data model."""

    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    sector: Mapped[Optional[str]] = mapped_column(String(100))
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    market_cap: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=20, scale=2)
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_sp500: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    prices = relationship("StockPrice", back_populates="stock")
    fundamentals = relationship("Fundamental", back_populates="stock")
    technical_indicators = relationship("TechnicalIndicator", back_populates="stock")
    predictions = relationship("Prediction", back_populates="stock")
    news_sentiment = relationship("NewsSentiment", back_populates="stock")


class StockPrice(Base):
    """Historical stock price data model."""

    __tablename__ = "stock_prices"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    open_price: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=4))
    high: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=4))
    low: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=4))
    close: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=4))
    volume: Mapped[int] = mapped_column(BigInteger)
    adjusted_close: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=4)
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    stock = relationship("Stock", back_populates="prices")

    # Indexes for performance
    __table_args__ = (Index("idx_stock_date", "stock_id", "date"),)


class Fundamental(Base):
    """Company fundamental data model."""

    __tablename__ = "fundamentals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    pe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=10, scale=4))
    pb_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=10, scale=4))
    roe: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=8, scale=6))
    debt_to_equity: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=8, scale=4)
    )
    revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=20, scale=2))
    net_income: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=20, scale=2)
    )
    eps: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=10, scale=4))
    dividend_yield: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=6, scale=4)
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    stock = relationship("Stock", back_populates="fundamentals")

    # Indexes
    __table_args__ = (Index("idx_fund_stock_date", "stock_id", "date"),)


class TechnicalIndicator(Base):
    """Technical indicators data model."""

    __tablename__ = "technical_indicators"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    sma_20: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=10, scale=4))
    sma_50: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=10, scale=4))
    sma_200: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=10, scale=4))
    ema_12: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=10, scale=4))
    ema_26: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=10, scale=4))
    rsi: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=6, scale=3))
    macd: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=10, scale=6))
    macd_signal: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=6)
    )
    bollinger_upper: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=4)
    )
    bollinger_lower: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=4)
    )
    atr: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=10, scale=4))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    stock = relationship("Stock", back_populates="technical_indicators")

    # Indexes
    __table_args__ = (Index("idx_tech_stock_date", "stock_id", "date"),)
