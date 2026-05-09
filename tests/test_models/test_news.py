"""
Tests for news sentiment models.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from app.models.news import NewsSentiment


class TestNewsSentiment:
    """Test NewsSentiment model."""

    @pytest.mark.asyncio
    async def test_create_news_sentiment(
        self, db_session, sample_stock, sample_news_data
    ):
        """Test creating news sentiment."""
        news_data = sample_news_data.copy()
        news_data["stock_id"] = sample_stock.id

        news = NewsSentiment(**news_data)
        db_session.add(news)
        await db_session.commit()
        await db_session.refresh(news)

        assert news.id is not None
        assert news.stock_id == sample_stock.id
        assert news.headline == "Apple Reports Strong Quarterly Results"
        assert (
            news.summary
            == "Apple exceeded analyst expectations with strong iPhone sales."
        )
        assert news.sentiment_score == Decimal("0.8")
        assert news.sentiment_label == "positive"
        assert news.source == "Reuters"
        assert news.url == "https://example.com/news/apple-results"
        assert news.author == "John Doe"
        assert news.relevance_score == Decimal("0.9")
        assert isinstance(news.date, datetime)
        assert isinstance(news.created_at, datetime)

    @pytest.mark.asyncio
    async def test_news_sentiment_minimal_creation(self, db_session, sample_stock):
        """Test creating news with minimal required fields."""
        news = NewsSentiment(
            stock_id=sample_stock.id,
            date=datetime.utcnow(),
            headline="Simple News Headline",
            sentiment_score=Decimal("0.1"),
            sentiment_label="neutral",
            source="Test Source",
        )
        db_session.add(news)
        await db_session.commit()
        await db_session.refresh(news)

        assert news.headline == "Simple News Headline"
        assert news.summary is None
        assert news.content is None
        assert news.url is None
        assert news.author is None
        assert news.relevance_score is None

    @pytest.mark.asyncio
    async def test_sentiment_labels(self, db_session, sample_stock):
        """Test different sentiment labels."""
        sentiment_data = [
            ("positive", Decimal("0.8"), "Bullish news about growth"),
            ("negative", Decimal("-0.6"), "Bearish outlook reported"),
            ("neutral", Decimal("0.1"), "Mixed signals in market"),
        ]

        for label, score, headline in sentiment_data:
            news = NewsSentiment(
                stock_id=sample_stock.id,
                date=datetime.utcnow(),
                headline=headline,
                sentiment_score=score,
                sentiment_label=label,
                source="Test Source",
            )
            db_session.add(news)

        await db_session.commit()

    @pytest.mark.asyncio
    async def test_sentiment_score_range(self, db_session, sample_stock):
        """Test sentiment score boundaries."""
        # Test extreme negative sentiment
        news_negative = NewsSentiment(
            stock_id=sample_stock.id,
            date=datetime.utcnow(),
            headline="Very Bad News",
            sentiment_score=Decimal("-1.0"),
            sentiment_label="negative",
            source="Test Source",
        )

        # Test extreme positive sentiment
        news_positive = NewsSentiment(
            stock_id=sample_stock.id,
            date=datetime.utcnow(),
            headline="Very Good News",
            sentiment_score=Decimal("1.0"),
            sentiment_label="positive",
            source="Test Source",
        )

        db_session.add_all([news_negative, news_positive])
        await db_session.commit()

        await db_session.refresh(news_negative)
        await db_session.refresh(news_positive)

        assert news_negative.sentiment_score == Decimal("-1.0")
        assert news_positive.sentiment_score == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_relevance_score_range(self, db_session, sample_stock):
        """Test relevance score boundaries."""
        # Test minimum relevance
        news_min = NewsSentiment(
            stock_id=sample_stock.id,
            date=datetime.utcnow(),
            headline="Barely Related News",
            sentiment_score=Decimal("0.0"),
            sentiment_label="neutral",
            source="Test Source",
            relevance_score=Decimal("0.0"),
        )

        # Test maximum relevance
        news_max = NewsSentiment(
            stock_id=sample_stock.id,
            date=datetime.utcnow(),
            headline="Highly Relevant News",
            sentiment_score=Decimal("0.5"),
            sentiment_label="positive",
            source="Test Source",
            relevance_score=Decimal("1.0"),
        )

        db_session.add_all([news_min, news_max])
        await db_session.commit()

        await db_session.refresh(news_min)
        await db_session.refresh(news_max)

        assert news_min.relevance_score == Decimal("0.0")
        assert news_max.relevance_score == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_long_content_handling(self, db_session, sample_stock):
        """Test handling of long news content."""
        long_content = "This is a very long news article content. " * 100
        long_summary = "This is a long summary. " * 20

        news = NewsSentiment(
            stock_id=sample_stock.id,
            date=datetime.utcnow(),
            headline="News with Long Content",
            summary=long_summary,
            content=long_content,
            sentiment_score=Decimal("0.3"),
            sentiment_label="positive",
            source="Test Source",
        )
        db_session.add(news)
        await db_session.commit()
        await db_session.refresh(news)

        assert len(news.content) > 1000
        assert len(news.summary) > 500
        assert news.headline == "News with Long Content"

    @pytest.mark.asyncio
    async def test_multiple_sources(self, db_session, sample_stock):
        """Test news from multiple sources."""
        sources = ["Reuters", "Bloomberg", "Wall Street Journal", "Financial Times"]

        for i, source in enumerate(sources):
            news = NewsSentiment(
                stock_id=sample_stock.id,
                date=datetime.utcnow(),
                headline=f"News from {source} #{i+1}",
                sentiment_score=Decimal(f"0.{i+1}"),
                sentiment_label="positive" if i % 2 == 0 else "negative",
                source=source,
                author=f"Reporter {i+1}",
            )
            db_session.add(news)

        await db_session.commit()

    @pytest.mark.asyncio
    async def test_news_with_url(self, db_session, sample_stock):
        """Test news with various URL formats."""
        urls = [
            "https://www.reuters.com/business/finance/apple-reports-earnings-2023-01-01/",
            "https://bloomberg.com/news/articles/2023/01/01/apple-stock-surge",
            "http://example.com/news/simple-url",
        ]

        for i, url in enumerate(urls):
            news = NewsSentiment(
                stock_id=sample_stock.id,
                date=datetime.utcnow(),
                headline=f"News Article {i+1}",
                sentiment_score=Decimal("0.5"),
                sentiment_label="neutral",
                source="Test Source",
                url=url,
            )
            db_session.add(news)

        await db_session.commit()

    @pytest.mark.asyncio
    async def test_news_time_series(self, db_session, sample_stock):
        """Test time series of news articles."""
        from datetime import timedelta

        base_date = datetime.utcnow()

        # Create news articles over several days
        for i in range(7):
            news_date = base_date - timedelta(days=i)
            sentiment = Decimal(f"0.{7-i}")  # Improving sentiment over time

            news = NewsSentiment(
                stock_id=sample_stock.id,
                date=news_date,
                headline=f"Daily News Update Day {i+1}",
                sentiment_score=sentiment,
                sentiment_label=(
                    "positive" if sentiment > Decimal("0.5") else "negative"
                ),
                source="Daily News Source",
            )
            db_session.add(news)

        await db_session.commit()
