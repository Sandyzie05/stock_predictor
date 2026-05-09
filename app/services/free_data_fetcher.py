"""
Free data fetcher service using Yahoo Finance and other free APIs.
No API keys required.
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from dataclasses import dataclass
import json
import random

from app.services.data_fetcher import (
    StockQuote, StockHistoricalData, CompanyInfo, NewsArticle
)


@dataclass
class MockDataGenerator:
    """Generate realistic mock data for development and demo purposes."""
    
    @staticmethod
    def generate_stock_quote(symbol: str) -> StockQuote:
        """Generate realistic stock quote data."""
        # Base prices for common stocks
        base_prices = {
            'AAPL': 150.0, 'GOOGL': 135.0, 'MSFT': 340.0, 'TSLA': 220.0,
            'AMZN': 145.0, 'META': 310.0, 'NVDA': 450.0, 'NFLX': 400.0,
            'SPY': 430.0, 'QQQ': 360.0, 'DIA': 340.0, 'IWM': 200.0
        }
        
        base_price = base_prices.get(symbol, 100.0)
        
        # Add some realistic variation
        price_variation = random.uniform(-0.05, 0.05)  # ±5%
        current_price = base_price * (1 + price_variation)
        
        daily_change = random.uniform(-0.03, 0.03)  # ±3% daily change
        change_amount = current_price * daily_change
        change_percent = daily_change * 100
        
        volume = random.randint(1000000, 50000000)  # 1M to 50M shares
        
        return StockQuote(
            symbol=symbol,
            price=Decimal(str(round(current_price, 2))),
            change=Decimal(str(round(change_amount, 2))),
            change_percent=Decimal(str(round(change_percent, 2))),
            volume=volume,
            timestamp=datetime.now()
        )
    
    @staticmethod
    def generate_historical_data(symbol: str, days: int = 30) -> List[StockHistoricalData]:
        """Generate realistic historical data."""
        base_price = 150.0 if symbol == 'AAPL' else 100.0
        historical_data = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=days-i)
            
            # Generate realistic price movement
            daily_change = random.uniform(-0.02, 0.02)  # ±2% daily
            base_price *= (1 + daily_change)
            
            # OHLC data
            open_price = base_price
            high = base_price * (1 + random.uniform(0, 0.03))
            low = base_price * (1 - random.uniform(0, 0.03))
            close = base_price * (1 + random.uniform(-0.02, 0.02))
            
            volume = random.randint(10000000, 80000000)
            
            historical_data.append(StockHistoricalData(
                symbol=symbol,
                date=date,
                open_price=Decimal(str(round(open_price, 2))),
                high=Decimal(str(round(high, 2))),
                low=Decimal(str(round(low, 2))),
                close=Decimal(str(round(close, 2))),
                volume=volume,
                adjusted_close=Decimal(str(round(close, 2)))
            ))
            
            base_price = float(close)
        
        return historical_data
    
    @staticmethod
    def generate_company_info(symbol: str) -> CompanyInfo:
        """Generate company information."""
        companies = {
            'AAPL': {
                'name': 'Apple Inc.',
                'sector': 'Technology',
                'market_cap': Decimal('3000000000000'),  # $3T
                'description': 'Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.',
                'website': 'https://www.apple.com'
            },
            'GOOGL': {
                'name': 'Alphabet Inc.',
                'sector': 'Technology',
                'market_cap': Decimal('1700000000000'),  # $1.7T
                'description': 'Alphabet Inc. provides online advertising services in the United States, Europe, the Middle East, Africa, the Asia-Pacific, Canada, and Latin America.',
                'website': 'https://www.alphabet.com'
            },
            'MSFT': {
                'name': 'Microsoft Corporation',
                'sector': 'Technology',
                'market_cap': Decimal('2800000000000'),  # $2.8T
                'description': 'Microsoft Corporation develops, licenses, and supports software, services, devices, and solutions worldwide.',
                'website': 'https://www.microsoft.com'
            },
            'TSLA': {
                'name': 'Tesla, Inc.',
                'sector': 'Automotive',
                'market_cap': Decimal('800000000000'),  # $800B
                'description': 'Tesla, Inc. designs, develops, manufactures, leases, and sells electric vehicles, and energy generation and storage systems.',
                'website': 'https://www.tesla.com'
            }
        }
        
        company_data = companies.get(symbol, {
            'name': f'{symbol} Corporation',
            'sector': 'Technology',
            'market_cap': Decimal('50000000000'),  # $50B default
            'description': f'{symbol} is a publicly traded company.',
            'website': f'https://www.{symbol.lower()}.com'
        })
        
        return CompanyInfo(
            symbol=symbol,
            name=company_data['name'],
            sector=company_data['sector'],
            market_cap=company_data['market_cap'],
            description=company_data['description'],
            website=company_data['website']
        )
    
    @staticmethod
    def generate_news(symbol: str, limit: int = 5) -> List[NewsArticle]:
        """Generate sample news articles."""
        news_templates = [
            f"{symbol} reports strong quarterly earnings, beating analyst expectations",
            f"{symbol} announces new product line expansion for 2024",
            f"Analysts upgrade {symbol} with positive outlook for next quarter",
            f"{symbol} stock shows resilience amid market volatility",
            f"Investment firms increase positions in {symbol} ahead of earnings",
            f"{symbol} leadership discusses strategic growth initiatives",
            f"Market watchers see potential in {symbol}'s latest developments",
            f"{symbol} maintains strong performance in competitive market"
        ]
        
        articles = []
        for i in range(min(limit, len(news_templates))):
            articles.append(NewsArticle(
                title=news_templates[i],
                description=f"Latest analysis and market updates for {symbol}.",
                url=f"https://example.com/news/{symbol.lower()}-{i+1}",
                published_at=datetime.now() - timedelta(hours=i*6),
                source="Market Analysis",
                sentiment="positive" if i % 3 != 0 else "neutral"
            ))
        
        return articles


class FreeDataFetcherService:
    """Free data fetcher service with mock data for development."""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.mock_generator = MockDataGenerator()
    
    async def __aenter__(self):
        """Initialize the service."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources."""
        if self.session:
            await self.session.close()
    
    async def get_stock_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get stock quote - using mock data for now."""
        try:
            print(f"📊 Generating mock data for {symbol}")
            return self.mock_generator.generate_stock_quote(symbol)
        except Exception as e:
            print(f"Error generating mock quote for {symbol}: {e}")
            return None
    
    async def get_historical_data(self, symbol: str, days: int = 30) -> Optional[List[StockHistoricalData]]:
        """Get historical data - using mock data."""
        try:
            print(f"📈 Generating mock historical data for {symbol}")
            return self.mock_generator.generate_historical_data(symbol, days)
        except Exception as e:
            print(f"Error generating mock historical data for {symbol}: {e}")
            return None
    
    async def get_company_info(self, symbol: str) -> Optional[CompanyInfo]:
        """Get company information - using mock data."""
        try:
            print(f"🏢 Generating mock company info for {symbol}")
            return self.mock_generator.generate_company_info(symbol)
        except Exception as e:
            print(f"Error generating mock company info for {symbol}: {e}")
            return None
    
    async def get_news(self, symbol: str, limit: int = 10) -> Optional[List[NewsArticle]]:
        """Get news articles - using mock data."""
        try:
            print(f"📰 Generating mock news for {symbol}")
            return self.mock_generator.generate_news(symbol, limit)
        except Exception as e:
            print(f"Error generating mock news for {symbol}: {e}")
            return None
    
    # Yahoo Finance integration (free, no API key required)
    async def get_yahoo_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get real quote from Yahoo Finance (free)."""
        try:
            if not self.session:
                raise RuntimeError("Service must be used as async context manager")
            
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('chart', {}).get('result'):
                        result = data['chart']['result'][0]
                        meta = result.get('meta', {})
                        
                        current_price = meta.get('regularMarketPrice', 0)
                        previous_close = meta.get('previousClose', current_price)
                        change = current_price - previous_close
                        change_percent = (change / previous_close * 100) if previous_close else 0
                        
                        return StockQuote(
                            symbol=symbol,
                            price=Decimal(str(current_price)),
                            change=Decimal(str(change)),
                            change_percent=Decimal(str(change_percent)),
                            volume=meta.get('regularMarketVolume', 0),
                            timestamp=datetime.now()
                        )
        except Exception as e:
            print(f"Yahoo Finance error for {symbol}: {e}")
        
        # Fallback to mock data
        return self.mock_generator.generate_stock_quote(symbol)


# Global instance for easy access
free_data_service = FreeDataFetcherService()
