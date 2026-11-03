from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.common import BaseResponse


class HealthData(BaseModel):
    """Payload for health status response."""
    status: str = Field(default="healthy", description="Application status")
    application: str = Field(default="NexOps", description="Application name")
    environment: str = Field(default="development", description="Current runtime environment")
    version: Optional[str] = Field(default=None, description="Current application version")


class HealthResponse(BaseResponse[HealthData]):
    """Standard health check response model."""
    pass

