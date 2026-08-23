"""Unit tests for the temporal split algorithm (src/ingestion/split.py).

Uses small, explicitly-fabricated toy dataframes to test the algorithm's
correctness — this is testing split LOGIC, not asserting anything about
the real IEEE-CIS dataset (that's tests/integration/test_temporal_split_real_data.py).
"""

from __future__ import annotations

import pandas as pd

from src.ingestion.split import assign_split, compute_split_boundaries, split_summary


def _toy_df(n: int = 100) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "TransactionID": range(1000, 1000 + n),
            "TransactionDT": range(0, n * 100, 100),  # strictly increasing, evenly spaced
            "isFraud": [1 if i % 10 == 0 else 0 for i in range(n)],
        }
    )


def test_split_fractions_approximately_70_15_15():
    df = _toy_df(1000)
    boundaries = compute_split_boundaries(df)
    assert boundaries.n_train == 700
    assert boundaries.n_validation == 150
    assert boundaries.n_test == 150
    assert boundaries.n_train + boundaries.n_validation + boundaries.n_test == 1000


def test_assign_split_covers_every_row_exactly_once():
    df = _toy_df(537)  # not evenly divisible, exercises rounding
    labels = assign_split(df)
    assert len(labels) == len(df)
    assert labels.isin(["train", "validation", "test"]).all()
    assert labels.notna().all()


def test_no_duplicate_transaction_id_across_splits():
    df = _toy_df(300)
    labels = assign_split(df)
    seen = set()
    for split_name in ("train", "validation", "test"):
        ids = set(df.loc[labels == split_name, "TransactionID"])
        assert seen.isdisjoint(ids), f"TransactionID overlap involving {split_name}"
        seen |= ids
    assert seen == set(df["TransactionID"])


def test_no_temporal_overlap_train_before_validation_before_test():
    df = _toy_df(300)
    labels = assign_split(df)
    train_max_dt = df.loc[labels == "train", "TransactionDT"].max()
    val_min_dt = df.loc[labels == "validation", "TransactionDT"].min()
    val_max_dt = df.loc[labels == "validation", "TransactionDT"].max()
    test_min_dt = df.loc[labels == "test", "TransactionDT"].min()

    assert train_max_dt <= val_min_dt
    assert val_max_dt <= test_min_dt


def test_deterministic_reproducibility():
    df = _toy_df(521)
    labels_1 = assign_split(df)
    labels_2 = assign_split(df)
    pd.testing.assert_series_equal(labels_1, labels_2)


def test_ties_in_transaction_dt_broken_by_row_order():
    """Multiple rows can share the exact same TransactionDT (real data has this) —
    the split must still be a deterministic, well-defined partition."""
    df = pd.DataFrame(
        {
            "TransactionID": range(10),
            "TransactionDT": [0, 0, 0, 100, 100, 200, 200, 200, 300, 300],
            "isFraud": [0] * 10,
        }
    )
    labels_1 = assign_split(df, train_frac=0.5, val_frac=0.3)
    labels_2 = assign_split(df, train_frac=0.5, val_frac=0.3)
    pd.testing.assert_series_equal(labels_1, labels_2)
    assert labels_1.isin(["train", "validation", "test"]).all()


def test_split_summary_reports_row_counts_dt_ranges_and_fraud_stats():
    df = _toy_df(1000)
    labels = assign_split(df)
    summary = split_summary(df, labels)

    assert set(summary.keys()) == {"train", "validation", "test"}
    for split_name, entry in summary.items():
        assert entry["row_count"] > 0
        assert entry["dt_min"] <= entry["dt_max"]
        assert "fraud_count" in entry
        assert "fraud_rate_pct" in entry
    assert sum(e["row_count"] for e in summary.values()) == len(df)
