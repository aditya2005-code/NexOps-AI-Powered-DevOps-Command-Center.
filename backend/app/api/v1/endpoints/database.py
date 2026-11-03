import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.dependencies import get_db
from app.schemas.common import BaseResponse, ErrorResponse, ErrorDetail

logger = logging.getLogger("nexops.database.health")
router = APIRouter()


@router.get(
    "/health/database",
    response_model=BaseResponse[Dict[str, Any]],
    summary="Database Connectivity Health Check",
    description="Validates live connectivity and query execution against the primary database.",
)
def database_health(db: Session = Depends(get_db)):
    """Check database health by executing a lightweight SELECT 1 query."""
    try:
        result = db.execute(text("SELECT 1;")).scalar()
        if result == 1:
            dialect_name = db.bind.dialect.name if db.bind else "unknown"
            return BaseResponse(
                success=True,
                message="Database connection successful",
                data={
                    "status": "healthy",
                    "database": dialect_name,
                },
            )
        raise RuntimeError("Database validation query returned unexpected result")
    except Exception as exc:
        logger.error("Database health check failed: %s", type(exc).__name__)
        error_body = ErrorResponse(
            success=False,
            message="Database connection failed",
            error=ErrorDetail(code="DATABASE_UNAVAILABLE", details=[]),
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=error_body.model_dump(),
        )

