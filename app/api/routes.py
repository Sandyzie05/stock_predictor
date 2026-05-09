"""
API routes module - routes are now organized in separate files.
"""

from fastapi import APIRouter
from app.api.routes.stocks import router as stocks_router
from app.api.routes.lists import router as lists_router
from app.api.routes.themes import router as themes_router

# Main API router
api_router = APIRouter()

# Include route modules
api_router.include_router(stocks_router)
api_router.include_router(lists_router)
api_router.include_router(themes_router)


@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Stock Predictor API is running"}


__all__ = ["api_router"]
