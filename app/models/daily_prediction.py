"""
Persistence models for daily prediction snapshots and evaluations.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    scenario: Mapped[Optional["DailyPredictionScenario"]] = relationship(
        back_populates="snapshot",
        uselist=False,
        cascade="all, delete-orphan",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_daily_prediction_symbol_date", "symbol", "report_date"),
        Index("idx_daily_prediction_status_date", "status", "report_date"),
    )


class DailyPredictionScenario(Base):
    """Stores the local multi-agent scenario review for a daily snapshot."""

    __tablename__ = "daily_prediction_scenario"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    snapshot_key: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("daily_prediction_snapshot.snapshot_key"),
        unique=True,
        index=True,
    )
    report_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    agent_count: Mapped[int] = mapped_column(Integer, default=0)
    scenario_verdict: Mapped[str] = mapped_column(String(20), index=True)
    support_score: Mapped[Decimal] = mapped_column(Numeric(precision=8, scale=4))
    disagreement_score: Mapped[Decimal] = mapped_column(Numeric(precision=8, scale=4))
    fragility_score: Mapped[Decimal] = mapped_column(Numeric(precision=8, scale=4))
    summary_text: Mapped[str] = mapped_column(Text)
    watch_next_session_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agents_json: Mapped[str] = mapped_column(Text)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    snapshot: Mapped["DailyPredictionSnapshot"] = relationship(back_populates="scenario")

    __table_args__ = (
        Index("idx_daily_prediction_scenario_symbol_date", "symbol", "report_date"),
    )
