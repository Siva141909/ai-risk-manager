"""Phase 4P/4Q/4U — agent evaluation, non-agent baseline comparison, demo cases.

Runs a fixed, curated set of 12 real cases (not model-selected) through
three configurations:
  A. Deterministic graph evidence only (no report synthesis)
  B. Graph evidence + template narrative (src/graph/explain.py, no LLM)
  C. Graph evidence + investigation agent (LangGraph + real Claude, via
     the Claude Agent SDK development backend — CLAUDE DEVELOPMENT RUN)

Per the explicit evaluation rule for this phase: pipeline/safety/tool/
evidence-validation correctness is proven separately by the automated
pytest suite (STUB TEST, deterministic, already passing). This script
produces the ONE thing only real Claude reasoning can be evaluated on —
qualitative investigation quality — and must not be conflated with
pipeline correctness.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from src.agents.case_contract import build_agent_input
from src.agents.graph import InvestigationGraphDeps, run_investigation
from src.agents.llm_client import ClaudeAgentSDKClient, StubLLMClient
from src.graph.case_interface import build_case
from src.graph.explain import build_evidence_and_narrative
from src.graph.signals import compute_customer_graph_signals
from src.rag.retrieval import PolicyCorpus
from src.tools.context import load_tool_data_context
from src.tools.registry import ToolRegistry

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data" / "processed" / "agent_evaluation"

# Fixed, curated evaluation set (Phase 4P: "not cases selected by the model") —
# real TransactionIDs identified directly from data/synthetic/full/ ground truth.
EVAL_CASES = [
    {"category": "1_strong_abuse_ring", "transaction_id": 3181534, "ml_score": 0.05, "ml_tier": "MEDIUM"},
    {"category": "2_weak_ring_noise_member", "transaction_id": 3524538, "ml_score": 0.02, "ml_tier": "LOW"},
    {"category": "3_legitimate_household", "transaction_id": 3224084, "ml_score": 0.01, "ml_tier": "LOW"},
    {"category": "4_legitimate_office", "transaction_id": 3140858, "ml_score": 0.02, "ml_tier": "LOW"},
    {"category": "5_legitimate_campus", "transaction_id": 3476296, "ml_score": 0.01, "ml_tier": "LOW"},
    {"category": "6_legitimate_business", "transaction_id": 3199839, "ml_score": 0.03, "ml_tier": "LOW"},
    # category 7 (ML-high AND graph-high) has ZERO real examples in this benchmark --
    # confirmed identical to Phase 3's quadrant-D-empty finding (docs/ML_GRAPH_ABLATION.md
    # §6) via the actual graph_flagged signal, not just ground-truth membership. Constructed
    # here as an explicitly-labeled synthetic test to exercise agent behavior on this
    # hypothetical combination -- NOT presented as a real detected case.
    {"category": "7_ml_high_graph_high_SYNTHETIC_TEST", "transaction_id": 3400379, "ml_score": 0.92, "ml_tier": "CRITICAL", "force_graph_evidence": True},
    {"category": "8_ml_low_graph_high", "transaction_id": 3457202, "ml_score": 0.011, "ml_tier": "MEDIUM"},
    {"category": "9_ml_high_graph_low", "transaction_id": 3400379, "ml_score": 0.85, "ml_tier": "CRITICAL"},
    {"category": "10_ml_low_graph_low", "transaction_id": 3400892, "ml_score": 0.005, "ml_tier": "LOW"},
    {"category": "11_conflicting_evidence", "transaction_id": 3181534, "ml_score": 0.01, "ml_tier": "LOW"},  # same ring member, but scored as if ML saw nothing
    {"category": "12_missing_data", "transaction_id": 2987000, "ml_score": 0.02, "ml_tier": "LOW"},
]

# Demo cases (Phase 4U) -- a subset of the eval categories above, reused
# to avoid duplicate real-API calls.
DEMO_CASE_CATEGORIES = [
    "1_strong_abuse_ring", "3_legitimate_household", "8_ml_low_graph_high",
    "11_conflicting_evidence", "12_missing_data",
]


def build_case_for(ctx, txn_id: int, ml_score: float, ml_tier: str, force_graph_evidence: bool = False):
    row = ctx.transactions_graph[ctx.transactions_graph["TransactionID"] == txn_id].iloc[0]
    signals_row = ctx.graph_signals[ctx.graph_signals["customer_proxy_id"] == row["customer_proxy_id"]]
    evidence = build_evidence_and_narrative(signals_row.iloc[0]) if len(signals_row) else None

    if force_graph_evidence and evidence is None:
        from src.graph.case_interface import GraphEvidence

        evidence = GraphEvidence(
            community_id=-1, community_size=5, n_shared_devices=1, n_shared_ips=1, n_shared_bank_accounts=1,
            multi_attribute_overlap=True, relationship_rarity_score=0.9, temporal_concentration_hours=2.0,
            detected_relationship_types=["SHARED_DEVICE", "SHARED_IP", "SHARED_BANK_ACCOUNT"],
            narrative="SYNTHETIC TEST CONSTRUCTION (no real example exists in this benchmark, docs/AGENT_EVALUATION.md): "
            "5 customer proxies connected through 1 shared device, 1 shared IP, and 1 shared bank-account proxy, "
            "concentrated within a 2-hour window.",
        )
    return build_case(row, ml_risk_score=ml_score, ml_risk_tier=ml_tier, graph_evidence=evidence)


def run_configuration_A(case) -> dict:
    """Deterministic graph evidence only -- no synthesis at all."""
    return {
        "config": "A_graph_evidence_only",
        "output": {
            "ml_risk_score": case.ml_risk_score,
            "ml_risk_tier": case.ml_risk_tier,
            "graph_evidence_raw": case.graph_evidence.__dict__ if case.graph_evidence else None,
        },
    }


def run_configuration_B(case) -> dict:
    """Graph evidence + deterministic template narrative -- no LLM."""
    return {
        "config": "B_graph_plus_template_narrative",
        "output": {
            "ml_risk_score": case.ml_risk_score,
            "ml_risk_tier": case.ml_risk_tier,
            "narrative": case.graph_evidence.narrative if case.graph_evidence else "No graph evidence available.",
        },
    }


def run_configuration_C(case, ctx, corpus, llm_client) -> dict:
    """Graph evidence + investigation agent."""
    registry = ToolRegistry(ctx=ctx, corpus=corpus)
    agent_input = build_agent_input(case)
    deps = InvestigationGraphDeps(registry=registry, llm_client=llm_client, corpus=corpus)

    t0 = time.time()
    try:
        report = run_investigation(agent_input, deps)
        error = None
    except Exception as e:  # noqa: BLE001
        report = None
        error = f"{type(e).__name__}: {e}"
    latency_s = time.time() - t0

    return {
        "config": "C_investigation_agent",
        "backend": llm_client.backend_name,
        "output": report,
        "error": error,
        "latency_seconds": round(latency_s, 2),
        "tool_calls": [{"name": c.name, "ok": c.ok, "error": c.error} for c in registry.call_log],
        "n_tool_calls": len(registry.call_log),
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ctx = load_tool_data_context(PROJECT_ROOT)
    corpus = PolicyCorpus.from_directory(PROJECT_ROOT / "docs" / "policy_documents")

    stub_client = StubLLMClient()
    claude_client = ClaudeAgentSDKClient()

    results = []
    for spec in EVAL_CASES:
        print(f"\n=== {spec['category']} (txn {spec['transaction_id']}) ===")
        case = build_case_for(
            ctx, spec["transaction_id"], spec["ml_score"], spec["ml_tier"],
            force_graph_evidence=spec.get("force_graph_evidence", False),
        )

        a = run_configuration_A(case)
        b = run_configuration_B(case)
        print("  Running STUB TEST agent config...")
        c_stub = run_configuration_C(case, ctx, corpus, stub_client)
        print(f"    stub validation_status={c_stub['output']['validation_status'] if c_stub['output'] else 'ERROR'}")
        print("  Running CLAUDE DEVELOPMENT RUN agent config (real Claude, via Agent SDK)...")
        c_claude = run_configuration_C(case, ctx, corpus, claude_client)
        print(f"    claude validation_status={c_claude['output']['validation_status'] if c_claude['output'] else 'ERROR'} "
              f"latency={c_claude['latency_seconds']}s")

        results.append(
            {
                "category": spec["category"],
                "transaction_id": spec["transaction_id"],
                "case_id": case.case_id,
                "configuration_A": a,
                "configuration_B": b,
                "configuration_C_stub": c_stub,
                "configuration_C_claude": c_claude,
            }
        )

    with (OUT_DIR / "evaluation_results.json").open("w") as f:
        json.dump(results, f, indent=2, default=str)

    demo_cases = [r for r in results if r["category"] in DEMO_CASE_CATEGORIES]
    with (OUT_DIR / "demo_cases.json").open("w") as f:
        json.dump(demo_cases, f, indent=2, default=str)

    print(f"\nWritten to {OUT_DIR}")


if __name__ == "__main__":
    main()
