"""Phase 5A.4 — health endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.config import APP_VERSION, GRAPH_CONFIG_VERSION, MODEL_VERSION, Settings
from src.api.dependencies import get_settings
from src.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    description=(
        "Reports service status and the static version labels of the frozen "
        "artifacts this API serves (ML model, graph config). Never returns "
        "secrets or credentials — the llm_backend field names which backend "
        "is configured (e.g. 'stub', 'claude_agent_sdk'), never a key or token."
    ),
)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_version=APP_VERSION,
        model_version=MODEL_VERSION,
        graph_config_version=GRAPH_CONFIG_VERSION,
        environment=settings.environment,
        llm_backend=settings.llm_backend,
    )
