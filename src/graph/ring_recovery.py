"""Ring recovery benchmark — Phase 1.5, Decision 10.

Tests whether a graph representation + community/connected-component
detection method can recover injected rings, measured as precision/
recall/F1 against synthetic ground truth. Per Decision 10's instruction,
this module is run and reported BEFORE any attempt to tune parameters
against these numbers — see docs/GRAPH_BENCHMARK.md.
"""

from __future__ import annotations

import networkx as nx
import pandas as pd


def detect_communities(g: nx.Graph, method: str = "louvain", seed: int = 42) -> dict[str, int]:
    """Return {node: community_id}. method: 'louvain' or 'connected_components'."""
    if g.number_of_nodes() == 0:
        return {}
    undirected = nx.Graph(g.to_undirected()) if g.is_directed() else g
    if method == "connected_components":
        communities = list(nx.connected_components(undirected))
    elif method == "louvain":
        has_weights = any("weight" in d for _, _, d in undirected.edges(data=True))
        communities = list(
            nx.algorithms.community.louvain_communities(
                undirected, weight="weight" if has_weights else None, seed=seed
            )
        )
    else:
        raise ValueError(f"unknown method: {method}")

    node_to_comm: dict[str, int] = {}
    for i, comm in enumerate(communities):
        for n in comm:
            node_to_comm[n] = i
    return node_to_comm


def evaluate_ring_recovery(
    rings: list[dict], node_to_community: dict, customer_node_fn=lambda c: c
) -> list[dict]:
    """For each ring: majority-vote the community of its CORE members (the
    ones actually carrying the shared attribute), then score everything in
    that community against the ring's true membership (core + noise).
    """
    results = []
    for r in rings:
        true_members = set(r["core_members"]) | set(r["noise_members"])
        core_nodes = [customer_node_fn(m) for m in r["core_members"]]
        member_comms = [node_to_community[n] for n in core_nodes if n in node_to_community]

        if not member_comms:
            results.append(
                {
                    "ring_id": r["ring_id"], "abuse_type": r["abuse_type"], "true_size": len(true_members),
                    "detected_size": 0, "precision": 0.0, "recall": 0.0, "f1": 0.0,
                    "note": "no core members present in this graph view",
                }
            )
            continue

        target_comm = pd.Series(member_comms).value_counts().index[0]
        detected_nodes = {n for n, c in node_to_community.items() if c == target_comm}

        node_to_customer = {customer_node_fn(m): m for m in true_members}
        detected_customers = {node_to_customer.get(n, n) for n in detected_nodes}

        tp = len(detected_customers & true_members)
        precision = tp / len(detected_customers) if detected_customers else 0.0
        recall = tp / len(true_members) if true_members else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        results.append(
            {
                "ring_id": r["ring_id"],
                "abuse_type": r["abuse_type"],
                "true_size": len(true_members),
                "detected_size": len(detected_customers),
                "true_positives": tp,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
            }
        )
    return results


def evaluate_legitimate_false_positives(
    legitimate_clusters: list[dict], node_to_community: dict, rings: list[dict], customer_node_fn=lambda c: c
) -> list[dict]:
    """For each legitimate cluster, check whether its detected community also
    contains a ring member — a false-positive contamination signal."""
    all_ring_members: set[str] = set()
    for r in rings:
        all_ring_members |= set(r["core_members"]) | set(r["noise_members"])

    results = []
    for c in legitimate_clusters:
        member_nodes = [customer_node_fn(m) for m in c["members"]]
        member_comms = [node_to_community[n] for n in member_nodes if n in node_to_community]
        if not member_comms:
            results.append(
                {"cluster_id": c["cluster_id"], "cluster_type": c["cluster_type"], "note": "not present in this graph view"}
            )
            continue

        target_comm = pd.Series(member_comms).value_counts().index[0]
        community_nodes = {n for n, cm in node_to_community.items() if cm == target_comm}

        node_to_customer_all = {customer_node_fn(m): m for m in (set(c["members"]) | all_ring_members)}
        community_customers = {node_to_customer_all.get(n, n) for n in community_nodes}
        contaminating = community_customers & all_ring_members

        results.append(
            {
                "cluster_id": c["cluster_id"],
                "cluster_type": c["cluster_type"],
                "community_size": len(community_customers),
                "false_positive": len(contaminating) > 0,
                "contaminating_ring_members": sorted(contaminating),
            }
        )
    return results


def summarize_ring_recovery(results: list[dict]) -> dict:
    scored = [r for r in results if "note" not in r]
    missed = [r for r in results if "note" in r or r.get("recall", 0) == 0]
    if not scored:
        return {"n_rings": len(results), "n_scored": 0, "mean_precision": None, "mean_recall": None, "mean_f1": None}
    return {
        "n_rings": len(results),
        "n_scored": len(scored),
        "n_missed_entirely": len(missed),
        "mean_precision": round(sum(r["precision"] for r in scored) / len(scored), 4),
        "mean_recall": round(sum(r["recall"] for r in scored) / len(scored), 4),
        "mean_f1": round(sum(r["f1"] for r in scored) / len(scored), 4),
    }


def summarize_false_positives(results: list[dict]) -> dict:
    scored = [r for r in results if "note" not in r]
    n_fp = sum(1 for r in scored if r["false_positive"])
    return {
        "n_clusters": len(results),
        "n_scored": len(scored),
        "n_false_positive": n_fp,
        "false_positive_rate": round(n_fp / len(scored), 4) if scored else None,
    }
