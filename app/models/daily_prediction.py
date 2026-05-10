"""
Persistence models for daily prediction snapshots and evaluations.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DailyPredictionSnapshot(Base):
    """Stores daily stock calls with source evidence for next-day validation."""

    __tablename__ = "daily_prediction_snapshot"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    snapshot_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    report_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    company_name: Mapped[str] = mapped_column(String(255))
    direction: Mapped[str] = mapped_column(String(16), index=True)
    topic: Mapped[str] = mapped_column(String(80), index=True)
    catalyst: Mapped[str] = mapped_column(String(255))
    horizon_days: Mapped[int] = mapped_column(default=1)
    baseline_price: Mapped[Decimal] = mapped_column(Numeric(precision=12, scale=4))
    baseline_timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    benchmark_symbol: Mapped[str] = mapped_column(String(16), default="SPY")
    benchmark_baseline_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=12, scale=4), nullable=True
    )
    model_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    conviction_score: Mapped[Decimal] = mapped_column(Numeric(precision=8, scale=4))
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(precision=8, scale=4))
    reasoning_json: Mapped[str] = mapped_column(Text)
    metrics_json: Mapped[str] = mapped_column(Text)
    source_ids_json: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[str] = mapped_column(Text)
    coverage_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    signal_breakdown_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    local_model_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    local_model_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    evaluation_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=12, scale=4), nullable=True
    )
    benchmark_evaluation_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=12, scale=4), nullable=True
    )
    realized_return_pct: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=4), nullable=True
    )
    benchmark_return_pct: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=4), nullable=True
    )
    excess_return_pct: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=4), nullable=True
    )
    evaluation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_daily_prediction_symbol_date", "symbol", "report_date"),
        Index("idx_daily_prediction_status_date", "status", "report_date"),
    )
