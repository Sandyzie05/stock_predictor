"""
Prediction and recommendation schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, validator

from app.models.prediction import RecommendationType


class PredictionBase(BaseModel):
    """Base prediction schema."""

    target_date: datetime = Field(..., description="Target prediction date")
    predicted_price: Decimal = Field(..., gt=0, description="Predicted stock price")
    confidence_score: Decimal = Field(
        ..., ge=0, le=1, description="Prediction confidence"
    )
    recommendation: RecommendationType = Field(
        ..., description="Investment recommendation"
    )
    reasoning: Optional[str] = Field(None, description="Reasoning for the prediction")

    @validator("target_date")
    @classmethod
    def target_date_must_be_future(cls, v):
        """Validate that target date is in the future."""
        if v <= datetime.utcnow():
            raise ValueError("Target date must be in the future")
        return v


class PredictionCreate(PredictionBase):
    """Schema for creating a prediction."""

    stock_id: int = Field(..., gt=0, description="Stock ID")
    model_version: str = Field(
        ..., min_length=1, max_length=50, description="Model version"
    )


class PredictionUpdate(BaseModel):
    """Schema for updating a prediction."""

    actual_price: Optional[Decimal] = Field(
        None, gt=0, description="Actual stock price"
    )
    accuracy_score: Optional[Decimal] = Field(
        None, ge=0, le=1, description="Prediction accuracy"
    )
    is_active: Optional[bool] = Field(None, description="Is prediction active")


class PredictionResponse(PredictionBase):
    """Schema for prediction response."""

    id: int
    stock_id: int
    model_version: str
    prediction_date: datetime
    actual_price: Optional[Decimal]
    accuracy_score: Optional[Decimal]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RecommendationSummary(BaseModel):
    """Summary of recommendations for a stock."""

    stock_symbol: str
    current_price: Optional[Decimal]
    latest_recommendation: RecommendationType
    confidence_score: Decimal
    target_price: Decimal
    potential_return: Optional[Decimal] = Field(
        None, description="Expected return percentage"
    )
    risk_level: Optional[str] = Field(None, description="Risk assessment")
    last_updated: datetime
