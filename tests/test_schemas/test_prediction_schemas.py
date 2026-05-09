"""
Tests for prediction schemas.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.prediction import RecommendationType
from app.schemas.prediction import (PredictionBase, PredictionCreate,
                                    PredictionResponse, PredictionUpdate,
                                    RecommendationSummary)


class TestPredictionBase:
    """Test PredictionBase schema."""

    def test_valid_prediction_base(self):
        """Test valid prediction base creation."""
        target_date = datetime.utcnow() + timedelta(days=30)

        prediction_data = {
            "target_date": target_date,
            "predicted_price": Decimal("160.00"),
            "confidence_score": Decimal("0.85"),
            "recommendation": RecommendationType.BUY,
            "reasoning": "Strong fundamentals and positive technical indicators.",
        }

        prediction = PredictionBase(**prediction_data)

        assert prediction.target_date == target_date
        assert prediction.predicted_price == Decimal("160.00")
        assert prediction.confidence_score == Decimal("0.85")
        assert prediction.recommendation == RecommendationType.BUY
        assert (
            prediction.reasoning
            == "Strong fundamentals and positive technical indicators."
        )

    def test_prediction_base_minimal(self):
        """Test prediction with minimal required fields."""
        target_date = datetime.utcnow() + timedelta(days=7)

        prediction = PredictionBase(
            target_date=target_date,
            predicted_price=Decimal("150.00"),
            confidence_score=Decimal("0.7"),
            recommendation=RecommendationType.HOLD,
        )

        assert prediction.reasoning is None
        assert prediction.target_date == target_date

    def test_target_date_validation_future(self):
        """Test that target date must be in the future."""
        past_date = datetime.utcnow() - timedelta(days=1)

        with pytest.raises(ValidationError) as exc_info:
            PredictionBase(
                target_date=past_date,
                predicted_price=Decimal("150.00"),
                confidence_score=Decimal("0.7"),
                recommendation=RecommendationType.HOLD,
            )

        assert "Target date must be in the future" in str(exc_info.value)

    def test_predicted_price_validation(self):
        """Test predicted price validation."""
        target_date = datetime.utcnow() + timedelta(days=7)

        # Zero or negative price should fail
        with pytest.raises(ValidationError):
            PredictionBase(
                target_date=target_date,
                predicted_price=Decimal("0"),
                confidence_score=Decimal("0.7"),
                recommendation=RecommendationType.HOLD,
            )

        with pytest.raises(ValidationError):
            PredictionBase(
                target_date=target_date,
                predicted_price=Decimal("-10.00"),
                confidence_score=Decimal("0.7"),
                recommendation=RecommendationType.HOLD,
            )

    def test_confidence_score_validation(self):
        """Test confidence score validation (0-1 range)."""
        target_date = datetime.utcnow() + timedelta(days=7)
        base_data = {
            "target_date": target_date,
            "predicted_price": Decimal("150.00"),
            "recommendation": RecommendationType.HOLD,
        }

        # Confidence above 1 should fail
        with pytest.raises(ValidationError):
            PredictionBase(**{**base_data, "confidence_score": Decimal("1.1")})

        # Negative confidence should fail
        with pytest.raises(ValidationError):
            PredictionBase(**{**base_data, "confidence_score": Decimal("-0.1")})

        # Valid confidence values
        for confidence in [Decimal("0"), Decimal("0.5"), Decimal("1")]:
            prediction = PredictionBase(**{**base_data, "confidence_score": confidence})
            assert prediction.confidence_score == confidence


class TestPredictionCreate:
    """Test PredictionCreate schema."""

    def test_prediction_create_with_stock_id(self):
        """Test creating prediction with stock ID."""
        target_date = datetime.utcnow() + timedelta(days=15)

        prediction = PredictionCreate(
            stock_id=1,
            model_version="v1.0.0",
            target_date=target_date,
            predicted_price=Decimal("175.00"),
            confidence_score=Decimal("0.9"),
            recommendation=RecommendationType.BUY,
        )

        assert prediction.stock_id == 1
        assert prediction.model_version == "v1.0.0"

    def test_stock_id_validation(self):
        """Test stock ID validation."""
        target_date = datetime.utcnow() + timedelta(days=7)

        # Zero or negative stock ID should fail
        with pytest.raises(ValidationError):
            PredictionCreate(
                stock_id=0,
                model_version="v1.0.0",
                target_date=target_date,
                predicted_price=Decimal("150.00"),
                confidence_score=Decimal("0.8"),
                recommendation=RecommendationType.HOLD,
            )

    def test_model_version_validation(self):
        """Test model version validation."""
        target_date = datetime.utcnow() + timedelta(days=7)
        base_data = {
            "stock_id": 1,
            "target_date": target_date,
            "predicted_price": Decimal("150.00"),
            "confidence_score": Decimal("0.8"),
            "recommendation": RecommendationType.HOLD,
        }

        # Empty model version should fail
        with pytest.raises(ValidationError):
            PredictionCreate(**{**base_data, "model_version": ""})

        # Too long model version should fail
        with pytest.raises(ValidationError):
            PredictionCreate(**{**base_data, "model_version": "x" * 51})


class TestPredictionUpdate:
    """Test PredictionUpdate schema."""

    def test_prediction_update_partial(self):
        """Test partial prediction update."""
        update = PredictionUpdate(
            actual_price=Decimal("158.50"), accuracy_score=Decimal("0.95")
        )

        assert update.actual_price == Decimal("158.50")
        assert update.accuracy_score == Decimal("0.95")
        assert update.is_active is None

    def test_prediction_update_all_none(self):
        """Test update with all None values."""
        update = PredictionUpdate()

        assert update.actual_price is None
        assert update.accuracy_score is None
        assert update.is_active is None

    def test_actual_price_validation(self):
        """Test actual price validation."""
        # Negative actual price should fail
        with pytest.raises(ValidationError):
            PredictionUpdate(actual_price=Decimal("-10.00"))

        # Zero actual price should fail
        with pytest.raises(ValidationError):
            PredictionUpdate(actual_price=Decimal("0"))

    def test_accuracy_score_validation(self):
        """Test accuracy score validation."""
        # Accuracy above 1 should fail
        with pytest.raises(ValidationError):
            PredictionUpdate(accuracy_score=Decimal("1.1"))

        # Negative accuracy should fail
        with pytest.raises(ValidationError):
            PredictionUpdate(accuracy_score=Decimal("-0.1"))


class TestPredictionResponse:
    """Test PredictionResponse schema."""

    def test_prediction_response_from_model(self, sample_prediction):
        """Test creating response from database model."""
        response = PredictionResponse.from_orm(sample_prediction)

        assert response.id == sample_prediction.id
        assert response.stock_id == sample_prediction.stock_id
        assert response.model_version == sample_prediction.model_version
        assert response.predicted_price == sample_prediction.predicted_price
        assert response.recommendation == sample_prediction.recommendation
        assert response.is_active == sample_prediction.is_active


class TestRecommendationSummary:
    """Test RecommendationSummary schema."""

    def test_valid_recommendation_summary(self):
        """Test valid recommendation summary creation."""
        summary_data = {
            "stock_symbol": "AAPL",
            "current_price": Decimal("150.00"),
            "latest_recommendation": RecommendationType.BUY,
            "confidence_score": Decimal("0.85"),
            "target_price": Decimal("165.00"),
            "potential_return": Decimal("10.0"),
            "risk_level": "Medium",
            "last_updated": datetime.utcnow(),
        }

        summary = RecommendationSummary(**summary_data)

        assert summary.stock_symbol == "AAPL"
        assert summary.latest_recommendation == RecommendationType.BUY
        assert summary.potential_return == Decimal("10.0")
        assert summary.risk_level == "Medium"

    def test_recommendation_summary_minimal(self):
        """Test recommendation summary with minimal fields."""
        summary = RecommendationSummary(
            stock_symbol="MSFT",
            latest_recommendation=RecommendationType.HOLD,
            confidence_score=Decimal("0.7"),
            target_price=Decimal("200.00"),
            last_updated=datetime.utcnow(),
        )

        assert summary.current_price is None
        assert summary.potential_return is None
        assert summary.risk_level is None

    def test_all_recommendation_types_in_summary(self):
        """Test all recommendation types in summary."""
        base_data = {
            "stock_symbol": "TEST",
            "confidence_score": Decimal("0.8"),
            "target_price": Decimal("100.00"),
            "last_updated": datetime.utcnow(),
        }

        for rec_type in [
            RecommendationType.BUY,
            RecommendationType.SELL,
            RecommendationType.HOLD,
        ]:
            summary = RecommendationSummary(
                **{**base_data, "latest_recommendation": rec_type}
            )
            assert summary.latest_recommendation == rec_type
