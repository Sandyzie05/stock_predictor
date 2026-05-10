"""
News and sentiment analysis models.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class NewsSentiment(Base):
    """News sentiment analysis model."""

    __tablename__ = "news_sentiment"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    date: Mapped[datetime] = mapped_column(DateTime, index=True)
    headline: Mapped[str] = mapped_column(String(500))
    summary: Mapped[Optional[str]] = mapped_column(Text)
    content: Mapped[Optional[str]] = mapped_column(Text)
    sentiment_score: Mapped[Decimal] = mapped_column(Numeric(precision=4, scale=3))
    sentiment_label: Mapped[str] = mapped_column(
        String(20)
    )  # positive, negative, neutral
    source: Mapped[str] = mapped_column(String(100))
    url: Mapped[Optional[str]] = mapped_column(Text)
    author: Mapped[Optional[str]] = mapped_column(String(200))
    relevance_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=4, scale=3)
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    stock = relationship("Stock", back_populates="news_sentiment")

    # Indexes
    __table_args__ = (
        Index("idx_news_stock_date", "stock_id", "date"),
        Index("idx_news_sentiment", "sentiment_label"),
        Index("idx_news_source", "source"),
    )
