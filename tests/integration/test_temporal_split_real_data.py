"""Integration tests: the temporal split against the real train_transaction.csv.

Confirms the split algorithm behaves correctly on the actual file, and
that persisted metadata (data/processed/split_metadata.json) matches a
fresh recomputation. Skips (does not fake) if the raw file or the
persisted metadata are absent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.ingestion.split import assign_split, split_summary

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW = PROJECT_ROOT / "data" / "raw" / "train_transaction.csv"
METADATA = PROJECT_ROOT / "data" / "processed" / "split_metadata.json"

requires_dataset = pytest.mark.skipif(
    not RAW.exists(), reason="train_transaction.csv not present — see docs/DATASET_ACQUISITION.md"
)
requires_split_metadata = pytest.mark.skipif(
    not METADATA.exists(), reason="split_metadata.json not built — run scripts/build_temporal_split.py"
)


@pytest.fixture(scope="module")
def real_df():
    return pd.read_csv(RAW, usecols=["TransactionID", "TransactionDT", "isFraud"])


@requires_dataset
def test_split_covers_all_590540_rows_exactly_once(real_df):
    labels = assign_split(real_df)
    assert len(labels) == 590_540
    assert labels.isin(["train", "validation", "test"]).all()


@requires_dataset
def test_real_data_no_duplicate_transaction_id_across_splits(real_df):
    labels = assign_split(real_df)
    seen: set[int] = set()
    for split_name in ("train", "validation", "test"):
        ids = set(real_df.loc[labels == split_name, "TransactionID"])
        assert seen.isdisjoint(ids)
        seen |= ids
    assert seen == set(real_df["TransactionID"])


@requires_dataset
def test_real_data_no_temporal_overlap(real_df):
    labels = assign_split(real_df)
    train_max_dt = real_df.loc[labels == "train", "TransactionDT"].max()
    val_min_dt = real_df.loc[labels == "validation", "TransactionDT"].min()
    val_max_dt = real_df.loc[labels == "validation", "TransactionDT"].max()
    test_min_dt = real_df.loc[labels == "test", "TransactionDT"].min()
    assert train_max_dt <= val_min_dt
    assert val_max_dt <= test_min_dt


@requires_dataset
def test_real_data_split_reproducible_across_runs(real_df):
    labels_1 = assign_split(real_df)
    labels_2 = assign_split(real_df)
    pd.testing.assert_series_equal(labels_1, labels_2)


@requires_dataset
def test_real_data_split_row_counts_match_audit():
    """Pins the exact split sizes recorded in docs/DATASET_AUDIT.md Section 5."""
    df = pd.read_csv(RAW, usecols=["TransactionID", "TransactionDT", "isFraud"])
    labels = assign_split(df)
    summary = split_summary(df, labels)
    assert summary["train"]["row_count"] == 413_378
    assert summary["validation"]["row_count"] == 88_581
    assert summary["test"]["row_count"] == 88_581


@requires_dataset
@requires_split_metadata
def test_persisted_metadata_matches_fresh_recomputation(real_df):
    labels = assign_split(real_df)
    fresh_summary = split_summary(real_df, labels)

    with METADATA.open() as f:
        persisted = json.load(f)

    for split_name in ("train", "validation", "test"):
        assert persisted["summary"][split_name]["row_count"] == fresh_summary[split_name]["row_count"]
        assert persisted["summary"][split_name]["fraud_count"] == fresh_summary[split_name]["fraud_count"]
        assert persisted["summary"][split_name]["dt_min"] == fresh_summary[split_name]["dt_min"]
        assert persisted["summary"][split_name]["dt_max"] == fresh_summary[split_name]["dt_max"]
