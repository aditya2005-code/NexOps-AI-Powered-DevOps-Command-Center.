from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class BaseResponse(BaseModel, Generic[DataT]):
    """Standardized API response envelope."""
    success: bool = True
    message: str
    data: Optional[DataT] = None


class ErrorDetail(BaseModel):
    """Structured error metadata."""
    code: str
    details: Any = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Standardized error envelope."""
    success: bool = False
    message: str
    error: ErrorDetail

