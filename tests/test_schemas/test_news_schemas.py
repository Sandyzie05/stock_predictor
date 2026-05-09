"""
Tests for news sentiment schemas.
"""

from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.news import (NewsSentimentBase, NewsSentimentCreate,
                              NewsSentimentResponse, SentimentAnalysis)


class TestNewsSentimentBase:
    """Test NewsSentimentBase schema."""

    def test_valid_news_sentiment_base(self):
        """Test valid news sentiment creation."""
        news_data = {
            "headline": "Apple Reports Strong Quarterly Results",
            "summary": "Apple exceeded analyst expectations.",
            "content": "Full article content here...",
            "sentiment_score": Decimal("0.8"),
            "sentiment_label": "positive",
            "source": "Reuters",
            "url": "https://example.com/news/apple-results",
            "author": "John Doe",
            "relevance_score": Decimal("0.9"),
        }

        news = NewsSentimentBase(**news_data)

        assert news.headline == "Apple Reports Strong Quarterly Results"
        assert news.sentiment_score == Decimal("0.8")
        assert news.sentiment_label == "positive"
        assert news.source == "Reuters"
        assert news.relevance_score == Decimal("0.9")

    def test_news_sentiment_minimal(self):
        """Test news sentiment with minimal required fields."""
        news = NewsSentimentBase(
            headline="Simple Headline",
            sentiment_score=Decimal("0.1"),
            sentiment_label="neutral",
            source="Test Source",
        )

        assert news.summary is None
        assert news.content is None
        assert news.url is None
        assert news.author is None
        assert news.relevance_score is None

    def test_headline_validation(self):
        """Test headline validation."""
        base_data = {
            "sentiment_score": Decimal("0.5"),
            "sentiment_label": "neutral",
            "source": "Test Source",
        }

        # Empty headline should fail
        with pytest.raises(ValidationError):
            NewsSentimentBase(**{**base_data, "headline": ""})

        # Too long headline should fail
        with pytest.raises(ValidationError):
            NewsSentimentBase(**{**base_data, "headline": "x" * 501})

        # Valid headline
        news = NewsSentimentBase(**{**base_data, "headline": "Valid Headline"})
        assert news.headline == "Valid Headline"

    def test_sentiment_score_validation(self):
        """Test sentiment score validation (-1 to 1 range)."""
        base_data = {
            "headline": "Test Headline",
            "sentiment_label": "neutral",
            "source": "Test Source",
        }

        # Score above 1 should fail
        with pytest.raises(ValidationError):
            NewsSentimentBase(**{**base_data, "sentiment_score": Decimal("1.1")})

        # Score below -1 should fail
        with pytest.raises(ValidationError):
            NewsSentimentBase(**{**base_data, "sentiment_score": Decimal("-1.1")})

        # Valid scores
        for score in [Decimal("-1"), Decimal("0"), Decimal("1")]:
            news = NewsSentimentBase(**{**base_data, "sentiment_score": score})
            assert news.sentiment_score == score

    def test_sentiment_label_validation(self):
        """Test sentiment label validation."""
        base_data = {
            "headline": "Test Headline",
            "sentiment_score": Decimal("0.5"),
            "source": "Test Source",
        }

        # Invalid sentiment label should fail
        with pytest.raises(ValidationError):
            NewsSentimentBase(**{**base_data, "sentiment_label": "invalid"})

        # Valid sentiment labels (case insensitive)
        for label in ["positive", "negative", "neutral", "POSITIVE", "Neutral"]:
            news = NewsSentimentBase(**{**base_data, "sentiment_label": label})
            assert news.sentiment_label == label.lower()

    def test_source_validation(self):
        """Test source validation."""
        base_data = {
            "headline": "Test Headline",
            "sentiment_score": Decimal("0.5"),
            "sentiment_label": "neutral",
        }

        # Empty source should fail
        with pytest.raises(ValidationError):
            NewsSentimentBase(**{**base_data, "source": ""})

        # Too long source should fail
        with pytest.raises(ValidationError):
            NewsSentimentBase(**{**base_data, "source": "x" * 101})

    def test_relevance_score_validation(self):
        """Test relevance score validation."""
        base_data = {
            "headline": "Test Headline",
            "sentiment_score": Decimal("0.5"),
            "sentiment_label": "neutral",
            "source": "Test Source",
        }

        # Score above 1 should fail
        with pytest.raises(ValidationError):
            NewsSentimentBase(**{**base_data, "relevance_score": Decimal("1.1")})

        # Negative score should fail
        with pytest.raises(ValidationError):
            NewsSentimentBase(**{**base_data, "relevance_score": Decimal("-0.1")})

        # Valid scores
        for score in [Decimal("0"), Decimal("0.5"), Decimal("1")]:
            news = NewsSentimentBase(**{**base_data, "relevance_score": score})
            assert news.relevance_score == score

    def test_url_validation(self):
        """Test URL validation."""
        base_data = {
            "headline": "Test Headline",
            "sentiment_score": Decimal("0.5"),
            "sentiment_label": "neutral",
            "source": "Test Source",
        }

        # Valid URLs
        valid_urls = [
            "https://example.com",
            "http://news.site.com/article/123",
            "https://www.reuters.com/business/finance/apple-reports-2023/",
        ]

        for url in valid_urls:
            news = NewsSentimentBase(**{**base_data, "url": url})
            assert str(news.url) == url

        # Invalid URL should fail
        with pytest.raises(ValidationError):
            NewsSentimentBase(**{**base_data, "url": "not-a-url"})


