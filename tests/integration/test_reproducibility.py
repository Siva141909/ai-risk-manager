"""Phase 1K — reproducibility tests for the full generator pipeline.

Runs against a real (but small) slice of train_transaction.csv, since the
pipeline's behavior at realistic cardinalities is what actually matters —
toy fixtures alone wouldn't exercise the mega-cluster/proxy-resolution
paths meaningfully. Skips (does not fake) if the raw file is absent.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.generator.pipeline import run_generator
from src.graph.build_graph import build_graph

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
    return pd.read_csv(RAW, usecols=COLUMNS, nrows=5000)


@requires_dataset
def test_same_seed_produces_identical_transactions(sample_df):
    r1 = run_generator(sample_df, seed=42)
    r2 = run_generator(sample_df, seed=42)
    pd.testing.assert_frame_equal(r1.transactions, r2.transactions)


@requires_dataset
def test_same_seed_produces_identical_cluster_and_ring_records(sample_df):
    r1 = run_generator(sample_df, seed=42)
    r2 = run_generator(sample_df, seed=42)
    assert r1.legitimate_clusters == r2.legitimate_clusters
    assert r1.rings == r2.rings


@requires_dataset
def test_same_seed_produces_identical_graph_structure(sample_df):
    r1 = run_generator(sample_df, seed=42)
    r2 = run_generator(sample_df, seed=42)
    g1 = build_graph(r1.transactions)
    g2 = build_graph(r2.transactions)
    assert set(g1.nodes) == set(g2.nodes)
    assert g1.number_of_edges() == g2.number_of_edges()
    assert sorted(g1.edges(data="relationship_type")) == sorted(g2.edges(data="relationship_type"))


@requires_dataset
def test_different_seed_produces_different_synthetic_assignment(sample_df):
    r1 = run_generator(sample_df, seed=42)
    r2 = run_generator(sample_df, seed=99)
    assert not r1.transactions["device_synthetic_id"].equals(r2.transactions["device_synthetic_id"])
    assert not r1.transactions["ip_synthetic_id"].equals(r2.transactions["ip_synthetic_id"])


@requires_dataset
def test_different_seed_produces_different_ring_composition(sample_df):
    r1 = run_generator(sample_df, seed=42)
    r2 = run_generator(sample_df, seed=99)
    assert r1.rings != r2.rings


@requires_dataset
def test_real_columns_byte_identical_before_and_after_generation(sample_df):
    """The generator must never alter real IEEE-CIS columns — only add new ones."""
    real_cols = COLUMNS
    result = run_generator(sample_df, seed=42)
    pd.testing.assert_frame_equal(
        sample_df[real_cols].reset_index(drop=True),
        result.transactions[real_cols].reset_index(drop=True),
    )
