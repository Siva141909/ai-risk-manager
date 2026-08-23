"""Phase 3C/3D/3E — full-benchmark weighting comparison, ring detection
by abuse type, and hard-negative evaluation.

Runs ONLY on the 4 ring-detection views (device, IP, bank_account,
multi-attribute) — never the full heterogeneous graph (Phase 1.5
Decision 2, re-verified in scripts/graph_health_full.py). Tests 3
weighting strategies (flat, inverse_frequency, inverse_log_frequency —
the "simple rarity-based" variant Phase 3C asks for) x connected-components
and Louvain, and reports results by abuse type and by legitimate-cluster
type, with 95% Wilson confidence intervals given the small ring counts.

Per Decision 10/Phase 3C's instruction: run and report first, do not
tune parameters against these numbers afterward.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.graph.relationship_views import build_multi_attribute_graph, build_relationship_graph
from src.graph.ring_recovery import (
    detect_communities,
    evaluate_legitimate_false_positives,
    evaluate_ring_recovery,
    summarize_false_positives,
    summarize_false_positives_by_cluster_type,
    summarize_ring_recovery,
    summarize_ring_recovery_by_abuse_type,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FULL_DIR = PROJECT_ROOT / "data" / "synthetic" / "full"
OUT = FULL_DIR / "graph_benchmark_full_report.json"

VIEWS = {
    "DEVICE_ONLY": ("relationship", "SHARED_DEVICE"),
    "IP_ONLY": ("relationship", "SHARED_IP"),
    "BANK_ONLY": ("relationship", "SHARED_BANK_ACCOUNT"),
    "MULTI_ATTRIBUTE": ("multi", None),
}

WEIGHTING_STRATEGIES = ["flat", "inverse_frequency", "inverse_log_frequency"]


def build_view(transactions: pd.DataFrame, view_name: str, weighting: str):
    kind, rel = VIEWS[view_name]
    if kind == "relationship":
        return build_relationship_graph(transactions, rel, weighting=weighting)
    return build_multi_attribute_graph(transactions, weighting=weighting)


def main() -> None:
    transactions = pd.read_parquet(FULL_DIR / "transactions.parquet")
    with (FULL_DIR / "rings.json").open() as f:
        rings = json.load(f)
    with (FULL_DIR / "legitimate_clusters.json").open() as f:
        clusters = json.load(f)

    report: dict = {"views": {}}

    for view_name in VIEWS:
        report["views"][view_name] = {}
        for weighting in WEIGHTING_STRATEGIES:
            g = build_view(transactions, view_name, weighting)
            report["views"][view_name][weighting] = {}
            for method in ("connected_components", "louvain"):
                node_to_comm = detect_communities(g, method=method)
                ring_results = evaluate_ring_recovery(rings, node_to_comm)
                fp_results = evaluate_legitimate_false_positives(clusters, node_to_comm, rings)

                entry = {
                    "ring_recovery_overall": summarize_ring_recovery(ring_results),
                    "ring_recovery_by_abuse_type": summarize_ring_recovery_by_abuse_type(ring_results),
                    "ring_recovery_detail": ring_results,
                    "false_positive_overall": summarize_false_positives(fp_results),
                    "false_positive_by_cluster_type": summarize_false_positives_by_cluster_type(fp_results),
                    "false_positive_detail": fp_results,
                }
                report["views"][view_name][weighting][method] = entry

                rr = entry["ring_recovery_overall"]
                fp = entry["false_positive_overall"]
                print(
                    f"{view_name:16s} {weighting:22s} {method:22s} "
                    f"P={rr['mean_precision']} R={rr['mean_recall']} F1={rr['mean_f1']} "
                    f"missed={rr['n_missed']} partial={rr['n_partial']} full={rr['n_full']} "
                    f"FP_rate={fp['false_positive_rate']}"
                )

    with OUT.open("w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nFull report written to {OUT}")


if __name__ == "__main__":
    main()
