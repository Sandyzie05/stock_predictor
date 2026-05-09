"""
Stock list and ranking schemas.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.prediction import RecommendationType


class StockListItem(BaseModel):
    """Base item for stock lists."""

    symbol: str = Field(..., description="Stock symbol")
    name: str = Field(..., description="Company name")
    current_price: Optional[Decimal] = Field(None, description="Current stock price")
    market_cap: Optional[Decimal] = Field(None, description="Market capitalization")
    sector: Optional[str] = Field(None, description="Company sector")
    last_updated: datetime = Field(..., description="Last data update time")


class ATHStock(StockListItem):
    """All-time high stock item."""

    ath_price: Decimal = Field(..., description="All-time high price")
    ath_date: datetime = Field(..., description="Date of all-time high")
    days_at_ath: int = Field(..., ge=0, description="Days since ATH was reached")
    price_change_percent: Decimal = Field(..., description="Percentage change from ATH")
    volume_spike: Optional[Decimal] = Field(
        None, description="Volume increase percentage"
    )
    reasoning: str = Field(..., description="Why this stock is notable at ATH")
    news_sentiment: Optional[str] = Field(None, description="Recent news sentiment")
    risk_factors: List[str] = Field(default=[], description="Potential risk factors")


class ATLStock(StockListItem):
    """All-time low stock item."""

    atl_price: Decimal = Field(..., description="All-time low price")
    atl_date: datetime = Field(..., description="Date of all-time low")
    days_at_atl: int = Field(..., ge=0, description="Days since ATL was reached")
    recovery_potential: Decimal = Field(
        ..., ge=0, le=1, description="Recovery potential score"
    )
    fundamental_strength: Optional[Decimal] = Field(
        None, description="Fundamental analysis score"
    )
    reasoning: str = Field(..., description="Why this stock is at ATL and potential")
    catalyst_events: List[str] = Field(
        default=[], description="Potential recovery catalysts"
    )


class UndervaluedStock(StockListItem):
    """Undervalued stock item."""

    fair_value_estimate: Decimal = Field(..., description="Estimated fair value")
    discount_percentage: Decimal = Field(
        ..., ge=0, description="Discount from fair value"
    )
    pe_ratio: Optional[Decimal] = Field(None, description="Price-to-earnings ratio")
    pb_ratio: Optional[Decimal] = Field(None, description="Price-to-book ratio")
    debt_to_equity: Optional[Decimal] = Field(None, description="Debt-to-equity ratio")
    roe: Optional[Decimal] = Field(None, description="Return on equity")
    revenue_growth: Optional[Decimal] = Field(None, description="Revenue growth rate")
    valuation_score: Decimal = Field(
        ..., ge=0, le=100, description="Overall valuation score"
    )
    reasoning: str = Field(..., description="Why this stock is undervalued")
    competitive_advantages: List[str] = Field(
        default=[], description="Company's competitive moats"
    )
    growth_catalysts: List[str] = Field(
        default=[], description="Potential growth drivers"
    )


class OvervaluedStock(StockListItem):
    """Overvalued stock item."""

    fair_value_estimate: Decimal = Field(..., description="Estimated fair value")
    premium_percentage: Decimal = Field(
        ..., ge=0, description="Premium over fair value"
    )
    pe_ratio: Optional[Decimal] = Field(None, description="Price-to-earnings ratio")
    pb_ratio: Optional[Decimal] = Field(None, description="Price-to-book ratio")
    price_to_sales: Optional[Decimal] = Field(None, description="Price-to-sales ratio")
    earnings_growth: Optional[Decimal] = Field(None, description="Earnings growth rate")
    valuation_score: Decimal = Field(
        ..., ge=0, le=100, description="Overall valuation score"
    )
    reasoning: str = Field(..., description="Why this stock is overvalued")
    risk_factors: List[str] = Field(default=[], description="Key risk factors")
    correction_probability: Optional[Decimal] = Field(
        None, ge=0, le=1, description="Price correction probability"
    )


class SP500Stock(StockListItem):
    """S&P 500 specific stock item."""

    sp500_weight: Optional[Decimal] = Field(None, description="Weight in S&P 500 index")
    index_performance: Optional[Decimal] = Field(
        None, description="Performance vs S&P 500"
    )
    beta: Optional[Decimal] = Field(None, description="Stock beta relative to market")
    dividend_yield: Optional[Decimal] = Field(
        None, description="Current dividend yield"
    )
    years_in_sp500: Optional[int] = Field(
        None, description="Years as S&P 500 constituent"
    )


class StockList(BaseModel):
    """Generic stock list container."""

    title: str = Field(..., description="List title")
    description: str = Field(..., description="List description")
    generated_at: datetime = Field(..., description="When the list was generated")
    total_count: int = Field(..., ge=0, description="Total number of items")
    methodology: str = Field(..., description="How the list was generated")
    data_sources: List[str] = Field(..., description="Data sources used")
    last_data_update: datetime = Field(..., description="Last data refresh time")
    refresh_frequency: str = Field(..., description="How often the list is updated")
    disclaimer: str = Field(
        default="This list is for informational purposes only and does not constitute investment advice.",
        description="Investment disclaimer",
    )


class ATHStockList(StockList):
    """All-time high stocks list."""

    stocks: List[ATHStock] = Field(..., description="Stocks at all-time highs")


class ATLStockList(StockList):
    """All-time low stocks list."""

    stocks: List[ATLStock] = Field(..., description="Stocks at all-time lows")


class UndervaluedStockList(StockList):
    """Undervalued stocks list."""

    stocks: List[UndervaluedStock] = Field(..., description="Undervalued stocks")


class OvervaluedStockList(StockList):
    """Overvalued stocks list."""

    stocks: List[OvervaluedStock] = Field(..., description="Overvalued stocks")


class SP500ATHList(StockList):
    """S&P 500 stocks at all-time highs."""

    stocks: List[ATHStock] = Field(..., description="S&P 500 stocks at ATH")


class SP500ATLList(StockList):
    """S&P 500 stocks at all-time lows."""

    stocks: List[ATLStock] = Field(..., description="S&P 500 stocks at ATL")


class StockRecommendation(BaseModel):
    """Individual stock recommendation."""

    stock: StockListItem
    recommendation: RecommendationType = Field(
        ..., description="Buy/Sell/Hold recommendation"
    )
    confidence: Decimal = Field(
        ..., ge=0, le=1, description="Recommendation confidence"
    )
    target_price: Optional[Decimal] = Field(None, description="Target price estimate")
    time_horizon: Optional[str] = Field(None, description="Investment time horizon")
    reasoning: str = Field(..., description="Detailed reasoning for recommendation")
    key_metrics: dict = Field(default={}, description="Key financial metrics")
    risk_assessment: str = Field(..., description="Risk level assessment")
    news_impact: Optional[str] = Field(None, description="Recent news impact summary")


class RecommendationsList(StockList):
    """List of stock recommendations."""

    recommendations: List[StockRecommendation] = Field(
        ..., description="Stock recommendations"
    )
