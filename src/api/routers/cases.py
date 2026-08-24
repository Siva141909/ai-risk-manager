"""Phase 5A.1/5A.2/5A.3 — case listing, detail, graph, and investigation
endpoints.

Route handlers here do exactly three things: validate/convert the
request, call one application service (`src/api/services.py`), and
shape the service's return value into a response schema. No ML, graph,
LangGraph, RAG, or tool logic is implemented in this file — every
handler is a thin translation layer, per the Phase 5A architecture
requirement.
"""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Depends, Query, Request
from starlette.concurrency import run_in_threadpool

from src.api.dependencies import get_case_service, get_graph_service, get_investigation_service, get_settings
from src.api.errors import ApiError, InvestigationTimeoutError
from src.api.schemas import (
    CaseDetailResponse,
    CaseGraphResponse,
    CaseListResponse,
    CaseSummaryResponse,
    GraphEvidenceResponse,
    GraphVizEdge,
    GraphVizNode,
    InvestigateRequest,
    InvestigationResponse,
    ProcessingMetadata,
    TransactionInfo,
)
from src.api.services import CaseService, GraphVisualizationService, InvestigationService, new_request_id
from src.graph.case_interface import Case
from src.logging_conf import get_logger

logger = get_logger("api.cases")

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


def _graph_evidence_response(case: Case) -> GraphEvidenceResponse | None:
    if case.graph_evidence is None:
        return None
    e = case.graph_evidence
    return GraphEvidenceResponse(
        community_id=e.community_id,
        community_size=e.community_size,
        n_shared_devices=e.n_shared_devices,
        n_shared_ips=e.n_shared_ips,
        n_shared_bank_accounts=e.n_shared_bank_accounts,
        multi_attribute_overlap=e.multi_attribute_overlap,
        relationship_rarity_score=e.relationship_rarity_score,
        temporal_concentration_hours=e.temporal_concentration_hours,
        detected_relationship_types=list(e.detected_relationship_types),
        narrative=e.narrative,
    )


