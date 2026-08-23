"""Deterministic temporal train/validation/test split for train_transaction.csv.

Row-time-order split per docs/DATASET_AUDIT.md Section 5: stable-sort by
TransactionDT ascending (ties broken by original row order via mergesort),
then split by row position at 70%/15%/15% boundaries. This is a pure
function of the input dataframe — no random state and no persisted
per-row assignment is required for reproducibility; the same dataframe
always produces the same split.

Kaggle's test_transaction.csv is never involved here — it has no isFraud
label and cannot be used for any supervised evaluation (docs/DATASET_AUDIT.md
Section 5).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

TRAIN_FRAC = 0.70
VAL_FRAC = 0.15
# TEST_FRAC is implied: 1 - TRAIN_FRAC - VAL_FRAC = 0.15


@dataclass(frozen=True)
class SplitBoundaries:
    n_total: int
    n_train: int
    n_validation: int
    n_test: int
    dt_min: float
    dt_train_end: float       # last TransactionDT included in train
    dt_validation_end: float  # last TransactionDT included in validation
    dt_max: float


def compute_split_boundaries(
    df: pd.DataFrame, train_frac: float = TRAIN_FRAC, val_frac: float = VAL_FRAC
) -> SplitBoundaries:
    """Compute row-count and TransactionDT boundaries for the 3-way split."""
    if not 0 < train_frac < 1 or not 0 < val_frac < 1 or train_frac + val_frac >= 1:
        raise ValueError("train_frac and val_frac must be in (0,1) and sum to < 1")

    n = len(df)
    n_train = int(n * train_frac)
    n_validation = int(n * val_frac)
    n_test = n - n_train - n_validation

    sorted_dt = df["TransactionDT"].sort_values(kind="mergesort")
    return SplitBoundaries(
        n_total=n,
        n_train=n_train,
        n_validation=n_validation,
        n_test=n_test,
        dt_min=float(sorted_dt.iloc[0]),
        dt_train_end=float(sorted_dt.iloc[n_train - 1]),
        dt_validation_end=float(sorted_dt.iloc[n_train + n_validation - 1]),
        dt_max=float(sorted_dt.iloc[-1]),
    )


def assign_split(
    df: pd.DataFrame, train_frac: float = TRAIN_FRAC, val_frac: float = VAL_FRAC
) -> pd.Series:
    """Return a Series aligned to df.index with values 'train'/'validation'/'test'.

    Deterministic: stable-sorts by TransactionDT (mergesort — ties broken by
    original row order), then assigns the first n_train rows to 'train',
    the next n_validation rows to 'validation', and the remainder to 'test'.
    """
    boundaries = compute_split_boundaries(df, train_frac, val_frac)
    sorted_index = df["TransactionDT"].sort_values(kind="mergesort").index

    labels = pd.Series(index=df.index, dtype="object")
    labels.loc[sorted_index[: boundaries.n_train]] = "train"
    labels.loc[sorted_index[boundaries.n_train : boundaries.n_train + boundaries.n_validation]] = (
        "validation"
    )
    labels.loc[sorted_index[boundaries.n_train + boundaries.n_validation :]] = "test"
    return labels


def split_summary(df: pd.DataFrame, labels: pd.Series) -> dict:
    """Per-split row counts, DT ranges, fraud counts/rates — for reporting/persistence."""
    summary = {}
    for split_name in ("train", "validation", "test"):
        mask = labels == split_name
        sub = df.loc[mask]
        entry = {
            "row_count": int(mask.sum()),
            "dt_min": float(sub["TransactionDT"].min()),
            "dt_max": float(sub["TransactionDT"].max()),
        }
        if "isFraud" in sub.columns:
            entry["fraud_count"] = int(sub["isFraud"].sum())
            entry["fraud_rate_pct"] = float(sub["isFraud"].mean() * 100)
        summary[split_name] = entry
    return summary
