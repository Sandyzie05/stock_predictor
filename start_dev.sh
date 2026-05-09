#!/bin/bash

echo "🚀 Starting Stock Predictor Development Server"
echo "=============================================="

# Load .env when present so local API keys and overrides are picked up.
if [ -f .env ]; then
  echo "🔐 Loading environment from .env"
  set -a
  . ./.env
  set +a
fi

# Set development defaults only when they are not already provided.
export ENVIRONMENT="${ENVIRONMENT:-development}"
export SECRET_KEY="${SECRET_KEY:-dev-secret-key}"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./stock_predictor_dev.db}"
export DEBUG="${DEBUG:-true}"

echo "📋 Environment Variables Set:"
echo "  ENVIRONMENT=$ENVIRONMENT"
echo "  SECRET_KEY=$SECRET_KEY"
echo "  DATABASE_URL=$DATABASE_URL"
echo ""

# Activate virtual environment and start server
echo "🔄 Activating virtual environment..."
source venv/bin/activate

echo "🚀 Starting FastAPI server..."
echo "📚 API Documentation: http://127.0.0.1:8000/docs"
echo "🏥 Health Check: http://127.0.0.1:8000/health"
echo "📊 API Health: http://127.0.0.1:8000/api/v1/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --log-level info
