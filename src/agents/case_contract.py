"""Phase 4A — the agent's input contract.

`Case` (src/graph/case_interface.py) is the ONLY object the investigation
agent ever receives. `AgentInput` below is built from a `Case` alone —
its constructor has no parameter through which a `CaseGroundTruth` could
even be passed, which is what makes "the agent must never receive
CaseGroundTruth" a structural guarantee, not a convention
(tested, tests/unit/test_agent_case_contract.py).

**Detection evidence vs. investigation evidence:**
- DETECTION EVIDENCE is what got the case created in the first place —
  `Case.ml_risk_score`, `Case.ml_risk_tier`, `Case.graph_evidence` (the
  Phase 3 deterministic signals). It is fixed before the agent runs and
  the agent cannot change it.
- INVESTIGATION EVIDENCE is what the agent's tool calls retrieve DURING
  the investigation (transaction history, related entities, policy
  chunks) — it did not exist as "evidence" until the agent asked for it,
  even though the underlying data existed all along.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.graph.case_interface import Case, GraphEvidence


@dataclass(frozen=True)
class DetectionEvidence:
    """What got this case created — fixed, agent cannot change it."""

    ml_risk_score: float
    ml_risk_tier: str
    graph_evidence: GraphEvidence | None


@dataclass(frozen=True)
class AgentInput:
    """The complete, and ONLY, input to the investigation agent."""

    case_id: str
    trigger_transaction_ids: list[int]
    trigger_transaction_dt: int
    customer_proxy_id: str
    customer_proxy_confidence: str
    graph_lookup_keys: dict[str, str | None]
    detection_evidence: DetectionEvidence


def build_agent_input(case: Case) -> AgentInput:
    """The only function that constructs AgentInput — takes a Case and
    NOTHING else, so there is no call site anywhere that could pass
    ground-truth data through even by mistake."""
    return AgentInput(
        case_id=case.case_id,
        trigger_transaction_ids=list(case.trigger_transaction_ids),
        trigger_transaction_dt=case.trigger_transaction_dt,
        customer_proxy_id=case.customer_proxy_id,
        customer_proxy_confidence=case.customer_proxy_confidence,
        graph_lookup_keys=dict(case.graph_lookup_keys),
        detection_evidence=DetectionEvidence(
            ml_risk_score=case.ml_risk_score,
            ml_risk_tier=case.ml_risk_tier,
            graph_evidence=case.graph_evidence,
        ),
    )
