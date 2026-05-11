#!/usr/bin/env python3
"""
Development server startup script.
"""

import os
import sys

# Set environment variables
os.environ["ENVIRONMENT"] = "development"
os.environ["SECRET_KEY"] = "dev-secret-key"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./stock_predictor_dev.db"
os.environ["DEBUG"] = "true"
os.environ.setdefault("HOST", "127.0.0.1")
os.environ.setdefault("PORT", "8000")

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.main import app
    print("✅ FastAPI app loaded successfully")
    
    # Import and run uvicorn
    import uvicorn
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"🚀 Starting development server on http://{host}:{port}")
    print(f"📚 API docs will be available at http://{host}:{port}/docs")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
    
except Exception as e:
    print(f"❌ Error starting server: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
