"""
Tests for prediction models.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.models.prediction import Prediction, RecommendationType


class TestPrediction:
    """Test Prediction model."""

    @pytest.mark.asyncio
    async def test_create_prediction(
        self, db_session, sample_stock, sample_prediction_data
    ):
        """Test creating a prediction."""
        prediction_data = sample_prediction_data.copy()
        prediction_data["stock_id"] = sample_stock.id

        prediction = Prediction(**prediction_data)
        db_session.add(prediction)
        await db_session.commit()
        await db_session.refresh(prediction)

        assert prediction.id is not None
        assert prediction.stock_id == sample_stock.id
        assert prediction.model_version == "v1.0.0"
        assert prediction.predicted_price == Decimal("160.00")
        assert prediction.confidence_score == Decimal("0.85")
        assert prediction.recommendation == RecommendationType.BUY
        assert (
            prediction.reasoning
            == "Strong fundamentals and positive technical indicators."
        )
        assert prediction.is_active is True
        assert isinstance(prediction.prediction_date, datetime)
        assert isinstance(prediction.target_date, datetime)
        assert isinstance(prediction.created_at, datetime)
        assert isinstance(prediction.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_prediction_minimal_creation(self, db_session, sample_stock):
        """Test creating prediction with minimal required fields."""
        prediction = Prediction(
            stock_id=sample_stock.id,
            model_version="v2.0.0",
            prediction_date=datetime.utcnow(),
            target_date=datetime.utcnow() + timedelta(days=7),
            predicted_price=Decimal("175.00"),
            confidence_score=Decimal("0.75"),
            recommendation=RecommendationType.HOLD,
        )
        db_session.add(prediction)
        await db_session.commit()
        await db_session.refresh(prediction)

        assert prediction.reasoning is None
        assert prediction.actual_price is None
        assert prediction.accuracy_score is None
        assert prediction.is_active is True

    @pytest.mark.asyncio
    async def test_recommendation_types(self, db_session, sample_stock):
        """Test all recommendation types."""
        recommendations = [
            (RecommendationType.BUY, "Strong buy signal"),
            (RecommendationType.SELL, "Bearish outlook"),
            (RecommendationType.HOLD, "Neutral position"),
        ]

        for rec_type, reasoning in recommendations:
            prediction = Prediction(
                stock_id=sample_stock.id,
                model_version="v1.0.0",
                prediction_date=datetime.utcnow(),
                target_date=datetime.utcnow() + timedelta(days=30),
                predicted_price=Decimal("150.00"),
                confidence_score=Decimal("0.8"),
                recommendation=rec_type,
                reasoning=reasoning,
            )
            db_session.add(prediction)

        await db_session.commit()

    @pytest.mark.asyncio
    async def test_prediction_with_actual_results(self, db_session, sample_stock):
        """Test updating prediction with actual results."""
        # Create prediction
        prediction = Prediction(
            stock_id=sample_stock.id,
            model_version="v1.0.0",
            prediction_date=datetime.utcnow() - timedelta(days=30),
            target_date=datetime.utcnow(),
            predicted_price=Decimal("160.00"),
            confidence_score=Decimal("0.85"),
            recommendation=RecommendationType.BUY,
        )
        db_session.add(prediction)
        await db_session.commit()
        await db_session.refresh(prediction)

        # Update with actual results
        prediction.actual_price = Decimal("158.50")
        prediction.accuracy_score = Decimal("0.92")  # Close to predicted

        await db_session.commit()
        await db_session.refresh(prediction)

        assert prediction.actual_price == Decimal("158.50")
        assert prediction.accuracy_score == Decimal("0.92")

    @pytest.mark.asyncio
    async def test_multiple_predictions_same_stock(self, db_session, sample_stock):
        """Test multiple predictions for the same stock."""
        base_date = datetime.utcnow()

        predictions_data = [
            {
                "model_version": "v1.0.0",
                "target_days": 7,
                "predicted_price": Decimal("155.00"),
                "recommendation": RecommendationType.BUY,
            },
            {
                "model_version": "v1.0.0",
                "target_days": 30,
                "predicted_price": Decimal("165.00"),
                "recommendation": RecommendationType.BUY,
            },
            {
                "model_version": "v2.0.0",
                "target_days": 7,
                "predicted_price": Decimal("150.00"),
                "recommendation": RecommendationType.HOLD,
            },
        ]

        for pred_data in predictions_data:
            prediction = Prediction(
                stock_id=sample_stock.id,
                model_version=pred_data["model_version"],
                prediction_date=base_date,
                target_date=base_date + timedelta(days=pred_data["target_days"]),
                predicted_price=pred_data["predicted_price"],
                confidence_score=Decimal("0.8"),
                recommendation=pred_data["recommendation"],
            )
            db_session.add(prediction)

        await db_session.commit()

    @pytest.mark.asyncio
    async def test_prediction_deactivation(self, sample_prediction):
        """Test deactivating predictions."""
        assert sample_prediction.is_active is True

        # Deactivate prediction (e.g., when model is updated)
        sample_prediction.is_active = False

        # Would normally commit here, but fixture handles rollback
        assert sample_prediction.is_active is False

    @pytest.mark.asyncio
    async def test_confidence_score_bounds(self, db_session, sample_stock):
        """Test confidence score boundaries."""
        # Test minimum confidence (0.0)
        prediction_min = Prediction(
            stock_id=sample_stock.id,
            model_version="v1.0.0",
            prediction_date=datetime.utcnow(),
            target_date=datetime.utcnow() + timedelta(days=7),
            predicted_price=Decimal("150.00"),
            confidence_score=Decimal("0.0"),
            recommendation=RecommendationType.HOLD,
        )

        # Test maximum confidence (1.0)
        prediction_max = Prediction(
            stock_id=sample_stock.id,
            model_version="v1.0.0",
            prediction_date=datetime.utcnow(),
            target_date=datetime.utcnow() + timedelta(days=7),
            predicted_price=Decimal("150.00"),
            confidence_score=Decimal("1.0"),
            recommendation=RecommendationType.BUY,
        )

        db_session.add_all([prediction_min, prediction_max])
        await db_session.commit()

        await db_session.refresh(prediction_min)
        await db_session.refresh(prediction_max)

        assert prediction_min.confidence_score == Decimal("0.0")
        assert prediction_max.confidence_score == Decimal("1.0")


class TestRecommendationType:
    """Test RecommendationType enum."""

    def test_recommendation_values(self):
        """Test recommendation type values."""
        assert RecommendationType.BUY.value == "buy"
        assert RecommendationType.SELL.value == "sell"
        assert RecommendationType.HOLD.value == "hold"

    def test_recommendation_string_representation(self):
        """Test string representation of recommendation types."""
        assert str(RecommendationType.BUY) == "RecommendationType.BUY"
        assert RecommendationType.BUY.name == "BUY"

    def test_recommendation_equality(self):
        """Test recommendation type equality."""
        assert RecommendationType.BUY == RecommendationType.BUY
        assert RecommendationType.BUY != RecommendationType.SELL

    def test_recommendation_from_string(self):
        """Test creating recommendation from string value."""
        assert RecommendationType("buy") == RecommendationType.BUY
        assert RecommendationType("sell") == RecommendationType.SELL
        assert RecommendationType("hold") == RecommendationType.HOLD
