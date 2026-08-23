"""Unit tests for src/graph/relationship_views.py, src/graph/health.py,
and src/graph/ring_recovery.py (Phase 1.5, Decisions 2-4, 9, 10)."""

from __future__ import annotations

import pandas as pd

from src.graph.health import graph_health_report
from src.graph.relationship_views import build_multi_attribute_graph, build_relationship_graph
from src.graph.ring_recovery import detect_communities, evaluate_ring_recovery, summarize_ring_recovery


def _toy_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "customer_proxy_id": ["c1", "c2", "c3", "c4", "c5"],
            "device_synthetic_id": ["DEV-1", "DEV-1", "DEV-2", "DEV-1", "DEV-3"],  # c1,c2,c4 share DEV-1
            "ip_synthetic_id": ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4", "5.5.5.5"],  # no sharing
            "bank_account_synthetic_id": ["B1", "B2", "B3", "B4", "B5"],  # no sharing
        }
    )


def test_relationship_graph_only_connects_customers_sharing_the_attribute():
    g = build_relationship_graph(_toy_df(), "SHARED_DEVICE", weighting="flat")
    assert g.has_edge("c1", "c2")
    assert g.has_edge("c1", "c4")
    assert not g.has_edge("c1", "c3")  # different device
    assert not g.has_node("c3") or g.degree("c3") == 0  # c3's device (DEV-2) is unique -> no edges
    assert "c5" not in g.nodes or g.degree("c5") == 0


def test_relationship_graph_excludes_singleton_entities():
    """An entity value used by only one customer must not create a node/edge."""
    g = build_relationship_graph(_toy_df(), "SHARED_IP", weighting="flat")
    assert g.number_of_edges() == 0


def test_inverse_frequency_weight_lower_for_larger_sharing_group():
    df = pd.DataFrame(
        {
            "customer_proxy_id": ["a", "b", "x", "y", "z"],
            "device_synthetic_id": ["SMALL", "SMALL", "BIG", "BIG", "BIG"],
        }
    )
    g_small_group = build_relationship_graph(df, "SHARED_DEVICE", weighting="inverse_frequency")
    weight_pair_of_2 = g_small_group["a"]["b"]["weight"]
    weight_pair_of_3 = g_small_group["x"]["y"]["weight"]
    assert weight_pair_of_2 > weight_pair_of_3  # smaller sharing group -> higher weight


def test_flat_weight_is_constant_regardless_of_group_size():
    df = pd.DataFrame(
        {
            "customer_proxy_id": ["a", "b", "x", "y", "z"],
            "device_synthetic_id": ["SMALL", "SMALL", "BIG", "BIG", "BIG"],
        }
    )
    g = build_relationship_graph(df, "SHARED_DEVICE", weighting="flat")
    assert g["a"]["b"]["weight"] == g["x"]["y"]["weight"]


def test_multi_attribute_graph_sums_weight_across_relationship_types():
    df = pd.DataFrame(
        {
            "customer_proxy_id": ["a", "b"],
            "device_synthetic_id": ["DEV-1", "DEV-1"],
            "ip_synthetic_id": ["1.1.1.1", "1.1.1.1"],
            "bank_account_synthetic_id": ["B1", "B2"],  # not shared
        }
    )
    g_device_only = build_relationship_graph(df, "SHARED_DEVICE", weighting="flat")
    g_multi = build_multi_attribute_graph(df, weighting="flat")
    assert g_multi["a"]["b"]["weight"] > g_device_only["a"]["b"]["weight"]
    assert set(g_multi["a"]["b"]["relationship_types"]) == {"SHARED_DEVICE", "SHARED_IP"}


def test_graph_health_report_detects_giant_component():
    import networkx as nx

    g = nx.complete_graph(50)  # fully connected -> 1 component, 100%
    report = graph_health_report(g)
    assert report["n_connected_components"] == 1
    assert report["largest_component_pct"] == 100.0


def test_graph_health_report_on_fragmented_graph():
    import networkx as nx

    g = nx.Graph()
    for i in range(0, 20, 2):
        g.add_edge(f"n{i}", f"n{i+1}")  # 10 disjoint pairs
    report = graph_health_report(g)
    assert report["n_connected_components"] == 10
    assert report["largest_component_pct"] == 10.0  # each pair is 2/20 = 10%


def test_ring_recovery_perfect_case():
    import networkx as nx

    g = nx.Graph()
    g.add_edges_from([("r1", "r2"), ("r2", "r3"), ("r1", "r3")])  # ring triangle, isolated
    node_to_comm = detect_communities(g, method="connected_components")
    rings = [{"ring_id": "RING-1", "abuse_type": "shared_device", "core_members": ["r1", "r2", "r3"], "noise_members": []}]
    results = evaluate_ring_recovery(rings, node_to_comm)
    assert results[0]["precision"] == 1.0
    assert results[0]["recall"] == 1.0
    assert results[0]["f1"] == 1.0


def test_ring_recovery_missing_core_members_reported_as_note():
    node_to_comm: dict[str, int] = {}
    rings = [{"ring_id": "RING-1", "abuse_type": "shared_device", "core_members": ["ghost1"], "noise_members": []}]
    results = evaluate_ring_recovery(rings, node_to_comm)
    assert "note" in results[0]
    assert results[0]["recall"] == 0.0


def test_summarize_ring_recovery_averages_across_rings():
    results = [
        {"ring_id": "A", "precision": 1.0, "recall": 1.0, "f1": 1.0},
        {"ring_id": "B", "precision": 0.5, "recall": 0.5, "f1": 0.5},
    ]
    summary = summarize_ring_recovery(results)
    assert summary["mean_precision"] == 0.75
    assert summary["mean_recall"] == 0.75
