from typing import Optional
from fastapi import APIRouter, Query
from app.core.config import settings
from app.schemas.health import HealthData, HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Versioned API Health Check",
    description="Returns operational status of the versioned NexOps API v1.",
)
async def api_health(
    echo: Optional[str] = Query(None, max_length=50, description="Optional echo string for validation checks")
) -> HealthResponse:
    """Return structured health status for NexOps API v1."""
    return HealthResponse(
        success=True,
        message="NexOps backend is operational",
        data=HealthData(
            status="healthy",
            application=settings.APP_NAME,
            environment=settings.APP_ENV,
            version=settings.APP_VERSION,
        ),
    )
