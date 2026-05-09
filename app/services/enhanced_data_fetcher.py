"""
Enhanced data fetcher service with multiple free data sources.
Integrates Yahoo Finance, Alpha Vantage (free tier), and other free APIs.
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
import json
import random

from app.services.free_data_fetcher import (
    FreeDataFetcherService, MockDataGenerator,
    StockQuote, StockHistoricalData, CompanyInfo, NewsArticle
)
from app.core.config import settings


class EnhancedDataFetcherService(FreeDataFetcherService):
    """Enhanced data fetcher with multiple free sources and fallbacks."""
    
    def __init__(self):
        super().__init__()
        self.alpha_vantage_key = settings.ALPHA_VANTAGE_API_KEY
        self.use_real_apis = bool(self.alpha_vantage_key)
        
    async def get_stock_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get stock quote with multiple fallbacks."""
        try:
            # Try Alpha Vantage if key available
            if self.alpha_vantage_key:
                quote = await self._get_alpha_vantage_quote(symbol)
                if quote:
                    print(f"📈 Alpha Vantage data for {symbol}: ${quote.price}")
                    return quote
            
            # Try Yahoo Finance as fallback
            quote = await self.get_yahoo_quote(symbol)
            if quote:
                print(f"📊 Yahoo Finance data for {symbol}: ${quote.price}")
                return quote
            
            # Use mock data as final fallback
            print(f"🎭 Using mock data for {symbol}")
            return self.mock_generator.generate_stock_quote(symbol)
            
        except Exception as e:
            print(f"Error fetching quote for {symbol}: {e}")
            return self.mock_generator.generate_stock_quote(symbol)
    
    async def _get_alpha_vantage_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get quote from Alpha Vantage (free tier: 5 calls/min, 500/day)."""
        if not self.alpha_vantage_key or not self.session:
            return None
        
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': self.alpha_vantage_key
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if 'Global Quote' in data:
                        quote_data = data['Global Quote']
                        
                        current_price = float(quote_data.get('05. price', 0))
                        change = float(quote_data.get('09. change', 0))
                        change_percent = float(quote_data.get('10. change percent', '0').replace('%', ''))
                        volume = int(float(quote_data.get('06. volume', 0)))
                        
                        return StockQuote(
                            symbol=symbol,
                            price=Decimal(str(current_price)),
                            change=Decimal(str(change)),
                            change_percent=Decimal(str(change_percent)),
                            volume=volume,
                            timestamp=datetime.now()
                        )
            
        except Exception as e:
            print(f"Alpha Vantage API error for {symbol}: {e}")
        
        return None
    
    async def get_company_info(self, symbol: str) -> Optional[CompanyInfo]:
        """Get company info with API fallbacks."""
        try:
            # Try Alpha Vantage company overview
            if self.alpha_vantage_key:
                company = await self._get_alpha_vantage_company(symbol)
                if company:
                    return company
            
            # Fallback to enhanced mock data
            return self._get_enhanced_company_info(symbol)
            
        except Exception as e:
            print(f"Error fetching company info for {symbol}: {e}")
            return self.mock_generator.generate_company_info(symbol)
    
    async def _get_alpha_vantage_company(self, symbol: str) -> Optional[CompanyInfo]:
        """Get company overview from Alpha Vantage."""
        if not self.alpha_vantage_key or not self.session:
            return None
        
        try:
            url = "https://www.alphavantage.co/query"
            params = {
                'function': 'OVERVIEW',
                'symbol': symbol,
                'apikey': self.alpha_vantage_key
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data and 'Symbol' in data:
                        market_cap = data.get('MarketCapitalization')
                        if market_cap and market_cap != 'None':
                            market_cap = Decimal(str(market_cap))
                        else:
                            market_cap = None
                        
                        return CompanyInfo(
                            symbol=symbol,
                            name=data.get('Name', f'{symbol} Corporation'),
                            sector=data.get('Sector', 'Technology'),
                            market_cap=market_cap,
                            description=data.get('Description', f'{symbol} is a publicly traded company.'),
                            website=data.get('OfficialSite', f'https://www.{symbol.lower()}.com')
                        )
            
        except Exception as e:
            print(f"Alpha Vantage company API error for {symbol}: {e}")
        
        return None
    
    def _get_enhanced_company_info(self, symbol: str) -> CompanyInfo:
        """Get enhanced company info with more realistic data."""
        # Enhanced company database
        enhanced_companies = {
            'AAPL': {
                'name': 'Apple Inc.',
                'sector': 'Technology',
                'market_cap': Decimal('3000000000000'),
                'description': 'Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide. The company serves consumers, and small and mid-sized businesses; and the education, enterprise, and government markets.',
                'website': 'https://www.apple.com'
            },
            'GOOGL': {
                'name': 'Alphabet Inc.',
                'sector': 'Communication Services',
                'market_cap': Decimal('1700000000000'),
                'description': 'Alphabet Inc. provides online advertising services and cloud computing solutions. The company operates Google Search, YouTube, Google Cloud, and other products and services.',
                'website': 'https://www.alphabet.com'
            },
            'MSFT': {
                'name': 'Microsoft Corporation',
                'sector': 'Technology',
                'market_cap': Decimal('2800000000000'),
                'description': 'Microsoft Corporation develops, licenses, and supports software, services, devices, and solutions worldwide. The company operates in three segments: Productivity and Business Processes, Intelligent Cloud, and More Personal Computing.',
                'website': 'https://www.microsoft.com'
            },
            'TSLA': {
                'name': 'Tesla, Inc.',
                'sector': 'Consumer Cyclical',
                'market_cap': Decimal('800000000000'),
                'description': 'Tesla, Inc. designs, develops, manufactures, leases, and sells electric vehicles, and energy generation and storage systems in the United States, China, and internationally.',
                'website': 'https://www.tesla.com'
            },
            'AMZN': {
                'name': 'Amazon.com, Inc.',
                'sector': 'Consumer Cyclical',
                'market_cap': Decimal('1500000000000'),
                'description': 'Amazon.com, Inc. engages in the retail sale of consumer products and subscriptions in North America and internationally.',
                'website': 'https://www.amazon.com'
            },
            'META': {
                'name': 'Meta Platforms, Inc.',
                'sector': 'Communication Services',
                'market_cap': Decimal('800000000000'),
                'description': 'Meta Platforms, Inc. develops products that enable people to connect and share with friends and family through mobile devices, personal computers, virtual reality headsets, and wearables worldwide.',
                'website': 'https://www.meta.com'
            },
            'NVDA': {
                'name': 'NVIDIA Corporation',
                'sector': 'Technology',
                'market_cap': Decimal('1200000000000'),
                'description': 'NVIDIA Corporation provides graphics, and compute and networking solutions in the United States, Taiwan, China, and internationally.',
                'website': 'https://www.nvidia.com'
            }
        }
        
        if symbol in enhanced_companies:
            data = enhanced_companies[symbol]
            return CompanyInfo(
                symbol=symbol,
                name=data['name'],
                sector=data['sector'],
                market_cap=data['market_cap'],
                description=data['description'],
                website=data['website']
            )
        
        # Fallback to mock generator for unknown symbols
        return self.mock_generator.generate_company_info(symbol)
    
    async def get_financial_news(self, symbol: str, limit: int = 5) -> List[NewsArticle]:
        """Get financial news with multiple sources."""
        try:
            # Try to get real news if API available
            news = await self._get_financial_news_api(symbol, limit)
            if news:
                return news
            
            # Fallback to enhanced mock news
            return self._get_enhanced_news(symbol, limit)
            
        except Exception as e:
            print(f"Error fetching news for {symbol}: {e}")
            return self.mock_generator.generate_news(symbol, limit)
    
    async def _get_financial_news_api(self, symbol: str, limit: int) -> Optional[List[NewsArticle]]:
        """Get news from financial APIs (placeholder for future API integration)."""
        # This could integrate with NewsAPI, Finnhub, or other news sources
        # For now, return None to fall back to enhanced mock data
        return None
    
    def _get_enhanced_news(self, symbol: str, limit: int) -> List[NewsArticle]:
        """Generate enhanced, more realistic news."""
        news_templates = {
            'AAPL': [
                "Apple reports record quarterly revenue driven by iPhone sales",
                "Apple announces new AI features coming to iPhone and Mac",
                "Analysts raise Apple target price on strong services growth",
                "Apple's vision for spatial computing gains momentum with new partnerships",
                "Apple Pay expansion continues with new banking partnerships"
            ],
            'GOOGL': [
                "Google Cloud revenue accelerates in latest quarter",
                "Alphabet's AI investments show promising returns",
                "Google Search maintains dominant market position",
                "YouTube Shorts reaches new milestone in user engagement",
                "Waymo expands autonomous vehicle testing to new cities"
            ],
            'TSLA': [
                "Tesla delivers record number of vehicles this quarter",
                "Tesla Supercharger network expansion accelerates globally",
                "Tesla's energy storage business shows strong growth",
                "New Tesla Model updates include enhanced autopilot features",
                "Tesla manufacturing efficiency improvements drive margin expansion"
            ]
        }
        
        templates = news_templates.get(symbol, [
            f"{symbol} reports quarterly earnings results",
            f"{symbol} announces strategic partnership initiative",
            f"Analysts update {symbol} price targets following latest developments",
            f"{symbol} management discusses growth strategy at investor conference",
            f"{symbol} shows resilience in current market conditions"
        ])
        
        articles = []
        for i, template in enumerate(templates[:limit]):
            sentiment = "positive" if i % 3 != 2 else "neutral"
            articles.append(NewsArticle(
                title=template,
                description=f"Latest market analysis and financial updates for {symbol}.",
                url=f"https://finance.example.com/{symbol.lower()}-news-{i+1}",
                published_at=datetime.now() - timedelta(hours=i*4),
                source=["MarketWatch", "Bloomberg", "Reuters", "Financial Times"][i % 4],
                sentiment=sentiment
            ))
        
        return articles
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to various data sources."""
        results = {
            "yahoo_finance": False,
            "alpha_vantage": False,
            "mock_data": True,
            "overall_status": "degraded"
        }
        
        try:
            # Test Yahoo Finance
            test_quote = await self.get_yahoo_quote("AAPL")
            results["yahoo_finance"] = test_quote is not None
            
            # Test Alpha Vantage if key available
            if self.alpha_vantage_key:
                av_quote = await self._get_alpha_vantage_quote("AAPL")
                results["alpha_vantage"] = av_quote is not None
            
            # Determine overall status
            if results["yahoo_finance"] or results["alpha_vantage"]:
                results["overall_status"] = "healthy"
            elif results["mock_data"]:
                results["overall_status"] = "degraded"
            else:
                results["overall_status"] = "unhealthy"
                
        except Exception as e:
            print(f"Connection test error: {e}")
        
        return results
