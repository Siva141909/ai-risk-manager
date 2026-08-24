"""Phase 5A — dependency providers.

All expensive/singleton objects (`ToolDataContext`, `PolicyCorpus`,
`CaseRepository`, the LLM client, the cache) are built ONCE at app
startup (`src/api/main.py`'s lifespan) and stored on `app.state` — never
rebuilt per-request. Route handlers depend on the small `Depends(...)`
functions below, never on `app.state` directly, so tests can override
them (`app.dependency_overrides`) without touching app startup.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from src.agents.llm_client import AnthropicAPIClient, ClaudeAgentSDKClient, LLMClient, StubLLMClient
from src.api.cache import InvestigationCache
from src.api.config import Settings
from src.api.repository import CaseRepository
from src.api.services import CaseService, GraphVisualizationService, InvestigationService
from src.rag.retrieval import PolicyCorpus
from src.tools.context import ToolDataContext, load_tool_data_context


@dataclass
class AppState:
    settings: Settings
    ctx: ToolDataContext
    corpus: PolicyCorpus
    repository: CaseRepository
    cache: InvestigationCache
    llm_client: LLMClient


def build_llm_client(backend: str) -> LLMClient:
    if backend == "stub":
        return StubLLMClient()
    if backend == "claude_agent_sdk":
        return ClaudeAgentSDKClient()
    if backend == "anthropic_api":
        return AnthropicAPIClient()
    raise ValueError(f"unknown llm backend: {backend!r}")


def build_app_state(settings: Settings) -> AppState:
    ctx = load_tool_data_context(settings.project_root)
    corpus = PolicyCorpus.from_directory(settings.project_root / "docs" / "policy_documents")
    repository = CaseRepository.from_project_root(ctx, settings.project_root)
    cache = InvestigationCache()
    llm_client = build_llm_client(settings.llm_backend)
    return AppState(settings=settings, ctx=ctx, corpus=corpus, repository=repository, cache=cache, llm_client=llm_client)


def get_app_state(request: Request) -> AppState:
    return request.app.state.risk_manager


def get_case_service(request: Request) -> CaseService:
    state: AppState = get_app_state(request)
    return CaseService(state.repository, state.ctx, state.cache, state.llm_client.backend_name)


def get_graph_service(request: Request) -> GraphVisualizationService:
    state: AppState = get_app_state(request)
    return GraphVisualizationService(state.ctx, state.corpus)


def get_investigation_service(request: Request) -> InvestigationService:
    state: AppState = get_app_state(request)
    return InvestigationService(state.ctx, state.corpus, state.llm_client, state.cache)


def get_settings(request: Request) -> Settings:
    state: AppState = get_app_state(request)
    return state.settings
