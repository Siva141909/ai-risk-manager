"""Phase 5A — FastAPI application factory.

FastAPI -> application service layer -> existing deterministic pipeline
-> case generation -> investigation agent -> structured response
(the Phase 5A architecture diagram). This module wires that stack
together and contains no ML/graph/agent/RAG/tool logic itself: routers
(`src/api/routers/`) call services (`src/api/services.py`), which call
the frozen Phase 2-4 modules.

Run for local development:
    uvicorn src.api.main:app --reload

`RISK_MANAGER_LLM_BACKEND` selects the LLM backend (`stub` by default —
no credential required; see docs/DEVELOPMENT_RUNBOOK.md).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.api.config import Settings
from src.api.dependencies import build_app_state
from src.api.errors import ApiError
from src.api.logging_mw import RequestLoggingMiddleware
from src.api.routers import cases, health
from src.api.security_mw import BodySizeLimitMiddleware
from src.logging_conf import get_logger

logger = get_logger("api.main")


def _error_body(request: Request, error_code: str, message: str) -> dict:
    return {
        "error_code": error_code,
        "message": message,
        "request_id": getattr(request.state, "request_id", ""),
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.risk_manager = build_app_state(settings)
        logger.info("api_startup", extra={"llm_backend": settings.llm_backend, "environment": settings.environment})
        yield

    app = FastAPI(
        title="AI Risk Manager API",
        version="0.5.0",
        description=(
            "Production-style backend for the AI Risk Manager fraud/coordinated-abuse investigation "
            "system. Wraps the frozen Phase 2-4 pipeline (ML risk scoring, graph evidence, and the "
            "LangGraph investigation agent) behind a clean REST API. See docs/API.md."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_body_bytes)
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(health.router)
    app.include_router(cases.router)

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(request, exc.error_code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic's own error detail is safe to return (it names fields/constraints,
        # never internal state) but is trimmed to avoid leaking overly verbose internals.
        first_error = exc.errors()[0] if exc.errors() else {"msg": "invalid request"}
        return JSONResponse(
            status_code=422,
            content=_error_body(request, "malformed_request", str(first_error.get("msg", "invalid request"))),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.info(
            "unhandled_exception",
            extra={
                "request_id": getattr(request.state, "request_id", ""),
                "path": request.url.path,
                "error_type": type(exc).__name__,
            },
        )
        return JSONResponse(
            status_code=500,
            content=_error_body(request, "internal_error", "an unexpected error occurred"),
        )

    return app


app = create_app()
