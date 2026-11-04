import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.incident import IncidentSeverity, IncidentStatus


class IncidentBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    status: IncidentStatus = IncidentStatus.OPEN
    source: str = Field(default="telemetry", max_length=100)
    source_id: Optional[str] = Field(None, max_length=255)
    root_cause_summary: Optional[str] = None


class IncidentCreate(IncidentBase):
    project_id: uuid.UUID


class IncidentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    severity: Optional[IncidentSeverity] = None
    status: Optional[IncidentStatus] = None
    root_cause_summary: Optional[str] = None
    resolved_at: Optional[datetime] = None


class IncidentResponse(IncidentBase):
    id: uuid.UUID
    project_id: uuid.UUID
    project_name: Optional[str] = None
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentEventCreate(BaseModel):
    incident_id: uuid.UUID
    event_type: str = Field(..., max_length=100)
    actor_type: str = Field(..., max_length=50)
    actor_identifier: Optional[str] = Field(None, max_length=100)
    description: str
    event_metadata: Dict[str, Any] = Field(default_factory=dict)


class IncidentEventResponse(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    event_type: str
    actor_type: str
    actor_identifier: Optional[str] = None
    description: str
    event_metadata: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

