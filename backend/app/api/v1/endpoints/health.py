from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str

@router.get("/health", response_model=HealthResponse)
async def health():
    from app.core.config import settings
    return HealthResponse(status="ok", version=settings.APP_VERSION, environment=settings.ENVIRONMENT)
