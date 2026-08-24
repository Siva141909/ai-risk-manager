"""Phase 5A — application service layer.

The only layer that touches domain objects (`Case`, `ToolRegistry`,
`run_investigation`, `PolicyCorpus`). FastAPI route handlers
(`src/api/routers/`) call these services and translate their return
values/exceptions into HTTP responses — they never import
`src.agents`, `src.tools`, `src.graph`, or `src.models` directly. No
ML/graph/agent/RAG/tool logic is implemented in this module either — it
only orchestrates the existing, frozen Phase 2-4 functions and times/
caches/error-wraps the calls (exactly the boundary Phase 5A.0's
architecture diagram describes).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from src.agents.case_contract import build_agent_input
from src.agents.graph import InvestigationGraphDeps, run_investigation
from src.agents.llm_client import LLMClient
from src.api.cache import InvestigationCache, InvestigationCacheKey
from src.api.config import GRAPH_CONFIG_VERSION, MODEL_VERSION, Settings
from src.api.errors import (
    AgentExecutionError,
    CaseNotFoundError,
    InvestigationNotFoundError,
    LLMUnavailableError,
    MalformedCaseIdError,
    UnsupportedInvestigationModeError,
)
from src.api.repository import CaseRepository, CaseSummary, transaction_id_from_case_id
from src.graph.case_interface import Case
from src.logging_conf import get_logger
from src.rag.retrieval import PolicyCorpus
from src.tools.context import ToolDataContext
from src.tools.registry import ToolRegistry

logger = get_logger("api.services")


# ---------------------------------------------------------------------------
# Case listing / detail / graph
# ---------------------------------------------------------------------------


class CaseService:
    def __init__(self, repository: CaseRepository, ctx: ToolDataContext, cache: InvestigationCache, llm_backend: str) -> None:
        self._repository = repository
        self._ctx = ctx
        self._cache = cache
        self._llm_backend = llm_backend

    def resolve_case_id(self, transaction_id: int | None, case_id: str | None) -> str:
        """Both `InvestigateRequest` fields ultimately resolve to a single
        canonical case_id — this is the one place that conversion happens."""
        if transaction_id is not None:
            from src.api.repository import case_id_for_transaction

            return case_id_for_transaction(transaction_id)
        assert case_id is not None
        try:
            transaction_id_from_case_id(case_id)
        except ValueError as exc:
            raise MalformedCaseIdError(str(exc)) from exc
        return case_id

    def list_cases(
        self,
        risk_tier: str | None,
        graph_flagged: bool | None,
        investigation_status: str | None,
        start_dt: int | None,
        end_dt: int | None,
        limit: int,
        offset: int,
    ) -> tuple[list[CaseSummary], int, list[bool]]:
        investigated_transaction_ids = None
        if investigation_status is not None:
            investigated_transaction_ids = {
                transaction_id_from_case_id(cid) for cid in self._cache.investigated_case_ids()
            }
        summaries, total = self._repository.list_cases(
            risk_tier=risk_tier, graph_flagged=graph_flagged,
            start_dt=start_dt, end_dt=end_dt, limit=limit, offset=offset,
            investigation_status=investigation_status, investigated_transaction_ids=investigated_transaction_ids,
        )
        has_investigation = [self._cache.has_case(s.case_id) for s in summaries]
        return summaries, total, has_investigation

    def get_case(self, case_id: str) -> Case:
        try:
            transaction_id_from_case_id(case_id)
        except ValueError as exc:
            raise MalformedCaseIdError(str(exc)) from exc
        case = self._repository.get_case(case_id)
        if case is None:
            raise CaseNotFoundError(
                f"case {case_id!r} not found — no frozen validation/test-split ML score exists for it "
                "(only validation/test transactions are servable; see docs/BACKEND_ARCHITECTURE.md)"
            )
        return case

    def get_investigation_report(self, case_id: str) -> dict:
        key = InvestigationCacheKey(
            case_id=case_id,
            investigation_mode="real_time",
            llm_backend=self._llm_backend,
            model_version=MODEL_VERSION,
            graph_config_version=GRAPH_CONFIG_VERSION,
        )
        report = self._cache.get(key)
        if report is None:
            raise InvestigationNotFoundError(
                f"no investigation has been run for case {case_id!r} yet — "
                "POST /api/v1/cases/investigate first"
            )
        return report


@dataclass(frozen=True)
class GraphVizResult:
    nodes: list[dict]
    edges: list[dict]


class GraphVisualizationService:
    """Reuses the existing, frozen tool functions
    (`get_related_entities`/`get_graph_neighbors`) to build a
    visualization payload — this module contains no graph algorithm of
    its own, only a small reshape of tool output into nodes/edges."""

    def __init__(self, ctx: ToolDataContext, corpus: PolicyCorpus) -> None:
        self._ctx = ctx
        self._corpus = corpus

    def build(self, case: Case) -> GraphVizResult:
        if case.graph_evidence is None:
            return GraphVizResult(nodes=[], edges=[])

        registry = ToolRegistry(ctx=self._ctx, corpus=self._corpus)
        center = case.customer_proxy_id
        nodes: dict[str, dict] = {center: {"customer_proxy_id": center, "is_center": True}}
        edges: list[dict] = []

        for rel_type in case.graph_evidence.detected_relationship_types:
            result = registry.call(
                "get_graph_neighbors", {"customer_proxy_id": center, "relationship_type": rel_type}
            )
            for neighbor in result.get("neighbors", []):
                neighbor_id = neighbor["neighbor_customer_proxy_id"]
                nodes.setdefault(neighbor_id, {"customer_proxy_id": neighbor_id, "is_center": False})
                edges.append(
                    {
                        "source": center,
                        "target": neighbor_id,
                        "relationship_type": rel_type,
                        "shared_entity_value": neighbor["shared_entity_value"],
                    }
                )

        return GraphVizResult(nodes=list(nodes.values()), edges=edges)


# ---------------------------------------------------------------------------
# Investigation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InvestigationOutcome:
    report: dict
    llm_backend: str
    cache_hit: bool
    agent_duration_ms: int | None


class InvestigationService:
    """Orchestrates `build_agent_input` + `run_investigation`
    (`src/agents/graph.py`, frozen Phase 4 logic) behind the API
    boundary. Translates the ONE thing that can genuinely fail here —
    the LLM client/transport raising, or any other unexpected exception
    escaping the graph — into `AgentExecutionError`. The graph's own
    designed fail-safe path (`validation_status="failed_human_review"`)
    never raises and is returned as a normal result, unchanged, per
    Phase 5A.5's explicit "agent failure must preserve the existing
    fail-safe human-review behavior."
    """

    def __init__(self, ctx: ToolDataContext, corpus: PolicyCorpus, llm_client: LLMClient, cache: InvestigationCache) -> None:
        self._ctx = ctx
        self._corpus = corpus
        self._llm_client = llm_client
        self._cache = cache

    def validate_mode(self, investigation_mode: str, cutoff_dt: int | None, case: Case) -> None:
        if investigation_mode != "real_time":
            raise UnsupportedInvestigationModeError(
                f"investigation_mode={investigation_mode!r} is not supported by the frozen Phase 4 "
                "agent, which always uses the case's own trigger transaction timestamp as its "
                "real-time boundary — only 'real_time' is currently valid"
            )
        if cutoff_dt is not None and cutoff_dt != case.trigger_transaction_dt:
            raise UnsupportedInvestigationModeError(
                f"cutoff_dt={cutoff_dt} does not match this case's trigger transaction timestamp "
                f"({case.trigger_transaction_dt}) — the frozen agent does not support an "
                "independently chosen cutoff; omit cutoff_dt or pass the exact trigger timestamp"
            )

    def investigate(self, case: Case, investigation_mode: str = "real_time") -> InvestigationOutcome:
        cache_key = InvestigationCacheKey(
            case_id=case.case_id,
            investigation_mode=investigation_mode,
            llm_backend=self._llm_client.backend_name,
            model_version=MODEL_VERSION,
            graph_config_version=GRAPH_CONFIG_VERSION,
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            return InvestigationOutcome(
                report=cached, llm_backend=self._llm_client.backend_name, cache_hit=True, agent_duration_ms=None
            )

        registry = ToolRegistry(ctx=self._ctx, corpus=self._corpus)
        agent_input = build_agent_input(case)
        deps = InvestigationGraphDeps(registry=registry, llm_client=self._llm_client, corpus=self._corpus)

        t0 = time.monotonic()
        try:
            report = run_investigation(agent_input, deps)
        except Exception as exc:  # noqa: BLE001 — translate any escaped exception to a clean API error
            logger.info(
                "investigation_agent_execution_failed",
                extra={"case_id": case.case_id, "llm_backend": self._llm_client.backend_name, "error_type": type(exc).__name__},
            )
            if _looks_like_llm_unavailable(exc):
                raise LLMUnavailableError(
                    f"the '{self._llm_client.backend_name}' LLM backend is unavailable right now "
                    f"({type(exc).__name__}) — this is a transport/backend failure, not an "
                    "evidence-validation failure (the agent's own fail-safe path never raises)"
                ) from exc
            raise AgentExecutionError(
                f"investigation failed for case {case.case_id!r} (backend={self._llm_client.backend_name}): "
                f"{type(exc).__name__}"
            ) from exc
        agent_duration_ms = int((time.monotonic() - t0) * 1000)

        self._cache.set(cache_key, report)
        return InvestigationOutcome(
            report=report, llm_backend=self._llm_client.backend_name, cache_hit=False, agent_duration_ms=agent_duration_ms
        )


_LLM_UNAVAILABLE_SIGNALS = ("session limit", "rate limit", "resulterror", "connection", "timed out", "timeout", "unavailable")


def _looks_like_llm_unavailable(exc: Exception) -> bool:
    """Heuristic classification of a raised exception as an LLM
    transport/availability failure (e.g. the Claude Agent SDK session-limit
    error observed during Phase 4 closure) vs. some other unexpected
    failure. Best-effort, like `src/agents/safety.py`'s injection-pattern
    scanner — used only to pick a more specific HTTP status, never to
    hide the underlying error from the log."""
    text = f"{type(exc).__name__} {exc}".lower()
    return any(signal in text for signal in _LLM_UNAVAILABLE_SIGNALS)


def new_request_id() -> str:
    return uuid.uuid4().hex
