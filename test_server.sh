#!/bin/bash

echo "🧪 Testing Server Configuration"
echo "==============================="

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Set simple environment
export ENVIRONMENT="development"
export SECRET_KEY="test-secret-key"
export DATABASE_URL="sqlite+aiosqlite:///./test.db"

echo "Starting server with minimal configuration..."
echo "Server will be at: http://localhost:8000"
echo ""

# Start with minimal settings
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
