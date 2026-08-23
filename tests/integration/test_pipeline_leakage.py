"""Phase 2M — pipeline-level leakage tests against real data.

Complements tests/unit/test_historical_features_leakage.py (which proves
the historical-feature MATH is leak-safe on a hand-crafted example) by
proving the same property holds when the FULL pipeline
(src/features/pipeline.py) runs on real transactions, and that the
temporal split it produces matches Phase 1A's standalone split exactly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.features.pipeline import RAW_TRANSACTION_COLUMNS, build_feature_matrix, get_split

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW = PROJECT_ROOT / "data" / "raw" / "train_transaction.csv"

requires_dataset = pytest.mark.skipif(
    not RAW.exists(), reason="train_transaction.csv not present — see docs/DATASET_ACQUISITION.md"
)


@pytest.fixture(scope="module")
def sample_df():
    df = pd.read_csv(RAW, usecols=RAW_TRANSACTION_COLUMNS, nrows=8000)
    return df.assign(DeviceType=None, has_identity_data=0)


@requires_dataset
def test_test_rows_never_appear_in_train_split(sample_df):
    artifact = build_feature_matrix(sample_df)
    X_train, _ = get_split(artifact, "train")
    X_test, _ = get_split(artifact, "test")
    train_ids = set(artifact.df.loc[X_train.index, "TransactionID"])
    test_ids = set(artifact.df.loc[X_test.index, "TransactionID"])
    assert train_ids.isdisjoint(test_ids)


@requires_dataset
def test_split_matches_standalone_phase_1a_split(sample_df):
    """The split computed inside the feature pipeline must be identical to
    src/ingestion/split.py's standalone result on the same data."""
    from src.ingestion.split import assign_split

    artifact = build_feature_matrix(sample_df)
    standalone_labels = assign_split(sample_df.sort_values("TransactionDT", kind="mergesort").reset_index(drop=True))
    pipeline_labels = artifact.df.sort_values("TransactionID")["split"].reset_index(drop=True)
    standalone_sorted = (
        sample_df.sort_values("TransactionDT", kind="mergesort")
        .assign(_split=standalone_labels.values)
        .sort_values("TransactionID")["_split"]
        .reset_index(drop=True)
    )
    assert (pipeline_labels.values == standalone_sorted.values).all()


@requires_dataset
def test_historical_features_leak_safe_on_real_pipeline_output(sample_df):
    """Truncate the real dataframe to an earlier time window and confirm
    early rows' historical features are byte-identical whether or not
    later rows exist — the same property tests/unit already proves on a
    toy example, now checked against the real pipeline end-to-end."""
    full_artifact = build_feature_matrix(sample_df)

    cutoff_dt = sample_df["TransactionDT"].quantile(0.5)
    truncated_df = sample_df[sample_df["TransactionDT"] <= cutoff_dt].reset_index(drop=True)
    truncated_artifact = build_feature_matrix(truncated_df)

    early_ids = truncated_df["TransactionID"]
    full_subset = full_artifact.df[full_artifact.df["TransactionID"].isin(early_ids)].set_index("TransactionID")
    truncated_subset = truncated_artifact.df.set_index("TransactionID")

    historical_cols = [c for c in full_artifact.feature_columns if c.startswith(("cust_", "card1_"))]
    for col in historical_cols:
        full_vals = full_subset.loc[early_ids, col]
        trunc_vals = truncated_subset.loc[early_ids, col]
        mismatches = ~(
            (full_vals.values == trunc_vals.values) | (pd.isna(full_vals.values) & pd.isna(trunc_vals.values))
        )
        assert not mismatches.any(), f"{col} differs when later rows are added — future leakage into a past row"


@requires_dataset
def test_reproducible_across_runs(sample_df):
    a1 = build_feature_matrix(sample_df)
    a2 = build_feature_matrix(sample_df)
    pd.testing.assert_frame_equal(a1.df, a2.df)
    assert a1.feature_columns == a2.feature_columns
