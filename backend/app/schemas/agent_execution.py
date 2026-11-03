import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.agent_execution import AgentType, AgentExecutionStatus


class AgentExecutionCreate(BaseModel):
    incident_id: Optional[uuid.UUID] = None
    agent_type: AgentType
    input_data: Dict[str, Any] = Field(default_factory=dict)


class AgentExecutionResponse(BaseModel):
    id: uuid.UUID
    incident_id: Optional[uuid.UUID] = None
    agent_type: AgentType
    status: AgentExecutionStatus
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    error_summary: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

