"""Relationship-specific customer-customer graph projections — Phase 1.5,
Decisions 2, 3, 4.

Decision 2 (hub entities): `merchant_proxy`, `email_domain_proxy`, and —
confirmed by measurement, not assumed — `payment_instrument_proxy` (its
`large_low_confidence`/`mega_unresolved` tiers still bridge hundreds of
unrelated customers even under the corrected localized model, see
docs/GRAPH_BENCHMARK.md) are EXCLUDED from every projection in this
module. They remain available as node attributes / ML features /
investigation evidence via the full heterogeneous graph
(src/graph/build_graph.py), just not as ring-detection topology.

Decision 3: one customer-customer projection per relationship type
(device / IP / bank_account), plus a combined multi-attribute view.

Decision 4: edge weights are NOT arbitrary. Two strategies are
implemented and compared empirically (docs/GRAPH_BENCHMARK.md) rather
than one being assumed correct:
  - "flat": a fixed prior weight per relationship type, reflecting
    expected legitimate-sharing base rates (shared device/bank_account
    are rarer and more discriminative than shared IP or address).
  - "inverse_frequency": flat weight scaled by 1/n_sharing, so an
    attribute shared by only 2 customers counts far more than one shared
    by hundreds (a large shared cluster is much more likely to be
    coincidental than a small one).
"""

from __future__ import annotations

import math

import networkx as nx
import pandas as pd

# Prior weight per relationship type, before any frequency adjustment —
# reflects Decision 4's stated priors: shared device/bank_account are
# high-signal, shared IP is moderate (ISP/NAT sharing is common), shared
# address is moderate/low (families genuinely share addresses often).
BASE_WEIGHT = {
    "SHARED_DEVICE": 5.0,
    "SHARED_BANK_ACCOUNT": 5.0,
    "SHARED_IP": 3.0,
    "SHARED_ADDRESS": 2.0,
}

RELATIONSHIP_ENTITY_COLUMNS = {
    "SHARED_DEVICE": "device_synthetic_id",
    "SHARED_IP": "ip_synthetic_id",
    "SHARED_BANK_ACCOUNT": "bank_account_synthetic_id",
    "SHARED_ADDRESS": "address_synthetic_id",
}


def _edge_weight(relationship_type: str, n_sharing: int, strategy: str) -> float:
    base = BASE_WEIGHT[relationship_type]
    if strategy == "flat":
        return base
    if strategy == "inverse_frequency":
        return base / n_sharing
    if strategy == "inverse_log_frequency":
        # dampened version: penalizes large clusters less harshly than raw 1/n
        return base / (1.0 + math.log(n_sharing))
    raise ValueError(f"unknown weighting strategy: {strategy}")


def build_relationship_graph(
    df: pd.DataFrame, relationship_type: str, weighting: str = "flat"
) -> nx.Graph:
    """Customer <-> entity <-> Customer projection for one relationship type.

    Nodes are customer_proxy_id values (bare, no 'customer_proxy:' prefix
    — this is a customer-customer graph, not the mixed-entity graph).
    Each edge carries `weight`, `relationship_type`, and `evidence`: the
    list of shared entity values (usually one) and how many customers
    share each, for traceability back to the source attribute.
    """
    entity_col = RELATIONSHIP_ENTITY_COLUMNS[relationship_type]
    g = nx.Graph()

    sub = df.dropna(subset=[entity_col, "customer_proxy_id"])
    for entity_value, group in sub.groupby(entity_col):
        customers = sorted(group["customer_proxy_id"].unique().tolist())
        n_sharing = len(customers)
        if n_sharing < 2:
            continue

        weight = _edge_weight(relationship_type, n_sharing, weighting)
        for i in range(len(customers)):
            for j in range(i + 1, len(customers)):
                c1, c2 = customers[i], customers[j]
                if g.has_edge(c1, c2):
                    g[c1][c2]["weight"] += weight
                    g[c1][c2]["evidence"].append({"value": entity_value, "n_sharing": n_sharing})
                else:
                    g.add_node(c1)
                    g.add_node(c2)
                    g.add_edge(
                        c1, c2,
                        weight=weight,
                        relationship_type=relationship_type,
                        evidence=[{"value": entity_value, "n_sharing": n_sharing}],
                    )
    return g


def build_multi_attribute_graph(
    df: pd.DataFrame,
    relationship_types: tuple[str, ...] = ("SHARED_DEVICE", "SHARED_IP", "SHARED_BANK_ACCOUNT"),
    weighting: str = "flat",
) -> nx.Graph:
    """Union of several relationship-specific projections into one weighted
    graph — an edge's weight is the SUM across every relationship type
    that connects the same pair, so a customer pair sharing 2+ attributes
    (device AND bank_account) ends up structurally stronger than a pair
    sharing just one — directly testing the design doc's Section 8
    "sharing 2+ attributes is a stronger signal" hypothesis.
    """
    combined = nx.Graph()
    for rel in relationship_types:
        g = build_relationship_graph(df, rel, weighting)
        for c1, c2, data in g.edges(data=True):
            if combined.has_edge(c1, c2):
                combined[c1][c2]["weight"] += data["weight"]
                combined[c1][c2]["relationship_types"].append(rel)
                combined[c1][c2]["evidence"].extend(data["evidence"])
            else:
                combined.add_edge(
                    c1, c2,
                    weight=data["weight"],
                    relationship_types=[rel],
                    evidence=list(data["evidence"]),
                )
    return combined
