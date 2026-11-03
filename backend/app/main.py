import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import RequestResponseEndpoint

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.schemas.health import HealthData, HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle management."""
    setup_logging(settings.LOG_LEVEL)
    yield


def create_app() -> FastAPI:
    """Factory function to build and configure the NexOps FastAPI application."""
    app_instance = FastAPI(
        title=settings.APP_NAME,
        description="AI-Powered DevOps Command Center",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 1. Request ID and Performance Middleware
    @app_instance.middleware("http")
    async def request_context_middleware(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Resolve or generate request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Let registered exception handlers format response, but preserve headers
            raise

        process_time = time.perf_counter() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.6f}s"
        return response

    # 2. CORS Middleware
    app_instance.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. Register Centralized Exception Handlers
    register_exception_handlers(app_instance)

    # 4. Register API Routes
    app_instance.include_router(v1_router, prefix=settings.API_V1_PREFIX)

    # 5. Root & Health Endpoints
    @app_instance.get(
        "/",
        response_model=HealthResponse,
        tags=["System"],
        summary="Root Application Information",
    )
    async def root() -> HealthResponse:
        return HealthResponse(
            success=True,
            message="NexOps backend is operational",
            data=HealthData(
                status="healthy",
                application=settings.APP_NAME,
                environment=settings.APP_ENV,
                version=settings.APP_VERSION,
            ),
        )

    @app_instance.get(
        "/health",
        response_model=HealthResponse,
        tags=["System"],
        summary="System Health Status",
    )
    async def health() -> HealthResponse:
        return HealthResponse(
            success=True,
            message="NexOps backend is operational",
            data=HealthData(
                status="healthy",
                application=settings.APP_NAME,
                environment=settings.APP_ENV,
                version=settings.APP_VERSION,
            ),
        )

    return app_instance


app = create_app()
