"""Phase 4E — real-time vs. retrospective temporal boundary tests.

Proves the agent cannot accidentally retrieve future evidence under
real-time mode: a tool called with cutoff_dt set never returns a
transaction with TransactionDT >= cutoff_dt, checked directly against
real tool output, not just against the cutoff dataclass in isolation.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.agents.temporal import InvestigationCutoff
from src.tools.context import ToolDataContext
from src.tools.registry import ToolRegistry


def _ctx_with_future_transactions() -> ToolDataContext:
    # customer 'a' has transactions before AND after a chosen trigger point
    graph_df = pd.DataFrame(
        {
            "TransactionID": [1, 2, 3, 4, 5],
            "TransactionDT": [1000, 2000, 5000, 8000, 20000],  # trigger will be at 5000
            "TransactionAmt": [10.0, 20.0, 30.0, 40.0, 50.0],
            "ProductCD": ["W"] * 5,
            "customer_proxy_id": ["a"] * 5,
            "customer_proxy_confidence": ["small"] * 5,
            "device_synthetic_id": [None] * 5,
            "ip_synthetic_id": [None] * 5,
            "bank_account_synthetic_id": [None] * 5,
        }
    )
    ml_df = pd.DataFrame(
        {
            "TransactionID": [1, 2, 3, 4, 5],
            "TransactionDT": [1000, 2000, 5000, 8000, 20000],
            "TransactionAmt": [10.0, 20.0, 30.0, 40.0, 50.0],
            "cust_txn_count_so_far": [0, 1, 2, 3, 4],
            "cust_txn_count_prior_24h": [0, 1, 2, 3, 4],
            "cust_time_since_last_txn": [None, 1000, 3000, 3000, 12000],
        }
    )
    from src.graph.signals import compute_customer_graph_signals

    signals = compute_customer_graph_signals(graph_df)
    return ToolDataContext(transactions_graph=graph_df, transactions_ml=ml_df, graph_signals=signals, case_risk_signals={})


def test_cutoff_for_case_uses_trigger_transaction_dt():
    cutoff = InvestigationCutoff.for_case(trigger_transaction_dt=5000)
    assert cutoff.case_event_time == 5000
    assert cutoff.real_time_cutoff == 5000
    assert cutoff.retrospective_investigation_cutoff is None


def test_cutoff_for_mode_rejects_unknown_mode():
    cutoff = InvestigationCutoff.for_case(5000)
    with pytest.raises(ValueError):
        cutoff.cutoff_for_mode("some_other_mode")


def test_real_time_transaction_history_excludes_future_rows():
    ctx = _ctx_with_future_transactions()
    cutoff = InvestigationCutoff.for_case(trigger_transaction_dt=5000)
    registry = ToolRegistry(ctx=ctx)

    result = registry.call(
        "get_transaction_history",
        {"customer_proxy_id": "a", "cutoff_dt": cutoff.cutoff_for_mode("real_time"), "max_results": 20},
    )
    returned_dts = [t["transaction_dt"] for t in result["transactions"]]
    assert all(dt < 5000 for dt in returned_dts)
    assert 5000 not in returned_dts  # the trigger transaction's OWN dt is not "prior" to itself
    assert 8000 not in returned_dts
    assert 20000 not in returned_dts
    assert result["mode"] == "real_time"


def test_retrospective_transaction_history_includes_future_rows():
    ctx = _ctx_with_future_transactions()
    cutoff = InvestigationCutoff.for_case(trigger_transaction_dt=5000)
    registry = ToolRegistry(ctx=ctx)

    result = registry.call(
        "get_transaction_history",
        {"customer_proxy_id": "a", "cutoff_dt": cutoff.cutoff_for_mode("retrospective"), "max_results": 20},
    )
    returned_dts = {t["transaction_dt"] for t in result["transactions"]}
    assert 8000 in returned_dts
    assert 20000 in returned_dts
    assert result["mode"] == "retrospective"


def test_real_time_temporal_activity_excludes_future_rows():
    ctx = _ctx_with_future_transactions()
    cutoff = InvestigationCutoff.for_case(trigger_transaction_dt=5000)
    registry = ToolRegistry(ctx=ctx)

    result = registry.call(
        "get_temporal_activity", {"customer_proxy_id": "a", "cutoff_dt": cutoff.cutoff_for_mode("real_time")}
    )
    # at cutoff=5000, only txns at 1000 and 2000 are "prior" -> latest prior txn_count_so_far should be 1 (the 2nd txn)
    assert result["txn_count_so_far"] == 1
    assert result["mode"] == "real_time"


def test_real_time_mode_never_returns_transaction_at_or_after_cutoff_across_many_cutoffs():
    """Property-style check across several cutoff points."""
    ctx = _ctx_with_future_transactions()
    registry = ToolRegistry(ctx=ctx, max_calls=100)
    for cutoff_dt in [1500, 3000, 6000, 9000, 25000]:
        result = registry.call(
            "get_transaction_history", {"customer_proxy_id": "a", "cutoff_dt": cutoff_dt, "max_results": 20}
        )
        for t in result["transactions"]:
            assert t["transaction_dt"] < cutoff_dt, (
                f"real-time mode with cutoff={cutoff_dt} returned a transaction at {t['transaction_dt']}"
            )
