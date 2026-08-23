"""Phase 1.5 regression guard: the corrected generation model must not
percolate into one giant connected component the way Phase 1's uniform
pooling did (docs/GRAPH_DATA_MODEL.md Finding 1). Runs against a real
data slice since percolation is a population-scale phenomenon a tiny
toy fixture wouldn't exercise meaningfully.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.generator.pipeline import run_generator
from src.graph.health import graph_health_report
from src.graph.relationship_views import build_relationship_graph

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW = PROJECT_ROOT / "data" / "raw" / "train_transaction.csv"

requires_dataset = pytest.mark.skipif(
    not RAW.exists(), reason="train_transaction.csv not present — see docs/DATASET_ACQUISITION.md"
)

COLUMNS = [
    "TransactionID", "isFraud", "TransactionDT", "TransactionAmt", "ProductCD",
    "card1", "card2", "card3", "card4", "card5", "card6", "addr1", "P_emaildomain",
]


@pytest.fixture(scope="module")
def sample_df():
    return pd.read_csv(RAW, usecols=COLUMNS, nrows=10_000)


@requires_dataset
def test_relationship_specific_graphs_do_not_percolate(sample_df):
    """No single-relationship-type customer graph should glue anywhere
    near all distinct customers into one component -- Phase 1's failure
    mode. Measured against the TOTAL distinct customer count (not the
    sharing-subgraph's own node count), because a single legitimate
    campus cluster (up to 60 members, by design) can legitimately be a
    large fraction of the small subgraph of "customers who share
    anything at all" without that being percolation -- the regression
    this guards against is thousands of UNRELATED customers collapsing
    together, not one deliberately-injected large legitimate cluster.
    """
    result = run_generator(sample_df, seed=42)
    n_total_customers = result.transactions["customer_proxy_id"].nunique()
    for rel in ("SHARED_DEVICE", "SHARED_IP", "SHARED_BANK_ACCOUNT"):
        g = build_relationship_graph(result.transactions, rel, weighting="flat")
        report = graph_health_report(g)
        largest_pct_of_all_customers = 100 * report["largest_component_size"] / n_total_customers
        assert largest_pct_of_all_customers < 5.0, (
            f"{rel} graph's largest component is {largest_pct_of_all_customers:.2f}% "
            "of ALL distinct customers -- percolation regression"
        )


@requires_dataset
def test_reproducibility_holds_under_corrected_model(sample_df):
    r1 = run_generator(sample_df, seed=42)
    r2 = run_generator(sample_df, seed=42)
    pd.testing.assert_frame_equal(r1.transactions, r2.transactions)
    assert r1.legitimate_clusters == r2.legitimate_clusters
    assert r1.rings == r2.rings


@requires_dataset
def test_different_seed_changes_neighborhood_assignment(sample_df):
    r1 = run_generator(sample_df, seed=42)
    r2 = run_generator(sample_df, seed=99)
    assert r1.legitimate_clusters != r2.legitimate_clusters
