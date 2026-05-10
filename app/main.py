"""
FastAPI main application module.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import api_router
from app.core.config import settings
from app.core.database import create_tables
from app.services.market_intelligence import MarketIntelligenceService


logger = logging.getLogger(__name__)


async def refresh_market_workspace_forever() -> None:
    """Keep the daily market workspace warm so new-day snapshots appear automatically."""
    interval_seconds = max(300, settings.MARKET_INTELLIGENCE_CACHE_TTL_SECONDS)
    while True:
        try:
            async with MarketIntelligenceService() as service:
                await service.build_today_report(limit=5)
                await service.daily_prediction_report(days=30)
        except asyncio.CancelledError:  # pragma: no cover - shutdown path
            raise
        except Exception:
            logger.exception("Market workspace refresh failed")

        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await create_tables()
    refresh_task = None
    if settings.ENABLE_MARKET_INTELLIGENCE and settings.ENVIRONMENT != "testing":
        refresh_task = asyncio.create_task(refresh_market_workspace_forever())
        app.state.market_workspace_refresh_task = refresh_task
    yield
    # Shutdown - cleanup if needed
    if refresh_task:
        refresh_task.cancel()
        try:
            await refresh_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Stock Predictor API",
    description="A comprehensive stock prediction and analysis service",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],  # Allow all hosts for development and local testing
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Serve the main web interface."""
    from fastapi.responses import FileResponse
    return FileResponse('app/static/index.html')


@app.get("/api")
async def api_root():
    """API root endpoint."""
    return {"message": "Stock Predictor API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
