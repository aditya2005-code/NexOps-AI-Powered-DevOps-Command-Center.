import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class AuditLogCreate(BaseModel):
    actor_type: str = Field(..., max_length=50)
    actor_identifier: Optional[str] = Field(None, max_length=100)
    action: str = Field(..., max_length=100)
    resource_type: str = Field(..., max_length=100)
    resource_id: Optional[uuid.UUID] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    actor_type: str
    actor_identifier: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[uuid.UUID] = None
    details: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

