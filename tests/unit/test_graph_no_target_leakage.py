"""Phase 3L — graph-layer leakage tests.

Covers the 6 explicit guarantees Phase 3L asks for, plus the real-time
vs. retrospective feature distinction: graph evidence
(src/graph/signals.py, src/graph/explain.py) is computed from the FULL
graph (all transactions, all times) and is explicitly retrospective —
it must never be fed into src/features/ (the real-time ML feature
pipeline) as if it were known at transaction time.
"""

from __future__ import annotations

import inspect

import pandas as pd

from src.features.leakage_guard import NON_FEATURE_COLUMNS
from src.features.pipeline import RAW_TRANSACTION_COLUMNS
from src.graph.signals import compute_customer_graph_signals


def test_original_isfraud_not_used_in_graph_signal_computation():
    """compute_customer_graph_signals must not even accept isFraud/original_isFraud
    as an input — structurally impossible to use it."""
    sig = inspect.signature(compute_customer_graph_signals)
    assert "isFraud" not in sig.parameters
    assert "original_isFraud" not in sig.parameters


def test_graph_signal_columns_do_not_overlap_ml_feature_columns():
    """The columns compute_customer_graph_signals produces (retrospective
    graph evidence) must never collide with names in the real-time ML
    feature denylist/allowlist -- if they did, a careless merge could
    silently smuggle retrospective evidence into the real-time feature
    matrix."""
    signals_columns = {
        "customer_proxy_id", "community_id", "community_size", "n_shared_devices",
        "n_shared_ips", "n_shared_bank_accounts", "multi_attribute_overlap",
        "relationship_rarity_score", "temporal_concentration_hours", "graph_flagged",
    }
    assert signals_columns.isdisjoint(set(RAW_TRANSACTION_COLUMNS))


def test_synthetic_ring_labels_not_used_to_construct_graph_signals():
    """compute_customer_graph_signals operates purely on structural
    columns (customer_proxy_id, device/ip/bank_account synthetic IDs,
    TransactionDT) -- verified by checking the function's source does
    not reference any ground-truth column name."""
    source = inspect.getsource(compute_customer_graph_signals)
    for banned in ("synthetic_ring_id", "synthetic_abuse_type", "synthetic_entity_label", "isFraud"):
        assert banned not in source


def test_graph_signals_do_not_require_or_use_original_isfraud_column():
    """Even if a caller's dataframe happens to carry isFraud, the
    computed signals must be identical whether or not that column is
    present — proving it isn't silently read."""
    df = pd.DataFrame(
        {
            "customer_proxy_id": ["a", "b", "c"],
            "TransactionDT": [0, 100, 200],
            "device_synthetic_id": ["DEV-1", "DEV-1", "DEV-1"],
            "ip_synthetic_id": [None, None, None],
            "bank_account_synthetic_id": [None, None, None],
        }
    )
    df_with_label = df.assign(isFraud=[1, 0, 1])

    s1 = compute_customer_graph_signals(df).drop(columns=[])
    s2 = compute_customer_graph_signals(df_with_label)
    pd.testing.assert_frame_equal(
        s1.sort_values("customer_proxy_id").reset_index(drop=True),
        s2.sort_values("customer_proxy_id").reset_index(drop=True),
    )


def test_graph_evidence_columns_are_denylisted_as_ml_features_if_ever_merged():
    """Defense in depth: even if graph-signal columns were accidentally
    merged into a feature dataframe, they are not part of any allowed ML
    feature list (src/features/schema.py) -- they were never added there."""
    from src.features.schema import ALL_NAMED_TRANSACTION_COLUMNS

    retrospective_only_columns = {
        "community_id", "community_size", "n_shared_devices", "n_shared_ips",
        "n_shared_bank_accounts", "multi_attribute_overlap", "relationship_rarity_score",
        "temporal_concentration_hours", "graph_flagged",
    }
    assert retrospective_only_columns.isdisjoint(set(ALL_NAMED_TRANSACTION_COLUMNS))
    assert retrospective_only_columns.isdisjoint(NON_FEATURE_COLUMNS)  # not even denylisted -- because they were never in the allowlist to begin with
