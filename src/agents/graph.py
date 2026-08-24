"""Phase 4F — the investigation LangGraph.

Simplified from the design doc's Section 16 proposal per Phase 4F's own
instruction ("do not blindly implement every node if a simpler workflow
is more reliable"): "Investigate Transaction History" and "Investigate
Related Entities" are folded into bounded evidence-collection nodes
(a fixed set of tool calls, not a separate LLM routing decision) since
at this tool count, giving the LLM a routing choice between them adds
latency and non-determinism without adding investigative value — the
LLM's judgment is reserved for report SYNTHESIS (Phase 4B: "must
investigate further using tools," not "must decide which tool to call
first").

```
START
  -> validate_case
  -> collect_core_evidence           (customer context, transaction history, temporal activity, risk signals)
  -> investigate_graph_context        (graph context, related entities, graph neighbors — SKIPPED if no graph evidence exists: early stop, Phase 4F)
  -> retrieve_policy                   (SKIPPED if no shared-infrastructure pattern found: early stop)
  -> generate_investigation_report      (LLM call)
  -> validate_report                     (deterministic, Phase 4N)
       -(failed, attempts < max)-> generate_investigation_report  (repair, with error feedback)
       -(failed, attempts >= max)-> fail_safe_human_review
       -(passed)-> finalize
  -> END
```
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from langgraph.graph import END, START, StateGraph

from src.agents.case_contract import AgentInput
from src.agents.safety import (
    AGENT_SYSTEM_PROMPT_INJECTION_CLAUSE,
    detect_injection_pattern,
    validate_investigation_report,
    valid_evidence_ids_from_call_log,
    wrap_untrusted_data,
)
from src.agents.schemas import EvidenceItem, InvestigationReport
from src.agents.state import InvestigationState
from src.rag.retrieval import PolicyCorpus
from src.tools.registry import ToolRegistry

MAX_VALIDATION_ATTEMPTS = 1  # 1 repair retry, then fail-safe (design doc Section 16)

REPORT_SYSTEM_PROMPT = (
    "You are a fraud-risk investigation assistant. You investigate a flagged transaction case "
    "using the evidence you are given and produce a structured investigation report. "
    + AGENT_SYSTEM_PROMPT_INJECTION_CLAUSE
    + " You must cite only evidence_id values that appear in the evidence bundle you are given — "
    "never invent one. You never determine or change the ML risk score or risk tier; you only "
    "report them. You never authorize an irreversible action — every recommendation requiring real "
    "account or financial consequence must be marked as requiring human approval. Respond with a "
    "single JSON object matching the requested schema, nothing else."
)


def _tool_call(registry: ToolRegistry, name: str, args: dict) -> dict:
    output = registry.call(name, args)
    return {"tool": name, "args": args, "output": output}


def node_validate_case(state: InvestigationState) -> dict:
    agent_input = state["agent_input"]
    if not agent_input.get("case_id"):
        return {"error": "invalid case: missing case_id"}
    return {
        "case_id": agent_input["case_id"],
        "cutoff_dt": agent_input["trigger_transaction_dt"],
        "tool_outputs": [],
        "validation_attempts": 0,
        "validation_errors": [],
        "injection_signals_detected": [],
        "error": None,
    }


def make_node_collect_core_evidence(registry: ToolRegistry):
    def node(state: InvestigationState) -> dict:
        customer_id = state["agent_input"]["customer_proxy_id"]
        cutoff = state["cutoff_dt"]
        outputs = list(state.get("tool_outputs", []))
        outputs.append(_tool_call(registry, "get_customer_context", {"customer_proxy_id": customer_id}))
        outputs.append(
            _tool_call(
                registry, "get_transaction_history",
                {"customer_proxy_id": customer_id, "cutoff_dt": cutoff, "max_results": 20},
            )
        )
        outputs.append(_tool_call(registry, "get_temporal_activity", {"customer_proxy_id": customer_id, "cutoff_dt": cutoff}))
        outputs.append(_tool_call(registry, "get_risk_signals", {"case_id": state["case_id"]}))
        outputs.append(_tool_call(registry, "get_previous_cases", {"customer_proxy_id": customer_id, "cutoff_dt": cutoff}))
        return {"tool_outputs": outputs}

    return node


def make_node_investigate_graph_context(registry: ToolRegistry):
    def node(state: InvestigationState) -> dict:
        has_graph_evidence = state["agent_input"]["detection_evidence"]["graph_evidence"] is not None
        if not has_graph_evidence:
            return {}  # early stop — nothing to investigate structurally

        customer_id = state["agent_input"]["customer_proxy_id"]
        outputs = list(state.get("tool_outputs", []))
        outputs.append(_tool_call(registry, "get_graph_context", {"customer_proxy_id": customer_id}))
        outputs.append(_tool_call(registry, "get_related_entities", {"customer_proxy_id": customer_id}))

        detected_types = state["agent_input"]["detection_evidence"]["graph_evidence"].get(
            "detected_relationship_types", []
        )
        for rel_type in detected_types:
            outputs.append(
                _tool_call(registry, "get_graph_neighbors", {"customer_proxy_id": customer_id, "relationship_type": rel_type})
            )
        return {"tool_outputs": outputs}

    return node


def make_node_retrieve_policy(registry: ToolRegistry, corpus: PolicyCorpus):
    def node(state: InvestigationState) -> dict:
        graph_evidence = state["agent_input"]["detection_evidence"]["graph_evidence"]
        if graph_evidence is None:
            return {"policy_chunks": []}  # early stop — no shared-infra pattern to look up policy for

        detected_types = graph_evidence.get("detected_relationship_types", [])
        pattern = detected_types[0].replace("SHARED_", "").lower() if detected_types else None
        result = registry.call(
            "get_policy",
            {"query": "shared infrastructure escalation guidance", "applies_to_pattern": pattern, "max_results": 3},
        )
        outputs = list(state.get("tool_outputs", []))
        outputs.append({"tool": "get_policy", "args": {"applies_to_pattern": pattern}, "output": result})
        return {"tool_outputs": outputs, "policy_chunks": result.get("chunks", [])}

    return node


def _build_evidence_bundle(state: InvestigationState) -> dict:
    detection = state["agent_input"]["detection_evidence"]
    evidence_items = []
    for call in state.get("tool_outputs", []):
        output = call["output"]
        if "error" in output:
            continue
        for key, value in output.items():
            if key == "evidence_id":
                evidence_items.append({"evidence_id": value, "source_tool": call["tool"]})
    return {
        "case_id": state["case_id"],
        "ml_risk_score": detection["ml_risk_score"],
        "ml_risk_tier": detection["ml_risk_tier"],
        "graph_evidence": detection["graph_evidence"],
        "tool_results": state.get("tool_outputs", []),
        "policy_chunks": state.get("policy_chunks", []),
        "evidence_items": evidence_items,
    }


def make_node_generate_report(llm_client):
    def node(state: InvestigationState) -> dict:
        bundle = _build_evidence_bundle(state)

        # scan every text-shaped tool output value for injection patterns before
        # handing it to the model — Phase 4M: detected signals get logged, not acted on
        injection_signals = list(state.get("injection_signals_detected", []))
        for call in state.get("tool_outputs", []):
            for value in _flatten_strings(call["output"]):
                hits = detect_injection_pattern(value)
                if hits:
                    injection_signals.append(f"{call['tool']}: {hits}")

        wrapped_evidence = wrap_untrusted_data("evidence_bundle", json.dumps(bundle, default=str))
        repair_note = ""
        if state.get("validation_errors"):
            repair_note = (
                "\n\nYour previous attempt failed validation for these reasons — fix them:\n"
                + "\n".join(state["validation_errors"])
            )

        user_prompt = (
            f"Investigate case {state['case_id']}.\n\n"
            f"<<EVIDENCE_JSON>>{json.dumps(bundle, default=str)}<<END_EVIDENCE_JSON>>\n\n"
            f"{wrapped_evidence}\n\n"
            "Produce a JSON object with fields: summary, trigger, risk_tier, graph_findings, "
            "behavioral_findings, legitimate_explanations (list), conflicting_evidence (bool), "
            "conflict_description, policy_findings (list), recommendation "
            "(close|monitor|investigate_further|escalate_to_human_analyst), confidence (0-1), "
            "evidence (list of {evidence_id, source_tool, summary, is_retrospective})."
            + repair_note
        )

        raw = llm_client.generate(REPORT_SYSTEM_PROMPT, user_prompt)
        draft = _parse_llm_json(raw)
        return {"draft_report": draft, "injection_signals_detected": injection_signals, "llm_backend": llm_client.backend_name}

    return node


def _flatten_strings(obj) -> list[str]:
    out = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(_flatten_strings(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(_flatten_strings(v))
    return out


def _parse_llm_json(raw: str) -> dict | None:
    """Returns None on genuine parse failure — the caller must treat that
    as an explicit validation failure, never silently proceed with an
    empty-but-technically-valid report built from all-default fields."""
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return None


def node_validate_report(state: InvestigationState) -> dict:
    draft = state.get("draft_report")
    detection = state["agent_input"]["detection_evidence"]

    if draft is None:
        return {
            "validation_errors": ["LLM output could not be parsed as JSON — treated as a validation failure, not silently accepted"],
            "validation_attempts": state.get("validation_attempts", 0) + 1,
        }

    try:
        report = InvestigationReport(
            case_id=state["case_id"],
            summary=draft.get("summary", ""),
            trigger=draft.get("trigger", f"ML risk tier {detection['ml_risk_tier']}"),
            risk_tier=detection["ml_risk_tier"],
            graph_findings=draft.get("graph_findings", ""),
            behavioral_findings=draft.get("behavioral_findings", ""),
            legitimate_explanations=draft.get("legitimate_explanations", []) or [],
            conflicting_evidence=bool(draft.get("conflicting_evidence", False)),
            conflict_description=draft.get("conflict_description"),
            policy_findings=draft.get("policy_findings", []) or [],
            recommendation=draft.get("recommendation", "investigate_further"),
            requires_human_review=(
                detection["ml_risk_tier"] in ("HIGH", "CRITICAL")
                or bool(draft.get("conflicting_evidence", False))
                or draft.get("recommendation") == "escalate_to_human_analyst"
            ),
            confidence=float(draft.get("confidence", 0.0)),
            evidence=[EvidenceItem(**e) for e in draft.get("evidence", [])],
            retrospective_evidence_used=False,
            investigation_complete=True,
        )
    except Exception as e:  # noqa: BLE001 — malformed LLM output must fail validation, not crash the graph
        return {"validation_errors": [f"schema parse failure: {e}"], "validation_attempts": state.get("validation_attempts", 0) + 1}

    valid_ids = valid_evidence_ids_from_call_log([], [c["output"] for c in state.get("tool_outputs", [])])
    result = validate_investigation_report(report, valid_ids, state["case_id"])

    attempts = state.get("validation_attempts", 0) + 1
    if result.passed:
        report_dict = report.model_dump()
        report_dict["validation_status"] = "passed"
        return {"final_report": report_dict, "validation_errors": [], "validation_attempts": attempts}
    return {"validation_errors": result.errors, "validation_attempts": attempts}


def node_fail_safe_human_review(state: InvestigationState) -> dict:
    detection = state["agent_input"]["detection_evidence"]
    report = InvestigationReport(
        case_id=state["case_id"],
        summary="Investigation could not be validated after the maximum repair attempts — routed to human review.",
        trigger=f"ML risk tier {detection['ml_risk_tier']}",
        risk_tier=detection["ml_risk_tier"],
        graph_findings=(detection["graph_evidence"] or {}).get("narrative", "No graph evidence.") if detection["graph_evidence"] else "No graph evidence.",
        behavioral_findings="Not synthesized — validation failed.",
        legitimate_explanations=[],
        conflicting_evidence=False,
        conflict_description=None,
        policy_findings=[],
        recommendation="escalate_to_human_analyst",
        requires_human_review=True,
        confidence=0.0,
        evidence=[],
        retrospective_evidence_used=False,
        investigation_complete=False,
        validation_status="failed_human_review",
    )
    return {"final_report": report.model_dump()}


def node_finalize(state: InvestigationState) -> dict:
    report = dict(state["final_report"])
    # Derived from the report's OWN cited evidence (each item's is_retrospective flag,
    # set when the underlying tool call had no real_time cutoff — src/agents/schemas.py),
    # not re-guessed from raw tool output shapes.
    report["retrospective_evidence_used"] = any(e.get("is_retrospective") for e in report.get("evidence", []))
    report["investigation_complete"] = state.get("error") is None and report.get("validation_status") == "passed"
    return {"final_report": report}


def _route_after_validation(state: InvestigationState) -> str:
    if state.get("final_report") and not state.get("validation_errors"):
        return "finalize"
    if state.get("validation_attempts", 0) > MAX_VALIDATION_ATTEMPTS:
        return "fail_safe"
    return "repair"


@dataclass
class InvestigationGraphDeps:
    registry: ToolRegistry
    llm_client: object
    corpus: PolicyCorpus


def build_investigation_graph(deps: InvestigationGraphDeps):
    workflow = StateGraph(InvestigationState)

    workflow.add_node("validate_case", node_validate_case)
    workflow.add_node("collect_core_evidence", make_node_collect_core_evidence(deps.registry))
    workflow.add_node("investigate_graph_context", make_node_investigate_graph_context(deps.registry))
    workflow.add_node("retrieve_policy", make_node_retrieve_policy(deps.registry, deps.corpus))
    workflow.add_node("generate_investigation_report", make_node_generate_report(deps.llm_client))
    workflow.add_node("validate_report", node_validate_report)
    workflow.add_node("fail_safe_human_review", node_fail_safe_human_review)
    workflow.add_node("finalize", node_finalize)

    workflow.add_edge(START, "validate_case")
    workflow.add_edge("validate_case", "collect_core_evidence")
    workflow.add_edge("collect_core_evidence", "investigate_graph_context")
    workflow.add_edge("investigate_graph_context", "retrieve_policy")
    workflow.add_edge("retrieve_policy", "generate_investigation_report")
    workflow.add_edge("generate_investigation_report", "validate_report")
    workflow.add_conditional_edges(
        "validate_report",
        _route_after_validation,
        {"finalize": "finalize", "repair": "generate_investigation_report", "fail_safe": "fail_safe_human_review"},
    )
    workflow.add_edge("fail_safe_human_review", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()


def run_investigation(agent_input: AgentInput, deps: InvestigationGraphDeps) -> dict:
    import dataclasses

    graph = build_investigation_graph(deps)
    initial_state: InvestigationState = {"agent_input": dataclasses.asdict(agent_input)}
    final_state = graph.invoke(initial_state)
    return final_state["final_report"]
