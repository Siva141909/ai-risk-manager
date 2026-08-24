"""Phase 5A.1 — explicit API request/response contracts.

Every request schema uses `extra="forbid"` (Phase 5A.8): a client
cannot smuggle an unrecognized field — such as an attempted
`risk_tier`/`ml_risk_score` override — into a request body; FastAPI
rejects it with 422 before any handler code runs. No response schema
here has a field for `CaseGroundTruth`, synthetic ring/cluster labels,
internal prompts, or credentials — this module never imports
`src.graph.case_interface.CaseGroundTruth` at all.

`InvestigationReportSchema` is a re-export of the frozen Phase 4 schema
(`src.agents.schemas.InvestigationReport`) — reused, not redefined, so
the API can never silently drift from the schema the deterministic
validator (`src/agents/safety.py`) actually enforces.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.agents.schemas import InvestigationReport as InvestigationReportSchema

__all__ = ["InvestigationReportSchema"]

RiskTier = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
InvestigationMode = Literal["real_time"]


# ---------------------------------------------------------------------------
# Shared / common
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error_code: str = Field(description="Stable machine-readable error identifier.")
    message: str = Field(description="Human-readable, client-safe error message — never a stack trace.")
    request_id: str


# ---------------------------------------------------------------------------
# Health (Phase 5A.4)
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["ok"]
    app_version: str
    model_version: str
    graph_config_version: str
    environment: str
    llm_backend: str


# ---------------------------------------------------------------------------
# Case listing / detail (Phase 5A.2/5A.3)
# ---------------------------------------------------------------------------


class CaseSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    transaction_id: int
    transaction_dt: int
    ml_risk_score: float
    ml_risk_tier: RiskTier
    graph_flagged: bool
    has_investigation: bool = Field(description="True if an investigation report has already been produced and cached for this case.")


class CaseListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[CaseSummaryResponse]
    total: int
    limit: int
    offset: int


class GraphEvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    community_id: int
    community_size: int
    n_shared_devices: int
    n_shared_ips: int
    n_shared_bank_accounts: int
    multi_attribute_overlap: bool
    relationship_rarity_score: float
    temporal_concentration_hours: float | None
    detected_relationship_types: list[str]
    narrative: str


class CaseDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    trigger_transaction_ids: list[int]
    trigger_transaction_dt: int
    ml_risk_score: float
    ml_risk_tier: RiskTier
    customer_proxy_id: str
    customer_proxy_confidence: str
    graph_lookup_keys: dict[str, str | None]
    graph_evidence: GraphEvidenceResponse | None
    has_investigation: bool


# ---------------------------------------------------------------------------
# Graph visualization (Phase 5A.3)
# ---------------------------------------------------------------------------


class GraphVizNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_proxy_id: str
    is_center: bool


class GraphVizEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str
    target: str
    relationship_type: str
    shared_entity_value: str


class CaseGraphResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    graph_evidence: GraphEvidenceResponse | None
    nodes: list[GraphVizNode]
    edges: list[GraphVizEdge]


# ---------------------------------------------------------------------------
# Investigation (Phase 5A.1/5A.6)
# ---------------------------------------------------------------------------


class InvestigateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction_id: int | None = Field(default=None, ge=0)
    case_id: str | None = Field(default=None, max_length=64)
    investigation_mode: InvestigationMode = "real_time"
    cutoff_dt: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Optional. The frozen Phase 4 agent always uses the case's own "
            "trigger transaction timestamp as its real-time boundary "
            "(docs/CASE_MODEL.md §5/§7) — if provided, this must equal that "
            "value exactly, or the request is rejected. See "
            "docs/BACKEND_ARCHITECTURE.md's investigation_mode design note."
        ),
    )

    @model_validator(mode="after")
    def _exactly_one_identifier(self) -> "InvestigateRequest":
        if (self.transaction_id is None) == (self.case_id is None):
            raise ValueError("exactly one of transaction_id or case_id must be provided")
        return self


class TransactionInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transaction_id: int
    transaction_dt: int


class ProcessingMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str
    llm_backend: str
    cache_hit: bool
    investigation_mode: InvestigationMode
    total_duration_ms: int
    case_lookup_duration_ms: int
    agent_duration_ms: int | None


class InvestigationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    transaction: TransactionInfo
    ml_risk_score: float
    ml_risk_tier: RiskTier
    graph_summary: GraphEvidenceResponse | None
    investigation_report: InvestigationReportSchema
    evidence: list[dict] = Field(description="Convenience top-level copy of investigation_report.evidence.")
    recommendation: str
    confidence: float
    human_approval_required: bool
    processing: ProcessingMetadata
