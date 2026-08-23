"""Phase 3B — full-benchmark graph health diagnostics.

Runs on the 4 RING-DETECTION graph views only (device, IP, bank_account,
multi-attribute) — explicitly NOT the full heterogeneous graph, which
Phase 1.5 Decision 2 and the approved Phase 3 architecture both exclude
from detection topology. The full heterogeneous graph's node/edge counts
are recorded separately in generation_metadata.json (Phase 3A) purely as
context, never fed into ring detection.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.graph.health import graph_health_report
from src.graph.relationship_views import build_multi_attribute_graph, build_relationship_graph

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FULL_DIR = PROJECT_ROOT / "data" / "synthetic" / "full"
OUT = FULL_DIR / "graph_health_full.json"


def main() -> None:
    transactions = pd.read_parquet(FULL_DIR / "transactions.parquet")
    n_total_customers = transactions["customer_proxy_id"].nunique()

    report: dict = {"n_total_customers": int(n_total_customers), "views": {}}

    for rel in ("SHARED_DEVICE", "SHARED_IP", "SHARED_BANK_ACCOUNT"):
        g = build_relationship_graph(transactions, rel, weighting="flat")
        health = graph_health_report(g)
        health["largest_component_pct_of_all_customers"] = round(
            100 * health.get("largest_component_size", 0) / n_total_customers, 4
        )
        report["views"][rel] = health
        print(f"{rel}: nodes={health['node_count']} edges={health['edge_count']} "
              f"components={health['n_connected_components']} "
              f"largest={health['largest_component_size']} "
              f"({health['largest_component_pct_of_all_customers']}% of all customers) "
              f"avg_degree={health['average_degree']}")

    g_multi = build_multi_attribute_graph(transactions, weighting="flat")
    health_multi = graph_health_report(g_multi)
    health_multi["largest_component_pct_of_all_customers"] = round(
        100 * health_multi.get("largest_component_size", 0) / n_total_customers, 4
    )
    report["views"]["MULTI_ATTRIBUTE"] = health_multi
    print(f"MULTI_ATTRIBUTE: nodes={health_multi['node_count']} edges={health_multi['edge_count']} "
          f"components={health_multi['n_connected_components']} "
          f"largest={health_multi['largest_component_size']} "
          f"({health_multi['largest_component_pct_of_all_customers']}% of all customers) "
          f"avg_degree={health_multi['average_degree']}")

    report["explicit_verification"] = {
        "full_heterogeneous_graph_used_for_detection": False,
        "note": (
            "The full heterogeneous graph (src/graph/build_graph.py) is built only in "
            "scripts/generate_full_benchmark.py for node/edge-count context "
            "(generation_metadata.json). Ring detection (Phase 3D) and this health report "
            "use ONLY the 4 views above, built via src/graph/relationship_views.py, which "
            "excludes merchant_proxy, email_domain_proxy, and payment_instrument_proxy by "
            "construction — those types are not even columns build_relationship_graph reads."
        ),
    }

    with OUT.open("w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nWritten to {OUT}")


if __name__ == "__main__":
    main()
