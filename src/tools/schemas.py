"""Phase 4C/4D — strict input/output schemas for every agent tool.

Every tool has exactly one input schema and one output schema here.
The LLM can only construct a tool call that validates against the input
schema (src/tools/registry.py enforces this before dispatch) — it cannot
pass arbitrary arguments or call anything not represented here.

No schema in this file has a field that could hold a ground-truth
column (original_isFraud, synthetic_ring_id, synthetic_abuse_type,
synthetic_ring_role, legitimate_cluster_id, legitimate_cluster_type,
synthetic_entity_label) — checked directly,
tests/unit/test_tool_schemas_and_authorization.py.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# get_transaction_history
# ---------------------------------------------------------------------------


class TransactionHistoryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_proxy_id: str
    cutoff_dt: int | None = Field(
        default=None,
        description="If set, only transactions with TransactionDT strictly before this value are returned "
        "(real-time mode, Phase 4E). If None, all known transactions are returned (retrospective mode).",
    )
    max_results: int = Field(default=20, ge=1, le=100)


class TransactionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    transaction_id: int
    transaction_dt: int
    amount: float
    product_cd: str


class TransactionHistoryOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_proxy_id: str
    mode: str  # "real_time" | "retrospective"
    transactions: list[TransactionRecord]
    n_total_known: int


# ---------------------------------------------------------------------------
# get_customer_context
# ---------------------------------------------------------------------------


class CustomerContextInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_proxy_id: str


class CustomerContextOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    customer_proxy_id: str
    customer_proxy_confidence: str
    total_known_transactions: int
    found: bool


# ---------------------------------------------------------------------------
# get_related_entities
# ---------------------------------------------------------------------------


class RelatedEntitiesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_proxy_id: str


class RelatedEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    entity_type: str  # "device" | "ip" | "bank_account"
    entity_value: str
    n_customers_sharing: int


class RelatedEntitiesOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_proxy_id: str
    entities: list[RelatedEntity]


# ---------------------------------------------------------------------------
# get_graph_context — deterministic graph evidence already computed (Phase 3)
# ---------------------------------------------------------------------------


class GraphContextInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_proxy_id: str


class GraphContextOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    found: bool
    community_id: int | None = None
    community_size: int | None = None
    n_shared_devices: int | None = None
    n_shared_ips: int | None = None
    n_shared_bank_accounts: int | None = None
    multi_attribute_overlap: bool | None = None
    relationship_rarity_score: float | None = None
    temporal_concentration_hours: float | None = None
    graph_flagged: bool | None = None
    narrative: str | None = None


# ---------------------------------------------------------------------------
# get_graph_neighbors
# ---------------------------------------------------------------------------


class GraphNeighborsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_proxy_id: str
    relationship_type: str = Field(description="One of SHARED_DEVICE, SHARED_IP, SHARED_BANK_ACCOUNT")
    max_results: int = Field(default=20, ge=1, le=100)


class GraphNeighbor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    neighbor_customer_proxy_id: str
    relationship_type: str
    shared_entity_value: str
    n_customers_sharing_this_entity: int
    neighbor_transaction_id: int
    neighbor_transaction_dt: int


class GraphNeighborsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_proxy_id: str
    relationship_type: str
    neighbors: list[GraphNeighbor]


# ---------------------------------------------------------------------------
# get_temporal_activity
# ---------------------------------------------------------------------------


class TemporalActivityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_proxy_id: str
    cutoff_dt: int | None = None


class TemporalActivityOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    customer_proxy_id: str
    mode: str
    txn_count_so_far: int | None
    txn_count_prior_24h: float | None
    time_since_last_txn_seconds: float | None
    found: bool


# ---------------------------------------------------------------------------
# get_merchant_context
# ---------------------------------------------------------------------------


class MerchantContextInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_cd: str


class MerchantContextOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    product_cd: str
    n_transactions_observed: int
    note: str


# ---------------------------------------------------------------------------
# get_previous_cases
# ---------------------------------------------------------------------------


class PreviousCasesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_proxy_id: str
    cutoff_dt: int | None = None


class PreviousCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    case_id: str
    transaction_id: int
    transaction_dt: int
    risk_tier_at_time: str


class PreviousCasesOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    customer_proxy_id: str
    mode: str
    previous_cases: list[PreviousCase]
    note: str


# ---------------------------------------------------------------------------
# get_risk_signals
# ---------------------------------------------------------------------------


class RiskSignalsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str


class RiskSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    signal_type: str
    value: str


class RiskSignalsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    signals: list[RiskSignal]


# ---------------------------------------------------------------------------
# get_policy (RAG)
# ---------------------------------------------------------------------------


class PolicyQueryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=500)
    applies_to_pattern: str | None = Field(
        default=None, description="Optional filter, e.g. 'shared_device', 'shared_bank_account'"
    )
    max_results: int = Field(default=3, ge=1, le=10)


class PolicyChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str
    citation: str  # "[POLICY:{doc_id}#{section_id}]"
    doc_id: str
    section_id: str
    text: str
    similarity_score: float


class PolicyQueryOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str
    chunks: list[PolicyChunk]
