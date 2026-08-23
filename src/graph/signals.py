"""Phase 3G — interpretable graph risk signals.

Every signal is precisely defined below and computed deterministically
from the multi-attribute graph's detected communities — never a single
opaque "ring detected = true" flag. These become the evidence the future
investigation agent (Phase 4+) consumes; no LLM is involved in computing
them (Phase 3K).

**Real-time vs. retrospective (Phase 3L):** every signal here is
computed from the FULL graph (all transactions, all times) — this makes
every signal RETROSPECTIVE INVESTIGATION evidence, not a real-time
feature. A relationship discovered here may have been formed by a
transaction that happened AFTER the trigger transaction being
investigated. This is fine for case investigation (an analyst reviewing
a flagged case benefits from the complete picture) but these signals
must NEVER be fed back into the real-time ML feature matrix
(src/features/) as if they were known at transaction time — see
docs/CASE_MODEL.md for the explicit real-time/retrospective boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx
import pandas as pd

from src.graph.relationship_views import build_multi_attribute_graph
from src.graph.ring_recovery import detect_communities

GRAPH_FLAG_MIN_COMMUNITY_SIZE = 3  # matches the generator's own ring_size_min — a community smaller
                                     # than any configured ring type cannot structurally be one


@dataclass(frozen=True)
class CustomerGraphSignals:
    customer_proxy_id: str
    community_id: int | None
    community_size: int                       # "number of connected suspicious customers" (incl. self)
    n_shared_devices: int                      # distinct device_synthetic_id values this customer shares with >=1 other customer
    n_shared_ips: int                            # same, for IP
    n_shared_bank_accounts: int                   # same, for bank_account
    multi_attribute_overlap: bool                  # shares >1 relationship TYPE with at least one other customer
    relationship_rarity_score: float                # 1 / (avg n_sharing across this customer's shared entities) — higher = rarer, more suspicious
    temporal_concentration_hours: float | None         # (max - min TransactionDT) / 3600 across the customer's OWN transactions in this community; None if only 1 txn
    graph_flagged: bool                                  # deterministic: community_size >= GRAPH_FLAG_MIN_COMMUNITY_SIZE


def compute_customer_graph_signals(transactions: pd.DataFrame, weighting: str = "flat") -> pd.DataFrame:
    """One row per customer_proxy_id that appears in the multi-attribute
    graph (i.e., shares at least one of device/IP/bank_account with
    someone else) — customers who share nothing are absent (their signals
    would all be zero/None/False by definition, not usefully distinct rows).
    """
    g = build_multi_attribute_graph(transactions, weighting=weighting)
    node_to_comm = detect_communities(g, method="louvain")

    device_deg = _degree_by_relationship(transactions, "device_synthetic_id")
    ip_deg = _degree_by_relationship(transactions, "ip_synthetic_id")
    bank_deg = _degree_by_relationship(transactions, "bank_account_synthetic_id")

    comm_sizes: dict[int, int] = {}
    for comm_id in node_to_comm.values():
        comm_sizes[comm_id] = comm_sizes.get(comm_id, 0) + 1

    dt_by_customer = transactions.groupby("customer_proxy_id")["TransactionDT"].agg(["min", "max", "count"])

    rows = []
    for customer_id, comm_id in node_to_comm.items():
        n_dev = device_deg.get(customer_id, 0)
        n_ip = ip_deg.get(customer_id, 0)
        n_bank = bank_deg.get(customer_id, 0)
        n_types_shared = sum(1 for x in (n_dev, n_ip, n_bank) if x > 0)

        sharing_counts = [x for x in (n_dev, n_ip, n_bank) if x > 0]
        rarity = round(1.0 / (sum(sharing_counts) / len(sharing_counts)), 4) if sharing_counts else 0.0

        dt_row = dt_by_customer.loc[customer_id] if customer_id in dt_by_customer.index else None
        temporal_hours = (
            round(float(dt_row["max"] - dt_row["min"]) / 3600, 2)
            if dt_row is not None and dt_row["count"] > 1
            else None
        )

        community_size = comm_sizes[comm_id]
        rows.append(
            CustomerGraphSignals(
                customer_proxy_id=customer_id,
                community_id=comm_id,
                community_size=community_size,
                n_shared_devices=n_dev,
                n_shared_ips=n_ip,
                n_shared_bank_accounts=n_bank,
                multi_attribute_overlap=n_types_shared > 1,
                relationship_rarity_score=rarity,
                temporal_concentration_hours=temporal_hours,
                graph_flagged=community_size >= GRAPH_FLAG_MIN_COMMUNITY_SIZE,
            )
        )

    return pd.DataFrame([r.__dict__ for r in rows])


def _degree_by_relationship(transactions: pd.DataFrame, entity_col: str) -> dict[str, int]:
    """For each customer, how many OTHER customers they share entity_col
    with — 0 if their value is unique to them."""
    sub = transactions.dropna(subset=[entity_col, "customer_proxy_id"])
    group_sizes = sub.groupby(entity_col)["customer_proxy_id"].nunique()
    shared_values = set(group_sizes[group_sizes > 1].index)

    degree: dict[str, int] = {}
    for entity_value, group in sub[sub[entity_col].isin(shared_values)].groupby(entity_col):
        customers = group["customer_proxy_id"].unique()
        for c in customers:
            degree[c] = degree.get(c, 0) + 1
    return degree
