"""Read-only IEEE-CIS raw-file validation.

Scope: schema/integrity checks only (Section 25's "Validation" stage) —
NOT ingestion, feature engineering, or the ML pipeline. Every function
here reads data/raw/*.csv and asserts facts about it; none of them
write, transform, or merge the raw files.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_FILES = [
    "train_transaction.csv",
    "train_identity.csv",
    "test_transaction.csv",
    "test_identity.csv",
    "sample_submission.csv",
]


def required_files_present(raw_dir: Path) -> dict[str, bool]:
    """Return {filename: exists} for every expected IEEE-CIS file."""
    return {name: (raw_dir / name).exists() for name in REQUIRED_FILES}


def check_transaction_id_unique(df: pd.DataFrame) -> bool:
    """True if TransactionID has no duplicates."""
    return df["TransactionID"].is_unique


def check_no_id_overlap(train_df: pd.DataFrame, test_df: pd.DataFrame) -> bool:
    """True if train and test TransactionID sets are disjoint."""
    return len(set(train_df["TransactionID"]) & set(test_df["TransactionID"])) == 0


def check_isfraud_only_in_train(train_df: pd.DataFrame, test_df: pd.DataFrame) -> bool:
    """True if isFraud exists in train and NOT in test (real, confirmed asymmetry)."""
    return "isFraud" in train_df.columns and "isFraud" not in test_df.columns


def normalize_identity_columns(identity_df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of an identity dataframe with '-' normalized to '_' in column names.

    Required because test_identity.csv uses 'id-01'..'id-38' while
    train_identity.csv uses 'id_01'..'id_38' for the identical fields
    (confirmed in docs/DATASET_AUDIT.md Section 10) — code that joins or
    unions train/test identity data must normalize this first.
    """
    return identity_df.rename(columns=lambda c: c.replace("-", "_"))


def check_identity_schemas_match_after_normalization(
    train_identity_df: pd.DataFrame, test_identity_df: pd.DataFrame
) -> bool:
    """True if train/test identity column sets match once '-' -> '_' is applied."""
    normalized_test = normalize_identity_columns(test_identity_df)
    return set(train_identity_df.columns) == set(normalized_test.columns)


def check_transaction_dt_monotonic(df: pd.DataFrame) -> bool:
    """True if TransactionDT is non-decreasing in row order (confirmed True for train)."""
    return df["TransactionDT"].is_monotonic_increasing
