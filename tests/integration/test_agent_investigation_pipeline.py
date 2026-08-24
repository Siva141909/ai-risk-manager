"""Phase 4F/4S — end-to-end LangGraph investigation pipeline tests.

Uses StubLLMClient exclusively (STUB TEST) — fast, free, deterministic,
no network. These test PIPELINE correctness (state transitions, tool
routing, validation, fail-safe behavior), never LLM reasoning quality.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.agents.case_contract import build_agent_input
from src.agents.graph import InvestigationGraphDeps, run_investigation
from src.agents.llm_client import LLMClient, StubLLMClient
from src.agents.schemas import InvestigationReport
from src.graph.case_interface import build_case
from src.graph.explain import build_evidence_and_narrative
from src.graph.signals import compute_customer_graph_signals
from src.rag.retrieval import PolicyCorpus
from src.tools.context import ToolDataContext
from src.tools.registry import ToolRegistry


def _make_ring_like_graph_df() -> pd.DataFrame:
    """4 customers sharing a bank account (ring-like), 2 unrelated singles."""
    rows = []
    for i, cust in enumerate(["r1", "r2", "r3", "r4"]):
        rows.append(
            dict(
                TransactionID=100 + i, TransactionDT=1000 + i * 60, TransactionAmt=25.0,
                ProductCD="W", customer_proxy_id=cust, customer_proxy_confidence="small",
                device_synthetic_id=None, ip_synthetic_id=None, bank_account_synthetic_id="BANK-SHARED",
            )
        )
    for i, cust in enumerate(["s1", "s2"]):
        rows.append(
            dict(
                TransactionID=200 + i, TransactionDT=5000 + i * 60, TransactionAmt=15.0,
                ProductCD="C", customer_proxy_id=cust, customer_proxy_confidence="singleton",
                device_synthetic_id=None, ip_synthetic_id=None, bank_account_synthetic_id=None,
            )
        )
    return pd.DataFrame(rows)


def _make_context() -> ToolDataContext:
    graph_df = _make_ring_like_graph_df()
    ml_df = graph_df[["TransactionID", "TransactionDT", "TransactionAmt"]].copy()
    ml_df["cust_txn_count_so_far"] = 0
    ml_df["cust_txn_count_prior_24h"] = 0
    ml_df["cust_time_since_last_txn"] = None
    signals = compute_customer_graph_signals(graph_df)
    return ToolDataContext(transactions_graph=graph_df, transactions_ml=ml_df, graph_signals=signals, case_risk_signals={})


@pytest.fixture(scope="module")
def policy_corpus():
    from pathlib import Path

    return PolicyCorpus.from_directory(Path(__file__).resolve().parent.parent.parent / "docs" / "policy_documents")


def _build_case_for(customer_proxy_id, ctx, ml_score, ml_tier):
    row = ctx.transactions_graph[ctx.transactions_graph["customer_proxy_id"] == customer_proxy_id].iloc[0]
    signals_row = ctx.graph_signals[ctx.graph_signals["customer_proxy_id"] == customer_proxy_id]
    evidence = build_evidence_and_narrative(signals_row.iloc[0]) if len(signals_row) else None
    return build_case(row, ml_risk_score=ml_score, ml_risk_tier=ml_tier, graph_evidence=evidence)


def test_ring_like_case_produces_passing_report_with_stub(policy_corpus):
    ctx = _make_context()
    registry = ToolRegistry(ctx=ctx, corpus=policy_corpus)
    case = _build_case_for("r1", ctx, ml_score=0.02, ml_tier="LOW")
    agent_input = build_agent_input(case)
    deps = InvestigationGraphDeps(registry=registry, llm_client=StubLLMClient(), corpus=policy_corpus)

    report = run_investigation(agent_input, deps)
    InvestigationReport(**report)  # re-validates the schema itself
    assert report["case_id"] == case.case_id
    assert report["validation_status"] == "passed"
    assert len(report["evidence"]) > 0


def test_low_risk_no_graph_evidence_skips_graph_and_policy_nodes(policy_corpus):
    ctx = _make_context()
    registry = ToolRegistry(ctx=ctx, corpus=policy_corpus)
    case = _build_case_for("s1", ctx, ml_score=0.001, ml_tier="LOW")
    agent_input = build_agent_input(case)
    deps = InvestigationGraphDeps(registry=registry, llm_client=StubLLMClient(), corpus=policy_corpus)

    report = run_investigation(agent_input, deps)
    tool_names_called = {c.name for c in registry.call_log}
    assert "get_graph_context" not in tool_names_called
    assert "get_policy" not in tool_names_called
    assert report["recommendation"] == "close"


def test_risk_tier_in_final_report_matches_frozen_ml_tier_exactly(policy_corpus):
    """Deterministic final risk tier (Phase 4S): the agent must report
    EXACTLY the tier it was given, never a different one."""
    ctx = _make_context()
    for tier in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        registry = ToolRegistry(ctx=ctx, corpus=policy_corpus)
        case = _build_case_for("r2", ctx, ml_score=0.5, ml_tier=tier)
        agent_input = build_agent_input(case)
        deps = InvestigationGraphDeps(registry=registry, llm_client=StubLLMClient(), corpus=policy_corpus)
        report = run_investigation(agent_input, deps)
        assert report["risk_tier"] == tier


def test_malformed_llm_output_triggers_repair_then_fail_safe(policy_corpus):
    class AlwaysMalformedClient:
        backend_name = "broken_stub"

        def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
            return "this is not json at all {{{"

    ctx = _make_context()
    registry = ToolRegistry(ctx=ctx, corpus=policy_corpus)
    case = _build_case_for("r3", ctx, ml_score=0.5, ml_tier="MEDIUM")
    agent_input = build_agent_input(case)
    deps = InvestigationGraphDeps(registry=registry, llm_client=AlwaysMalformedClient(), corpus=policy_corpus)

    report = run_investigation(agent_input, deps)
    assert report["validation_status"] == "failed_human_review"
    assert report["requires_human_review"] is True
    assert report["recommendation"] == "escalate_to_human_analyst"
    assert report["evidence"] == []  # no fabricated evidence in the fail-safe report


def test_llm_inventing_evidence_id_triggers_repair_then_fail_safe(policy_corpus):
    class FabricatingClient:
        backend_name = "fabricating_stub"

        def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
            import json

            return json.dumps(
                {
                    "summary": "Fabricated investigation.",
                    "trigger": "ML risk tier MEDIUM",
                    "graph_findings": "x",
                    "behavioral_findings": "x",
                    "recommendation": "close",
                    "confidence": 0.9,
                    "evidence": [
                        {
                            "evidence_id": "CUST-FABRICATED0",
                            "source_tool": "get_customer_context",
                            "summary": "invented",
                            "is_retrospective": False,
                        }
                    ],
                }
            )

    ctx = _make_context()
    registry = ToolRegistry(ctx=ctx, corpus=policy_corpus)
    case = _build_case_for("r4", ctx, ml_score=0.5, ml_tier="MEDIUM")
    agent_input = build_agent_input(case)
    deps = InvestigationGraphDeps(registry=registry, llm_client=FabricatingClient(), corpus=policy_corpus)

    report = run_investigation(agent_input, deps)
    assert report["validation_status"] == "failed_human_review"


def test_tool_call_budget_never_exceeded_for_a_single_investigation(policy_corpus):
    ctx = _make_context()
    registry = ToolRegistry(ctx=ctx, corpus=policy_corpus, max_calls=100)
    case = _build_case_for("r1", ctx, ml_score=0.9, ml_tier="CRITICAL")
    agent_input = build_agent_input(case)
    deps = InvestigationGraphDeps(registry=registry, llm_client=StubLLMClient(), corpus=policy_corpus)

    run_investigation(agent_input, deps)
    # bounded: collect_core_evidence(5) + graph_context(2 + up to 3 relationship types) + policy(1) + repair attempts
    assert len(registry.call_log) < 20  # generous bound proving no infinite loop / call explosion


def test_repair_loop_is_bounded_not_infinite(policy_corpus):
    """A client that ALWAYS fabricates evidence must still terminate the
    graph within MAX_VALIDATION_ATTEMPTS + 1 report-generation calls, not
    loop forever."""
    call_count = {"n": 0}

    class AlwaysFabricatingClient:
        backend_name = "always_fabricating"

        def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
            call_count["n"] += 1
            import json

            return json.dumps({"summary": "x", "recommendation": "close", "confidence": 0.1, "evidence": [{"evidence_id": "CUST-NEVER-REAL", "source_tool": "get_customer_context", "summary": "x", "is_retrospective": False}]})

    ctx = _make_context()
    registry = ToolRegistry(ctx=ctx, corpus=policy_corpus)
    case = _build_case_for("r2", ctx, ml_score=0.5, ml_tier="MEDIUM")
    agent_input = build_agent_input(case)
    deps = InvestigationGraphDeps(registry=registry, llm_client=AlwaysFabricatingClient(), corpus=policy_corpus)

    report = run_investigation(agent_input, deps)
    assert report["validation_status"] == "failed_human_review"
    assert call_count["n"] <= 3  # bounded — proves no infinite loop
