"""
News and sentiment analysis schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, validator


class NewsSentimentBase(BaseModel):
    """Base news sentiment schema."""

    headline: str = Field(
        ..., min_length=1, max_length=500, description="News headline"
    )
    summary: Optional[str] = Field(None, description="News summary")
    content: Optional[str] = Field(None, description="Full news content")
    sentiment_score: Decimal = Field(
        ..., ge=-1, le=1, description="Sentiment score (-1 to 1)"
    )
    sentiment_label: str = Field(..., description="Sentiment label")
    source: str = Field(..., min_length=1, max_length=100, description="News source")
    url: Optional[HttpUrl] = Field(None, description="News article URL")
    author: Optional[str] = Field(None, max_length=200, description="Article author")
    relevance_score: Optional[Decimal] = Field(
        None, ge=0, le=1, description="Relevance score"
    )

    @validator("sentiment_label")
    @classmethod
    def validate_sentiment_label(cls, v):
        """Validate sentiment label."""
        allowed_labels = {"positive", "negative", "neutral"}
        if v.lower() not in allowed_labels:
            raise ValueError(f"Sentiment label must be one of {allowed_labels}")
        return v.lower()


class NewsSentimentCreate(NewsSentimentBase):
    """Schema for creating news sentiment."""

    stock_id: int = Field(..., gt=0, description="Stock ID")
    date: datetime = Field(..., description="News date")


class NewsSentimentResponse(NewsSentimentBase):
    """Schema for news sentiment response."""

    id: int
    stock_id: int
    date: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class SentimentAnalysis(BaseModel):
    """Aggregate sentiment analysis for a stock."""

    stock_symbol: str
    period_start: datetime
    period_end: datetime
    total_articles: int = Field(..., ge=0)
    positive_count: int = Field(..., ge=0)
    negative_count: int = Field(..., ge=0)
    neutral_count: int = Field(..., ge=0)
    average_sentiment: Decimal = Field(..., ge=-1, le=1)
    sentiment_trend: str = Field(..., description="Improving, Declining, or Stable")
    most_relevant_news: list[NewsSentimentResponse] = Field(
        default=[], description="Top relevant news"
    )

    @validator("sentiment_trend")
    @classmethod
    def validate_sentiment_trend(cls, v):
        """Validate sentiment trend."""
        allowed_trends = {"improving", "declining", "stable"}
        if v.lower() not in allowed_trends:
            raise ValueError(f"Sentiment trend must be one of {allowed_trends}")
        return v.lower()
