#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "🚀 Starting Stock Predictor - Production Mode (With Fallbacks)"
echo "=============================================================="

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

# Check for API key
if [ -n "$ALPHA_VANTAGE_API_KEY" ]; then
    echo "  ALPHA_VANTAGE_API_KEY=***${ALPHA_VANTAGE_API_KEY: -4}"
    echo "✅ Will use Alpha Vantage for real data"
else
    echo "  ALPHA_VANTAGE_API_KEY=not_set"
    echo "📊 Will use Yahoo Finance + enhanced mock data"
fi

echo ""
echo "🔄 Starting production server..."
echo "📚 API Documentation: http://localhost:8000/docs"
echo "🏥 Health Check: http://localhost:8000/health"
echo "📊 API Health: http://localhost:8000/api/v1/health"
echo ""
echo "💡 Data Sources (in order of preference):"
echo "   1. Alpha Vantage (if API key valid)"
echo "   2. Yahoo Finance (free, reliable)"
echo "   3. Enhanced mock data (realistic fallback)"
echo ""
echo "Press Ctrl+C to stop the server"

# Start Uvicorn production server (single worker to avoid host header issues)
uvicorn app.main:app --host 127.0.0.1 --port 8000
