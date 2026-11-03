import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    repository_url: Optional[str] = Field(None, max_length=255)
    default_branch: str = Field(default="main", max_length=50)
    environment: str = Field(default="development", max_length=50)
    status: str = Field(default="active", max_length=50)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    repository_url: Optional[str] = Field(None, max_length=255)
    default_branch: Optional[str] = Field(None, max_length=50)
    environment: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=50)


class ProjectResponse(ProjectBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

