"""Phase 5C, Requirement 7 — illustrative false-positive cost model for
the coordinated-abuse (graph) detector.

**ILLUSTRATIVE COST MODEL — not Razorpay's real internal cost.** Reuses
the same ₹500 "analyst investigation + customer friction" unit cost
already used for the ML layer's false-positive cost
(`src/evaluation/cost.py::fit_cost_model`'s `false_positive_cost_inr`
default) for consistency across the project — restated here, not
imported, because the unit of analysis differs: the ML cost model
counts a false positive per TRANSACTION, while a graph false positive
here is one INVESTIGATION per flagged COMMUNITY (an analyst who opens a
case on a graph-flagged cluster investigates the cluster once, not once
per transaction inside it).

A false positive here is defined exactly as Track 02 Requirement 7
states: **legitimate shared infrastructure incorrectly flagged as
coordinated abuse** — i.e. a legitimate cluster (household/office/
campus/business) whose detected community also contains a ring member
(`src/graph/ring_recovery.py::evaluate_legitimate_false_positives`).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

ILLUSTRATIVE_FP_INVESTIGATION_COST_INR = 500.0


@dataclass(frozen=True)
class FalsePositiveCostResult:
    n_false_positive_clusters: int
    n_false_positive_transactions: int
    cost_per_investigation_inr: float
    total_illustrative_cost_inr: float


def compute_false_positive_cost(
    fp_results: list[dict],
    legitimate_clusters: list[dict],
    transactions: pd.DataFrame,
    cost_per_investigation_inr: float = ILLUSTRATIVE_FP_INVESTIGATION_COST_INR,
) -> FalsePositiveCostResult:
    """fp_results: output of `evaluate_legitimate_false_positives`.
    legitimate_clusters: the raw cluster records (for member customer_proxy_ids).
    transactions: the held-out benchmark's transaction table, used to count
    ACTUAL transaction rows for each false-positive cluster's members
    (a customer_proxy is not always exactly 1 transaction)."""
    fp_cluster_ids = {r["cluster_id"] for r in fp_results if r.get("false_positive")}
    n_fp_clusters = len(fp_cluster_ids)

    fp_member_ids: set[str] = set()
    for c in legitimate_clusters:
        if c["cluster_id"] in fp_cluster_ids:
            fp_member_ids.update(c["members"])
    n_fp_transactions = int(transactions["customer_proxy_id"].isin(fp_member_ids).sum())

    total_cost = n_fp_clusters * cost_per_investigation_inr
    return FalsePositiveCostResult(
        n_false_positive_clusters=n_fp_clusters,
        n_false_positive_transactions=n_fp_transactions,
        cost_per_investigation_inr=cost_per_investigation_inr,
        total_illustrative_cost_inr=round(total_cost, 2),
    )
