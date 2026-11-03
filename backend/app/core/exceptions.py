import logging
from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger("nexops.exceptions")


def get_request_headers(request: Request) -> dict[str, str]:
    """Extract request-id header to attach to error responses."""
    request_id = getattr(request.state, "request_id", None)
    headers: dict[str, str] = {}
    if request_id:
        headers["X-Request-ID"] = request_id
    return headers


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle standard HTTP exceptions with unified error envelope."""
    status_code = exc.status_code
    message = exc.detail if isinstance(exc.detail, str) else "HTTP Exception"
    code = "NOT_FOUND" if status_code == status.HTTP_404_NOT_FOUND else f"HTTP_{status_code}"

    error_body = ErrorResponse(
        success=False,
        message=message,
        error=ErrorDetail(code=code, details=[]),
    )

    return JSONResponse(
        status_code=status_code,
        content=error_body.model_dump(),
        headers=get_request_headers(request),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors with clean structured details."""
    details: list[dict[str, Any]] = []
    for err in exc.errors():
        loc = " -> ".join([str(item) for item in err.get("loc", []) if item != "body"])
        details.append({
            "field": loc or "body",
            "message": err.get("msg", "Invalid value"),
            "type": err.get("type", "value_error"),
        })

    error_body = ErrorResponse(
        success=False,
        message="Validation failed",
        error=ErrorDetail(code="VALIDATION_ERROR", details=details),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT") else 422,
        content=error_body.model_dump(),
        headers=get_request_headers(request),
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors without leaking stack traces or credentials."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("Unhandled server exception occurred. Request ID: %s, Error: %s", request_id, str(exc))

    error_body = ErrorResponse(
        success=False,
        message="Internal server error",
        error=ErrorDetail(code="INTERNAL_SERVER_ERROR", details=[]),
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_body.model_dump(),
        headers=get_request_headers(request),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all custom exception handlers on the FastAPI application."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