class TestNewsSentimentCreate:
    """Test NewsSentimentCreate schema."""

    def test_news_sentiment_create_with_stock_id(self):
        """Test creating news sentiment with stock ID."""
        news = NewsSentimentCreate(
            stock_id=1,
            date=datetime.utcnow(),
            headline="Test News",
            sentiment_score=Decimal("0.7"),
            sentiment_label="positive",
            source="Test Source",
        )

        assert news.stock_id == 1
        assert isinstance(news.date, datetime)

    def test_stock_id_validation(self):
        """Test stock ID validation."""
        # Zero or negative stock ID should fail
        with pytest.raises(ValidationError):
            NewsSentimentCreate(
                stock_id=0,
                date=datetime.utcnow(),
                headline="Test News",
                sentiment_score=Decimal("0.7"),
                sentiment_label="positive",
                source="Test Source",
            )


class TestNewsSentimentResponse:
    """Test NewsSentimentResponse schema."""

    def test_news_sentiment_response_from_model(self, sample_news_sentiment):
        """Test creating response from database model."""
        response = NewsSentimentResponse.from_orm(sample_news_sentiment)

        assert response.id == sample_news_sentiment.id
        assert response.stock_id == sample_news_sentiment.stock_id
        assert response.headline == sample_news_sentiment.headline
        assert response.sentiment_score == sample_news_sentiment.sentiment_score
        assert response.sentiment_label == sample_news_sentiment.sentiment_label


class TestSentimentAnalysis:
    """Test SentimentAnalysis schema."""

    def test_valid_sentiment_analysis(self, sample_news_sentiment):
        """Test valid sentiment analysis creation."""
        from datetime import timedelta

        analysis_data = {
            "stock_symbol": "AAPL",
            "period_start": datetime.utcnow() - timedelta(days=7),
            "period_end": datetime.utcnow(),
            "total_articles": 10,
            "positive_count": 6,
            "negative_count": 2,
            "neutral_count": 2,
            "average_sentiment": Decimal("0.4"),
            "sentiment_trend": "improving",
            "most_relevant_news": [sample_news_sentiment],
        }

        analysis = SentimentAnalysis(**analysis_data)

        assert analysis.stock_symbol == "AAPL"
        assert analysis.total_articles == 10
        assert analysis.positive_count == 6
        assert analysis.average_sentiment == Decimal("0.4")
        assert analysis.sentiment_trend == "improving"

    def test_sentiment_analysis_minimal(self):
        """Test sentiment analysis with minimal required fields."""
        analysis = SentimentAnalysis(
            stock_symbol="MSFT",
            period_start=datetime.utcnow() - timedelta(days=1),
            period_end=datetime.utcnow(),
            total_articles=5,
            positive_count=2,
            negative_count=1,
            neutral_count=2,
            average_sentiment=Decimal("0.2"),
            sentiment_trend="stable",
        )

        assert analysis.most_relevant_news == []

    def test_article_count_validation(self):
        """Test article count validation."""
        base_data = {
            "stock_symbol": "TEST",
            "period_start": datetime.utcnow() - datetime.timedelta(days=1),
            "period_end": datetime.utcnow(),
            "average_sentiment": Decimal("0.0"),
            "sentiment_trend": "stable",
        }

        # Negative counts should fail
        with pytest.raises(ValidationError):
            SentimentAnalysis(
                **{
                    **base_data,
                    "total_articles": -1,
                    "positive_count": 0,
                    "negative_count": 0,
                    "neutral_count": 0,
                }
            )

    def test_sentiment_trend_validation(self):
        """Test sentiment trend validation."""
        base_data = {
            "stock_symbol": "TEST",
            "period_start": datetime.utcnow() - datetime.timedelta(days=1),
            "period_end": datetime.utcnow(),
            "total_articles": 5,
            "positive_count": 2,
            "negative_count": 1,
            "neutral_count": 2,
            "average_sentiment": Decimal("0.2"),
        }

        # Invalid trend should fail
        with pytest.raises(ValidationError):
            SentimentAnalysis(**{**base_data, "sentiment_trend": "invalid"})

        # Valid trends (case insensitive)
        for trend in ["improving", "declining", "stable", "IMPROVING", "Stable"]:
            analysis = SentimentAnalysis(**{**base_data, "sentiment_trend": trend})
            assert analysis.sentiment_trend == trend.lower()

    def test_average_sentiment_bounds(self):
        """Test average sentiment bounds."""
        base_data = {
            "stock_symbol": "TEST",
            "period_start": datetime.utcnow() - datetime.timedelta(days=1),
            "period_end": datetime.utcnow(),
            "total_articles": 5,
            "positive_count": 2,
            "negative_count": 1,
            "neutral_count": 2,
            "sentiment_trend": "stable",
        }

        # Average sentiment above 1 should fail
        with pytest.raises(ValidationError):
            SentimentAnalysis(**{**base_data, "average_sentiment": Decimal("1.1")})

        # Average sentiment below -1 should fail
        with pytest.raises(ValidationError):
            SentimentAnalysis(**{**base_data, "average_sentiment": Decimal("-1.1")})

        # Valid bounds
        for sentiment in [Decimal("-1"), Decimal("0"), Decimal("1")]:
            analysis = SentimentAnalysis(
                **{**base_data, "average_sentiment": sentiment}
            )
            assert analysis.average_sentiment == sentiment
