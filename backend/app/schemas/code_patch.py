import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CodePatchCreate(BaseModel):
    incident_id: uuid.UUID
    agent_execution_id: Optional[uuid.UUID] = None
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    patch_content: str
    base_commit: Optional[str] = Field(None, max_length=40)


class CodePatchResponse(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    agent_execution_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    patch_content: str
    patch_hash: str
    base_commit: Optional[str] = None
    status: str
    is_hash_valid: bool = Field(default=True, description="Verified cryptographic SHA-256 integrity")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

