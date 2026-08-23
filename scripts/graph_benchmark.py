"""Phase 1.5 — graph strategy comparison + ring recovery benchmark.

Compares 4 graph representations (Decision 3's "compare graph
strategies") against the dev dataset's injected rings and legitimate
clusters, using both connected-components and Louvain (Decision 9/10):

  A. Full heterogeneous graph (src/graph/build_graph.py) — includes hub
     entity types (merchant_proxy, email_domain_proxy,
     payment_instrument_proxy), kept as the baseline "what Phase 1 did."
  B. Relationship-specific graphs, flat weighting (device / ip / bank_account)
  C. Relationship-specific graphs, inverse-frequency weighting
  D. Multi-attribute combined graph (device+ip+bank_account), flat AND
     inverse-frequency weighting

Reports graph health (Decision 9) and ring-recovery precision/recall/F1
plus legitimate-cluster false-positive rate (Decision 10) for every
strategy, so the comparison is decided by evidence, not assumption.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.graph.build_graph import build_graph
from src.graph.health import graph_health_report
from src.graph.relationship_views import build_multi_attribute_graph, build_relationship_graph
from src.graph.ring_recovery import (
    detect_communities,
    evaluate_legitimate_false_positives,
    evaluate_ring_recovery,
    summarize_false_positives,
    summarize_ring_recovery,
)

DEV_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "dev"
OUT = DEV_DIR / "graph_benchmark_report.json"


def run_strategy(name: str, g, rings: list[dict], clusters: list[dict], customer_node_fn, methods=("connected_components", "louvain")) -> dict:
    result: dict = {"strategy": name, "health": graph_health_report(g)}
    for method in methods:
        node_to_comm = detect_communities(g, method=method)
        ring_results = evaluate_ring_recovery(rings, node_to_comm, customer_node_fn)
        fp_results = evaluate_legitimate_false_positives(clusters, node_to_comm, rings, customer_node_fn)
        result[method] = {
            "ring_recovery_summary": summarize_ring_recovery(ring_results),
            "ring_recovery_detail": ring_results,
            "false_positive_summary": summarize_false_positives(fp_results),
            "false_positive_detail": fp_results,
        }
    return result


def main() -> None:
    transactions = pd.read_csv(DEV_DIR / "transactions.csv")
    with (DEV_DIR / "rings.json").open() as f:
        rings = json.load(f)
    with (DEV_DIR / "legitimate_clusters.json").open() as f:
        clusters = json.load(f)

    strategies = []

    # A. Full heterogeneous graph (includes hub entities)
    g_full = build_graph(transactions)
    strategies.append(
        run_strategy("A_full_heterogeneous", g_full, rings, clusters, customer_node_fn=lambda c: f"customer_proxy:{c}")
    )

    # B. Relationship-specific graphs, flat weighting
    for rel in ("SHARED_DEVICE", "SHARED_IP", "SHARED_BANK_ACCOUNT"):
        g = build_relationship_graph(transactions, rel, weighting="flat")
        strategies.append(run_strategy(f"B_flat_{rel}", g, rings, clusters, customer_node_fn=lambda c: c))

    # C. Relationship-specific graphs, inverse-frequency weighting
    for rel in ("SHARED_DEVICE", "SHARED_IP", "SHARED_BANK_ACCOUNT"):
        g = build_relationship_graph(transactions, rel, weighting="inverse_frequency")
        strategies.append(run_strategy(f"C_invfreq_{rel}", g, rings, clusters, customer_node_fn=lambda c: c))

    # D. Multi-attribute combined graph — flat and inverse-frequency
    g_multi_flat = build_multi_attribute_graph(transactions, weighting="flat")
    strategies.append(run_strategy("D_multi_attr_flat", g_multi_flat, rings, clusters, customer_node_fn=lambda c: c))

    g_multi_invfreq = build_multi_attribute_graph(transactions, weighting="inverse_frequency")
    strategies.append(
        run_strategy("D_multi_attr_invfreq", g_multi_invfreq, rings, clusters, customer_node_fn=lambda c: c)
    )

    with OUT.open("w") as f:
        json.dump(strategies, f, indent=2, default=str)

    # concise console summary
    print(f"{'strategy':<28} {'method':<22} {'components':>10} {'largest%':>9} {'mean_P':>8} {'mean_R':>8} {'mean_F1':>8} {'FP_rate':>8}")
    for s in strategies:
        for method in ("connected_components", "louvain"):
            h = s["health"]
            rr = s[method]["ring_recovery_summary"]
            fp = s[method]["false_positive_summary"]
            print(
                f"{s['strategy']:<28} {method:<22} {h['n_connected_components']:>10} "
                f"{h['largest_component_pct']:>8.2f}% {rr['mean_precision'] or 0:>8.3f} "
                f"{rr['mean_recall'] or 0:>8.3f} {rr['mean_f1'] or 0:>8.3f} "
                f"{fp['false_positive_rate'] or 0:>8.3f}"
            )

    print(f"\nFull report written to {OUT}")


if __name__ == "__main__":
    main()
