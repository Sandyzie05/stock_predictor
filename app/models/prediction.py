"""
Prediction and recommendation models.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RecommendationType(str, Enum):
    """Recommendation types."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class Prediction(Base):
    """Stock prediction and recommendation model."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    model_version: Mapped[str] = mapped_column(String(50))
    prediction_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    target_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    predicted_price: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=4))
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(precision=4, scale=3))
    recommendation: Mapped[RecommendationType] = mapped_column(
        SQLEnum(RecommendationType)
    )
    reasoning: Mapped[Optional[str]] = mapped_column(Text)
    actual_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=4)
    )
    accuracy_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=4, scale=3)
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    stock = relationship("Stock", back_populates="predictions")

    # Indexes
    __table_args__ = (
        Index("idx_pred_stock_date", "stock_id", "prediction_date"),
        Index("idx_pred_target_date", "target_date"),
        Index("idx_pred_recommendation", "recommendation"),
    )
