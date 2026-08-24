"""Phase 4I — the agent's structured output schema.

Every field has one clear purpose (documented inline). `evidence` is the
canonical citation list — every factual claim elsewhere in the report
must be traceable to at least one entry here (enforced by
src/agents/safety.py's validation node, Phase 4N), and every entry's
`evidence_id` must have come from an actual tool call
(src/tools/registry.py's call log) — the agent cannot invent one.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RecommendationType = Literal["close", "monitor", "investigate_further", "escalate_to_human_analyst"]


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_id: str = Field(description="Must exactly match an evidence_id returned by a tool call — never invented.")
    source_tool: str
    summary: str = Field(description="One-line human-readable summary of what this evidence shows.")
    is_retrospective: bool = Field(
        description="True if this evidence came from a tool call with no real_time cutoff "
        "(i.e., may include information from after the trigger transaction)."
    )


class InvestigationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    summary: str = Field(description="2-4 sentence synthesis of the investigation.")

    trigger: str = Field(description="What triggered this case — the ML risk tier and score, plainly stated.")
    risk_tier: str = Field(description="The DETERMINISTIC risk tier from src/models/thresholds.py — the agent reports it, never sets or changes it.")

    graph_findings: str = Field(description="What the deterministic graph evidence shows (Phase 3G/3K).")
    behavioral_findings: str = Field(description="What tool-retrieved transaction/temporal history shows — NOT a repeat of graph_findings.")
    legitimate_explanations: list[str] = Field(default_factory=list, description="Plausible non-fraud explanations, if any, grounded in retrieved evidence/policy.")
    conflicting_evidence: bool = Field(description="True if structural and behavioral evidence point in different directions.")
    conflict_description: str | None = Field(default=None, description="Required if conflicting_evidence is True — states the conflict plainly, not resolved by force.")

    policy_findings: list[str] = Field(default_factory=list, description="Policy citations in [POLICY:doc#section] form, from get_policy calls only.")

    recommendation: RecommendationType
    requires_human_review: bool = Field(description="True whenever recommendation is escalate_to_human_analyst, OR conflicting_evidence is True, OR risk_tier is HIGH/CRITICAL.")
    human_approval_required_for_action: bool = Field(
        default=True,
        description="Always True — the agent never authorizes an irreversible action itself (Phase 4J non-negotiable boundary).",
    )

    confidence: float = Field(ge=0.0, le=1.0, description="Investigation completeness/consistency confidence — NOT the ML risk score, and never overrides it.")

    evidence: list[EvidenceItem] = Field(default_factory=list)
    retrospective_evidence_used: bool = Field(description="True if any evidence item has is_retrospective=True.")
    investigation_complete: bool = Field(description="False if the tool-call budget was exhausted or a required tool failed before enough evidence was gathered.")

    validation_status: Literal["passed", "failed_repaired", "failed_human_review"] = Field(
        default="passed", description="Set by the deterministic validation node (Phase 4N), never by the LLM."
    )
