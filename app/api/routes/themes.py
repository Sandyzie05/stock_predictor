"""
Theme research API routes.
"""

from fastapi import APIRouter

from app.services.theme_models import AIInfrastructureThemeModel


router = APIRouter(prefix="/themes", tags=["themes"])


@router.get("/ai-infrastructure", response_model=dict)
async def get_ai_infrastructure_theme():
    """Get the AI infrastructure and inference theme map."""
    return AIInfrastructureThemeModel().get_theme_map()
