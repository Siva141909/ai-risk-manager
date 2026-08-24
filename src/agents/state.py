"""Phase 4F — LangGraph investigation state.

Deliberately close to the design doc's Section 15/16 proposal, simplified
where a separate node would add process without adding reliability
(Phase 4F: "do not blindly implement every node if a simpler workflow is
more reliable") — "Investigate Transaction History" and "Investigate
Related Entities" are folded into evidence-collection nodes that each
make a bounded, fixed set of tool calls rather than being separate
LLM-driven decision points, since at this tool count an LLM routing
decision between them adds latency and non-determinism without adding
investigative value.
"""

from __future__ import annotations

from typing import Any, TypedDict


class InvestigationState(TypedDict, total=False):
    case_id: str
    agent_input: dict  # src/agents/case_contract.py::AgentInput, serialized
    cutoff_dt: int

    tool_outputs: list[dict]  # every raw tool output dict, in call order
    evidence_bundle: dict  # assembled for the report-generation prompt

    policy_chunks: list[dict]

    draft_report: dict | None  # raw JSON from the LLM, pre-validation
    validation_errors: list[str]
    validation_attempts: int

    final_report: dict | None
    llm_backend: str

    error: str | None
    injection_signals_detected: list[str]
