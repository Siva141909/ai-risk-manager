"""Phase 1I — graph-ready representation.

NetworkX only — explicitly NOT Neo4j (design doc Section 13: no
algorithmic need at this data volume) and NOT a GNN (design doc Section
14: nothing here learns embeddings, this is a plain typed multigraph).

Nodes: customer_proxy, payment_instrument_proxy, merchant_proxy,
email_domain_proxy, synthetic_device, synthetic_ip,
synthetic_bank_account, synthetic_address — each tagged with a
`node_type` attribute.

Edges: one per (transaction, entity-the-customer-touched) pair, carrying
`relationship_type`, `timestamp` (TransactionDT), and `transaction_id` —
this is what lets a downstream ring/community-detection pass reconstruct
"which transaction is this edge evidence from," per Phase 1I's brief.
"""

from __future__ import annotations

import networkx as nx
import pandas as pd

NODE_TYPE_COLUMNS = {
    "customer_proxy": "customer_proxy_id",
    "payment_instrument_proxy": "payment_instrument_proxy_id",
    "merchant_proxy": "ProductCD",
    "email_domain_proxy": "P_emaildomain",
    "synthetic_device": "device_synthetic_id",
    "synthetic_ip": "ip_synthetic_id",
    "synthetic_bank_account": "bank_account_synthetic_id",
    "synthetic_address": "address_synthetic_id",
}

# (source node type, target node type, relationship label) — matches the
# design doc's Section 13 edge list, extended with the entity types
# Phase 1I explicitly asked for (email_domain, address).
EDGE_RELATIONSHIPS = [
    ("customer_proxy", "payment_instrument_proxy", "CUSTOMER_USED_PAYMENT_INSTRUMENT"),
    ("customer_proxy", "merchant_proxy", "CUSTOMER_PAID_MERCHANT"),
    ("customer_proxy", "email_domain_proxy", "CUSTOMER_USED_EMAIL_DOMAIN"),
    ("customer_proxy", "synthetic_device", "CUSTOMER_USED_DEVICE"),
    ("customer_proxy", "synthetic_ip", "CUSTOMER_USED_IP"),
    ("customer_proxy", "synthetic_bank_account", "CUSTOMER_USED_BANK_ACCOUNT"),
    ("customer_proxy", "synthetic_address", "CUSTOMER_USED_ADDRESS"),
]


def build_graph(df: pd.DataFrame) -> nx.MultiDiGraph:
    """Build the typed entity graph from a generator-output dataframe.

    df must contain the columns referenced in NODE_TYPE_COLUMNS (missing
    optional columns, e.g. if a caller only wants a subset of entity
    types, are simply skipped) plus TransactionID and TransactionDT.
    """
    g = nx.MultiDiGraph()

    for node_type, col in NODE_TYPE_COLUMNS.items():
        if col not in df.columns:
            continue
        for value in df[col].dropna().unique():
            g.add_node(f"{node_type}:{value}", node_type=node_type, value=value)

    for src_type, dst_type, relationship in EDGE_RELATIONSHIPS:
        src_col = NODE_TYPE_COLUMNS[src_type]
        dst_col = NODE_TYPE_COLUMNS[dst_type]
        if src_col not in df.columns or dst_col not in df.columns:
            continue

        sub = df.dropna(subset=[src_col, dst_col])
        for row in sub.itertuples(index=False):
            src_id = f"{src_type}:{getattr(row, src_col)}"
            dst_id = f"{dst_type}:{getattr(row, dst_col)}"
            g.add_edge(
                src_id,
                dst_id,
                relationship_type=relationship,
                timestamp=getattr(row, "TransactionDT"),
                transaction_id=getattr(row, "TransactionID"),
            )

    return g


def node_type_counts(g: nx.MultiDiGraph) -> dict[str, int]:
    counts: dict[str, int] = {}
    for _, data in g.nodes(data=True):
        counts[data["node_type"]] = counts.get(data["node_type"], 0) + 1
    return counts


def edge_relationship_counts(g: nx.MultiDiGraph) -> dict[str, int]:
    counts: dict[str, int] = {}
    for _, _, data in g.edges(data=True):
        rel = data["relationship_type"]
        counts[rel] = counts.get(rel, 0) + 1
    return counts
