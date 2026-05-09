# 🔑 API Keys & Data Sources Guide

## 🚀 **Current Status: FREE DATA SERVICE ACTIVE**

Your Stock Predictor is **currently working** with a **Free Data Service** that requires **NO API KEYS**. You can use the system immediately!

---

## 📊 **What's Working Now (FREE):**

✅ **Yahoo Finance Integration** - Real stock quotes (no API key needed)  
✅ **Mock Data Generator** - Realistic demo data for development  
✅ **All UI Features** - Search, analysis, stock lists  
✅ **ML Predictions** - Based on available data  
✅ **System Monitoring** - Health checks and metrics  

---

## 🔄 **Upgrade Path: Premium Data Sources**

### **Tier 1: Enhanced Free APIs**
```bash
# Alpha Vantage (Free tier: 5 calls/min, 500/day)
ALPHA_VANTAGE_API_KEY=your_key_here

# Financial Modeling Prep (Free tier: 250 calls/day)  
FMP_API_KEY=your_key_here
```

### **Tier 2: Professional APIs**
```bash
# Polygon.io (Paid: Real-time data)
POLYGON_API_KEY=your_key_here

# NewsAPI (Paid: Unlimited news)
NEWS_API_KEY=your_key_here

# IEX Cloud (Paid: Enterprise features)
IEX_API_KEY=your_key_here
```

### **Tier 3: Brokerage Integration**
```bash
# Robinhood (via SnapTrade - requires setup)
SNAPTRADE_CLIENT_ID=your_client_id
SNAPTRADE_CONSUMER_KEY=your_consumer_key

# TD Ameritrade (requires app approval)
TDA_API_KEY=your_key_here
```

---

## 🎯 **Getting Started with API Keys**

### **1. Alpha Vantage (Recommended First Step)**
- **Free**: 5 calls/min, 500/day
- **Sign up**: https://www.alphavantage.co/support/#api-key
- **What you get**: Real-time quotes, historical data, financial news

```bash
# Add to your .env file:
ALPHA_VANTAGE_API_KEY=your_key_here
```

### **2. Polygon.io (Best for Real-time)**
- **Free**: 5 calls/min (delayed data)
- **Paid**: $99/month (real-time)
- **Sign up**: https://polygon.io/
- **What you get**: Real-time quotes, options data, crypto

```bash
# Add to your .env file:
POLYGON_API_KEY=your_key_here
```

### **3. NewsAPI (For Sentiment Analysis)**
- **Free**: 1000 requests/month
- **Paid**: From $449/month
- **Sign up**: https://newsapi.org/
- **What you get**: Real financial news, sentiment analysis

```bash
# Add to your .env file:
NEWS_API_KEY=your_key_here
```

---

## 🔧 **How to Add API Keys**

### **Method 1: Environment File (Recommended)**
1. Edit your `.env` file:
```bash
nano /Users/sandgupt/RandomIdeasWithAI/stock_predictor/.env
```

2. Add your API keys:
```bash
# Free APIs
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
NEWS_API_KEY=your_news_api_key

# Premium APIs  
POLYGON_API_KEY=your_polygon_key
IEX_API_KEY=your_iex_key
```

3. Restart the server:
```bash
./start_dev.sh
```

### **Method 2: Export in Terminal**
```bash
export ALPHA_VANTAGE_API_KEY=your_key_here
export POLYGON_API_KEY=your_key_here
./start_dev.sh
```

---

## 🚦 **Data Source Priority**

The system automatically falls back through these sources:

1. **Polygon.io** (if API key available) - Highest quality
2. **Alpha Vantage** (if API key available) - Good quality  
3. **Yahoo Finance** (free, always available) - Basic data
4. **Mock Data** (always available) - Demo/development

---

## 💰 **Cost Breakdown**

| Service | Free Tier | Paid Plan | Best For |
|---------|-----------|-----------|----------|
| **Yahoo Finance** | ✅ Unlimited | N/A | Basic quotes |
| **Alpha Vantage** | 500 calls/day | $49.99/month | Getting started |
| **Polygon.io** | 5 calls/min | $99/month | Real-time data |
| **NewsAPI** | 1000/month | $449/month | News sentiment |
| **IEX Cloud** | 500k credits | $9/month | Comprehensive |

---

## 🤖 **Robinhood Integration**

For **Robinhood** account integration:

1. **Use SnapTrade** (recommended broker API)
   - Sign up: https://snaptrade.com/
   - Get sandbox credentials first
   - Production requires business verification

2. **Unofficial Robinhood API** (higher risk)
   - Use robin-stocks Python library
   - Requires your Robinhood login
   - May violate terms of service

---

## 🎉 **Quick Start Recommendations**

### **For Demo/Development:**
✅ **Use current free setup** - Already working!

### **For Real Trading:**
1. Get **Alpha Vantage** free key (5 minutes setup)
2. Add **NewsAPI** free key for sentiment
3. Upgrade to **Polygon.io** when you need real-time

### **For Production:**
1. **Polygon.io** ($99/month) for real-time data
2. **NewsAPI** ($449/month) for comprehensive news
3. **SnapTrade** for brokerage integration

---

## ⚠️ **Important Notes**

- **Current system works without any API keys**
- **Add keys gradually** as you need more features
- **Free tiers are perfect** for testing and development
- **Always test with paper trading** before real money
- **API keys are stored securely** in environment variables

---

**🚀 Ready to get started? Your system is already running with free data!**
**Visit: http://127.0.0.1:8000**