@router.get(
    "",
    response_model=CaseListResponse,
    summary="List cases",
    description=(
        "Lists cases from the deterministic development repository (validation/test-split "
        "transactions with a frozen ML score, Phase 3 graph signals). Filterable by risk tier, "
        "graph flag, investigation status, and TransactionDT range — this synthetic dataset has no "
        "real wall-clock dates, so the range filters operate on TransactionDT (relative seconds), "
        "not calendar dates; see docs/API.md."
    ),
    responses={422: {"description": "invalid filter/pagination parameter (e.g. an unrecognized risk_tier value)"}},
)
def list_cases(
    risk_tier: str | None = Query(default=None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$"),
    graph_flagged: bool | None = Query(default=None),
    investigation_status: str | None = Query(default=None, pattern="^(investigated|not_investigated)$"),
    start_dt: int | None = Query(default=None, ge=0, description="Inclusive TransactionDT lower bound."),
    end_dt: int | None = Query(default=None, ge=0, description="Inclusive TransactionDT upper bound."),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: CaseService = Depends(get_case_service),
) -> CaseListResponse:
    summaries, total, has_investigation = service.list_cases(
        risk_tier=risk_tier, graph_flagged=graph_flagged, investigation_status=investigation_status,
        start_dt=start_dt, end_dt=end_dt, limit=limit, offset=offset,
    )
    items = [
        CaseSummaryResponse(
            case_id=s.case_id, transaction_id=s.transaction_id, transaction_dt=s.transaction_dt,
            ml_risk_score=s.ml_risk_score, ml_risk_tier=s.ml_risk_tier, graph_flagged=s.graph_flagged,
            has_investigation=hi,
        )
        for s, hi in zip(summaries, has_investigation)
    ]
    return CaseListResponse(items=items, total=total, limit=limit, offset=offset)


def _has_investigation(service: CaseService, case_id: str) -> bool:
    try:
        service.get_investigation_report(case_id)
        return True
    except ApiError:
        return False


@router.get(
    "/{case_id}",
    response_model=CaseDetailResponse,
    summary="Get case details",
    description="Returns the deterministic Case for a case_id — ML risk score/tier, graph evidence, no ground truth.",
    responses={404: {"description": "case not found"}, 400: {"description": "malformed case_id"}},
)
def get_case(case_id: str, service: CaseService = Depends(get_case_service)) -> CaseDetailResponse:
    case = service.get_case(case_id)
    return CaseDetailResponse(
        case_id=case.case_id,
        trigger_transaction_ids=list(case.trigger_transaction_ids),
        trigger_transaction_dt=case.trigger_transaction_dt,
        ml_risk_score=case.ml_risk_score,
        ml_risk_tier=case.ml_risk_tier,
        customer_proxy_id=case.customer_proxy_id,
        customer_proxy_confidence=case.customer_proxy_confidence,
        graph_lookup_keys=dict(case.graph_lookup_keys),
        graph_evidence=_graph_evidence_response(case),
        has_investigation=_has_investigation(service, case.case_id),
    )


@router.get(
    "/{case_id}/graph",
    response_model=CaseGraphResponse,
    summary="Get graph evidence for visualization",
    description="Returns the case's deterministic graph evidence plus a nodes/edges payload suitable for a graph-visualization frontend.",
    responses={404: {"description": "case not found"}},
)
def get_case_graph(
    case_id: str,
    case_service: CaseService = Depends(get_case_service),
    graph_service: GraphVisualizationService = Depends(get_graph_service),
) -> CaseGraphResponse:
    case = case_service.get_case(case_id)
    viz = graph_service.build(case)
    return CaseGraphResponse(
        case_id=case.case_id,
        graph_evidence=_graph_evidence_response(case),
        nodes=[GraphVizNode(**n) for n in viz.nodes],
        edges=[GraphVizEdge(**e) for e in viz.edges],
    )


@router.get(
    "/{case_id}/investigation",
    response_model=dict,
    summary="Get an existing investigation report",
    description=(
        "Returns the InvestigationReport already produced for this case, if any. Does NOT trigger "
        "a new investigation — use POST /api/v1/cases/investigate for that. 404 if none exists yet."
    ),
    responses={404: {"description": "no investigation has been run for this case yet"}},
)
def get_case_investigation(case_id: str, service: CaseService = Depends(get_case_service)) -> dict:
    return service.get_investigation_report(case_id)


@router.post(
    "/investigate",
    response_model=InvestigationResponse,
    summary="Run (or return a cached) agent investigation for a case",
    description=(
        "Runs the frozen Phase 4 LangGraph investigation agent for a transaction_id or case_id. "
        "This can take 20-60s against a real Claude backend (synchronous by design for this phase, "
        "see docs/BACKEND_ARCHITECTURE.md §6) — results are cached at the application layer so an "
        "identical request is never re-run against a live LLM unnecessarily. The client can only "
        "REQUEST an investigation; it cannot set the ML risk score/tier or graph evidence — those "
        "always come from the frozen, server-side dataset."
    ),
    responses={
        404: {"description": "case not found"},
        400: {"description": "malformed request or unsupported investigation_mode/cutoff_dt"},
        503: {"description": "LLM backend unavailable"},
        504: {"description": "investigation timed out"},
    },
)
async def investigate(
    request: Request,
    body: InvestigateRequest,
    case_service: CaseService = Depends(get_case_service),
    investigation_service: InvestigationService = Depends(get_investigation_service),
    settings=Depends(get_settings),
) -> InvestigationResponse:
    request_id = getattr(request.state, "request_id", new_request_id())
    t0 = time.monotonic()

    case_id = case_service.resolve_case_id(body.transaction_id, body.case_id)
    t_lookup0 = time.monotonic()
    case = case_service.get_case(case_id)
    investigation_service.validate_mode(body.investigation_mode, body.cutoff_dt, case)
    case_lookup_ms = int((time.monotonic() - t_lookup0) * 1000)

    try:
        outcome = await asyncio.wait_for(
            run_in_threadpool(investigation_service.investigate, case, body.investigation_mode),
            timeout=settings.investigation_timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise InvestigationTimeoutError(
            f"investigation for case {case_id!r} did not complete within "
            f"{settings.investigation_timeout_seconds}s"
        ) from exc

    report = outcome.report
    total_ms = int((time.monotonic() - t0) * 1000)

    logger.info(
        "investigation_completed",
        extra={
            "request_id": request_id, "case_id": case_id, "llm_backend": outcome.llm_backend,
            "cache_hit": outcome.cache_hit, "agent_duration_ms": outcome.agent_duration_ms,
            "total_duration_ms": total_ms, "validation_status": report.get("validation_status"),
        },
    )

    return InvestigationResponse(
        case_id=case.case_id,
        transaction=TransactionInfo(transaction_id=case.trigger_transaction_ids[0], transaction_dt=case.trigger_transaction_dt),
        ml_risk_score=case.ml_risk_score,
        ml_risk_tier=case.ml_risk_tier,
        graph_summary=_graph_evidence_response(case),
        investigation_report=report,
        evidence=report.get("evidence", []),
        recommendation=report.get("recommendation", ""),
        confidence=report.get("confidence", 0.0),
        human_approval_required=report.get("human_approval_required_for_action", True),
        processing=ProcessingMetadata(
            request_id=request_id, llm_backend=outcome.llm_backend, cache_hit=outcome.cache_hit,
            investigation_mode=body.investigation_mode, total_duration_ms=total_ms,
            case_lookup_duration_ms=case_lookup_ms, agent_duration_ms=outcome.agent_duration_ms,
        ),
    )
