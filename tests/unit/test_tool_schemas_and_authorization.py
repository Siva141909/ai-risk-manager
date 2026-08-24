"""Phase 4C/4D/4G/4S — tool schema, authorization boundary, and rate-limit tests."""

from __future__ import annotations

import pandas as pd
import pytest

from src.generator.ground_truth import GROUND_TRUTH_COLUMNS
from src.tools.context import ToolDataContext
from src.tools.registry import (
    ALLOWED_TOOL_NAMES,
    MAX_REPEATED_IDENTICAL_CALLS,
    TOOL_REGISTRY,
    ToolAuthorizationError,
    ToolCallBudgetExceeded,
    ToolRegistry,
)
from src.tools.schemas import (
    CustomerContextOutput,
    GraphContextOutput,
    GraphNeighborsOutput,
    MerchantContextOutput,
    PolicyQueryOutput,
    PreviousCasesOutput,
    RelatedEntitiesOutput,
    RiskSignalsOutput,
    TemporalActivityOutput,
    TransactionHistoryOutput,
)


def _toy_ctx() -> ToolDataContext:
    graph_df = pd.DataFrame(
        {
            "TransactionID": [1, 2, 3],
            "TransactionDT": [0, 3600, 7200],
            "TransactionAmt": [10.0, 20.0, 30.0],
            "ProductCD": ["W", "W", "C"],
            "customer_proxy_id": ["a", "a", "b"],
            "customer_proxy_confidence": ["small", "small", "small"],
            "device_synthetic_id": ["DEV-1", "DEV-1", None],
            "ip_synthetic_id": [None, None, None],
            "bank_account_synthetic_id": [None, None, None],
        }
    )
    ml_df = pd.DataFrame(
        {
            "TransactionID": [1, 2, 3],
            "TransactionDT": [0, 3600, 7200],
            "TransactionAmt": [10.0, 20.0, 30.0],
            "cust_txn_count_so_far": [0, 1, 0],
            "cust_txn_count_prior_24h": [0, 1, 0],
            "cust_time_since_last_txn": [None, 3600, None],
        }
    )
    from src.graph.signals import compute_customer_graph_signals

    signals = compute_customer_graph_signals(graph_df)
    return ToolDataContext(transactions_graph=graph_df, transactions_ml=ml_df, graph_signals=signals, case_risk_signals={})


def test_every_registered_tool_output_schema_has_no_ground_truth_field():
    output_schemas = [
        TransactionHistoryOutput, CustomerContextOutput, RelatedEntitiesOutput, GraphContextOutput,
        GraphNeighborsOutput, TemporalActivityOutput, MerchantContextOutput, PreviousCasesOutput,
        RiskSignalsOutput, PolicyQueryOutput,
    ]
    for schema in output_schemas:
        field_names = set(schema.model_fields.keys())
        for gt_col in GROUND_TRUTH_COLUMNS:
            assert gt_col not in field_names, f"{schema.__name__} exposes ground-truth field {gt_col}"


def test_expected_ten_tools_are_registered():
    expected = {
        "get_transaction_history", "get_customer_context", "get_related_entities", "get_graph_context",
        "get_graph_neighbors", "get_temporal_activity", "get_merchant_context", "get_previous_cases",
        "get_risk_signals", "get_policy",
    }
    assert expected == ALLOWED_TOOL_NAMES == set(TOOL_REGISTRY.keys())


def test_unregistered_tool_name_is_rejected():
    registry = ToolRegistry(ctx=_toy_ctx())
    with pytest.raises(ToolAuthorizationError):
        registry.call("drop_table_transactions", {})


def test_arbitrary_sql_like_call_is_rejected():
    registry = ToolRegistry(ctx=_toy_ctx())
    with pytest.raises(ToolAuthorizationError):
        registry.call("execute_sql", {"query": "SELECT * FROM transactions"})


def test_invalid_arguments_return_error_not_exception():
    registry = ToolRegistry(ctx=_toy_ctx())
    result = registry.call("get_transaction_history", {"customer_proxy_id": "a", "unexpected_field": "x"})
    assert "error" in result


def test_extra_fields_rejected_by_strict_schema():
    registry = ToolRegistry(ctx=_toy_ctx())
    result = registry.call("get_customer_context", {"customer_proxy_id": "a", "sql_injection": "'; DROP TABLE"})
    assert "error" in result


def test_valid_call_succeeds_and_is_deterministic():
    registry = ToolRegistry(ctx=_toy_ctx())
    r1 = registry.call("get_customer_context", {"customer_proxy_id": "a"})
    r2 = registry.call("get_customer_context", {"customer_proxy_id": "a"})
    assert r1 == r2
    assert r1["found"] is True


def test_tool_call_budget_enforced():
    registry = ToolRegistry(ctx=_toy_ctx(), max_calls=3)
    for i in range(3):
        registry.call("get_customer_context", {"customer_proxy_id": f"cust-{i}"})
    with pytest.raises(ToolCallBudgetExceeded):
        registry.call("get_customer_context", {"customer_proxy_id": "one-too-many"})


def test_repeated_identical_call_is_refused_after_limit():
    registry = ToolRegistry(ctx=_toy_ctx(), max_calls=20)
    for _ in range(MAX_REPEATED_IDENTICAL_CALLS):
        result = registry.call("get_customer_context", {"customer_proxy_id": "a"})
        assert "error" not in result
    result = registry.call("get_customer_context", {"customer_proxy_id": "a"})
    assert "error" in result
    assert "repeated" in result["error"]


def test_tool_failure_represented_explicitly_not_propagated():
    """A tool that internally raises must produce {'error': ...}, not crash the caller."""
    from src.tools.registry import TOOL_REGISTRY, ToolSpec

    def _always_fails(ctx, inp):
        raise RuntimeError("simulated backend failure")

    broken_registry = TOOL_REGISTRY.copy()
    broken_registry["get_customer_context"] = ToolSpec(
        "get_customer_context", TOOL_REGISTRY["get_customer_context"].input_schema, _always_fails
    )
    import src.tools.registry as registry_module

    original = registry_module.TOOL_REGISTRY
    registry_module.TOOL_REGISTRY = broken_registry
    try:
        registry = ToolRegistry(ctx=_toy_ctx())
        result = registry.call("get_customer_context", {"customer_proxy_id": "a"})
        assert "error" in result
        assert "simulated backend failure" in result["error"]
        assert registry.call_log[-1].ok is False
    finally:
        registry_module.TOOL_REGISTRY = original


def test_evidence_ids_are_deterministic_across_runs():
    ctx = _toy_ctx()
    r1 = ToolRegistry(ctx=ctx).call("get_customer_context", {"customer_proxy_id": "a"})
    r2 = ToolRegistry(ctx=ctx).call("get_customer_context", {"customer_proxy_id": "a"})
    assert r1["evidence_id"] == r2["evidence_id"]
