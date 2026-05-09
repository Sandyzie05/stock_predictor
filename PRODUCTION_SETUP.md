# 🚀 Stock Predictor - Production Setup Guide

## 📋 **Production Requirements**

To run the Stock Predictor with **real market data**, you'll need API keys from the following services:

### **Required API Keys:**

#### 1. **Alpha Vantage** (Recommended - Free Tier Available)
- **Purpose**: Real-time stock quotes, company info, historical data
- **Free Tier**: 5 calls/minute, 500/day
- **Get Key**: https://www.alphavantage.co/support/#api-key
- **Cost**: Free (Premium plans available)

#### 2. **Polygon.io** (Professional Grade)
- **Purpose**: Real-time market data, advanced analytics
- **Free Tier**: 5 calls/minute
- **Get Key**: https://polygon.io/
- **Cost**: Free tier available, paid plans from $99/month

#### 3. **NewsAPI** (Optional - For News Sentiment)
- **Purpose**: Financial news and sentiment analysis
- **Free Tier**: 1000 requests/month
- **Get Key**: https://newsapi.org/
- **Cost**: Free (Premium plans available)

---

## 🔧 **Production Environment Setup**

### **Step 1: Get API Keys**

1. **Alpha Vantage** (Start here - it's free and reliable):
   ```bash
   # Visit: https://www.alphavantage.co/support/#api-key
   # Sign up with email
   # Copy your API key
   ```

2. **Polygon.io** (For advanced features):
   ```bash
   # Visit: https://polygon.io/
   # Create account
   # Get your API key from dashboard
   ```

3. **NewsAPI** (For news sentiment):
   ```bash
   # Visit: https://newsapi.org/
   # Register with email
   # Get your API key
   ```

### **Step 2: Create Production Environment File**

```bash
# Create production environment file
cp .env.example .env.production

# Edit the file with your API keys
nano .env.production
```

Add your keys to `.env.production`:
```bash
# Production Environment
ENVIRONMENT=production
SECRET_KEY=your-super-secure-secret-key-here

# Database (Use PostgreSQL for production)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/stock_predictor

# API Keys for Real Data
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
POLYGON_API_KEY=your_polygon_key_here
NEWS_API_KEY=your_news_api_key_here

# Optional: Redis for caching
REDIS_URL=redis://localhost:6379

# Security
CORS_ORIGINS=["https://yourdomain.com"]
TRUSTED_HOSTS=["yourdomain.com"]
```

### **Step 3: Setup Production Database**

```bash
# Install PostgreSQL (macOS)
brew install postgresql
brew services start postgresql

# Create database
createdb stock_predictor

# Run migrations
export DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/stock_predictor
alembic upgrade head
```

### **Step 4: Install Production Dependencies**

```bash
# Activate virtual environment
source venv/bin/activate

# Install production dependencies
pip install uvicorn[standard] gunicorn

# Verify installation
pip list | grep -E "(uvicorn|gunicorn|asyncpg)"
```

---

## 🚀 **Running Production Version**

### **Option 1: Quick Start with Alpha Vantage (Recommended)**

```bash
# Set environment variables
export ENVIRONMENT=production
export SECRET_KEY=your-secure-secret-key
export DATABASE_URL=sqlite+aiosqlite:///./stock_predictor_prod.db
export ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here

# Run production server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### **Option 2: Full Production with PostgreSQL**

```bash
# Load environment from file
export $(cat .env.production | grep -v '^#' | xargs)

# Run with Gunicorn (production WSGI server)
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### **Option 3: Docker Production Deployment**

```bash
# Build production image
docker build -t stock-predictor:prod .

# Run with environment file
docker run -p 8000:8000 --env-file .env.production stock-predictor:prod
```

---

## 🧪 **Testing Real Data**

Once you have API keys set up, test the real data:

```bash
# Test Alpha Vantage connection
curl "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey=YOUR_KEY"

# Test your production app
curl http://localhost:8000/api/v1/stocks/AAPL/quote

# Should return real Apple stock price!
```

---

## 📊 **API Key Priority & Fallbacks**

The system uses this priority order:

1. **Alpha Vantage** (if key provided) - Real data
2. **Polygon.io** (if key provided) - Real data  
3. **Yahoo Finance** - Free real data (limited)
4. **Mock Data** - Fallback for development

---

## 💰 **Cost Breakdown**

### **Free Tier (Recommended for Testing)**
- **Alpha Vantage**: Free (500 calls/day)
- **NewsAPI**: Free (1000 requests/month)
- **Total**: $0/month

### **Professional Tier**
- **Alpha Vantage Pro**: $49.99/month
- **Polygon.io Basic**: $99/month
- **NewsAPI Premium**: $49/month
- **Total**: ~$200/month

---

## 🔐 **Security Best Practices**

### **API Key Security**
```bash
# Never commit API keys to git
echo ".env*" >> .gitignore

# Use environment variables
export ALPHA_VANTAGE_API_KEY=your_key_here

# Rotate keys regularly
# Monitor API usage
```

### **Production Security**
```bash
# Use strong secret key
export SECRET_KEY=$(openssl rand -hex 32)

# Enable HTTPS
# Set up proper CORS
# Use database authentication
# Enable API rate limiting
```

---

## 🚀 **Quick Production Start Script**

Create `start_prod.sh`:
```bash
#!/bin/bash
echo "🚀 Starting Stock Predictor - Production Mode"
echo "=============================================="

# Check for required API keys
if [ -z "$ALPHA_VANTAGE_API_KEY" ]; then
    echo "❌ ALPHA_VANTAGE_API_KEY not set"
    echo "Get one free at: https://www.alphavantage.co/support/#api-key"
    exit 1
fi

echo "✅ API Keys validated"
echo "🔄 Starting production server..."

# Set production environment
export ENVIRONMENT=production
export SECRET_KEY=${SECRET_KEY:-$(openssl rand -hex 32)}
export DATABASE_URL=${DATABASE_URL:-"sqlite+aiosqlite:///./stock_predictor_prod.db"}

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

echo "🌐 Production server running at: http://localhost:8000"
echo "📚 API Documentation: http://localhost:8000/docs"
```

Make it executable:
```bash
chmod +x start_prod.sh
```

---

## 📈 **Expected Results with Real Data**

With API keys configured, you'll get:

- **Real-time stock prices** (updated every minute)
- **Accurate company information** 
- **Historical price data** for analysis
- **Professional-grade recommendations**
- **Real financial news** sentiment

---

## 🆘 **Troubleshooting**

### **Common Issues:**

1. **"API key invalid"**
   ```bash
   # Verify your key works:
   curl "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey=YOUR_KEY"
   ```

2. **"Rate limit exceeded"**
   ```bash
   # Alpha Vantage: 5 calls/minute, 500/day
   # Wait or upgrade to premium
   ```

3. **"Database connection failed"**
   ```bash
   # Check DATABASE_URL format
   # Ensure PostgreSQL is running
   ```

---

**🎯 Ready to get real data? Start with Alpha Vantage - it's free and takes 2 minutes to set up!**
