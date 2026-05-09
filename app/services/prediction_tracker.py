"""
Persistence and evaluation for event-linked market ideas.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.market_intelligence import MarketPredictionAudit
from app.services.real_data_fetcher import RealDataFetcherService


class PredictionTrackerService:
    """Records market ideas and evaluates them after the holding window."""

    def __init__(self, data_fetcher: Optional[RealDataFetcherService] = None):
        self._data_fetcher = data_fetcher

    async def record_market_ideas(
        self, as_of: datetime, ideas: Iterable[Dict[str, Any]], horizon_days: int = 5
    ) -> int:
        """Persist unique idea records for later evaluation."""
        created = 0
        async with AsyncSessionLocal() as session:
            for idea in ideas:
                report_key = self._report_key(as_of, idea)
                existing = await session.scalar(
                    select(MarketPredictionAudit).where(
                        MarketPredictionAudit.report_key == report_key
                    )
                )
                if existing:
                    continue

                current_price = self._as_decimal(idea.get("currentPrice"))
                if current_price is None:
                    continue

                record = MarketPredictionAudit(
                    report_key=report_key,
                    symbol=idea["symbol"],
                    company_name=idea.get("companyName") or idea["symbol"],
                    direction=idea["direction"],
                    topic=idea.get("topic") or "market",
                    catalyst=idea.get("catalyst") or "Market catalyst",
                    horizon_days=horizon_days,
                    baseline_price=current_price,
                    baseline_timestamp=as_of,
                    conviction_score=self._as_decimal(idea.get("score")) or Decimal("0"),
                    confidence_score=self._as_decimal(idea.get("confidence"))
                    or Decimal("0"),
                    reasoning_json=json.dumps(idea.get("reasoning") or []),
                    metrics_json=json.dumps(idea.get("metrics") or {}),
                    source_ids_json=json.dumps(idea.get("sourceIds") or []),
                    status="pending",
                )
                session.add(record)
                created += 1

            if created:
                await session.commit()
        return created

    async def evaluate_due_predictions(self, as_of: Optional[datetime] = None) -> Dict[str, int]:
        """Evaluate any pending records whose holding window has elapsed."""
        as_of = as_of or datetime.utcnow()
        evaluated = 0

        close_fetcher = False
        data_fetcher = self._data_fetcher
        if data_fetcher is None:
            data_fetcher = RealDataFetcherService()
            await data_fetcher.__aenter__()
            close_fetcher = True

        try:
            async with AsyncSessionLocal() as session:
                result = await session.scalars(
                    select(MarketPredictionAudit).where(
                        MarketPredictionAudit.status == "pending"
                    )
                )
                records = list(result)

                for record in records:
                    target_date = record.baseline_timestamp + timedelta(
                        days=record.horizon_days
                    )
                    if as_of < target_date:
                        continue

                    evaluation_price = await self._resolve_evaluation_price(
                        data_fetcher,
                        record.symbol,
                        record.baseline_timestamp,
                        target_date,
                    )
                    if evaluation_price is None or record.baseline_price is None:
                        continue

                    realized_return = (
                        (evaluation_price - record.baseline_price)
                        / record.baseline_price
                        * Decimal("100")
                    )
                    direction = (record.direction or "").lower()
                    is_correct = (
                        realized_return >= Decimal("0.5")
                        if direction == "up"
                        else realized_return <= Decimal("-0.5")
                    )

                    record.evaluated_at = as_of
                    record.evaluation_price = evaluation_price
                    record.realized_return_pct = realized_return.quantize(
                        Decimal("0.0001")
                    )
                    record.status = "correct" if is_correct else "incorrect"
                    record.evaluation_notes = (
                        f"{record.symbol} moved {float(realized_return):.2f}% over "
                        f"{record.horizon_days}d against a {direction} thesis."
                    )
                    evaluated += 1

                if evaluated:
                    await session.commit()
        finally:
            if close_fetcher and data_fetcher:
                await data_fetcher.__aexit__(None, None, None)

        return {"evaluated": evaluated}

    async def scoreboard(self, days: int = 90) -> Dict[str, Any]:
        """Return a simple tracking summary and recent call history."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        async with AsyncSessionLocal() as session:
            result = await session.scalars(
                select(MarketPredictionAudit)
                .where(MarketPredictionAudit.created_at >= cutoff)
                .order_by(MarketPredictionAudit.created_at.desc())
            )
            rows = list(result)

        correct = [row for row in rows if row.status == "correct"]
        incorrect = [row for row in rows if row.status == "incorrect"]
        pending = [row for row in rows if row.status == "pending"]
        evaluated_total = len(correct) + len(incorrect)
        accuracy = (
            round((len(correct) / evaluated_total) * 100, 2) if evaluated_total else None
        )

        return {
            "windowDays": days,
            "totalIdeas": len(rows),
            "evaluatedIdeas": evaluated_total,
            "pendingIdeas": len(pending),
            "correctIdeas": len(correct),
            "incorrectIdeas": len(incorrect),
            "accuracyPct": accuracy,
            "recentIdeas": [self._to_api(row) for row in rows[:12]],
        }

    async def _resolve_evaluation_price(
        self,
        data_fetcher: RealDataFetcherService,
        symbol: str,
        baseline_timestamp: datetime,
        target_date: datetime,
    ) -> Optional[Decimal]:
        historical = await data_fetcher.get_historical_data(
            symbol, max(10, (target_date - baseline_timestamp).days + 5)
        )
        if not historical:
            quote = await data_fetcher.get_stock_quote(symbol)
            return quote.price if quote else None

        for point in historical:
            if point.date >= target_date:
                return point.close
        return historical[-1].close if historical else None

    def _report_key(self, as_of: datetime, idea: Dict[str, Any]) -> str:
        catalyst = (idea.get("catalyst") or "catalyst").lower().replace("|", " ")
        return (
            f"{as_of.date().isoformat()}|{idea['symbol']}|{idea['direction']}|"
            f"{catalyst[:120]}"
        )

    def _to_api(self, row: MarketPredictionAudit) -> Dict[str, Any]:
        return {
            "symbol": row.symbol,
            "companyName": row.company_name,
            "direction": row.direction,
            "topic": row.topic,
            "catalyst": row.catalyst,
            "horizonDays": row.horizon_days,
            "baselinePrice": float(row.baseline_price),
            "baselineTimestamp": row.baseline_timestamp.isoformat(),
            "convictionScore": float(row.conviction_score),
            "confidenceScore": float(row.confidence_score),
            "status": row.status,
            "evaluatedAt": row.evaluated_at.isoformat() if row.evaluated_at else None,
            "evaluationPrice": float(row.evaluation_price)
            if row.evaluation_price is not None
            else None,
            "realizedReturnPct": float(row.realized_return_pct)
            if row.realized_return_pct is not None
            else None,
            "evaluationNotes": row.evaluation_notes,
            "reasoning": json.loads(row.reasoning_json or "[]"),
            "metrics": json.loads(row.metrics_json or "{}"),
            "sourceIds": json.loads(row.source_ids_json or "[]"),
            "createdAt": row.created_at.isoformat(),
        }

    @staticmethod
    def _as_decimal(value: Any) -> Optional[Decimal]:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None
