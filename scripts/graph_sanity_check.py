"""Phase 1J — graph sanity check.

Diagnostics only — this does NOT claim the graph detects fraud (that's
future Phase 2 work). It measures whether the graph is structurally
sane: node/edge counts, degree distribution, connected-component sizes,
community structure, and — critically — whether legitimate clusters and
injected rings are entangled in the graph (they should be separable by
more than raw connectivity alone, since a connected component can
legitimately contain both an innocent decoy and ring members).
"""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import pandas as pd

from src.graph.build_graph import build_graph, edge_relationship_counts, node_type_counts

DEV_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "dev"
OUT = DEV_DIR / "graph_sanity_report.json"


def degree_stats(g: nx.MultiDiGraph) -> dict:
    degrees = pd.Series(dict(g.degree()))
    return {
        "describe": degrees.describe().to_dict(),
        "top_10_highest_degree_nodes": [
            {"node": n, "degree": int(d), "node_type": g.nodes[n]["node_type"]}
            for n, d in degrees.sort_values(ascending=False).head(10).items()
        ],
    }


def connected_component_stats(g: nx.MultiDiGraph) -> dict:
    undirected = g.to_undirected()
    components = list(nx.connected_components(undirected))
    sizes = sorted((len(c) for c in components), reverse=True)
    return {
        "n_components": len(components),
        "largest_component_size": sizes[0] if sizes else 0,
        "size_describe": pd.Series(sizes).describe().to_dict() if sizes else {},
        "top_10_component_sizes": sizes[:10],
    }, components


def community_stats(g: nx.MultiDiGraph) -> dict:
    undirected = nx.Graph(g.to_undirected())  # collapse multigraph -> simple graph for community detection
    try:
        communities = nx.algorithms.community.louvain_communities(undirected, seed=42)
        method = "louvain"
    except Exception:
        communities = nx.algorithms.community.greedy_modularity_communities(undirected)
        method = "greedy_modularity"
    sizes = sorted((len(c) for c in communities), reverse=True)
    return {
        "method": method,
        "n_communities": len(communities),
        "size_describe": pd.Series(sizes).describe().to_dict() if sizes else {},
        "top_10_community_sizes": sizes[:10],
    }


def ring_and_legitimate_overlap(transactions: pd.DataFrame, components: list[set]) -> dict:
    """For each connected component, check whether it contains ring
    members, legitimate-cluster members, decoys, or a mix — this is the
    'does the graph require actual analysis' check Phase 1J asked for."""

    def customer_node(cust_id: str) -> str:
        return f"customer_proxy:{cust_id}"

    ring_customers = set(transactions.loc[transactions["synthetic_ring_id"].notna(), "customer_proxy_id"])
    legit_customers = set(
        transactions.loc[transactions["legitimate_cluster_id"].notna(), "customer_proxy_id"]
    )
    decoy_customers = set(
        transactions.loc[transactions["synthetic_ring_role"] == "decoy_bystander", "customer_proxy_id"]
    )

    ring_nodes = {customer_node(c) for c in ring_customers}
    legit_nodes = {customer_node(c) for c in legit_customers}
    decoy_nodes = {customer_node(c) for c in decoy_customers}

    mixed_components = 0
    ring_only_components = 0
    legit_only_components = 0
    for comp in components:
        has_ring = bool(comp & ring_nodes)
        has_legit = bool(comp & legit_nodes)
        has_decoy = bool(comp & decoy_nodes)
        if has_ring and (has_legit or has_decoy):
            mixed_components += 1
        elif has_ring:
            ring_only_components += 1
        elif has_legit:
            legit_only_components += 1

    return {
        "n_ring_customer_nodes": len(ring_nodes),
        "n_legitimate_customer_nodes": len(legit_nodes),
        "n_decoy_customer_nodes": len(decoy_nodes),
        "components_mixing_ring_and_legit_or_decoy": mixed_components,
        "components_ring_only": ring_only_components,
        "components_legit_only": legit_only_components,
        "interpretation": (
            "mixed components confirm shared-attribute connectivity alone does not "
            "separate ring members from legitimate/decoy entities -- ring detection "
            "requires more than connected-components, consistent with the design "
            "doc's Section 14 rationale for adding Louvain and other signals on top."
        ),
    }


def ring_size_distribution(rings_json: list[dict]) -> dict:
    sizes = [r["size"] for r in rings_json]
    return {
        "n_rings": len(rings_json),
        "sizes": sizes,
        "by_abuse_type": {
            t: [r["size"] for r in rings_json if r["abuse_type"] == t]
            for t in sorted({r["abuse_type"] for r in rings_json})
        },
    }


def main() -> None:
    transactions = pd.read_csv(DEV_DIR / "transactions.csv")
    with (DEV_DIR / "rings.json").open() as f:
        rings_json = json.load(f)
    with (DEV_DIR / "legitimate_clusters.json").open() as f:
        clusters_json = json.load(f)

    g = build_graph(transactions)

    cc_stats, components = connected_component_stats(g)

    report = {
        "node_counts": {"total": g.number_of_nodes(), "by_type": node_type_counts(g)},
        "edge_counts": {"total": g.number_of_edges(), "by_relationship": edge_relationship_counts(g)},
        "degree_stats": degree_stats(g),
        "connected_components": cc_stats,
        "communities": community_stats(g),
        "n_legitimate_clusters": len(clusters_json),
        "n_injected_rings": len(rings_json),
        "ring_size_distribution": ring_size_distribution(rings_json),
        "ring_legitimate_overlap": ring_and_legitimate_overlap(transactions, components),
    }

    with OUT.open("w") as f:
        json.dump(report, f, indent=2, default=str)

    print(json.dumps(report, indent=2, default=str))
    print(f"\nWritten to {OUT}")


if __name__ == "__main__":
    main()
