"""Graph health diagnostics — Phase 1.5, Decision 9.

Generic health report reusable across every graph view (full
heterogeneous graph, each relationship-specific projection, the
multi-attribute graph) so pathological percolation is always visible,
not just when someone happens to check.
"""

from __future__ import annotations

import networkx as nx
import pandas as pd


def graph_health_report(g: nx.Graph) -> dict:
    n_nodes = g.number_of_nodes()
    n_edges = g.number_of_edges()

    if n_nodes == 0:
        return {"node_count": 0, "edge_count": 0, "empty": True}

    undirected = g.to_undirected() if g.is_directed() else g
    components = list(nx.connected_components(undirected))
    sizes = sorted((len(c) for c in components), reverse=True)

    degrees = pd.Series(dict(g.degree()))
    isolated = int((degrees == 0).sum())

    return {
        "node_count": n_nodes,
        "edge_count": n_edges,
        "n_connected_components": len(components),
        "largest_component_size": sizes[0] if sizes else 0,
        "largest_component_pct": round(100 * sizes[0] / n_nodes, 3) if sizes else 0.0,
        "component_size_describe": pd.Series(sizes).describe().to_dict() if sizes else {},
        "top_10_component_sizes": sizes[:10],
        "average_degree": round(float(degrees.mean()), 3),
        "degree_describe": degrees.describe().to_dict(),
        "isolated_node_count": isolated,
        "isolated_node_pct": round(100 * isolated / n_nodes, 3),
    }


def health_report_by_relationship(df: pd.DataFrame, build_fn, relationship_types: list[str], weighting: str = "flat") -> dict:
    """Run graph_health_report separately for each relationship type."""
    return {rel: graph_health_report(build_fn(df, rel, weighting)) for rel in relationship_types}
