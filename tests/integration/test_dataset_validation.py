"""Integration tests for src/ingestion/validation.py against the real
IEEE-CIS files in data/raw/.

These tests read the actual raw CSVs (large files) and check real,
measured facts recorded in docs/DATASET_AUDIT.md — they do not construct
fake/fixture data to stand in for the real dataset. If the raw files are
not present, tests are skipped (not passed, not faked) with a clear
reason, consistent with Phase 0's "detect, don't fabricate" rule.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.ingestion.validation import (
    REQUIRED_FILES,
    check_identity_schemas_match_after_normalization,
    check_isfraud_only_in_train,
    check_no_id_overlap,
    check_transaction_dt_monotonic,
    check_transaction_id_unique,
    normalize_identity_columns,
    required_files_present,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

_all_present = all(required_files_present(RAW_DIR).values())

requires_dataset = pytest.mark.skipif(
    not _all_present,
    reason="IEEE-CIS raw files not present in data/raw/ — see docs/DATASET_ACQUISITION.md",
)


def test_required_files_present_reports_accurately():
    """Always runs: reports which files exist without assuming either way."""
    presence = required_files_present(RAW_DIR)
    assert set(presence.keys()) == set(REQUIRED_FILES)
    # This assertion only holds once the dataset has actually been acquired.
    if _all_present:
        assert all(presence.values())


@requires_dataset
def test_all_five_files_present():
    presence = required_files_present(RAW_DIR)
    assert all(presence.values()), presence


@requires_dataset
def test_train_transaction_id_unique():
    df = pd.read_csv(RAW_DIR / "train_transaction.csv", usecols=["TransactionID"])
    assert check_transaction_id_unique(df)


@requires_dataset
def test_test_transaction_id_unique():
    df = pd.read_csv(RAW_DIR / "test_transaction.csv", usecols=["TransactionID"])
    assert check_transaction_id_unique(df)


@requires_dataset
def test_no_transaction_id_overlap_between_train_and_test():
    train_df = pd.read_csv(RAW_DIR / "train_transaction.csv", usecols=["TransactionID"])
    test_df = pd.read_csv(RAW_DIR / "test_transaction.csv", usecols=["TransactionID"])
    assert check_no_id_overlap(train_df, test_df)


@requires_dataset
def test_isfraud_only_in_train():
    train_cols = pd.read_csv(RAW_DIR / "train_transaction.csv", nrows=0).columns
    test_cols = pd.read_csv(RAW_DIR / "test_transaction.csv", nrows=0).columns
    train_df = pd.DataFrame(columns=train_cols)
    test_df = pd.DataFrame(columns=test_cols)
    assert check_isfraud_only_in_train(train_df, test_df)


@requires_dataset
def test_identity_schemas_match_after_hyphen_normalization():
    train_id_cols = pd.read_csv(RAW_DIR / "train_identity.csv", nrows=0).columns
    test_id_cols = pd.read_csv(RAW_DIR / "test_identity.csv", nrows=0).columns
    train_id_df = pd.DataFrame(columns=train_id_cols)
    test_id_df = pd.DataFrame(columns=test_id_cols)
    assert check_identity_schemas_match_after_normalization(train_id_df, test_id_df)
    # And confirm they do NOT match without normalization (real, measured quirk).
    assert set(train_id_df.columns) != set(test_id_df.columns)


@requires_dataset
def test_normalize_identity_columns_strips_hyphens():
    df = pd.DataFrame(columns=["TransactionID", "id-01", "id-38", "DeviceType"])
    normalized = normalize_identity_columns(df)
    assert list(normalized.columns) == ["TransactionID", "id_01", "id_38", "DeviceType"]


@requires_dataset
def test_train_transaction_dt_monotonic_by_row_order():
    df = pd.read_csv(RAW_DIR / "train_transaction.csv", usecols=["TransactionDT"])
    assert check_transaction_dt_monotonic(df)


@requires_dataset
def test_measured_row_and_column_counts_match_audit():
    """Pins the exact dimensions recorded in docs/DATASET_AUDIT.md.

    This dataset is a static, immutable Kaggle competition download —
    these are not arbitrary/fragile numbers, they are the audited facts
    of the specific files this project uses. A change here means the
    raw files changed and the audit needs to be re-run.
    """
    train_txn = pd.read_csv(RAW_DIR / "train_transaction.csv", usecols=["TransactionID"])
    train_identity = pd.read_csv(RAW_DIR / "train_identity.csv", usecols=["TransactionID"])
    test_txn = pd.read_csv(RAW_DIR / "test_transaction.csv", usecols=["TransactionID"])
    test_identity = pd.read_csv(RAW_DIR / "test_identity.csv", usecols=["TransactionID"])
    sample_sub = pd.read_csv(RAW_DIR / "sample_submission.csv")

    assert len(train_txn) == 590_540
    assert len(train_identity) == 144_233
    assert len(test_txn) == 506_691
    assert len(test_identity) == 141_907
    assert len(sample_sub) == 506_691


@requires_dataset
def test_sample_submission_ids_match_test_transaction_ids():
    sample_sub = pd.read_csv(RAW_DIR / "sample_submission.csv")
    test_txn = pd.read_csv(RAW_DIR / "test_transaction.csv", usecols=["TransactionID"])
    assert set(sample_sub["TransactionID"]) == set(test_txn["TransactionID"])


@requires_dataset
def test_target_distribution_matches_audit():
    """Pins the measured fraud rate — real data, not a fabricated assumption."""
    train_txn = pd.read_csv(RAW_DIR / "train_transaction.csv", usecols=["isFraud"])
    counts = train_txn["isFraud"].value_counts().to_dict()
    assert counts[0] == 569_877
    assert counts[1] == 20_663
