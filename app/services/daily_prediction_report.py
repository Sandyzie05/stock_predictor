"""
Daily prediction snapshot storage and performance reporting.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.daily_prediction import DailyPredictionSnapshot
from app.services.real_data_fetcher import RealDataFetcherService


class DailyPredictionReportService:
    """Persist daily calls and summarize whether the system is improving."""

    def __init__(self, data_fetcher: Optional[RealDataFetcherService] = None):
        self._data_fetcher = data_fetcher

    async def record_predictions(
        self,
        as_of: datetime,
        ideas: Iterable[Dict[str, Any]],
        horizon_days: int = 1,
        benchmark_symbol: str = "SPY",
    ) -> int:
        """Persist one snapshot per symbol/day so it can be checked the next day."""
        created = 0
        benchmark_price = await self._resolve_baseline_price(benchmark_symbol)
        report_date = as_of.replace(hour=0, minute=0, second=0, microsecond=0)

        async with AsyncSessionLocal() as session:
            for idea in ideas:
                snapshot_key = self._snapshot_key(report_date, idea)
                existing = await session.scalar(
                    select(DailyPredictionSnapshot).where(
                        DailyPredictionSnapshot.snapshot_key == snapshot_key
                    )
                )
                if existing:
                    continue

                baseline_price = self._as_decimal(idea.get("currentPrice"))
                if baseline_price is None:
                    continue

                record = DailyPredictionSnapshot(
                    snapshot_key=snapshot_key,
                    report_date=report_date,
                    symbol=idea["symbol"],
                    company_name=idea.get("companyName") or idea["symbol"],
                    direction=idea["direction"],
                    topic=idea.get("topic") or "market",
                    catalyst=idea.get("catalyst") or "Daily catalyst",
                    horizon_days=horizon_days,
                    baseline_price=baseline_price,
                    baseline_timestamp=as_of,
                    benchmark_symbol=benchmark_symbol,
                    benchmark_baseline_price=benchmark_price,
                    model_version=idea.get("modelVersion"),
                    conviction_score=self._as_decimal(idea.get("score")) or Decimal("0"),
                    confidence_score=self._as_decimal(idea.get("confidence"))
                    or Decimal("0"),
                    reasoning_json=json.dumps(idea.get("reasoning") or []),
                    metrics_json=json.dumps(idea.get("metrics") or {}),
                    source_ids_json=json.dumps(idea.get("sourceIds") or []),
                    evidence_json=json.dumps(idea.get("supportingEvidence") or []),
                    coverage_json=json.dumps(idea.get("coverage") or {}),
                    signal_breakdown_json=json.dumps(
                        idea.get("signalBreakdown") or {}
                    ),
                    local_model_json=json.dumps(idea.get("localModelAnalysis"))
                    if idea.get("localModelAnalysis") is not None
                    else None,
                    local_model_error=idea.get("localModelError"),
                    status="pending",
                )
                session.add(record)
                created += 1

            if created:
                await session.commit()

        return created

    async def evaluate_due_predictions(
        self, as_of: Optional[datetime] = None
    ) -> Dict[str, int]:
        """Resolve any pending snapshots whose verification window has elapsed."""
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
                    select(DailyPredictionSnapshot).where(
                        DailyPredictionSnapshot.status == "pending"
                    )
                )
                rows = list(result)

                for row in rows:
                    target_date = row.baseline_timestamp + timedelta(
                        days=row.horizon_days
                    )
                    if as_of < target_date:
                        continue

                    evaluation_price = await self._resolve_price_on_or_after(
                        data_fetcher,
                        row.symbol,
                        row.baseline_timestamp,
                        target_date,
                    )
                    benchmark_price = await self._resolve_price_on_or_after(
                        data_fetcher,
                        row.benchmark_symbol,
                        row.baseline_timestamp,
                        target_date,
                    )
                    if evaluation_price is None or row.baseline_price is None:
                        continue

                    realized_return = (
                        (evaluation_price - row.baseline_price)
                        / row.baseline_price
                        * Decimal("100")
                    )
                    benchmark_return = None
                    if benchmark_price is not None and row.benchmark_baseline_price:
                        benchmark_return = (
                            (benchmark_price - row.benchmark_baseline_price)
                            / row.benchmark_baseline_price
                            * Decimal("100")
                        )

                    excess_return = (
                        realized_return - benchmark_return
                        if benchmark_return is not None
                        else None
                    )
                    direction_correct = (
                        realized_return >= Decimal("0")
                        if row.direction == "up"
                        else realized_return <= Decimal("0")
                    )

                    row.evaluated_at = as_of
                    row.evaluation_price = evaluation_price
                    row.benchmark_evaluation_price = benchmark_price
                    row.realized_return_pct = realized_return.quantize(
                        Decimal("0.0001")
                    )
                    row.benchmark_return_pct = (
                        benchmark_return.quantize(Decimal("0.0001"))
                        if benchmark_return is not None
                        else None
                    )
                    row.excess_return_pct = (
                        excess_return.quantize(Decimal("0.0001"))
                        if excess_return is not None
                        else None
                    )
                    row.status = "correct" if direction_correct else "incorrect"
                    row.evaluation_notes = self._evaluation_note(
                        row.symbol,
                        row.direction,
                        realized_return,
                        benchmark_return,
                        excess_return,
                    )
                    evaluated += 1

                if evaluated:
                    await session.commit()
        finally:
            if close_fetcher and data_fetcher:
                await data_fetcher.__aexit__(None, None, None)

        return {"evaluated": evaluated}

    async def report(
        self, days: int = 30, as_of: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Return a daily report with recent calls, outcomes, and improvement trend."""
        as_of = as_of or datetime.utcnow()
        await self.evaluate_due_predictions(as_of)

        cutoff = as_of.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
            days=days
        )
        async with AsyncSessionLocal() as session:
            result = await session.scalars(
                select(DailyPredictionSnapshot)
                .where(DailyPredictionSnapshot.report_date >= cutoff)
                .order_by(
                    DailyPredictionSnapshot.report_date.desc(),
                    DailyPredictionSnapshot.created_at.desc(),
                )
            )
            rows = list(result)

        evaluated_rows = [row for row in rows if row.status in {"correct", "incorrect"}]
        today_key = as_of.date().isoformat()
        today_predictions = [
            self._to_api(row)
            for row in rows
            if row.report_date.date().isoformat() == today_key
        ]
        recent_evaluations = [self._to_api(row) for row in evaluated_rows[:10]]
        daily_breakdown = self._daily_breakdown(rows)
        trend = self._trend_summary(evaluated_rows)
        overall = self._overall_summary(rows, evaluated_rows)

        narrative = self._narrative(overall, trend)

        return {
            "asOf": as_of.isoformat(),
            "windowDays": days,
            "overall": overall,
            "trend": trend,
            "narrative": narrative,
            "todayPredictions": today_predictions,
            "recentEvaluations": recent_evaluations,
            "dailyBreakdown": daily_breakdown,
            "localModelPlan": {
                "enabled": settings.ENABLE_LOCAL_LLM,
                "provider": getattr(settings, "LOCAL_LLM_PROVIDER", None) or "planned",
                "baseUrl": settings.LOCAL_LLM_BASE_URL,
                "model": settings.LOCAL_LLM_MODEL,
                "embeddingModel": getattr(settings, "LOCAL_LLM_EMBEDDING_MODEL", None),
                "workflow": [
                    "retrieve fresh evidence from market, news, filing, and macro sources",
                    "rank and filter evidence before prompting the local model",
                    "ask the local model for a structured thesis, counter-arguments, and changed-fact summary",
                    "store the local-model output beside the raw evidence for next-day review",
                ],
            },
        }

    async def _resolve_baseline_price(self, symbol: str) -> Optional[Decimal]:
        close_fetcher = False
        data_fetcher = self._data_fetcher
        if data_fetcher is None:
            data_fetcher = RealDataFetcherService()
            await data_fetcher.__aenter__()
            close_fetcher = True

        try:
            quote = await data_fetcher.get_stock_quote(symbol)
            return quote.price if quote else None
        finally:
            if close_fetcher and data_fetcher:
                await data_fetcher.__aexit__(None, None, None)

    async def _resolve_price_on_or_after(
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

    def _overall_summary(
        self,
        rows: List[DailyPredictionSnapshot],
        evaluated_rows: List[DailyPredictionSnapshot],
    ) -> Dict[str, Any]:
        correct_count = len([row for row in evaluated_rows if row.status == "correct"])
        accuracy = (
            round((correct_count / len(evaluated_rows)) * 100, 2)
            if evaluated_rows
            else None
        )
        avg_return = self._average_decimal(
            row.realized_return_pct for row in evaluated_rows
        )
        avg_benchmark = self._average_decimal(
            row.benchmark_return_pct for row in evaluated_rows
        )
        avg_excess = self._average_decimal(
            row.excess_return_pct for row in evaluated_rows
        )

        return {
            "totalPredictions": len(rows),
            "evaluatedPredictions": len(evaluated_rows),
            "pendingPredictions": len([row for row in rows if row.status == "pending"]),
            "correctPredictions": correct_count,
            "incorrectPredictions": len(
                [row for row in evaluated_rows if row.status == "incorrect"]
            ),
            "accuracyPct": accuracy,
            "averageReturnPct": avg_return,
            "averageBenchmarkReturnPct": avg_benchmark,
            "averageExcessReturnPct": avg_excess,
        }

    def _daily_breakdown(
        self, rows: List[DailyPredictionSnapshot]
    ) -> List[Dict[str, Any]]:
        grouped: Dict[str, List[DailyPredictionSnapshot]] = defaultdict(list)
        for row in rows:
            grouped[row.report_date.date().isoformat()].append(row)

        breakdown = []
        for report_date in sorted(grouped.keys(), reverse=True):
            bucket = grouped[report_date]
            evaluated = [row for row in bucket if row.status in {"correct", "incorrect"}]
            correct = len([row for row in evaluated if row.status == "correct"])
            breakdown.append(
                {
                    "reportDate": report_date,
                    "totalPredictions": len(bucket),
                    "evaluatedPredictions": len(evaluated),
                    "accuracyPct": round((correct / len(evaluated)) * 100, 2)
                    if evaluated
                    else None,
                    "averageExcessReturnPct": self._average_decimal(
                        row.excess_return_pct for row in evaluated
                    ),
                }
            )
        return breakdown

    def _trend_summary(
        self, evaluated_rows: List[DailyPredictionSnapshot]
    ) -> Dict[str, Any]:
        if not evaluated_rows:
            return {
                "status": "insufficient-history",
                "message": "No evaluated daily predictions yet.",
            }

        recent = evaluated_rows[:7]
        prior = evaluated_rows[7:14]
        recent_accuracy = self._accuracy_for(recent)
        prior_accuracy = self._accuracy_for(prior)
        recent_excess = self._average_decimal(row.excess_return_pct for row in recent)
        prior_excess = self._average_decimal(row.excess_return_pct for row in prior)

        status = "stable"
        if recent_accuracy is not None and prior_accuracy is not None:
            if recent_accuracy > prior_accuracy:
                status = "improving"
            elif recent_accuracy < prior_accuracy:
                status = "slipping"

        return {
            "status": status,
            "recentWindowEvaluated": len(recent),
            "priorWindowEvaluated": len(prior),
            "recentAccuracyPct": recent_accuracy,
            "priorAccuracyPct": prior_accuracy,
            "recentAverageExcessReturnPct": recent_excess,
            "priorAverageExcessReturnPct": prior_excess,
        }

    def _narrative(self, overall: Dict[str, Any], trend: Dict[str, Any]) -> List[str]:
        lines = []
        accuracy = overall.get("accuracyPct")
        if accuracy is None:
            lines.append(
                "Daily prediction snapshots are being stored, but not enough next-day outcomes have settled yet."
            )
        else:
            lines.append(
                f"Daily next-day accuracy is {accuracy:.2f}% across "
                f"{overall['evaluatedPredictions']} evaluated calls."
            )

        avg_excess = overall.get("averageExcessReturnPct")
        if avg_excess is not None:
            lines.append(
                f"Average excess return versus the benchmark is {avg_excess:.4f}%."
            )

        if trend.get("status") == "improving":
            lines.append("Recent evaluated calls are improving versus the prior window.")
        elif trend.get("status") == "slipping":
            lines.append("Recent evaluated calls are weaker than the prior window and need review.")
        else:
            lines.append(trend.get("message") or "Recent performance looks broadly stable.")

        lines.append(
            "Each stored prediction keeps its evidence links, raw reasoning, and benchmark comparison so we can audit why it worked or failed."
        )
        return lines

    def _to_api(self, row: DailyPredictionSnapshot) -> Dict[str, Any]:
        return {
            "reportDate": row.report_date.date().isoformat(),
            "symbol": row.symbol,
            "companyName": row.company_name,
            "direction": row.direction,
            "topic": row.topic,
            "catalyst": row.catalyst,
            "horizonDays": row.horizon_days,
            "baselinePrice": float(row.baseline_price),
            "baselineTimestamp": row.baseline_timestamp.isoformat(),
            "benchmarkSymbol": row.benchmark_symbol,
            "benchmarkBaselinePrice": float(row.benchmark_baseline_price)
            if row.benchmark_baseline_price is not None
            else None,
            "modelVersion": row.model_version,
            "convictionScore": float(row.conviction_score),
            "confidenceScore": float(row.confidence_score),
            "status": row.status,
            "reasoning": json.loads(row.reasoning_json or "[]"),
            "metrics": json.loads(row.metrics_json or "{}"),
            "sourceIds": json.loads(row.source_ids_json or "[]"),
            "supportingEvidence": json.loads(row.evidence_json or "[]"),
            "coverage": json.loads(row.coverage_json or "{}"),
            "signalBreakdown": json.loads(row.signal_breakdown_json or "{}"),
            "localModelAnalysis": json.loads(row.local_model_json)
            if row.local_model_json
            else None,
            "localModelError": row.local_model_error,
            "evaluatedAt": row.evaluated_at.isoformat() if row.evaluated_at else None,
            "evaluationPrice": float(row.evaluation_price)
            if row.evaluation_price is not None
            else None,
            "benchmarkEvaluationPrice": float(row.benchmark_evaluation_price)
            if row.benchmark_evaluation_price is not None
            else None,
            "realizedReturnPct": float(row.realized_return_pct)
            if row.realized_return_pct is not None
            else None,
            "benchmarkReturnPct": float(row.benchmark_return_pct)
            if row.benchmark_return_pct is not None
            else None,
            "excessReturnPct": float(row.excess_return_pct)
            if row.excess_return_pct is not None
            else None,
            "evaluationNotes": row.evaluation_notes,
            "createdAt": row.created_at.isoformat(),
        }

    @staticmethod
    def _snapshot_key(report_date: datetime, idea: Dict[str, Any]) -> str:
        catalyst = (idea.get("catalyst") or "catalyst").lower().replace("|", " ")
        return (
            f"{report_date.date().isoformat()}|{idea['symbol']}|{idea['direction']}|"
            f"{catalyst[:120]}"
        )

    @staticmethod
    def _evaluation_note(
        symbol: str,
        direction: str,
        realized_return: Decimal,
        benchmark_return: Optional[Decimal],
        excess_return: Optional[Decimal],
    ) -> str:
        base = (
            f"{symbol} moved {float(realized_return):.2f}% the next session "
            f"against an expected {direction} move."
        )
        if benchmark_return is None or excess_return is None:
            return base
        return (
            f"{base} Benchmark moved {float(benchmark_return):.2f}%, "
            f"so excess return was {float(excess_return):.2f}%."
        )

    @staticmethod
    def _accuracy_for(rows: List[DailyPredictionSnapshot]) -> Optional[float]:
        if not rows:
            return None
        correct = len([row for row in rows if row.status == "correct"])
        return round((correct / len(rows)) * 100, 2)

    @staticmethod
    def _average_decimal(values: Iterable[Optional[Decimal]]) -> Optional[float]:
        normalized = [float(value) for value in values if value is not None]
        if not normalized:
            return None
        return round(sum(normalized) / len(normalized), 4)

    @staticmethod
    def _as_decimal(value: Any) -> Optional[Decimal]:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None
