#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "🚀 Starting Stock Predictor - REAL DATA Production Mode"
echo "======================================================="

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    echo "🔄 Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️ Virtual environment not found. Please run 'make dev' first."
    exit 1
fi

# Set production environment variables for REAL data
export ENVIRONMENT="production"
export SECRET_KEY=${SECRET_KEY:-$(openssl rand -hex 32)}
export DATABASE_URL=${DATABASE_URL:-"sqlite+aiosqlite:///./stock_predictor_prod.db"}
export DEBUG="false"

echo "📋 Production Environment Variables Set:"
echo "  ENVIRONMENT=$ENVIRONMENT"
echo "  DATABASE_URL=$DATABASE_URL"
echo "  DEBUG=$DEBUG"

# Check for API key and set preferences
if [ -n "$ALPHA_VANTAGE_API_KEY" ]; then
    echo "  ALPHA_VANTAGE_API_KEY=***${ALPHA_VANTAGE_API_KEY: -4}"
    echo "✅ Will use Alpha Vantage for premium real data"
else
    echo "  ALPHA_VANTAGE_API_KEY=not_set"
    echo "📊 Will use Yahoo Finance for free real data"
fi

echo ""
echo "🌐 REAL DATA SOURCES ENABLED:"
echo "   ✅ Yahoo Finance API (real-time quotes)"
echo "   ✅ Enhanced company database"
echo "   ✅ Real financial calculations"
echo "   ❌ Mock data DISABLED"
echo ""
echo "🔄 Starting production server with REAL data..."
echo "📚 API Documentation: http://localhost:8000/docs"
echo "🏥 Health Check: http://localhost:8000/health"
echo "📊 Stock Quote Test: http://localhost:8000/api/v1/stocks/AAPL/quote"
echo ""
echo "💰 You will see REAL stock prices from Yahoo Finance!"
echo "Press Ctrl+C to stop the server"

# Start Uvicorn production server
uvicorn app.main:app --host 127.0.0.1 --port 8000
