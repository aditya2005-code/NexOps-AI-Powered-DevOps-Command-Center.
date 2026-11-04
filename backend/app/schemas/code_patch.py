import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
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


class PatchApplicationStatusResponse(BaseModel):
    patch_id: uuid.UUID
    incident_id: uuid.UUID
    status: str
    base_commit: Optional[str] = None
    applied_at: Optional[datetime] = None
    applied_by: Optional[str] = None
    modified_files: List[str] = Field(default_factory=list)
    lines_added: Optional[int] = None
    lines_removed: Optional[int] = None
    execution_details: Dict[str, Any] = Field(default_factory=dict)
    error_summary: Optional[str] = None
    is_hash_valid: bool = Field(default=True, description="Verified cryptographic SHA-256 integrity")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

