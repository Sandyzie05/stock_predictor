"""
Stock analysis service for technical and fundamental analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import numpy as np

from app.services.data_fetcher import CompanyInfo, StockHistoricalData
from app.services.real_data_fetcher import RealDataFetcherService


@dataclass
class TechnicalIndicators:
    """Technical analysis indicators."""

    symbol: str
    date: datetime
    sma_20: Optional[Decimal] = None
    sma_50: Optional[Decimal] = None
    sma_200: Optional[Decimal] = None
    ema_12: Optional[Decimal] = None
    ema_26: Optional[Decimal] = None
    rsi: Optional[Decimal] = None
    macd: Optional[Decimal] = None
    macd_signal: Optional[Decimal] = None
    macd_histogram: Optional[Decimal] = None
    bollinger_upper: Optional[Decimal] = None
    bollinger_lower: Optional[Decimal] = None
    bollinger_middle: Optional[Decimal] = None
    atr: Optional[Decimal] = None
    volume_sma: Optional[Decimal] = None


@dataclass
class FundamentalMetrics:
    """Fundamental analysis metrics."""

    symbol: str
    date: datetime
    market_cap: Optional[Decimal] = None
    pe_ratio: Optional[Decimal] = None
    pb_ratio: Optional[Decimal] = None
    ps_ratio: Optional[Decimal] = None
    debt_to_equity: Optional[Decimal] = None
    current_ratio: Optional[Decimal] = None
    roe: Optional[Decimal] = None
    roa: Optional[Decimal] = None
    profit_margin: Optional[Decimal] = None
    revenue_growth: Optional[Decimal] = None
    earnings_growth: Optional[Decimal] = None


@dataclass
class StockAnalysis:
    """Complete stock analysis results."""

    symbol: str
    analysis_date: datetime
    current_price: Optional[Decimal] = None
    technical_indicators: Optional[TechnicalIndicators] = None
    fundamental_metrics: Optional[FundamentalMetrics] = None
    trend_analysis: Optional[str] = None
    support_resistance: Optional[Dict[str, Decimal]] = None
    volatility: Optional[Decimal] = None
    volume_analysis: Optional[Dict[str, Any]] = None


class StockAnalyzerService:
    """Service for technical and fundamental stock analysis."""

    def __init__(self):
        self.data_fetcher: Optional[RealDataFetcherService] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.data_fetcher = RealDataFetcherService()
        await self.data_fetcher.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.data_fetcher:
            await self.data_fetcher.__aexit__(exc_type, exc_val, exc_tb)

    async def analyze_stock(
        self,
        symbol: str,
        days: int = 252,
        include_technical: bool = True,
        include_fundamental: bool = True,
    ) -> Optional[StockAnalysis]:
        """Complete stock analysis with technical and fundamental metrics."""
        if not self.data_fetcher:
            raise RuntimeError(
                "StockAnalyzerService must be used as async context manager"
            )

        try:
            # Get historical data and current quote
            historical_data = await self.data_fetcher.get_historical_data(symbol, days)
            current_quote = await self.data_fetcher.get_stock_quote(symbol)
            company_info = await self.data_fetcher.get_company_info(symbol)

            if not historical_data:
                return None

            analysis = StockAnalysis(
                symbol=symbol.upper(),
                analysis_date=datetime.utcnow(),
                current_price=current_quote.price if current_quote else None,
            )

            # Technical analysis
            if include_technical and len(historical_data) >= 20:
                analysis.technical_indicators = (
                    await self._calculate_technical_indicators(historical_data)
                )
                analysis.trend_analysis = self._analyze_trend(historical_data)
                analysis.support_resistance = self._find_support_resistance(
                    historical_data
                )
                analysis.volatility = self._calculate_volatility(historical_data)
                analysis.volume_analysis = self._analyze_volume(historical_data)

            # Fundamental analysis
            if include_fundamental and company_info:
                analysis.fundamental_metrics = (
                    await self._calculate_fundamental_metrics(
                        symbol,
                        company_info,
                        current_quote.price if current_quote else None,
                    )
                )

            return analysis

        except Exception as e:
            print(f"Error analyzing stock {symbol}: {e}")
            return None

    async def _calculate_technical_indicators(
        self, data: List[StockHistoricalData]
    ) -> TechnicalIndicators:
        """Calculate technical indicators from historical data."""
        if not data:
            return TechnicalIndicators(symbol="", date=datetime.utcnow())

        # Convert to numpy arrays for calculations
        closes = np.array([float(d.close) for d in data])
        highs = np.array([float(d.high) for d in data])
        lows = np.array([float(d.low) for d in data])
        volumes = np.array([float(d.volume) for d in data])

        latest_data = data[-1]

        indicators = TechnicalIndicators(
            symbol=latest_data.symbol, date=latest_data.date
        )

        # Simple Moving Averages
        if len(closes) >= 20:
            indicators.sma_20 = Decimal(str(np.mean(closes[-20:])))
        if len(closes) >= 50:
            indicators.sma_50 = Decimal(str(np.mean(closes[-50:])))
        if len(closes) >= 200:
            indicators.sma_200 = Decimal(str(np.mean(closes[-200:])))

        # Exponential Moving Averages
        if len(closes) >= 12:
            indicators.ema_12 = Decimal(str(self._calculate_ema(closes, 12)))
        if len(closes) >= 26:
            indicators.ema_26 = Decimal(str(self._calculate_ema(closes, 26)))

        # RSI
        if len(closes) >= 15:
            indicators.rsi = Decimal(str(self._calculate_rsi(closes, 14)))

        # MACD
        if indicators.ema_12 and indicators.ema_26:
            macd_value = float(indicators.ema_12) - float(indicators.ema_26)
            indicators.macd = Decimal(str(macd_value))

            # MACD Signal line (9-period EMA of MACD)
            if len(closes) >= 35:  # Need enough data for signal line
                macd_history = self._calculate_macd_history(closes)
                if len(macd_history) >= 9:
                    signal = self._calculate_ema(np.array(macd_history), 9)
                    indicators.macd_signal = Decimal(str(signal))
                    indicators.macd_histogram = Decimal(str(macd_value - signal))

        # Bollinger Bands
        if len(closes) >= 20:
            sma_20 = np.mean(closes[-20:])
            std_20 = np.std(closes[-20:])
            indicators.bollinger_middle = Decimal(str(sma_20))
            indicators.bollinger_upper = Decimal(str(sma_20 + (2 * std_20)))
            indicators.bollinger_lower = Decimal(str(sma_20 - (2 * std_20)))

        # Average True Range (ATR)
        if len(closes) >= 15:
            indicators.atr = Decimal(str(self._calculate_atr(highs, lows, closes, 14)))

        # Volume SMA
        if len(volumes) >= 20:
            indicators.volume_sma = Decimal(str(np.mean(volumes[-20:])))

        return indicators

    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calculate Exponential Moving Average."""
        multiplier = 2 / (period + 1)
        ema = prices[0]  # Start with first price

        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return ema

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate Relative Strength Index."""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_macd_history(self, prices: np.ndarray) -> List[float]:
        """Calculate MACD history for signal line calculation."""
        macd_history = []

        for i in range(26, len(prices)):
            ema_12 = self._calculate_ema(prices[: i + 1], 12)
            ema_26 = self._calculate_ema(prices[: i + 1], 26)
            macd_history.append(ema_12 - ema_26)

        return macd_history

    def _calculate_atr(
        self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14
    ) -> float:
        """Calculate Average True Range."""
        tr_values = []

        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            tr_values.append(tr)

        return np.mean(tr_values[-period:])

    def _analyze_trend(self, data: List[StockHistoricalData]) -> str:
        """Analyze price trend."""
        if len(data) < 20:
            return "insufficient_data"

        recent_closes = [float(d.close) for d in data[-20:]]

        # Simple trend analysis based on moving averages
        short_ma = np.mean(recent_closes[-5:])
        long_ma = np.mean(recent_closes[-20:])

        if short_ma > long_ma * 1.02:
            return "bullish"
        elif short_ma < long_ma * 0.98:
            return "bearish"
        else:
            return "sideways"

    def _find_support_resistance(
        self, data: List[StockHistoricalData]
    ) -> Dict[str, Decimal]:
        """Find support and resistance levels."""
        if len(data) < 20:
            return {}

        recent_data = data[-50:] if len(data) >= 50 else data
        highs = [float(d.high) for d in recent_data]
        lows = [float(d.low) for d in recent_data]

        # Simple support/resistance based on recent highs/lows
        resistance = max(highs)
        support = min(lows)

        return {
            "support": Decimal(str(support)),
            "resistance": Decimal(str(resistance)),
            "current_range": Decimal(str(resistance - support)),
        }

    def _calculate_volatility(self, data: List[StockHistoricalData]) -> Decimal:
        """Calculate price volatility (standard deviation of returns)."""
        if len(data) < 20:
            return Decimal("0")

        closes = [float(d.close) for d in data[-30:]]  # 30-day volatility
        returns = [
            (closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes))
        ]

        volatility = np.std(returns) * np.sqrt(252)  # Annualized volatility
        return Decimal(str(round(volatility, 4)))

    def _analyze_volume(self, data: List[StockHistoricalData]) -> Dict[str, Any]:
        """Analyze volume patterns."""
        if len(data) < 20:
            return {}

        volumes = [float(d.volume) for d in data[-20:]]
        avg_volume = np.mean(volumes)
        recent_volume = volumes[-1]

        volume_trend = (
            "increasing"
            if recent_volume > avg_volume * 1.2
            else "decreasing" if recent_volume < avg_volume * 0.8 else "normal"
        )

        return {
            "average_volume": int(avg_volume),
            "recent_volume": int(recent_volume),
            "volume_ratio": round(recent_volume / avg_volume, 2),
            "volume_trend": volume_trend,
        }

    async def _calculate_fundamental_metrics(
        self, symbol: str, company_info: CompanyInfo, current_price: Optional[Decimal]
    ) -> FundamentalMetrics:
        """Calculate fundamental analysis metrics."""
        metrics = FundamentalMetrics(
            symbol=symbol.upper(),
            date=datetime.utcnow(),
            market_cap=company_info.market_cap,
        )

        # Note: In a production system, you'd fetch financial data from APIs
        # For now, we'll populate what we have and leave placeholders for others

        # These would typically come from financial data APIs like Alpha Vantage, Quandl, etc.
        # metrics.pe_ratio = await self._get_pe_ratio(symbol)
        # metrics.pb_ratio = await self._get_pb_ratio(symbol)
        # metrics.debt_to_equity = await self._get_debt_to_equity(symbol)
        # etc.

        return metrics

    async def get_technical_signals(
        self, symbol: str, days: int = 100
    ) -> Optional[Dict[str, str]]:
        """Get trading signals based on technical analysis."""
        analysis = await self.analyze_stock(
            symbol, days=days, include_technical=True, include_fundamental=False
        )

        if not analysis or not analysis.technical_indicators:
            return None

        signals = {}
        indicators = analysis.technical_indicators

        # RSI signals
        if indicators.rsi:
            rsi_value = float(indicators.rsi)
            if rsi_value > 70:
                signals["rsi"] = "overbought"
            elif rsi_value < 30:
                signals["rsi"] = "oversold"
            else:
                signals["rsi"] = "neutral"

        # MACD signals
        if indicators.macd and indicators.macd_signal:
            macd_diff = float(indicators.macd) - float(indicators.macd_signal)
            signals["macd"] = "bullish" if macd_diff > 0 else "bearish"

        # Moving average signals
        if indicators.sma_20 and indicators.sma_50 and analysis.current_price:
            price = float(analysis.current_price)
            sma_20 = float(indicators.sma_20)
            sma_50 = float(indicators.sma_50)

            if price > sma_20 > sma_50:
                signals["moving_averages"] = "bullish"
            elif price < sma_20 < sma_50:
                signals["moving_averages"] = "bearish"
            else:
                signals["moving_averages"] = "mixed"

        # Bollinger Bands signals
        if (
            indicators.bollinger_upper
            and indicators.bollinger_lower
            and analysis.current_price
        ):
            price = float(analysis.current_price)
            upper = float(indicators.bollinger_upper)
            lower = float(indicators.bollinger_lower)

            if price > upper:
                signals["bollinger"] = "overbought"
            elif price < lower:
                signals["bollinger"] = "oversold"
            else:
                signals["bollinger"] = "normal"

        return signals
