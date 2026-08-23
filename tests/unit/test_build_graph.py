"""Unit tests for src/graph/build_graph.py (Phase 1I)."""

from __future__ import annotations

import pandas as pd

from src.graph.build_graph import build_graph, edge_relationship_counts, node_type_counts


def _toy_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "TransactionID": [1, 2, 3],
            "TransactionDT": [100, 200, 300],
            "customer_proxy_id": ["cust-A", "cust-B", "cust-A"],
            "payment_instrument_proxy_id": ["pi-1", "pi-2", "pi-1"],
            "ProductCD": ["W", "C", "W"],
            "P_emaildomain": ["gmail.com", None, "gmail.com"],
            "device_synthetic_id": ["DEV-1", "DEV-1", "DEV-2"],  # cust-A and cust-B share DEV-1
            "ip_synthetic_id": ["1.2.3.4", "5.6.7.8", "1.2.3.4"],
            "bank_account_synthetic_id": ["BANK-1", "BANK-2", "BANK-1"],
            "address_synthetic_id": ["ADDR-1", "ADDR-2", "ADDR-1"],
        }
    )


def test_node_types_present():
    g = build_graph(_toy_df())
    types = node_type_counts(g)
    assert types["customer_proxy"] == 2
    assert types["payment_instrument_proxy"] == 2
    assert types["synthetic_device"] == 2


def test_shared_device_creates_shared_node_not_duplicate():
    g = build_graph(_toy_df())
    assert g.has_node("synthetic_device:DEV-1")
    # both cust-A and cust-B have an edge into the SAME device node
    assert g.has_edge("customer_proxy:cust-A", "synthetic_device:DEV-1")
    assert g.has_edge("customer_proxy:cust-B", "synthetic_device:DEV-1")


def test_missing_email_domain_produces_no_edge_for_that_row():
    g = build_graph(_toy_df())
    counts = edge_relationship_counts(g)
    # 3 rows but only 2 have a non-null P_emaildomain
    assert counts["CUSTOMER_USED_EMAIL_DOMAIN"] == 2
    assert counts["CUSTOMER_USED_DEVICE"] == 3


def test_edge_carries_relationship_type_timestamp_and_transaction_id():
    g = build_graph(_toy_df())
    edge_data = g.get_edge_data("customer_proxy:cust-A", "synthetic_device:DEV-1")
    first_edge = next(iter(edge_data.values()))
    assert first_edge["relationship_type"] == "CUSTOMER_USED_DEVICE"
    assert first_edge["timestamp"] == 100
    assert first_edge["transaction_id"] == 1


def test_connected_component_links_customers_sharing_a_device():
    import networkx as nx

    g = build_graph(_toy_df())
    undirected = g.to_undirected()
    components = list(nx.connected_components(undirected))
    # cust-A and cust-B must be in the same component (linked via DEV-1)
    same_component = any({"customer_proxy:cust-A", "customer_proxy:cust-B"} <= c for c in components)
    assert same_component
