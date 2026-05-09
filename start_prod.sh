#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "🚀 Starting Stock Predictor - Production Mode"
echo "=============================================="

# Check for required API keys
if [ -z "$ALPHA_VANTAGE_API_KEY" ]; then
    echo "❌ ALPHA_VANTAGE_API_KEY not set"
    echo ""
    echo "🔑 To get real stock data, you need an Alpha Vantage API key:"
    echo "1. Visit: https://www.alphavantage.co/support/#api-key"
    echo "2. Sign up with your email (free)"
    echo "3. Copy your API key"
    echo "4. Run: export ALPHA_VANTAGE_API_KEY=your_key_here"
    echo ""
    echo "Or continue with mock data by running:"
    echo "./start_dev.sh"
    exit 1
fi

echo "✅ Alpha Vantage API key found"

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    echo "🔄 Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️ Virtual environment not found. Please run 'make dev' first."
    exit 1
fi

# Set production environment variables
export ENVIRONMENT="production"
export SECRET_KEY=${SECRET_KEY:-$(openssl rand -hex 32)}
export DATABASE_URL=${DATABASE_URL:-"sqlite+aiosqlite:///./stock_predictor_prod.db"}

echo "📋 Production Environment Variables Set:"
echo "  ENVIRONMENT=$ENVIRONMENT"
echo "  DATABASE_URL=$DATABASE_URL"
echo "  ALPHA_VANTAGE_API_KEY=***${ALPHA_VANTAGE_API_KEY: -4}"

echo ""
echo "🔄 Starting production server with real data..."
echo "📚 API Documentation: http://localhost:8000/docs"
echo "🏥 Health Check: http://localhost:8000/health"
echo "📊 API Health: http://localhost:8000/api/v1/health"
echo "💰 Real stock data from Alpha Vantage"
echo ""
echo "Press Ctrl+C to stop the server"

# Start Uvicorn production server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
