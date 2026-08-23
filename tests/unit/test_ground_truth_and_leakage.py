"""Unit tests for src/generator/ground_truth.py (Phase 1G) and
src/features/leakage_guard.py (Phase 1H)."""

from __future__ import annotations

import pandas as pd
import pytest

from src.features.leakage_guard import (
    GROUND_TRUTH_COLUMNS,
    NON_FEATURE_COLUMNS,
    LeakageError,
    assert_no_leakage,
    filter_allowed_features,
)
from src.generator.ground_truth import consolidate_ground_truth


def _toy_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "isFraud": [0, 1, 0, 0],
            "synthetic_ring_id": [pd.NA, "RING-A-000", pd.NA, pd.NA],
            "synthetic_ring_role": [pd.NA, "core_member", pd.NA, "decoy_bystander"],
            "legitimate_cluster_id": [pd.NA, pd.NA, "LEGIT-HOUSEHOLD-000", pd.NA],
        }
    )


def test_original_isfraud_matches_isfraud_exactly():
    df = _toy_df()
    out = consolidate_ground_truth(df)
    assert (out["original_isFraud"] == out["isFraud"]).all()


def test_original_isfraud_is_a_copy_not_a_view():
    """Mutating isFraud afterward must not silently mutate original_isFraud."""
    df = _toy_df()
    out = consolidate_ground_truth(df)
    out.loc[0, "isFraud"] = 1
    assert out.loc[0, "original_isFraud"] == 0


def test_synthetic_entity_label_precedence_ring_over_legit():
    df = pd.DataFrame(
        {
            "isFraud": [0],
            "synthetic_ring_id": ["RING-A-000"],
            "synthetic_ring_role": ["core_member"],
            "legitimate_cluster_id": ["LEGIT-HOUSEHOLD-000"],  # should never co-occur in practice, but precedence must be well-defined
        }
    )
    out = consolidate_ground_truth(df)
    assert out["synthetic_entity_label"].iloc[0] == "ring_member"


def test_synthetic_entity_label_categories():
    df = _toy_df()
    out = consolidate_ground_truth(df)
    labels = out["synthetic_entity_label"].tolist()
    assert labels == ["normal", "ring_member", "legitimate_shared_infra", "decoy_bystander"]


def test_ground_truth_columns_denylisted_from_features():
    for col in GROUND_TRUTH_COLUMNS:
        assert col in NON_FEATURE_COLUMNS


def test_assert_no_leakage_raises_on_ground_truth_column():
    df = pd.DataFrame({"amount": [1, 2], "synthetic_ring_id": ["A", None]})
    with pytest.raises(LeakageError):
        assert_no_leakage(df)


def test_assert_no_leakage_raises_on_isfraud():
    df = pd.DataFrame({"amount": [1, 2], "isFraud": [0, 1]})
    with pytest.raises(LeakageError):
        assert_no_leakage(df)


def test_assert_no_leakage_passes_clean_feature_frame():
    df = pd.DataFrame({"amount": [1, 2], "hour_of_day": [3, 4]})
    assert_no_leakage(df)  # must not raise


def test_filter_allowed_features_strips_all_denylisted_columns():
    df = pd.DataFrame(
        {
            "amount": [1, 2],
            "isFraud": [0, 1],
            "TransactionID": [100, 101],
            "customer_proxy_id": ["A", "B"],
            "synthetic_ring_id": [None, "RING-A-000"],
            "synthetic_entity_label": ["normal", "ring_member"],
        }
    )
    filtered = filter_allowed_features(df)
    assert list(filtered.columns) == ["amount"]
    assert_no_leakage(filtered)  # must not raise after filtering
