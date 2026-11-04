import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.approval import ApprovalDecision


class ApprovalCreate(BaseModel):
    patch_id: uuid.UUID
    patch_hash: str = Field(..., max_length=64)
    decision: ApprovalDecision
    reviewer_identifier: str = Field(..., max_length=100)
    comment: Optional[str] = None


class ApprovalResponse(BaseModel):
    id: uuid.UUID
    patch_id: uuid.UUID
    patch_hash: str
    decision: ApprovalDecision
    reviewer_identifier: str
    comment: Optional[str] = None
    decided_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatchApproveRequest(BaseModel):
    comment: Optional[str] = Field(None, max_length=1000, description="Optional reviewer comment on approval")


class PatchRejectRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=1000, description="Optional rejection reason")

